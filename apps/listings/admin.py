from django.contrib import admin
from .models import Neighborhood, Listing, ListingImage

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1
 
@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'property_type', 'neighborhood', 'price')
    list_filter = ('status', 'property_type', 'listing_type')
    inlines = [ListingImageInline]

@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)

