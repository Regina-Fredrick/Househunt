from django import forms
from django.forms import inlineformset_factory
from .models import Listing, ListingImage, LandlordVerification


class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'price', 'property_type',
            'bedrooms', 'bathrooms', 'neighborhood', 'listing_type',
            'street_address', 'latitude', 'longitude',
        ]
        widgets = {
            'street_address': forms.TextInput(attrs={
                'placeholder': 'e.g. 14 Riverside Drive, off Chiromo Rd',
            }),
            'latitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'e.g. -1.268813'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'placeholder': 'e.g. 36.803434'}),
        }
        help_texts = {
            'street_address': 'Only shown to buyers after they unlock the listing.',
            'latitude': 'Optional — powers the map pin once unlocked.',
            'longitude': 'Optional — powers the map pin once unlocked.',
        }

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


class LandlordVerificationForm(forms.ModelForm):
    class Meta:
        model = LandlordVerification
        fields = ['business_name', 'registration_number', 'id_document']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Riverside Properties Ltd',
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'KRA PIN or business reg. number',
            }),
            'id_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }