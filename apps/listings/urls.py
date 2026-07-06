from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_listing_view, name='create_listing'),
    path('mine/', views.my_listings_view, name='my_listings'),
    path('<int:pk>/edit/', views.edit_listing_view, name='edit_listing'),
    path('<int:pk>/delete/', views.delete_listing_view, name='delete_listing'),
]
