from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django.utils import timezone
from django import forms
from .models import Neighborhood, Listing, ListingImage, UnlockLedger, LandlordVerification


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1


class RejectionReasonForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    reason = forms.CharField(widget=forms.Textarea, label='Reason for rejection')


def approve_listings(modeladmin, request, queryset):
    queryset.update(status='approved')
    for listing in queryset:
        if listing.owner.email:
            send_mail(
                subject='Your listing has been approved - HouseHunt',
                message=f'Hi {listing.owner.get_full_name() or listing.owner.username},\n\nYour listing "{listing.title}" has been approved and is now live on HouseHunt.\n\nThank you!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[listing.owner.email],
                fail_silently=True,
            )
approve_listings.short_description = 'Approve selected listings'


def reject_listings(modeladmin, request, queryset):
    form = None

    if 'apply' in request.POST:
        form = RejectionReasonForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            for listing in queryset:
                listing.status = 'rejected'
                listing.rejection_reason = reason
                listing.save()
                if listing.owner.email:
                    send_mail(
                        subject='Your listing was not approved - HouseHunt',
                        message=(
                            f'Hi {listing.owner.get_full_name() or listing.owner.username},\n\n'
                            f'Unfortunately your listing "{listing.title}" was not approved at this time.\n\n'
                            f'Reason: {reason}\n\n'
                            f'Please review our listing guidelines and resubmit.\n\nHouseHunt Team'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[listing.owner.email],
                        fail_silently=True,
                    )
            modeladmin.message_user(request, f'{queryset.count()} listing(s) rejected.')
            return None

    if not form:
        form = RejectionReasonForm(
            initial={'_selected_action': request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)}
        )

    return render(request, 'admin/reject_with_reason.html', {
        'listings': queryset,
        'form': form,
    })
reject_listings.short_description = 'Reject selected listings (with reason)'


def clear_flag(modeladmin, request, queryset):
    """
    Dismisses a fraud flag without touching the listing's approval status —
    distinct from approve/reject, since a moderator may decide a
    Category Cheat / Price Tripwire flag was a false positive on an
    otherwise-fine listing, or already-approved listing.

    Note: `_run_fraud_checks()` re-runs on every save() (see models.py), so
    if the listing is edited again later and still matches a fraud
    pattern, it will get re-flagged automatically — this action only
    clears the *current* flag, not the underlying pattern-matching.
    """
    updated = queryset.exclude(flagged_reason='').update(flagged_reason='')
    modeladmin.message_user(request, f'Cleared fraud flag on {updated} listing(s).')
clear_flag.short_description = 'Clear fraud flag (does not change approval status)'


class FlaggedFilter(admin.SimpleListFilter):
    """
    Django's list_filter can't filter directly on "non-empty text field",
    so this is a small custom filter giving moderators a one-click way to
    see only flagged listings — the core of the Safety & Fraud Audit desk.
    """
    title = 'fraud flag'
    parameter_name = 'flagged'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Flagged'),
            ('no', 'Not flagged'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.exclude(flagged_reason='')
        if self.value() == 'no':
            return queryset.filter(flagged_reason='')
        return queryset


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'is_flagged', 'property_type', 'neighborhood', 'price', 'created_at')
    list_filter = ('status', FlaggedFilter, 'property_type', 'listing_type', 'neighborhood')
    search_fields = ('title', 'owner__username', 'owner__email', 'flagged_reason')
    readonly_fields = ('created_at', 'views_count')
    actions = [approve_listings, reject_listings, clear_flag]
    inlines = [ListingImageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'neighborhood')

    @admin.display(description='Flag', boolean=True)
    def is_flagged(self, obj):
        return bool(obj.flagged_reason)


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(UnlockLedger)
class UnlockLedgerAdmin(admin.ModelAdmin):
    # Updated for Phase 2: status/checkout_request_id/completed_at/
    # failure_reason now exist since unlocks go through the real async
    # M-Pesa flow rather than being created synchronously as in Phase 1.
    list_display = ('user', 'listing', 'status', 'amount_paid', 'payment_reference', 'unlocked_at', 'completed_at')
    list_filter = ('status', 'unlocked_at')
    search_fields = ('user__username', 'listing__title', 'payment_reference', 'checkout_request_id')
    readonly_fields = ('unlocked_at', 'completed_at', 'checkout_request_id')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'listing')


def verify_landlords(modeladmin, request, queryset):
    updated = queryset.exclude(status='verified').update(
        status='verified', reviewed_at=timezone.now(), rejection_reason=''
    )
    modeladmin.message_user(request, f'Verified {updated} landlord(s).')
verify_landlords.short_description = 'Mark selected as verified'


def reject_landlords(modeladmin, request, queryset):
    """
    Same request.POST['apply'] two-step pattern as reject_listings — shows
    a reason form first, then applies it on confirmation.
    """
    form = None

    if 'apply' in request.POST:
        form = RejectionReasonForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            queryset.update(status='rejected', rejection_reason=reason, reviewed_at=timezone.now())
            modeladmin.message_user(request, f'{queryset.count()} landlord(s) rejected.')
            return None

    if not form:
        form = RejectionReasonForm(
            initial={'_selected_action': request.POST.getlist(admin.helpers.ACTION_CHECKBOX_NAME)}
        )

    return render(request, 'admin/reject_with_reason.html', {
        'listings': queryset,  # reusing the existing reject_with_reason.html template
        'form': form,
    })
reject_landlords.short_description = 'Reject selected (with reason)'


@admin.register(LandlordVerification)
class LandlordVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'business_name', 'registration_number', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__username', 'business_name', 'registration_number')
    readonly_fields = ('submitted_at',)
    actions = [verify_landlords, reject_landlords]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')