import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useQuery } from 'react-query'
import { analyticsAPI } from '../../services/api'
import { useAuthStore } from '../../store/authStore'
import { Box, Typography, CircularProgress, Alert } from '@mui/material'

const SalesChart = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  
  // Use the real analytics API for sales vs forecast comparison
  const { data: salesData = [], isLoading, error } = useQuery(
    ['salesVsForecastChart', storeId],
    async () => {
      const response = await analyticsAPI.getSalesVsForecast(storeId, 7)
      return response.data.data || []
    },
    {
      refetchInterval: 60000, // Refetch every minute
      retry: 2,
      staleTime: 30000, // Consider data stale after 30 seconds
    }
  )

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height={300}>
        <CircularProgress size={24} />
        <Typography variant="body2" sx={{ ml: 1 }}>Loading sales data...</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Box height={300} display="flex" alignItems="center" justifyContent="center">
        <Alert severity="warning" sx={{ maxWidth: 400 }}>
          Unable to load sales chart. Please ensure the backend API is running.
        </Alert>
      </Box>
    )
  }

  if (!salesData.length) {
    return (
      <Box height={300} display="flex" alignItems="center" justifyContent="center">
        <Typography color="text.secondary">No sales data available for this period.</Typography>
      </Box>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={salesData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="day" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="sales" stroke="#1976d2" strokeWidth={2} name="Actual Sales" />
        <Line type="monotone" dataKey="forecast" stroke="#9c27b0" strokeWidth={2} strokeDasharray="5 5" name="Forecast" />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default SalesChart
