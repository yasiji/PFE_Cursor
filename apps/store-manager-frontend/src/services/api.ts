import axios, { AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// API service functions
export const authAPI = {
  login: (username: string, password: string) => {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return api.post('/api/v1/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (data: {
    username: string
    email: string
    password: string
    role: string
    store_id?: number
  }) => api.post('/api/v1/auth/register', data),
  getMe: () => api.get('/api/v1/auth/me'),
}

export const forecastAPI = {
  getForecast: (storeId: string, skuId: string, horizonDays: number = 7) =>
    api.post('/api/v1/forecast', {
      store_id: storeId,
      sku_id: skuId,
      horizon_days: horizonDays,
      include_uncertainty: true,
    }),
}

export const replenishmentAPI = {
  getReplenishmentPlan: (
    storeId: string,
    targetDate: string,
    currentInventory: Array<{
      sku_id: string
      quantity: number
      expiry_date?: string
    }>
  ) =>
    api.post('/api/v1/replenishment_plan', {
      store_id: storeId,
      date: targetDate,
      current_inventory: currentInventory,
    }),
}

export const orderAPI = {
  approveOrder: (orderId: number, notes?: string) =>
    api.post(`/api/v1/orders/${orderId}/approve`, { notes }),
  rejectOrder: (orderId: number, reason: string) =>
    api.post(`/api/v1/orders/${orderId}/reject`, { reason }),
  executeOrder: (orderId: number) =>
    api.post(`/api/v1/orders/${orderId}/execute`),
  createOrder: (storeId: string, recommendationIds: number[], orderDate?: string) =>
    api.post('/api/v1/orders', {
      store_id: storeId,
      recommendation_ids: recommendationIds,
      order_date: orderDate,
    }),
  getOrder: (orderId: number) => api.get(`/api/v1/orders/${orderId}`),
  updateOrderStatus: (orderId: number, status: string, actualArrivalDate?: string) =>
    api.put(`/api/v1/orders/${orderId}/status`, {
      status,
      actual_arrival_date: actualArrivalDate,
    }),
  getStoreOrders: (storeId: string, status?: string, startDate?: string, endDate?: string) =>
    api.get(`/api/v1/orders/stores/${storeId}/orders`, {
      params: { status, start_date: startDate, end_date: endDate },
    }),
}

export const storeAPI = {
  getStoreStats: (storeId: string) => api.get(`/api/v1/stores/${storeId}/stats`),
  getStoreProducts: (storeId: string) => api.get(`/api/v1/stores/${storeId}/products`),
  getStoreInventory: (storeId: string) => api.get(`/api/v1/stores/${storeId}/inventory`),
  getStoreSales: (storeId: string, startDate: string, endDate: string) =>
    api.get(`/api/v1/stores/${storeId}/sales`, {
      params: { start_date: startDate, end_date: endDate },
    }),
  getForecastAccuracy: (storeId: string, days: number = 30) =>
    api.get(`/api/v1/stores/${storeId}/forecast-accuracy`, {
      params: { days },
    }),
  getTopProducts: (storeId: string, limit: number = 10, sortBy: string = 'sales_volume', periodDays: number = 30) =>
    api.get(`/api/v1/stores/${storeId}/top-products`, {
      params: { limit, sort_by: sortBy, period_days: periodDays },
    }),
  getForecastInsights: (storeId: string, horizonDays: number = 7) =>
    api.get(`/api/v1/stores/${storeId}/forecast-insights`, {
      params: { horizon_days: horizonDays },
    }),
  getSalesPatterns: (storeId: string, periodDays: number = 90) =>
    api.get(`/api/v1/stores/${storeId}/sales-patterns`, {
      params: { period_days: periodDays },
    }),
  getRecommendations: (storeId: string, status: string = 'pending') =>
    api.get(`/api/v1/stores/${storeId}/recommendations`, {
      params: { status },
    }),
  getRefillPlan: (storeId: string, targetDate?: string) =>
    api.get(`/api/v1/stores/${storeId}/refill-plan`, {
      params: targetDate ? { target_date: targetDate } : {},
    }),
  getExtendedForecast: (storeId: string, category?: string, product?: string) =>
    api.get(`/api/v1/stores/${storeId}/forecast-extended`, {
      params: { category, product },
    }),
}

export const notificationAPI = {
  getNotifications: (read?: boolean, severity?: string, limit: number = 50) =>
    api.get('/api/v1/notifications', {
      params: { read, severity, limit },
    }),
  getUnreadCount: () => api.get('/api/v1/notifications/unread-count'),
  markAsRead: (notificationId: number) =>
    api.post(`/api/v1/notifications/${notificationId}/read`),
  markAllAsRead: () => api.post('/api/v1/notifications/read-all'),
  generateNotifications: (storeId: string) =>
    api.post('/api/v1/notifications/generate', null, {
      params: { store_id: storeId },
    }),
}

export const settingsAPI = {
  // Get all settings
  getSettings: () => api.get('/api/v1/settings'),
  
  // Update all settings at once
  updateSettings: (settings: any) => api.put('/api/v1/settings', settings),
  
  // Notification settings
  getNotificationSettings: () => api.get('/api/v1/settings/notifications'),
  updateNotificationSettings: (settings: any) => api.put('/api/v1/settings/notifications', settings),
  
  // Dashboard settings
  getDashboardSettings: () => api.get('/api/v1/settings/dashboard'),
  updateDashboardSettings: (settings: any) => api.put('/api/v1/settings/dashboard', settings),
  
  // Display settings
  getDisplaySettings: () => api.get('/api/v1/settings/display'),
  updateDisplaySettings: (settings: any) => api.put('/api/v1/settings/display', settings),
  
  // Forecast settings
  getForecastSettings: () => api.get('/api/v1/settings/forecast'),
  updateForecastSettings: (settings: any) => api.put('/api/v1/settings/forecast', settings),
  
  // Reset to defaults
  resetSettings: () => api.post('/api/v1/settings/reset'),
}

export const analyticsAPI = {
  // Real-time weather forecast from Open-Meteo API
  getWeatherForecast: (storeId: string, daysAhead: number = 7) =>
    api.get(`/api/v1/analytics/stores/${storeId}/weather-forecast`, {
      params: { days_ahead: daysAhead },
    }),
  
  // Real holidays from Nager.Date API
  getUpcomingHolidays: (storeId: string, daysAhead: number = 30) =>
    api.get(`/api/v1/analytics/stores/${storeId}/upcoming-holidays`, {
      params: { days_ahead: daysAhead },
    }),
  
  // Combined demand factors (weather + holidays + day patterns)
  getDemandFactors: (storeId: string, daysAhead: number = 7) =>
    api.get(`/api/v1/analytics/stores/${storeId}/demand-factors`, {
      params: { days_ahead: daysAhead },
    }),
  
  // Category analysis
  getCategoryAnalysis: (storeId: string, periodDays: number = 30) =>
    api.get(`/api/v1/analytics/stores/${storeId}/category-analysis`, {
      params: { period_days: periodDays },
    }),
  
  // Top/worst products
  getTopProducts: (storeId: string, limit: number = 5, sortBy: string = 'revenue', periodDays: number = 30) =>
    api.get(`/api/v1/analytics/stores/${storeId}/top-products`, {
      params: { limit, sort_by: sortBy, period_days: periodDays },
    }),
  
  // Forecast chart data
  getForecastChart: (storeId: string, daysAhead: number = 7) =>
    api.get(`/api/v1/analytics/stores/${storeId}/forecast-chart`, {
      params: { days_ahead: daysAhead },
    }),
  
  // Sales vs forecast comparison
  getSalesVsForecast: (storeId: string, periodDays: number = 7) =>
    api.get(`/api/v1/analytics/stores/${storeId}/sales-forecast-comparison`, {
      params: { period_days: periodDays },
    }),
}