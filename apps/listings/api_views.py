"""
apps/listings/api_views.py
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
import logging

from .models import Listing, Neighborhood, UnlockLedger, ListingImage
from .serializers import (
    ListingCardSerializer, ListingDetailSerializer, NeighborhoodSerializer,
    MyListingSerializer, ListingCreateSerializer, ListingImageUploadSerializer,
)
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