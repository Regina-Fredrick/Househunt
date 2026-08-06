import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiPost } from '../utils/api';

const GOOGLE_CLIENT_ID = '558997406922-lk1s69k87v1le0p5vq9hdpjk93h5t9pd.apps.googleusercontent.com';
export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  useEffect(() => {
    function initGoogle() {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: async (response) => {
          try {
            const user = await apiPost('/api/auth/google-login/', { credential: response.credential });
            onLogin(user);
            navigate('/mine');
          } catch (err) {
            setError(err.message);
          }
        },
      });
      window.google.accounts.id.renderButton(
        document.getElementById('googleSignInDiv'),
        { theme: 'outline', size: 'large' }
      );
    }

    if (window.google) {
      initGoogle();
    } else {
      const interval = setInterval(() => {
        if (window.google) {
          clearInterval(interval);
          initGoogle();
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, []);
  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await apiPost('/api/auth/login/', { username, password });
      onLogin(user);
      navigate('/mine');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400 }}>
      <h2>Login</h2>
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <label>Username</label>
        <input
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
       <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <div style={{ marginTop: 16 }}>
        <div id="googleSignInDiv"></div>
      </div>
    </div>
  );
}