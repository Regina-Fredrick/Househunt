from django import forms
from django.forms import inlineformset_factory
from .models import Listing, ListingImage


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'price', 'property_type',
            'bedrooms', 'bathrooms', 'neighborhood', 'listing_type',
        ]

    def clean_price(self):
        price = self.cleaned_data['price']
        if price <= 0:
            raise forms.ValidationError('Price must be greater than 0.')
        return price


ListingImageFormSet = inlineformset_factory(
    Listing,
    ListingImage,
    fields=['image', 'order'],
    extra=5,
    max_num=5,
    can_delete=False,
)
