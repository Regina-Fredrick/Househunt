from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ListingForm, ListingImageFormSet


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
                return redirect('profile')
    else:
        form = ListingForm()
        formset = ListingImageFormSet()

    return render(request, 'listings/create_listing.html', {
        'form': form,
        'formset': formset,
    })
