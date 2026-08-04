import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiGet } from '../utils/api';

const STATUS_BADGE = {
  pending: 'badge-warning',
  confirmed: 'badge-success',
  cancelled: 'badge-danger',
  completed: 'badge-success',
};

export default function MyBookingsPage() {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    apiGet('/api/listings/tours/mine/')
      .then((data) => setBookings(data.results || data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>Loading your bookings...</p>;
  if (error) return <div className="alert alert-error">{error}</div>;

  return (
    <div>
      <h2 style={{ marginBottom: 20 }}>My Bookings</h2>

      {bookings.length === 0 ? (
        <p className="muted">You haven't requested any tours yet.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Listing</th>
              <th>Date</th>
              <th>Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {bookings.map((b) => (
              <tr key={b.id}>
                <td><Link to={`/listings/${b.listing}`}>{b.listing_title}</Link></td>
                <td>{b.requested_date}</td>
                <td>{b.requested_time}</td>
                <td><span className={`badge ${STATUS_BADGE[b.status]}`}>{b.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}