import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { apiGet, getCsrfToken } from '../utils/api';

const STATUS_STYLES = {
  approved: { background: '#E6FBF8', color: '#1AA89A' },
  rejected: { background: '#FDECEE', color: '#E05263' },
  pending: { background: '#FFF4E8', color: '#F2994A' },
};

function StatCard({ label, value, color }) {
  return (
    <div className="card" style={{ padding: 16, cursor: 'default' }}>
      <div className="muted" style={{ fontSize: '0.85rem' }}>{label}</div>
      <div style={{ fontSize: '1.8rem', fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

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
  if (error) return <p style={{ color: '#E05263' }}>{error}</p>;

  const total = listings.length;
  const pending = listings.filter((l) => l.status === 'pending').length;
  const approved = listings.filter((l) => l.status === 'approved').length;
  const totalViews = listings.reduce((sum, l) => sum + (l.views_count || 0), 0);

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>My Listings</h2>

      <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', marginBottom: 24 }}>
        <StatCard label="Total Listings" value={total} color="#7C5CFC" />
        <StatCard label="Pending" value={pending} color="#F2994A" />
        <StatCard label="Approved" value={approved} color="#1AA89A" />
        <StatCard label="Total Views" value={totalViews} color="#5B8DEF" />
      </div>

      {listings.length === 0 ? (
        <p className="muted">You have no listings yet.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #EDEEF2' }}>
              <th style={{ padding: 8 }}>Title</th>
              <th style={{ padding: 8 }}>Price</th>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8 }}>Views</th>
              <th style={{ padding: 8 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((listing) => (
              <tr key={listing.id} style={{ borderBottom: '1px solid #F2F3F5' }}>
                <td style={{ padding: 8 }}>
                  <Link to={`/listings/${listing.id}`}>{listing.title}</Link>
                </td>
                <td style={{ padding: 8 }}>KES {listing.price}</td>
                <td style={{ padding: 8 }}>
                  <span style={{
                    ...STATUS_STYLES[listing.status],
                    padding: '3px 10px',
                    borderRadius: 8,
                    fontSize: '0.85rem',
                    fontWeight: 600,
                  }}>
                    {listing.status}
                  </span>
                </td>
                <td style={{ padding: 8 }}>{listing.views_count}</td>
                <td style={{ padding: 8 }}>
                  <button
                    onClick={() => navigate(`/listings/${listing.id}/edit`)}
                    style={{ marginRight: 8, padding: '4px 12px', borderRadius: 6, border: '1px solid #E3E5EA', background: 'white', cursor: 'pointer' }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(listing.id, listing.title)}
                    style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid #E05263', color: '#E05263', background: 'white', cursor: 'pointer' }}
                  >
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