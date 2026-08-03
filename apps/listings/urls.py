from django.urls import path
from . import views
from .views import (
    create_listing_view,
    my_listings_view,
    edit_listing_view,
    delete_listing_view,
    browse_listings_view,
    listing_detail_view,
    report_listing_view,
    unlock_listing_view,
)

urlpatterns = [
    path('', views.browse_listings_view, name='browse_listings'),
    path('create/', views.create_listing_view, name='create_listing'),
    path('mine/', views.my_listings_view, name='my_listings'),
    path('<int:pk>/', views.listing_detail_view, name='listing_detail'),
    path('<int:pk>/edit/', views.edit_listing_view, name='edit_listing'),
    path('<int:pk>/delete/', views.delete_listing_view, name='delete_listing'),
    path('<int:pk>/unlock/', views.unlock_listing_view, name='unlock_listing'),
    path('<int:pk>/unlock/status/', views.unlock_status_view, name='unlock_status'),
    path('mpesa/callback/', views.mpesa_callback_view, name='mpesa_callback'),
]
