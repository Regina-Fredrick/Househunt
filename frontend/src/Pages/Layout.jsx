import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout({ user, onLogout }) {
  return (
    <div style={{ display: 'flex' }}>
      <Sidebar user={user} onLogout={onLogout} />
      <div style={{ flex: 1, padding: '24px 32px' }}>
        <Outlet />
      </div>
    </div>
  );
}