import { useState } from 'react';
import { apiPost } from '../utils/api';

export default function RequestTourModal({ listingId, onClose, onSuccess }) {
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiPost('/api/listings/tours/create/', {
        listing: listingId,
        requested_date: date,
        requested_time: time,
        message,
      });
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ padding: 20, marginTop: 16, maxWidth: 400 }}>
      <h4>Request a Tour</h4>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={handleSubmit}>
        <label>Date</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required />

        <label>Time</label>
        <input type="time" value={time} onChange={(e) => setTime(e.target.value)} required />

        <label>Message (optional)</label>
        <textarea value={message} onChange={(e) => setMessage(e.target.value)} rows={3} />

        <div style={{ marginTop: 12 }}>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginRight: 8 }}>
            {loading ? 'Sending...' : 'Send Request'}
          </button>
          <button type="button" onClick={onClose} className="btn-outline btn-sm">Cancel</button>
        </div>
      </form>
    </div>
  );
}