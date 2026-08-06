import hashlib
import io
from decimal import Decimal
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Avg
from django.utils import timezone
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
    SINGLE_UNIT_TYPES = ('apartment', 'house')
    COMPLEX_PHRASES = ['full complex', 'gated community', 'block of flats', 'entire building', 'multiple units']
    NEW_ACCOUNT_DAYS = 3
    HIGH_VALUE_THRESHOLD = Decimal('500000')

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.PROTECT)
    street_address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.PositiveIntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    flagged_reason = models.TextField(blank=True)
    report_count = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        self._run_fraud_checks()
        super().save(*args, **kwargs)

    def _run_fraud_checks(self):
        reasons = []

        if self.property_type in self.SINGLE_UNIT_TYPES:
            desc_lower = (self.description or '').lower()
            for phrase in self.COMPLEX_PHRASES:
                if phrase in desc_lower:
                    reasons.append(
                        f"Category mismatch: description mentions '{phrase}' but listed as {self.get_property_type_display()}"
                    )
                    break

        if self.price and self.neighborhood_id and self.property_type and self.listing_type:
            others = Listing.objects.filter(
                neighborhood_id=self.neighborhood_id,
                property_type=self.property_type,
                listing_type=self.listing_type,
                status='approved',
            ).exclude(pk=self.pk)
            avg = others.aggregate(avg_price=Avg('price'))['avg_price']
            if avg and self.price < (avg * Decimal('0.4')):
                reasons.append(
                    f"Price tripwire: KES {self.price} is under 40% of neighborhood average (KES {avg:.0f})"
                )

        if self.owner_id:
            shared_phone_listings = Listing.objects.filter(
                owner__phone_number=self.owner.phone_number
            ).exclude(owner_id=self.owner_id).exclude(pk=self.pk)
            if self.owner.phone_number and shared_phone_listings.exists():
                reasons.append(
                    "Shared contact: this phone number is also used by another account posting listings"
                )

            account_age_days = (timezone.now() - self.owner.date_joined).days
            if account_age_days < self.NEW_ACCOUNT_DAYS and self.price and self.price > self.HIGH_VALUE_THRESHOLD:
                reasons.append(
                    f"New account + high value: account is {account_age_days} day(s) old, listing priced at KES {self.price}"
                )

        self.flagged_reason = ' | '.join(reasons)

    def __str__(self):
        return self.title


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='listings/')
    thumbnail = models.ImageField(upload_to='listings/thumbnails/', blank=True, null=True)
    image_hash = models.CharField(max_length=64, blank=True, db_index=True)
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and self.image:
            self.image_hash = self._compute_hash()
        super().save(*args, **kwargs)
        if self.image and not self.thumbnail:
            self._generate_thumbnail()
        if is_new and self.image_hash:
            self._check_duplicate()

    def _compute_hash(self):
        self.image.seek(0)
        digest = hashlib.md5(self.image.read()).hexdigest()
        self.image.seek(0)
        return digest

    def _check_duplicate(self):
        duplicate = ListingImage.objects.filter(
            image_hash=self.image_hash
        ).exclude(listing_id=self.listing_id).exists()
        if duplicate:
            existing = self.listing.flagged_reason
            note = "Duplicate image: this photo appears on another listing"
            if note not in existing:
                combined = f"{existing} | {note}" if existing else note
                Listing.objects.filter(pk=self.listing_id).update(flagged_reason=combined)

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


class UnlockLedger(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocks')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='unlocks')
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    payment_method = models.CharField(
        max_length=20,
        choices=[('mpesa', 'M-Pesa'), ('ad_reward', 'Watched Ad')],
        default='mpesa',
    )
    payment_reference = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.CharField(max_length=255, blank=True)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'listing')

    def __str__(self):
        return f"{self.user.username} / {self.listing.title} ({self.status})"


class LandlordVerification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='landlord_verification')
    business_name = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(
        max_length=100, blank=True,
        help_text="KRA PIN or business registration number"
    )
    id_document = models.FileField(upload_to='kyc_documents/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"


class ListingReport(models.Model):
    REASON_CHOICES = [
        ('unavailable', 'Unavailable'),
        ('scam', 'Scam'),
    ]
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('listing', 'reporter')

    def __str__(self):
        return f"{self.reporter.username} reported {self.listing.title} ({self.reason})"


class TourRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='tour_requests')
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tour_requests')
    requested_date = models.DateField()
    requested_time = models.TimeField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requester.username} -> {self.listing.title} ({self.status})"