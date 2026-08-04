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
        color: active ? '#1A1D29' : '#8B92A5',
        background: active ? '#F1EDFE' : 'transparent',
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
      borderRight: '1px solid #EDEEF2',
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
        </>
      )}
      <div style={{ marginTop: 24, borderTop: '1px solid #EDEEF2', paddingTop: 16 }}>
        {user ? (
          <button
            onClick={onLogout}
            style={{
              width: '100%',
              padding: '10px 16px',
              borderRadius: 10,
              border: '1px solid #E3E5EA',
              background: 'transparent',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            Logout ({user.username})
          </button>
        ) : (
          <NavItem to="/login" label="Login" active={location.pathname === '/login'} />
        )}
      </div>
    </div>
  );
}