import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './Pages/Layout';
import BrowsePage from './Pages/BrowsePage';
import DetailPage from './Pages/DetailPage';
import LoginPage from './Pages/LoginPage';
import RegisterPage from './Pages/RegisterPage';
import MyListingsPage from './Pages/MyListingsPage';
import CreateListingPage from './Pages/CreateListingPage';
import EditListingPage from './Pages/EditListingPage';
import ProfilePage from './Pages/ProfilePage';
import AdminDashboardPage from './Pages/AdminDashboardPage';
import MyBookingsPage from './Pages/MyBookingsPage';
import BulkImportPage from './Pages/BulkImportPage';
import { apiGet, apiPost } from './utils/api';

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    apiGet('/api/auth/me/')
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function handleLogout() {
    await apiPost('/api/auth/logout/', {});
    setUser(null);
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout user={user} onLogout={handleLogout} />}>
          <Route index element={<BrowsePage />} />
          <Route path="listings/:id" element={<DetailPage />} />
          <Route path="login" element={<LoginPage onLogin={setUser} />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="mine" element={<MyListingsPage />} />
          <Route path="create" element={<CreateListingPage />} />
          <Route path="listings/:id/edit" element={<EditListingPage />} />
          <Route path="profile" element={<ProfilePage user={user} onUpdate={setUser} />} />
          <Route path="admin" element={<AdminDashboardPage />} />
          <Route path="bookings" element={<MyBookingsPage />} />
          <Route path="bulk-import" element={<BulkImportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;