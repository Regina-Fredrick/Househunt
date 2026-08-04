import { useEffect, useState } from 'react';
import { getCsrfToken } from '../utils/api';

export default function ProfilePage({ user, onUpdate }) {
  const [form, setForm] = useState({ email: '', phone_number: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({ email: user.email || '', phone_number: user.phone_number || '' });
    }
  }, [user]);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
    setSuccess('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      const csrfToken = await getCsrfToken();
      const res = await fetch('/api/auth/me/', {
        method: 'PATCH',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(form),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      onUpdate(data);
      setSuccess('Profile updated.');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (!user) return <p>Loading...</p>;

  return (
    <div style={{ maxWidth: 400 }}>
      <h2>My Profile</h2>

      {error && <div style={{ background: '#FDECEE', color: '#E05263', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}
      {success && <div style={{ background: '#E6FBF8', color: '#1AA89A', padding: 12, borderRadius: 8, marginBottom: 16 }}>{success}</div>}

      <label>Username</label>
      <input value={user.username} disabled style={{ background: '#F8F9FB' }} />

      <label>Role</label>
      <input value={user.role} disabled style={{ background: '#F8F9FB' }} />

      <form onSubmit={handleSubmit}>
        <label>Email</label>
        <input name="email" type="email" value={form.email} onChange={handleChange} />

        <label>Phone Number</label>
        <input name="phone_number" value={form.phone_number} onChange={handleChange} placeholder="0712345678" />
        <p className="muted" style={{ fontSize: '0.85rem', marginTop: -8 }}>
          Used for M-Pesa unlock payments and WhatsApp contact on your listings.
        </p>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8 }}>
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  );
}