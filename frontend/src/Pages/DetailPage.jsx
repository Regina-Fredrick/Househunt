import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';

export default function DetailPage() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/listings/${id}/`)
      .then((res) => res.json())
      .then((data) => {
        setListing(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load listing', err);
        setLoading(false);
      });
  }, [id]);

  if (loading) return <p>Loading...</p>;
  if (!listing) return <p>Listing not found.</p>;

  return (
    <div>
      <Link to="/" style={{ display: 'inline-block', marginBottom: 16 }}>&larr; Back to listings</Link>

      <h2 style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{listing.title}</h2>
      <p style={{ color: '#8B92A5' }}>
        {listing.neighborhood?.name} &middot; {listing.views_count} views
      </p>

      {listing.images && listing.images.length > 0 && (
        <img
          src={listing.images[0].image}
          alt={listing.title}
          style={{ width: '100%', maxHeight: 400, objectFit: 'cover', borderRadius: 16, marginBottom: 20 }}
        />
      )}

      <p style={{
        display: 'inline-block',
        background: '#FFF4E8',
        color: '#F2994A',
        fontWeight: 700,
        padding: '6px 16px',
        borderRadius: 8,
        fontSize: '1.25rem',
      }}>
        KES {listing.price}
      </p>

      <p style={{ marginTop: 16 }}>
        {listing.bedrooms} bedrooms &middot; {listing.bathrooms} bathrooms &middot; {listing.property_type}
      </p>

      <hr />
      <h4>Description</h4>
      <p>{listing.description}</p>

      {!listing.is_unlocked && listing.pending_unlock !== undefined && (
        <div style={{
          background: '#F1EDFE',
          border: '1px solid #7C5CFC',
          borderRadius: 12,
          padding: 16,
          marginTop: 20,
        }}>
          <strong>This listing is locked.</strong>
          <p style={{ margin: '8px 0 0' }}>Unlock full photos and contact details for KES 500.</p>
        </div>
      )}

      {listing.is_unlocked && (
        <div style={{ marginTop: 20 }}>
          <p><strong>Owner:</strong> {listing.owner_username}</p>
          <p><strong>Phone:</strong> {listing.owner_phone}</p>
        </div>
      )}
    </div>
  );
}