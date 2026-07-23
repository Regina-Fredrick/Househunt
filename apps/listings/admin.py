from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django import forms
from .models import Neighborhood, Listing, ListingImage


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


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'property_type', 'neighborhood', 'price', 'created_at')
    list_filter = ('status', 'property_type', 'listing_type', 'neighborhood')
    search_fields = ('title', 'owner__username', 'owner__email')
    readonly_fields = ('created_at', 'views_count')
    actions = [approve_listings, reject_listings]
    inlines = [ListingImageInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner', 'neighborhood')


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)