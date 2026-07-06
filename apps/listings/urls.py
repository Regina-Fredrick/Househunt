from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_listing_view, name='create_listing'),
]
