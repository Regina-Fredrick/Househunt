import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, getCsrfToken } from '../utils/api';

const STATUS_BADGE = {
  approved: 'badge-success',
  rejected: 'badge-danger',
  pending: 'badge-warning',
};

const STAT_COLORS = {
  total: 'var(--forest)',
  pending: 'var(--clay)',
  approved: 'var(--sage)',
  views: 'var(--brick)',
};

export default function MyListingsPage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  function loadListings() {
    return apiGet('/api/listings/mine/').then((data) => {
      setListings(data.results || data);
    });
  }

  useEffect(() => {
    loadListings()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id, title) {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/listings/${id}/delete/`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken },
      });
      if (!res.ok) throw new Error('Delete failed');
      setListings(listings.filter((l) => l.id !== id));
    } catch (err) {
      alert(err.message);
    }
  }

  if (loading) return <p>Loading your listings...</p>;
  if (error) return <div className="alert alert-error">{error}</div>;

  const total = listings.length;
  const pending = listings.filter((l) => l.status === 'pending').length;
  const approved = listings.filter((l) => l.status === 'approved').length;
  const totalViews = listings.reduce((sum, l) => sum + (l.views_count || 0), 0);

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>My Listings</h2>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 24 }}>
        <div className="card stat-card">
          <div className="stat-card-label">Total Listings</div>
          <div className="stat-card-value" style={{ color: STAT_COLORS.total }}>{total}</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-label">Pending</div>
          <div className="stat-card-value" style={{ color: STAT_COLORS.pending }}>{pending}</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-label">Approved</div>
          <div className="stat-card-value" style={{ color: STAT_COLORS.approved }}>{approved}</div>
        </div>
        <div className="card stat-card">
          <div className="stat-card-label">Total Views</div>
          <div className="stat-card-value" style={{ color: STAT_COLORS.views }}>{totalViews}</div>
        </div>
      </div>

      {listings.length === 0 ? (
        <p className="muted">You have no listings yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Price</th>
              <th>Status</th>
              <th>Views</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((listing) => (
              <tr key={listing.id}>
                <td><Link to={`/listings/${listing.id}`}>{listing.title}</Link></td>
                <td>KES {listing.price}</td>
                <td><span className={`badge ${STATUS_BADGE[listing.status]}`}>{listing.status}</span></td>
                <td>{listing.views_count}</td>
                <td>
                  <button onClick={() => navigate(`/listings/${listing.id}/edit`)} className="btn-outline btn-sm" style={{ marginRight: 8 }}>
                    Edit
                  </button>
                  <button onClick={() => handleDelete(listing.id, listing.title)} className="btn-outline-danger btn-sm">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}