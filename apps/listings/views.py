import json
import logging
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import F, Sum, Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .forms import ListingForm, ListingImageFormSet, LandlordVerificationForm
from .filters import ListingFilter
from .models import Listing, ListingReport, UnlockLedger, LandlordVerification
from . import mpesa

logger = logging.getLogger(__name__)

@login_required
def create_listing_view(request):
    pending_count = Listing.objects.filter(
        owner=request.user,
        status='pending'
    ).count()

    if pending_count >= 5:
        messages.error(
            request,
            'You already have 5 listings under review. Please wait for them to be approved or rejected before submitting more.'
        )
        return redirect('my_listings')

    if request.method == 'POST':
        form = ListingForm(request.POST)
        formset = ListingImageFormSet(request.POST, request.FILES)

        if form.is_valid() and formset.is_valid():
            image_forms = [
                f for f in formset.forms
                if f.cleaned_data.get('image')
            ]
            if not image_forms:
                messages.error(request, 'Please upload at least one image.')
            else:
                listing = form.save(commit=False)
                listing.owner = request.user
                listing.status = 'pending'
                listing.save()

                for image_form in image_forms:
                    image = image_form.save(commit=False)
                    image.listing = listing
                    image.save()

                messages.success(request, 'Listing submitted for review.')
                return redirect('my_listings')
    else:
        form = ListingForm()
        formset = ListingImageFormSet()

    return render(request, 'listings/create_listing.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def my_listings_view(request):
    all_listings = Listing.objects.filter(owner=request.user)
    stats = {
        'total': all_listings.count(),
        'pending': all_listings.filter(status='pending').count(),
        'approved': all_listings.filter(status='approved').count(),
        'rejected': all_listings.filter(status='rejected').count(),
        'total_views': sum(l.views_count for l in all_listings),
    }

    listings = all_listings.select_related('neighborhood').prefetch_related('images').order_by('-created_at')
    paginator = Paginator(listings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'listings/my_listings.html', {
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
def edit_listing_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)

    if request.method == 'POST':
        form = ListingForm(request.POST, instance=listing)
        formset = ListingImageFormSet(request.POST, request.FILES, instance=listing)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Listing updated.')
            return redirect('my_listings')
    else:
        form = ListingForm(instance=listing)
        formset = ListingImageFormSet(instance=listing)

    return render(request, 'listings/edit_listing.html', {
        'form': form,
        'formset': formset,
        'listing': listing,
    })


@login_required
def delete_listing_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)

    if request.method == 'POST':
        listing.delete()
        messages.success(request, 'Listing deleted.')
        return redirect('my_listings')

    return render(request, 'listings/delete_confirm.html', {'listing': listing})


def browse_listings_view(request):
    queryset = Listing.objects.filter(status='approved').select_related('neighborhood', 'owner').prefetch_related('images').order_by('-created_at')
    listing_filter = ListingFilter(request.GET, queryset=queryset)

    paginator = Paginator(listing_filter.qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'listings/browse.html', {
        'page_obj': page_obj,
        'filter': listing_filter,
    })


def listing_detail_view(request, pk):
    listing = get_object_or_404(Listing.objects.select_related('neighborhood', 'owner').prefetch_related('images'), pk=pk, status='approved')

    Listing.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    listing.refresh_from_db()

    is_unlocked = False
    pending_unlock = False
    if request.user.is_authenticated:
        is_unlocked = UnlockLedger.objects.filter(
            user=request.user, listing=listing, status='completed'
        ).exists()
        if not is_unlocked:
            pending_unlock = UnlockLedger.objects.filter(
                user=request.user, listing=listing, status='pending'
            ).exists()

    return render(request, 'listings/detail.html', {
        'listing': listing,
        'is_unlocked': is_unlocked,
        'pending_unlock': pending_unlock,
        'unlock_price': 500,
    })


UNLOCK_PRICE = 500


@login_required
@require_POST
def unlock_listing_view(request, pk):
    """
    Triggers a real M-Pesa STK Push. Does NOT create a completed unlock here
    — that only happens once mpesa_callback_view receives and verifies the
    payment result. This view just:
      1. Creates/reuses a 'pending' UnlockLedger row for (user, listing)
      2. Calls Daraja to push the payment prompt to the user's phone
      3. Redirects back to the detail page, where JS polls unlock_status_view
    """
    listing = get_object_or_404(Listing, pk=pk, status='approved')

    already_unlocked = UnlockLedger.objects.filter(
        user=request.user, listing=listing, status='completed'
    ).exists()
    if already_unlocked:
        messages.info(request, 'You already unlocked this listing.')
        return redirect('listing_detail', pk=pk)

    phone_number = (request.user.phone_number or '').strip()
    # Normalize common Kenyan formats (0712345678, +254712345678) to
    # Daraja's required 2547XXXXXXXX with no leading 0 or +.
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]

    if not phone_number.startswith('254') or len(phone_number) != 12:
        messages.error(
            request,
            'Please add a valid M-Pesa phone number (e.g. 0712345678) to your profile before unlocking.'
        )
        return redirect('listing_detail', pk=pk)

    ledger, _ = UnlockLedger.objects.update_or_create(
        user=request.user,
        listing=listing,
        defaults={
            'amount_paid': UNLOCK_PRICE,
            'status': 'pending',
            'failure_reason': '',
        },
    )

    callback_url = f"{settings.MPESA_CALLBACK_BASE_URL}/listings/mpesa/callback/"

    try:
        response = mpesa.stk_push(
            phone_number=phone_number,
            amount=UNLOCK_PRICE,
            account_reference=str(listing.pk),
            transaction_desc=f"Unlock listing {listing.pk}",
            callback_url=callback_url,
        )
        ledger.checkout_request_id = response.get('CheckoutRequestID', '')
        ledger.save(update_fields=['checkout_request_id'])
        messages.success(request, 'Check your phone to complete the M-Pesa payment.')
    except mpesa.MpesaError as exc:
        logger.error("STK Push failed for listing %s, user %s: %s", listing.pk, request.user.pk, exc)
        ledger.status = 'failed'
        ledger.failure_reason = str(exc)[:255]
        ledger.save(update_fields=['status', 'failure_reason'])
        messages.error(request, 'Could not start the M-Pesa payment. Please try again.')

    return redirect('listing_detail', pk=pk)


@login_required
def unlock_status_view(request, pk):
    """
    Polled by JS on the detail page after an unlock attempt, since the
    actual payment confirmation arrives asynchronously via the M-Pesa
    callback, not in the same request that triggered the STK Push.
    """
    ledger = UnlockLedger.objects.filter(user=request.user, listing_id=pk).first()
    if not ledger:
        return JsonResponse({'status': 'none'})
    return JsonResponse({
        'status': ledger.status,
        'failure_reason': ledger.failure_reason,
    })


@csrf_exempt
@require_POST
def mpesa_callback_view(request):
    """
    Daraja POSTs the STK Push result here, asynchronously, once the user
    completes (or cancels/ignores) the payment prompt on their phone.

    IMPORTANT: always return HTTP 200 with {"ResultCode": 0, "ResultDesc":
    "Accepted"} regardless of what we found — Safaricom retries a
    non-200/unexpected response up to 3 times, then quarantines the app.
    Any internal error handling below must never let an exception escape
    without still returning this acknowledgement.
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        stk_callback = payload.get('Body', {}).get('stkCallback', {})
        checkout_request_id = stk_callback.get('CheckoutRequestID', '')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc', '')

        ledger = UnlockLedger.objects.filter(checkout_request_id=checkout_request_id).first()
        if not ledger:
            logger.warning("M-Pesa callback for unknown CheckoutRequestID: %s", checkout_request_id)
        else:
            if result_code == 0:
                items = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                metadata = {item.get('Name'): item.get('Value') for item in items}
                ledger.status = 'completed'
                ledger.payment_reference = str(metadata.get('MpesaReceiptNumber', ''))
                if metadata.get('Amount') is not None:
                    ledger.amount_paid = metadata['Amount']
                ledger.completed_at = timezone.now()
                ledger.save(update_fields=['status', 'payment_reference', 'amount_paid', 'completed_at'])
            else:
                ledger.status = 'failed'
                ledger.failure_reason = result_desc[:255]
                ledger.save(update_fields=['status', 'failure_reason'])
    except Exception:
        logger.exception("Error processing M-Pesa callback")

    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

@login_required
def report_listing_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, status='approved')

    if request.method == 'POST':
        reason = request.POST.get('reason')
        if reason in ('unavailable', 'scam'):
            _, created = ListingReport.objects.get_or_create(
                listing=listing,
                reporter=request.user,
                defaults={'reason': reason},
            )
            if created:
                listing.report_count = listing.reports.count()
                if listing.report_count >= 3:
                    listing.status = 'rejected'
                    listing.rejection_reason = 'Automatically unpublished after multiple user reports.'
                listing.save()
                messages.success(request, 'Thank you, your report has been submitted.')
            else:
                messages.info(request, 'You already reported this listing.')

    return redirect('listing_detail', pk=pk)

@staff_member_required
def revenue_dashboard_view(request):
    """
    Financial Controller desk — read-only revenue summary + chart.
    Staff-only (not a public or even a regular-user page). Refunds/reversals
    are NOT handled here yet — that needs a separate M-Pesa Reversal API
    integration, its own credentials, and its own review before wiring in,
    since it moves real money back out.
    """
    completed = UnlockLedger.objects.filter(status='completed')

    total_revenue = completed.aggregate(total=Sum('amount_paid'))['total'] or 0
    total_unlocks = completed.count()

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    revenue_today = completed.filter(completed_at__gte=today_start).aggregate(total=Sum('amount_paid'))['total'] or 0
    revenue_week = completed.filter(completed_at__gte=week_start).aggregate(total=Sum('amount_paid'))['total'] or 0
    revenue_month = completed.filter(completed_at__gte=month_start).aggregate(total=Sum('amount_paid'))['total'] or 0

    # Last 30 days, filled with zeros for days with no unlocks so the chart
    # doesn't just skip gaps and look misleadingly smooth.
    thirty_days_ago = today_start - timedelta(days=29)
    daily_qs = (
        completed.filter(completed_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('completed_at'))
        .values('day')
        .annotate(revenue=Sum('amount_paid'), count=Count('id'))
    )
    daily_map = {row['day']: row for row in daily_qs}

    chart_labels = []
    chart_data = []
    for i in range(30):
        day = (thirty_days_ago + timedelta(days=i)).date()
        chart_labels.append(day.strftime('%b %d'))
        chart_data.append(float(daily_map.get(day, {}).get('revenue') or 0))

    top_listings = (
        completed.values('listing__id', 'listing__title')
        .annotate(revenue=Sum('amount_paid'), unlocks=Count('id'))
        .order_by('-revenue')[:10]
    )

    pending_count = UnlockLedger.objects.filter(status='pending').count()
    failed_count = UnlockLedger.objects.filter(status='failed').count()

    return render(request, 'listings/revenue_dashboard.html', {
        'total_revenue': total_revenue,
        'total_unlocks': total_unlocks,
        'revenue_today': revenue_today,
        'revenue_week': revenue_week,
        'revenue_month': revenue_month,
        'pending_count': pending_count,
        'failed_count': failed_count,
        'chart_labels': json.dumps(chart_labels),
        'chart_data': json.dumps(chart_data),
        'top_listings': top_listings,
    })


@login_required
def submit_kyc_view(request):
    """
    Enterprise Landlord Hub — self-service KYC submission. Any logged-in
    user can submit; nothing downstream (bulk import, featured placement,
    B2B tier) is gated on status='verified' yet — that gating is future
    work once those features themselves exist. This view is just the
    submission + resubmission mechanism.
    """
    verification, _ = LandlordVerification.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = LandlordVerificationForm(request.POST, request.FILES, instance=verification)
        if form.is_valid():
            verification = form.save(commit=False)
            # Any edit/resubmission resets status to pending for re-review,
            # even if it was previously verified or rejected.
            verification.status = 'pending'
            verification.reviewed_at = None
            verification.save()
            messages.success(request, 'Verification submitted. We\'ll review it shortly.')
            return redirect('submit_kyc')
    else:
        form = LandlordVerificationForm(instance=verification)

    return render(request, 'listings/submit_kyc.html', {
        'form': form,
        'verification': verification,
    })