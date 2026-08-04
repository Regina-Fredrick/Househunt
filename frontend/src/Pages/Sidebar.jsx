import { Link, useLocation } from 'react-router-dom';

function NavItem({ to, label, active }) {
  return (
    <Link
      to={to}
      style={{
        display: 'block',
        padding: '10px 16px',
        borderRadius: 10,
        marginBottom: 4,
        textDecoration: 'none',
        color: active ? 'var(--ink)' : 'var(--muted)',
        background: active ? 'var(--brick-bg)' : 'transparent',
        fontWeight: active ? 600 : 500,
      }}
    >
      {label}
    </Link>
  );
}

export default function Sidebar({ user, onLogout }) {
  const location = useLocation();

  return (
    <div style={{
      width: 220,
      minHeight: '100vh',
      background: 'white',
      borderRight: '1px solid var(--line)',
      padding: '20px 12px',
      boxSizing: 'border-box',
    }}>
      <div style={{
        fontFamily: 'Space Grotesk, sans-serif',
        fontWeight: 700,
        fontSize: '1.4rem',
        padding: '0 12px 20px',
      }}>
        Househunt
      </div>

      <NavItem to="/" label="Browse" active={location.pathname === '/'} />
      {user && (
        <>
          <NavItem to="/mine" label="My Listings" active={location.pathname === '/mine'} />
          <NavItem to="/create" label="+ New Listing" active={location.pathname === '/create'} />
          <NavItem to="/profile" label="Profile" active={location.pathname === '/profile'} />
          {user.is_staff && (
            <NavItem to="/admin" label="Moderation" active={location.pathname === '/admin'} />
          )}
        </>
      )}
      <div style={{ marginTop: 24, borderTop: '1px solid var(--line)', paddingTop: 16 }}>
        {user ? (
          <button
            onClick={onLogout}
            style={{
              width: '100%',
              padding: '10px 16px',
              borderRadius: 10,
              border: '1px solid var(--line)',
              background: 'transparent',
              color: 'var(--ink)',
              cursor: 'pointer',
              textAlign: 'left',
              fontFamily: 'Inter, sans-serif',
              fontSize: '0.95rem',
            }}
          >
            Logout ({user.username})
          </button>
        ) : (
          <>
            <NavItem to="/login" label="Login" active={location.pathname === '/login'} />
            <NavItem to="/register" label="Register" active={location.pathname === '/register'} />
          </>
        )}
      </div>
    </div>
  );
}