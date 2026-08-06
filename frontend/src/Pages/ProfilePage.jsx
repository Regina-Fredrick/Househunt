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

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      <form onSubmit={handleSubmit}>
        {/* Username/Role were previously OUTSIDE the <form> tag — theme.css
            only styles `form label`/`form input`, so they were falling back
            to unstyled inline defaults. Moved inside to inherit the same
            block layout, width, and spacing as Email/Phone below. Still
            read-only via `disabled`; nothing about form submission changes
            since handleSubmit only sends email/phone_number regardless. */}
        <label>Username</label>
        <input value={user.username} disabled />

        <label>Role</label>
        <input value={user.role} disabled />

        <label>Email</label>
        <input name="email" type="email" value={form.email} onChange={handleChange} />

        <label>Phone Number</label>
        <input name="phone_number" value={form.phone_number} onChange={handleChange} placeholder="0712345678" />
        <p className="muted" style={{ fontSize: '0.95rem', marginTop: 4 }}>
          Used for M-Pesa unlock payments and WhatsApp contact on your listings.
        </p>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 8 }}>
          {loading ? 'Saving...' : 'Save Changes'}
        </button>
      </form>
    </div>
  );
}