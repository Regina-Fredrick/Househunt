import io
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from apps.accounts.models import User


class Neighborhood(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Listing(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('land', 'Land'),
        ('commercial', 'Commercial'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    LISTING_TYPE_CHOICES = [
        ('sale', 'Sale'),
        ('rent', 'Rent'),
    ]
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.PROTECT)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.PositiveIntegerField(default=0)
    rejection_reason = models.TextField(blank=True)

    def __str__(self):
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listings/')
    thumbnail = models.ImageField(upload_to='listings/thumbnails/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and not self.thumbnail:
            self._generate_thumbnail()

    def _generate_thumbnail(self):
        img = Image.open(self.image)
        img = img.convert('RGB')
        img.thumbnail((400, 400))

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        buffer.seek(0)

        thumb_name = f'thumb_{self.pk}.jpg'
        self.thumbnail.save(thumb_name, ContentFile(buffer.read()), save=False)
        super().save(update_fields=['thumbnail'])

    def __str__(self):
        return f"Image for {self.listing.title}"
