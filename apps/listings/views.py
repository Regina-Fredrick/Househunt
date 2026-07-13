from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import F
from .forms import ListingForm, ListingImageFormSet
from .filters import ListingFilter
from .models import Listing


@login_required
def create_listing_view(request):
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
    listings = Listing.objects.filter(owner=request.user).order_by('-created_at')
    paginator = Paginator(listings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'listings/my_listings.html', {'page_obj': page_obj})


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
    queryset = Listing.objects.filter(status='approved').order_by('-created_at')
    listing_filter = ListingFilter(request.GET, queryset=queryset)

    paginator = Paginator(listing_filter.qs, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'listings/browse.html', {
        'page_obj': page_obj,
        'filter': listing_filter,
    })


def listing_detail_view(request, pk):
    listing = get_object_or_404(Listing, pk=pk, status='approved')

    Listing.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    listing.refresh_from_db()

    return render(request, 'listings/detail.html', {'listing': listing})
