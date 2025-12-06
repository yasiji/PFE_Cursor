import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import ForecastPage from './pages/ForecastPage'
import ProductsPage from './pages/ProductsPage'
import InventoryPage from './pages/InventoryPage'
import AnalyticsPage from './pages/AnalyticsPage'
import OrdersPage from './pages/OrdersPage'
import RefillPage from './pages/RefillPage'
import SettingsPage from './pages/SettingsPage'
import MainLayout from './components/layout/MainLayout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import NotificationProvider from './components/notifications/NotificationProvider'

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <NotificationProvider>
      <Routes>
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage />}
        />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="forecast" element={<ForecastPage />} />
          <Route path="refill" element={<RefillPage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </NotificationProvider>
  )
}

export default App

