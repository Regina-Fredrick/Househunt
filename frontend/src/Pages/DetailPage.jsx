import { useEffect, useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { apiGet, apiPost } from '../utils/api';
import RequestTourModal from './RequestTourModal';
import ListingMap from './ListingMap';
export default function DetailPage() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [loading, setLoading] = useState(true);
  const [unlocking, setUnlocking] = useState(false);
  const [unlockMessage, setUnlockMessage] = useState('');
  const [unlockError, setUnlockError] = useState('');
  const [showTourForm, setShowTourForm] = useState(false);
  const [tourRequested, setTourRequested] = useState(false);
  const pollRef = useRef(null);
  function loadListing() {
    return apiGet(`/api/listings/${id}/`).then(setListing);
  }

  useEffect(() => {
    loadListing().finally(() => setLoading(false));
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [id]);

  async function handleUnlock() {
    setUnlockError('');
    setUnlocking(true);
    try {
      const res = await apiPost(`/api/listings/${id}/unlock/`, {});
      setUnlockMessage(res.detail || 'Check your phone to complete the M-Pesa payment.');

      pollRef.current = setInterval(async () => {
        try {
          const statusRes = await apiGet(`/api/listings/${id}/unlock/status/`);
          if (statusRes.status === 'completed') {
            clearInterval(pollRef.current);
            setUnlocking(false);
            setUnlockMessage('Payment confirmed! Unlocking listing...');
            await loadListing();
          } else if (statusRes.status === 'failed') {
            clearInterval(pollRef.current);
            setUnlocking(false);
            setUnlockError(statusRes.failure_reason || 'Payment failed. Please try again.');
          }
        } catch (err) {
          clearInterval(pollRef.current);
          setUnlocking(false);
        }
      }, 3000);
    } catch (err) {
      setUnlockError(err.message);
      setUnlocking(false);
    }
  }

  if (loading) return <p>Loading...</p>;
  if (!listing) return <p>Listing not found.</p>;

  return (
    <div>
      <Link to="/" className="nav-link" style={{ display: 'inline-block', marginBottom: 16 }}>
        &larr; Back to listings
      </Link>

      <h2>{listing.title}</h2>
      <p className="muted">
        {listing.neighborhood?.name} &middot; {listing.views_count} views
      </p>

      {listing.images && listing.images.length > 0 && (
        <img
          src={listing.images[0].image}
          alt={listing.title}
          style={{ width: '100%', maxHeight: 400, objectFit: 'cover', borderRadius: 16, marginBottom: 20 }}
        />
      )}

      <p className="price-tag price-tag-lg">KES {listing.price}</p>

      <p style={{ marginTop: 16 }}>
        {listing.bedrooms} bedrooms &middot; {listing.bathrooms} bathrooms &middot; {listing.property_type}
      </p>

      <hr />
      <h4>Description</h4>
      <p>{listing.description}</p>

      {!listing.is_unlocked && (
        <div className="lock-box">
          <strong>This listing is locked.</strong>
          <p style={{ margin: '8px 0 0' }}>Unlock full photos and contact details for KES 300.</p>

          {unlockError && (
            <p style={{ color: '#E05263', marginTop: 8 }}>{unlockError}</p>
          )}
          {unlockMessage && !unlockError && (
            <p style={{ color: '#7C5CFC', marginTop: 8 }}>{unlockMessage}</p>
          )}

          <button
            className="btn btn-primary"
            style={{ marginTop: 12 }}
            onClick={handleUnlock}
            disabled={unlocking}
          >
            {unlocking ? 'Waiting for payment...' : 'Unlock for KES 300'}
          </button>
        </div>
      )}

{listing.is_unlocked && (
        <div style={{ marginTop: 20 }}>
          <p><strong>Owner:</strong> {listing.owner_username}</p>
          <p><strong>Phone:</strong> {listing.owner_phone}</p>
          {listing.street_address && <p><strong>Address:</strong> {listing.street_address}</p>}
          <ListingMap latitude={listing.latitude} longitude={listing.longitude} title={listing.title} />
        </div>
      )}
      {!showTourForm && !tourRequested && (
        <button className="btn btn-primary" style={{ marginTop: 20 }} onClick={() => setShowTourForm(true)}>
          Request a Tour
        </button>
      )}

      {tourRequested && (
        <div className="alert alert-success" style={{ marginTop: 20 }}>
          Tour request sent! The owner will confirm shortly.
        </div>
      )}

{showTourForm && (
        <RequestTourModal
          listingId={listing.id}
          onClose={() => setShowTourForm(false)}
          onSuccess={() => {
            setShowTourForm(false);
            setTourRequested(true);
          }}
        />
      )}

      {listing.similar_listings && listing.similar_listings.length > 0 && (
        <div style={{ marginTop: 40 }}>
          <h4 style={{ marginBottom: 16 }}>Similar Listings</h4>
          <div className="grid">
            {listing.similar_listings.map((s) => (
              <Link key={s.id} to={`/listings/${s.id}`} className="card">
                {s.hero_image && (
                  <img src={s.hero_image} alt={s.title} className="card-img" />
                )}
                <div className="card-body">
                  <h5 style={{ fontSize: '0.95rem', margin: '0 0 6px' }}>{s.title}</h5>
                  <p className="price-tag">KES {s.price}</p>
                  <p className="muted" style={{ fontSize: '0.85rem', margin: '6px 0 0' }}>
                    {s.neighborhood?.name}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}