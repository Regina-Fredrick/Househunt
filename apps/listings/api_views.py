"""
apps/listings/api_views.py
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
import logging

from .models import Listing, Neighborhood, UnlockLedger, ListingImage
from .serializers import (
    ListingCardSerializer, ListingDetailSerializer, NeighborhoodSerializer,
    MyListingSerializer, ListingCreateSerializer, ListingImageUploadSerializer,
    ListingEditSerializer, AdminListingSerializer,
    TourRequestSerializer, TourRequestCreateSerializer,
)
from .models import TourRequest
from .filters import ListingFilter
from . import mpesa

logger = logging.getLogger(__name__)


class NeighborhoodListAPIView(generics.ListAPIView):
    queryset = Neighborhood.objects.filter(is_active=True).order_by('name')
    serializer_class = NeighborhoodSerializer
    permission_classes = [permissions.AllowAny]


class ListingBrowseAPIView(generics.ListAPIView):
    serializer_class = ListingCardSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ListingFilter

    def get_queryset(self):
        return Listing.objects.filter(status='approved').select_related(
            'neighborhood', 'owner'
        ).prefetch_related('images').order_by('-created_at')


class ListingDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ListingDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Listing.objects.filter(status='approved').select_related(
        'neighborhood', 'owner'
    ).prefetch_related('images')

    def get_object(self):
        obj = super().get_object()
        Listing.objects.filter(pk=obj.pk).update(views_count=obj.views_count + 1)
        obj.refresh_from_db()
        return obj


class MyListingsAPIView(generics.ListAPIView):
    serializer_class = MyListingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Listing.objects.filter(owner=self.request.user).select_related(
            'neighborhood'
        ).prefetch_related('images').order_by('-created_at')


class CreateListingAPIView(generics.CreateAPIView):
    serializer_class = ListingCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        pending_count = Listing.objects.filter(owner=request.user, status='pending').count()
        if pending_count >= 5:
            return Response(
                {'detail': 'You already have 5 listings under review. Please wait for them to be approved or rejected before submitting more.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.save(owner=request.user, status='pending')
        return Response(MyListingSerializer(listing, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_listing_image_api_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)

    if listing.images.count() >= 5:
        return Response({'detail': 'Maximum 5 images per listing.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ListingImageUploadSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(listing=listing, order=listing.images.count())
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unlock_listing_api_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, status='approved')

    already_unlocked = UnlockLedger.objects.filter(
        user=request.user, listing=listing, status='completed'
    ).exists()
    if already_unlocked:
        return Response({'detail': 'Already unlocked.'}, status=status.HTTP_200_OK)

    phone_number = (request.user.phone_number or '').strip()
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]

    if not phone_number.startswith('254') or len(phone_number) != 12:
        return Response(
            {'detail': 'Add a valid M-Pesa phone number to your profile before unlocking.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ledger, _ = UnlockLedger.objects.update_or_create(
        user=request.user, listing=listing,
        defaults={'amount_paid': 500, 'status': 'pending', 'failure_reason': ''},
    )
    callback_url = f"{settings.MPESA_CALLBACK_BASE_URL}/listings/mpesa/callback/"

    try:
        response = mpesa.stk_push(
            phone_number=phone_number,
            amount=500,
            account_reference=str(listing.pk),
            transaction_desc=f"Unlock listing {listing.pk}",
            callback_url=callback_url,
        )
        ledger.checkout_request_id = response.get('CheckoutRequestID', '')
        ledger.save(update_fields=['checkout_request_id'])
        return Response({'detail': 'Check your phone to complete the M-Pesa payment.'})
    except mpesa.MpesaError as exc:
        logger.error("STK Push failed for listing %s, user %s: %s", listing.pk, request.user.pk, exc)
        ledger.status = 'failed'
        ledger.failure_reason = str(exc)[:255]
        ledger.save(update_fields=['status', 'failure_reason'])
        return Response({'detail': 'Could not start the M-Pesa payment.'}, status=status.HTTP_502_BAD_GATEWAY)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unlock_status_api_view(request, pk):
    ledger = UnlockLedger.objects.filter(user=request.user, listing_id=pk).first()
    if not ledger:
        return Response({'status': 'none'})
    return Response({'status': ledger.status, 'failure_reason': ledger.failure_reason})
class EditListingAPIView(generics.UpdateAPIView):
    serializer_class = ListingEditSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Listing.objects.filter(owner=self.request.user)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        listing = self.get_object()
        return Response(MyListingSerializer(listing, context={'request': request}).data)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_listing_api_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    listing.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)   
class AdminModerationQueueAPIView(generics.ListAPIView):
    """Pending listings and/or flagged listings, for admin review."""
    serializer_class = AdminListingSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        from django.db.models import Q
        return Listing.objects.filter(
            Q(status='pending') | ~Q(flagged_reason='')
        ).select_related('neighborhood', 'owner').order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_approve_listing_api_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.status = 'approved'
    listing.save()
    if listing.owner.email:
        from django.core.mail import send_mail
        send_mail(
            'Your listing has been approved - HouseHunt',
            f'Hi {listing.owner.username},\n\nYour listing "{listing.title}" has been approved and is now live.',
            settings.DEFAULT_FROM_EMAIL,
            [listing.owner.email],
            fail_silently=True,
        )
    return Response(AdminListingSerializer(listing).data)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def admin_reject_listing_api_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    reason = request.data.get('reason', '')
    listing.status = 'rejected'
    listing.rejection_reason = reason
    listing.save()
    if listing.owner.email:
        from django.core.mail import send_mail
        send_mail(
            'Your listing was not approved - HouseHunt',
            f'Hi {listing.owner.username},\n\nYour listing "{listing.title}" was not approved.\n\nReason: {reason}',
            settings.DEFAULT_FROM_EMAIL,
            [listing.owner.email],
            fail_silently=True,
        )
    return Response(AdminListingSerializer(listing).data)  
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def unlock_with_ad_api_view(request, pk):
    """
    Grants free access after the user watches a rewarded ad on the
    frontend. The frontend only calls this from Google's reward-earned
    callback, so by the time this endpoint runs, the ad has already
    been confirmed watched client-side. amount_paid=0 distinguishes
    this from a real M-Pesa transaction in the ledger/revenue reports.
    """
    listing = get_object_or_404(Listing, pk=pk, status='approved')

    ledger, _ = UnlockLedger.objects.update_or_create(
        user=request.user, listing=listing,
        defaults={
            'amount_paid': 0,
            'payment_method': 'ad_reward',
            'status': 'completed',
            'completed_at': timezone.now(),
        },
    )
class CreateTourRequestAPIView(generics.CreateAPIView):
    serializer_class = TourRequestCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tour_request = serializer.save(requester=request.user)
        return Response(TourRequestSerializer(tour_request).data, status=status.HTTP_201_CREATED)


class MyTourRequestsAPIView(generics.ListAPIView):
    """Bookings the logged-in user has requested as a buyer."""
    serializer_class = TourRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TourRequest.objects.filter(requester=self.request.user).select_related('listing')


class IncomingTourRequestsAPIView(generics.ListAPIView):
    """Bookings requested on listings the logged-in user owns."""
    serializer_class = TourRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TourRequest.objects.filter(listing__owner=self.request.user).select_related('listing', 'requester')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_tour_request_status_api_view(request, pk):
    tour_request = get_object_or_404(TourRequest, pk=pk, listing__owner=request.user)
    new_status = request.data.get('status')
    if new_status not in ('confirmed', 'cancelled', 'completed'):
        return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)
    tour_request.status = new_status
    tour_request.save()
    return Response(TourRequestSerializer(tour_request).data)  
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def neighborhood_report_api_view(request, neighborhood_id):
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas
    from django.db.models import Avg, Min, Max, Count

    neighborhood = get_object_or_404(Neighborhood, pk=neighborhood_id)
    listings = Listing.objects.filter(neighborhood=neighborhood, status='approved')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{neighborhood.name}_report.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 3 * cm

    p.setFont('Helvetica-Bold', 20)
    p.drawString(2 * cm, y, f"Neighborhood Intelligence Report")
    y -= 1 * cm
    p.setFont('Helvetica-Bold', 16)
    p.drawString(2 * cm, y, neighborhood.name)
    y -= 1.5 * cm

    p.setFont('Helvetica', 10)
    p.drawString(2 * cm, y, f"Generated by Househunt \u2014 based on active listings on the platform.")
    y -= 1.5 * cm

    total_listings = listings.count()
    p.setFont('Helvetica-Bold', 13)
    p.drawString(2 * cm, y, f"Active Listings: {total_listings}")
    y -= 1 * cm

    if total_listings == 0:
        p.setFont('Helvetica', 11)
        p.drawString(2 * cm, y, "Not enough data yet for this neighborhood.")
    else:
        for listing_type, label in [('rent', 'For Rent'), ('sale', 'For Sale')]:
            subset = listings.filter(listing_type=listing_type)
            if not subset.exists():
                continue
            stats = subset.aggregate(avg=Avg('price'), lo=Min('price'), hi=Max('price'), n=Count('id'))
            p.setFont('Helvetica-Bold', 12)
            p.drawString(2 * cm, y, label)
            y -= 0.7 * cm
            p.setFont('Helvetica', 10)
            p.drawString(2.5 * cm, y, f"Listings: {stats['n']}")
            y -= 0.6 * cm
            p.drawString(2.5 * cm, y, f"Average price: KES {stats['avg']:.0f}")
            y -= 0.6 * cm
            p.drawString(2.5 * cm, y, f"Price range: KES {stats['lo']:.0f} - KES {stats['hi']:.0f}")
            y -= 1 * cm

        p.setFont('Helvetica-Bold', 12)
        p.drawString(2 * cm, y, "By Property Type")
        y -= 0.7 * cm
        p.setFont('Helvetica', 10)
        for prop_type, prop_label in Listing.PROPERTY_TYPE_CHOICES:
            subset = listings.filter(property_type=prop_type)
            count = subset.count()
            if count == 0:
                continue
            avg = subset.aggregate(avg=Avg('price'))['avg']
            p.drawString(2.5 * cm, y, f"{prop_label}: {count} listing(s), avg KES {avg:.0f}")
            y -= 0.6 * cm

    p.showPage()
    p.save()
    return response
