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
      <h2 style={{ marginBottom: 20 }}>Browse Listings</h2>
      <div className="grid">
        {listings.map((listing) => (
          <Link key={listing.id} to={`/listings/${listing.id}`} className="card">
            {listing.images && listing.images[0] && (
              <img
                src={listing.images[0].image}
                alt={listing.title}
                className="card-img"
              />
            )}
            <div className="card-body">
              <h3 style={{ fontSize: '1rem', margin: '0 0 6px' }}>{listing.title}</h3>
              <p className="price-tag">KES {listing.price}</p>
              <p className="muted" style={{ fontSize: '0.85rem', margin: '6px 0 0' }}>
                {listing.neighborhood?.name}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}