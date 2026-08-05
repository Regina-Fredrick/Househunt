"""
apps/listings/serializers.py

Key difference from the old template-based approach: gated fields
(interior images, street_address, latitude, longitude) are only included
in the JSON at all when the requesting user has actually unlocked the
listing. Unlike the CSS-blur approach in Phase 1/2, an unauthorized user's
browser never receives this data in the first place — there's nothing to
"unblur" via dev tools.
"""
from decimal import Decimal
from rest_framework import serializers
from .models import Listing, ListingImage, Neighborhood, UnlockLedger, TourRequest


class NeighborhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighborhood
        fields = ['id', 'name']


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'thumbnail', 'order']


class ListingCardSerializer(serializers.ModelSerializer):
    """Used for browse/list views — lighter payload, hero image only."""
    neighborhood = NeighborhoodSerializer(read_only=True)
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'price', 'property_type', 'listing_type',
            'bedrooms', 'bathrooms', 'neighborhood', 'hero_image', 'views_count',
        ]

    def get_hero_image(self, obj):
        first = obj.images.order_by('order').first()
        if not first:
            return None
        request = self.context.get('request')
        url = first.thumbnail.url if first.thumbnail else first.image.url
        return request.build_absolute_uri(url) if request else url


class ListingDetailSerializer(serializers.ModelSerializer):
    """
    Used for the detail view. is_unlocked, images, street_address,
    latitude, and longitude are all computed based on the requesting user —
    this is where the actual paywall enforcement happens now, server-side,
    not just in the template.
    """
    neighborhood = NeighborhoodSerializer(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    owner_phone = serializers.CharField(source='owner.phone_number', read_only=True)
    images = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()
    pending_unlock = serializers.SerializerMethodField()
    street_address = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    similar_listings = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'price', 'property_type', 'listing_type',
            'bedrooms', 'bathrooms', 'neighborhood', 'owner_username', 'owner_phone',
            'views_count', 'created_at', 'images', 'is_unlocked', 'pending_unlock',
            'street_address', 'latitude', 'longitude', 'similar_listings',
        ]

    def get_similar_listings(self, obj):
        from django.db.models import Q
        request = self.context.get('request')
        price_min = obj.price * Decimal('0.7')
        price_max = obj.price * Decimal('1.3')

        similar = Listing.objects.filter(
            Q(neighborhood_id=obj.neighborhood_id) | Q(property_type=obj.property_type)
        ).filter(
            status='approved',
            price__gte=price_min,
            price__lte=price_max,
        ).exclude(pk=obj.pk).select_related('neighborhood').prefetch_related('images')[:4]

        return ListingCardSerializer(similar, many=True, context={'request': request}).data
    def _is_unlocked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if not hasattr(obj, '_is_unlocked_cache'):
            obj._is_unlocked_cache = UnlockLedger.objects.filter(
                user=request.user, listing=obj, status='completed'
            ).exists()
        return obj._is_unlocked_cache

    def get_is_unlocked(self, obj):
        return self._is_unlocked(obj)

    def get_pending_unlock(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if self._is_unlocked(obj):
            return False
        return UnlockLedger.objects.filter(
            user=request.user, listing=obj, status='pending'
        ).exists()

    def get_images(self, obj):
        request = self.context.get('request')
        all_images = obj.images.order_by('order')
        hero = all_images.first()
        result = []
        if hero:
            url = request.build_absolute_uri(hero.image.url) if request else hero.image.url
            result.append({'id': hero.id, 'image': url, 'order': hero.order})

        if self._is_unlocked(obj):
            for img in all_images[1:]:
                url = request.build_absolute_uri(img.image.url) if request else img.image.url
                result.append({'id': img.id, 'image': url, 'order': img.order})

        return result

    def get_street_address(self, obj):
        return obj.street_address if self._is_unlocked(obj) else None

    def get_latitude(self, obj):
        return obj.latitude if self._is_unlocked(obj) else None

    def get_longitude(self, obj):
        return obj.longitude if self._is_unlocked(obj) else None


class MyListingSerializer(serializers.ModelSerializer):
    neighborhood = NeighborhoodSerializer(read_only=True)
    hero_image = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'price', 'status', 'property_type', 'listing_type',
            'bedrooms', 'bathrooms', 'neighborhood', 'hero_image', 'views_count',
            'created_at',
        ]

    def get_hero_image(self, obj):
        first = obj.images.order_by('order').first()
        if not first:
            return None
        request = self.context.get('request')
        url = first.thumbnail.url if first.thumbnail else first.image.url
        return request.build_absolute_uri(url) if request else url
class ListingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'price', 'property_type', 'listing_type',
            'bedrooms', 'bathrooms', 'neighborhood',
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than 0.')
        return value


class ListingImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'order']   
class ListingEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'price', 'property_type', 'listing_type',
            'bedrooms', 'bathrooms', 'neighborhood',
        ]

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError('Price must be greater than 0.')
        return value 
class AdminListingSerializer(serializers.ModelSerializer):
    neighborhood = NeighborhoodSerializer(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'price', 'status', 'flagged_reason', 'report_count',
            'property_type', 'neighborhood', 'owner_username', 'created_at',
        ]  
class TourRequestSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    requester_username = serializers.CharField(source='requester.username', read_only=True)

    class Meta:
        model = TourRequest
        fields = [
            'id', 'listing', 'listing_title', 'requester_username',
            'requested_date', 'requested_time', 'message', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class TourRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TourRequest
        fields = ['listing', 'requested_date', 'requested_time', 'message']     