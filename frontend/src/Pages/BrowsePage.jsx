import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

export default function BrowsePage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/listings/')
      .then((res) => res.json())
      .then((data) => {
        setListings(data.results || data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load listings', err);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading listings...</p>;

  if (listings.length === 0) return <p>No listings found.</p>;

  return (
    <div>
      <h2 style={{ fontFamily: 'Space Grotesk, sans-serif', marginBottom: 20 }}>
        Browse Listings
      </h2>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
        gap: 20,
      }}>
        {listings.map((listing) => (
          <Link
            key={listing.id}
            to={`/listings/${listing.id}`}
            style={{
              textDecoration: 'none',
              color: 'inherit',
              background: 'white',
              borderRadius: 16,
              overflow: 'hidden',
              boxShadow: '0 2px 12px rgba(26,29,41,0.06)',
              display: 'block',
            }}
          >
            {listing.images && listing.images[0] && (
              <img
                src={listing.images[0].image}
                alt={listing.title}
                style={{ width: '100%', height: 160, objectFit: 'cover' }}
              />
            )}
            <div style={{ padding: 14 }}>
              <h3 style={{ fontSize: '1rem', margin: '0 0 6px' }}>{listing.title}</h3>
              <p style={{
                display: 'inline-block',
                background: '#FFF4E8',
                color: '#F2994A',
                fontWeight: 700,
                padding: '3px 10px',
                borderRadius: 8,
                fontSize: '0.9rem',
              }}>
                KES {listing.price}
              </p>
              <p style={{ color: '#8B92A5', fontSize: '0.85rem', margin: '6px 0 0' }}>
                {listing.neighborhood?.name}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}