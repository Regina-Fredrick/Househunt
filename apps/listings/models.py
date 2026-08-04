import io
from decimal import Decimal
from PIL import Image
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Avg
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

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES)
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.PROTECT)
    # Premium/gated data — only shown to users who have unlocked the listing (see UnlockLedger)
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
            # avg comes back as Decimal; 0.4 must also be Decimal or Python
            # raises TypeError when multiplying the two.
            if avg and self.price < (avg * Decimal('0.4')):
                reasons.append(
                    f"Price tripwire: KES {self.price} is under 40% of neighborhood average (KES {avg:.0f})"
                )

        self.flagged_reason = ' | '.join(reasons)

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


class UnlockLedger(models.Model):
    """
    Records a paywall unlock attempt/success. One row per (user, listing) —
    the unique_together constraint means a user is never charged twice for
    the same listing.

    Phase 1: rows were created directly by the unlock view (simulated payment,
    status always effectively 'completed' the moment the row existed).

    Phase 2: the flow is now asynchronous —
      1. unlock_listing_view creates a 'pending' row and triggers STK Push,
         storing checkout_request_id so the callback can find this row again.
      2. M-Pesa's callback (mpesa_callback_view) arrives later, looks up the
         row by checkout_request_id, and flips status to 'completed' or
         'failed' based on the result.
      3. is_unlocked (in listing_detail_view) only checks for status='completed'
         rows — a 'pending' or 'failed' row does NOT unlock gated content.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='unlocks')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='unlocks')
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=500)
    payment_method = models.CharField(
        max_length=20,
        choices=[('mpesa', 'M-Pesa'), ('ad_reward', 'Watched Ad')],
        default='mpesa',
    )
    payment_reference = models.CharField(max_length=100, blank=True)  # M-Pesa receipt number, filled in on success
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
    """
    Enterprise Landlord Hub — KYC verification for landlords/developers who
    want the enterprise/commercial tier (bulk import, featured placement,
    etc. — those come in later Phase 3 work; this model is just the
    verification record they're built on top of).

    One row per user. Resubmitting after a rejection resets status back to
    'pending' rather than creating a new row, so there's always a single
    current verification state per user, with rejection_reason preserved
    as history until the next submission overwrites it.
    """
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
        return f"{self.user.username} — {self.get_status_display()}"


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