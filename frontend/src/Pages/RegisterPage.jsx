import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { apiPost } from '../utils/api';

export default function RegisterPage() {
  const [form, setForm] = useState({
    username: '', email: '', password: '', phone_number: '', role: 'buyer',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await apiPost('/api/auth/register/', form);
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div style={{ maxWidth: 400 }}>
        <h2>Check your email</h2>
        <p>We sent a verification link to your email address. Click it to activate your account, then come back and log in.</p>
        <button className="btn btn-primary" onClick={() => navigate('/login')}>Go to Login</button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h2>Register</h2>
      {error && <div style={{ background: '#FDECEE', color: '#E05263', padding: 12, borderRadius: 8, marginBottom: 16 }}>{error}</div>}
      <form onSubmit={handleSubmit}>
        <label>Username</label>
        <input name="username" value={form.username} onChange={handleChange} required />

        <label>Email</label>
        <input name="email" type="email" value={form.email} onChange={handleChange} required />

        <label>Phone Number</label>
        <input name="phone_number" value={form.phone_number} onChange={handleChange} placeholder="0712345678" />

        <label>Role</label>
        <select name="role" value={form.role} onChange={handleChange}>
          <option value="buyer">Buyer</option>
          <option value="owner">Owner</option>
          <option value="agent">Agent</option>
        </select>

        <label>Password</label>
        <input name="password" type="password" value={form.password} onChange={handleChange} required minLength={8} />

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ marginTop: 16 }}>
          {loading ? 'Creating account...' : 'Register'}
        </button>
      </form>
      <p style={{ marginTop: 16 }}>
        Already have an account? <Link to="/login">Login</Link>
      </p>
    </div>
  );
}