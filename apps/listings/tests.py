import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from .models import Neighborhood, Listing, ListingImage, UnlockLedger


class StatusWorkflowTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testagent',
            password='testpass123',
            email='agent@test.com'
        )
        self.neighborhood = Neighborhood.objects.create(name='Kilimani')

    def _make_listing(self, status):
        return Listing.objects.create(
            owner=self.user,
            title=f'{status} listing',
            description='Test description',
            price=50000,
            property_type='apartment',
            neighborhood=self.neighborhood,
            status=status,
            listing_type='rent',
        )

    def test_pending_listing_not_in_browse(self):
        self._make_listing('pending')
        response = self.client.get(reverse('browse_listings'))
        self.assertNotContains(response, 'pending listing')

    def test_rejected_listing_not_in_browse(self):
        self._make_listing('rejected')
        response = self.client.get(reverse('browse_listings'))
        self.assertNotContains(response, 'rejected listing')

    def test_approved_listing_appears_in_browse(self):
        self._make_listing('approved')
        response = self.client.get(reverse('browse_listings'))
        self.assertContains(response, 'approved listing')

    def test_pending_listing_detail_returns_404(self):
        listing = self._make_listing('pending')
        response = self.client.get(reverse('listing_detail', args=[listing.pk]))
        self.assertEqual(response.status_code, 404)

    def test_rate_limit_blocks_sixth_pending_listing(self):
        for i in range(5):
            self._make_listing('pending')
        self.client.login(username='testagent', password='testpass123')
        response = self.client.get(reverse('create_listing'))
        self.assertRedirects(response, reverse('my_listings'))


def _generate_test_image_file(name='test.jpg'):
    """Small in-memory JPEG so ListingImage's ImageField has something real
    to save/thumbnail during tests, without needing a fixture file on disk."""
    img = Image.new('RGB', (100, 100), color='blue')
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/jpeg')


class PaywallTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username='owneragent',
            password='testpass123',
            email='owner@test.com'
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            password='testpass123',
            email='buyer@test.com'
        )
        self.neighborhood = Neighborhood.objects.create(name='Kilimani')
        self.listing = Listing.objects.create(
            owner=self.owner,
            title='Two bedroom apartment',
            description='Test description',
            price=50000,
            property_type='apartment',
            neighborhood=self.neighborhood,
            status='approved',
            listing_type='rent',
        )
        # Two images: first is the always-free "hero" shot (order=0), second
        # is gated interior content — the paywall only has something to gate
        # when there's more than one image.
        ListingImage.objects.create(listing=self.listing, image=_generate_test_image_file('hero.jpg'), order=0)
        ListingImage.objects.create(listing=self.listing, image=_generate_test_image_file('interior.jpg'), order=1)

    def test_anonymous_user_sees_locked_detail_page(self):
        response = self.client.get(reverse('listing_detail', args=[self.listing.pk]))
        self.assertFalse(response.context['is_unlocked'])

    def test_logged_in_user_without_unlock_is_locked(self):
        self.client.login(username='buyer', password='testpass123')
        response = self.client.get(reverse('listing_detail', args=[self.listing.pk]))
        self.assertFalse(response.context['is_unlocked'])

    def test_unlocking_creates_ledger_row(self):
        self.client.login(username='buyer', password='testpass123')
        self.client.post(reverse('unlock_listing', args=[self.listing.pk]))
        self.assertTrue(
            UnlockLedger.objects.filter(user=self.buyer, listing=self.listing).exists()
        )

    def test_unlocked_user_sees_unlocked_flag(self):
        self.client.login(username='buyer', password='testpass123')
        UnlockLedger.objects.create(user=self.buyer, listing=self.listing, amount_paid=500)
        response = self.client.get(reverse('listing_detail', args=[self.listing.pk]))
        self.assertTrue(response.context['is_unlocked'])

    def test_double_unlock_does_not_create_duplicate_ledger_row(self):
        self.client.login(username='buyer', password='testpass123')
        self.client.post(reverse('unlock_listing', args=[self.listing.pk]))
        self.client.post(reverse('unlock_listing', args=[self.listing.pk]))
        self.assertEqual(
            UnlockLedger.objects.filter(user=self.buyer, listing=self.listing).count(), 1
        )

    def test_unlock_requires_login(self):
        response = self.client.post(reverse('unlock_listing', args=[self.listing.pk]))
        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(
            UnlockLedger.objects.filter(listing=self.listing).exists()
        )

    def test_cannot_unlock_non_approved_listing(self):
        pending_listing = Listing.objects.create(
            owner=self.owner,
            title='Pending listing',
            description='Test description',
            price=40000,
            property_type='apartment',
            neighborhood=self.neighborhood,
            status='pending',
            listing_type='rent',
        )
        self.client.login(username='buyer', password='testpass123')
        response = self.client.post(reverse('unlock_listing', args=[pending_listing.pk]))
        self.assertEqual(response.status_code, 404)