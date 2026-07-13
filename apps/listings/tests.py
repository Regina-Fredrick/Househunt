from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import User
from .models import Neighborhood, Listing


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
