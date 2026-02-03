import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import adminApi from './api/adminApi';
import Sidebar from './components/Sidebar';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Storms from './pages/Storms';
import Customers from './pages/Customers';
import ApiUsage from './pages/ApiUsage';

function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-gray-900">
      <Sidebar />
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = adminApi.getToken();

    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const data = await adminApi.getMe();

      // Only allow owners
      if (data.user?.role !== 'owner') {
        adminApi.logout();
        setLoading(false);
        return;
      }

      setAuthenticated(true);
    } catch {
      adminApi.logout();
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (!authenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  return <AdminLayout>{children}</AdminLayout>;
}

export default function AdminApp() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route path="/" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />

      <Route path="/storms" element={
        <ProtectedRoute>
          <Storms />
        </ProtectedRoute>
      } />

      <Route path="/customers" element={
        <ProtectedRoute>
          <Customers />
        </ProtectedRoute>
      } />

      <Route path="/usage" element={
        <ProtectedRoute>
          <ApiUsage />
        </ProtectedRoute>
      } />

      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}
