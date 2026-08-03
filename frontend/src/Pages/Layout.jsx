import { Link, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div>
      <nav style={{
        background: 'white',
        borderBottom: '1px solid #EDEEF2',
        padding: '12px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <Link to="/" style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontWeight: 700,
          fontSize: '1.5rem',
          color: '#1A1D29',
          textDecoration: 'none',
        }}>
          Househunt
        </Link>
        <div>
          <Link to="/" style={{ marginRight: 16 }}>Browse</Link>
        </div>
      </nav>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px' }}>
        <Outlet />
      </div>
    </div>
  );
}