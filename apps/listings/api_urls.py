"""
apps/listings/api_urls.py — new file.

Wire this into config/urls.py with:
    path('api/listings/', include('apps.listings.api_urls')),

This runs ALONGSIDE the existing path('listings/', include('apps.listings.urls'))
— the old template-based site keeps working at /listings/... while the new
JSON API lives at /api/listings/... . Nothing needs to be removed yet; this
lets you build/test the React frontend incrementally without breaking the
current working site.
"""
from django.urls import path
from . import api_views

urlpatterns = [
    path('neighborhoods/', api_views.NeighborhoodListAPIView.as_view(), name='api_neighborhoods'),
    path('mine/', api_views.MyListingsAPIView.as_view(), name='api_my_listings'),
    path('', api_views.ListingBrowseAPIView.as_view(), name='api_listing_browse'),
    path('<int:pk>/', api_views.ListingDetailAPIView.as_view(), name='api_listing_detail'),
    path('<int:pk>/unlock/', api_views.unlock_listing_api_view, name='api_unlock_listing'),
    path('<int:pk>/unlock/status/', api_views.unlock_status_api_view, name='api_unlock_status'),
    path('create/', api_views.CreateListingAPIView.as_view(), name='api_create_listing'),
    path('<int:pk>/upload-image/', api_views.upload_listing_image_api_view, name='api_upload_image'),
    path('<int:pk>/edit/', api_views.EditListingAPIView.as_view(), name='api_edit_listing'),
    path('<int:pk>/delete/', api_views.delete_listing_api_view, name='api_delete_listing'),
]