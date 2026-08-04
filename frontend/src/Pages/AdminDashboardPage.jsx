import { useEffect, useState } from 'react';
import { apiGet, getCsrfToken } from '../utils/api';

export default function AdminDashboardPage() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  function loadQueue() {
    return apiGet('/api/listings/admin/queue/').then((data) => {
      setListings(data.results || data);
    });
  }

  useEffect(() => {
    loadQueue()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleApprove(id) {
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/listings/${id}/admin-approve/`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'X-CSRFToken': csrfToken },
      });
      if (!res.ok) throw new Error('Approve failed');
      setListings(listings.filter((l) => l.id !== id));
    } catch (err) {
      alert(err.message);
    }
  }

  async function submitReject(id) {
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch(`/api/listings/${id}/admin-reject/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ reason: rejectReason }),
      });
      if (!res.ok) throw new Error('Reject failed');
      setListings(listings.filter((l) => l.id !== id));
      setRejectingId(null);
      setRejectReason('');
    } catch (err) {
      alert(err.message);
    }
  }

  if (loading) return <p>Loading moderation queue...</p>;
  if (error) return <p style={{ color: '#E05263' }}>{error === 'Request failed' ? 'You do not have admin access.' : error}</p>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>Moderation Queue</h2>

      {listings.length === 0 ? (
        <p className="muted">Nothing to review right now.</p>
      ) : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid #EDEEF2' }}>
              <th style={{ padding: 8 }}>Title</th>
              <th style={{ padding: 8 }}>Owner</th>
              <th style={{ padding: 8 }}>Price</th>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8 }}>Flag</th>
              <th style={{ padding: 8 }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map((listing) => (
              <tr key={listing.id} style={{ borderBottom: '1px solid #F2F3F5' }}>
                <td style={{ padding: 8 }}>{listing.title}</td>
                <td style={{ padding: 8 }}>{listing.owner_username}</td>
                <td style={{ padding: 8 }}>KES {listing.price}</td>
                <td style={{ padding: 8 }}>{listing.status}</td>
                <td style={{ padding: 8 }}>
                  {listing.flagged_reason ? (
                    <span style={{ background: '#FDECEE', color: '#E05263', padding: '3px 10px', borderRadius: 8, fontSize: '0.8rem' }}>
                      {listing.flagged_reason}
                    </span>
                  ) : (
                    <span className="muted">—</span>
                  )}
                </td>
                <td style={{ padding: 8 }}>
                  {rejectingId === listing.id ? (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <input
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Reason"
                        style={{ margin: 0, padding: '4px 8px', width: 140 }}
                      />
                      <button onClick={() => submitReject(listing.id)} className="btn btn-primary" style={{ padding: '4px 10px' }}>
                        Confirm
                      </button>
                      <button onClick={() => setRejectingId(null)} style={{ padding: '4px 10px' }}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => handleApprove(listing.id)}
                        style={{ marginRight: 8, padding: '4px 12px', borderRadius: 6, border: '1px solid #1AA89A', color: '#1AA89A', background: 'white', cursor: 'pointer' }}
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => setRejectingId(listing.id)}
                        style={{ padding: '4px 12px', borderRadius: 6, border: '1px solid #E05263', color: '#E05263', background: 'white', cursor: 'pointer' }}
                      >
                        Reject
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}