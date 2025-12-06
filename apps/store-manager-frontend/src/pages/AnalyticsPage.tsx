import { useState, useMemo } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
  Chip,
} from '@mui/material'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { useAuthStore } from '../store/authStore'
import { useQuery } from 'react-query'
import { storeAPI, analyticsAPI } from '../services/api'
import { format, subDays } from 'date-fns'
import ThirtyDayForecastTab from './components/ThirtyDayForecastTab'

const AnalyticsPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const [timeRange, setTimeRange] = useState('7d')
  const [tabValue, setTabValue] = useState(0)

  // Calculate date range and days based on timeRange
  const { dateRange, periodDays } = useMemo(() => {
    const endDate = new Date()
    let startDate = new Date()
    let days = 7
    
    switch (timeRange) {
      case '7d':
        startDate = subDays(endDate, 7)
        days = 7
        break
      case '30d':
        startDate = subDays(endDate, 30)
        days = 30
        break
      case '90d':
        startDate = subDays(endDate, 90)
        days = 90
        break
      case '1y':
        startDate = subDays(endDate, 365)
        days = 365
        break
      default:
        startDate = subDays(endDate, 7)
        days = 7
    }
    
    return {
      dateRange: {
        start: format(startDate, 'yyyy-MM-dd'),
        end: format(endDate, 'yyyy-MM-dd'),
      },
      periodDays: days,
    }
  }, [timeRange])

  // Fetch sales vs forecast data from API (REAL DATA)
  const { data: salesData = [], isLoading: salesLoading, error: salesError } = useQuery(
    ['salesVsForecast', storeId, periodDays],
    async () => {
      const response = await analyticsAPI.getSalesVsForecast(storeId, Math.min(periodDays, 30))
      return response.data.data || []
    },
    {
      enabled: tabValue === 0 || tabValue === 1,
      refetchInterval: 60000,
      retry: 2,
    }
  )

  // Fetch forecast chart data (REAL-TIME from Open-Meteo & Nager.Date APIs)
  const { data: forecastChartData = [], isLoading: forecastLoading } = useQuery(
    ['forecastChart', storeId],
    async () => {
      const response = await analyticsAPI.getForecastChart(storeId, 7)
      return response.data.chart_data || []
    },
    {
      enabled: tabValue === 0,
      refetchInterval: 300000, // Refetch every 5 minutes
      retry: 2,
    }
  )

  // Fetch category analysis (REAL DATA)
  const { data: categoryData = [], isLoading: categoryLoading } = useQuery(
    ['categoryAnalysis', storeId, periodDays],
    async () => {
      const response = await analyticsAPI.getCategoryAnalysis(storeId, periodDays)
      return response.data.categories || []
    },
    {
      enabled: tabValue === 3,
      refetchInterval: 300000,
      retry: 2,
    }
  )

  // Fetch top products (REAL DATA)
  const { data: topProductsData, isLoading: productsLoading } = useQuery(
    ['topProducts', storeId, periodDays],
    async () => {
      const response = await analyticsAPI.getTopProducts(storeId, 5, 'revenue', periodDays)
      return response.data
    },
    {
      enabled: tabValue === 2,
      refetchInterval: 300000,
      retry: 2,
    }
  )

  // Fetch demand factors (weather & holidays - REAL-TIME)
  const { data: demandFactors } = useQuery(
    ['demandFactors', storeId],
    async () => {
      const response = await analyticsAPI.getDemandFactors(storeId, 7)
      return response.data
    },
    {
      enabled: tabValue === 0,
      refetchInterval: 300000,
    }
  )

  const bestSellers = topProductsData?.best_sellers || []
  const worstSellers = topProductsData?.worst_sellers || []

  const COLORS = ['#1976d2', '#2e7d32', '#ed6c02', '#9c27b0', '#0288d1', '#d32f2f', '#7b1fa2']

  // Format forecast data for chart
  const forecastData = forecastChartData.map((item: any) => ({
    day: item.day,
    forecast: item.forecast,
    lower: item.lower,
    upper: item.upper,
    weather: item.weather,
    isHoliday: item.is_holiday,
  }))

  // Format category data for pie chart
  const categoryChartData = categoryData.map((cat: any) => ({
    name: cat.name,
    value: cat.revenue_percent || 0,
    revenue: cat.total_revenue || 0,
  }))

  const isLoading = salesLoading || forecastLoading || categoryLoading || productsLoading

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 600 }}>
            Analytics & Reports
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Real-time data from Open-Meteo (weather) and Nager.Date (holidays) APIs
          </Typography>
        </Box>
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Time Range</InputLabel>
          <Select value={timeRange} label="Time Range" onChange={(e) => setTimeRange(e.target.value)}>
            <MenuItem value="7d">Last 7 Days</MenuItem>
            <MenuItem value="30d">Last 30 Days</MenuItem>
            <MenuItem value="90d">Last 90 Days</MenuItem>
            <MenuItem value="1y">Last Year</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Data source indicator */}
      <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
        <Chip label="Weather: Open-Meteo API" size="small" color="primary" variant="outlined" />
        <Chip label="Holidays: Nager.Date API" size="small" color="secondary" variant="outlined" />
        <Chip label="Real-time data" size="small" color="success" variant="outlined" />
      </Box>

      <Card sx={{ mb: 3 }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab label="Sales & Forecasting" />
            <Tab label="Revenue & Profit" />
            <Tab label="Product Performance" />
            <Tab label="Category Analysis" />
            <Tab label="30-Day Forecast" />
          </Tabs>
        </Box>

        <CardContent>
          {/* Show loading state */}
          {isLoading && (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight={200}>
              <CircularProgress />
              <Typography sx={{ ml: 2 }}>Loading real-time data...</Typography>
            </Box>
          )}

          {/* Show error state */}
          {salesError && tabValue < 2 && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Error loading data. Please ensure the backend API is running.
            </Alert>
          )}

          {tabValue === 0 && !isLoading && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Sales Trend vs Forecast
                </Typography>
                {salesData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={salesData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Line
                        type="monotone"
                        dataKey="sales"
                        stroke="#1976d2"
                        strokeWidth={2}
                        name="Actual Sales"
                      />
                      <Line
                        type="monotone"
                        dataKey="forecast"
                        stroke="#9c27b0"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        name="Forecast"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert severity="info">No sales data available for this period.</Alert>
                )}
              </Grid>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Next 7 Days Forecast (Real-time Weather & Holidays Applied)
                </Typography>
                {forecastData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={forecastData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis />
                      <Tooltip 
                        content={({ active, payload, label }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload
                            return (
                              <Box sx={{ bgcolor: 'background.paper', p: 1.5, border: '1px solid #ccc', borderRadius: 1 }}>
                                <Typography variant="subtitle2">{label}</Typography>
                                <Typography variant="body2">Forecast: {data.forecast} units</Typography>
                                <Typography variant="body2">Range: {data.lower} - {data.upper}</Typography>
                                <Typography variant="body2" color="text.secondary">
                                  Weather: {data.weather}
                                </Typography>
                                {data.isHoliday && (
                                  <Chip label="Holiday" size="small" color="warning" sx={{ mt: 0.5 }} />
                                )}
                              </Box>
                            )
                          }
                          return null
                        }}
                      />
                      <Legend />
                      <Area
                        type="monotone"
                        dataKey="upper"
                        stroke="#8884d8"
                        fill="#8884d8"
                        fillOpacity={0.1}
                        name="Upper Bound"
                      />
                      <Area
                        type="monotone"
                        dataKey="forecast"
                        stroke="#1976d2"
                        fill="#1976d2"
                        fillOpacity={0.3}
                        name="Forecast"
                      />
                      <Area
                        type="monotone"
                        dataKey="lower"
                        stroke="#8884d8"
                        fill="#fff"
                        name="Lower Bound"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert severity="info">Loading forecast data...</Alert>
                )}
              </Grid>
              {/* Show notable factors */}
              {demandFactors?.notable_days && (
                <Grid item xs={12}>
                  <Typography variant="subtitle2" gutterBottom>
                    Notable Days This Week
                  </Typography>
                  <Box display="flex" gap={1} flexWrap="wrap">
                    {demandFactors.notable_days.holidays?.map((h: any, i: number) => (
                      <Chip 
                        key={i} 
                        label={`${h.name} (${h.factor}x)`} 
                        color="warning" 
                        size="small"
                      />
                    ))}
                    {demandFactors.notable_days.high_demand_days?.map((d: any, i: number) => (
                      <Chip 
                        key={i} 
                        label={`${d.reason}: ${d.factor}x demand`} 
                        color="success" 
                        size="small" 
                        variant="outlined"
                      />
                    ))}
                  </Box>
                </Grid>
              )}
            </Grid>
          )}

          {tabValue === 1 && !isLoading && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  Revenue & Profit Trends
                </Typography>
                {salesData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={350}>
                    <LineChart data={salesData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="day" />
                      <YAxis yAxisId="left" />
                      <YAxis yAxisId="right" orientation="right" />
                      <Tooltip />
                      <Legend />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="revenue"
                        stroke="#1976d2"
                        strokeWidth={2}
                        name="Revenue ($)"
                      />
                      <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="profit"
                        stroke="#2e7d32"
                        strokeWidth={2}
                        name="Profit ($)"
                      />
                      <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="margin_percent"
                        stroke="#ed6c02"
                        strokeWidth={2}
                        strokeDasharray="5 5"
                        name="Margin (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert severity="info">No revenue data available.</Alert>
                )}
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Revenue Trend
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={salesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="#1976d2"
                      fill="#1976d2"
                      fillOpacity={0.6}
                      name="Revenue"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Profit Trend
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={salesData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="profit"
                      stroke="#2e7d32"
                      fill="#2e7d32"
                      fillOpacity={0.6}
                      name="Profit"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Grid>
            </Grid>
          )}

          {tabValue === 2 && !isLoading && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Best Sellers
                </Typography>
                <Card variant="outlined">
                  <CardContent>
                    {bestSellers.length > 0 ? (
                      bestSellers.map((item: any, index: number) => (
                        <Box
                          key={index}
                          display="flex"
                          justifyContent="space-between"
                          alignItems="center"
                          sx={{ py: 1, borderBottom: index < bestSellers.length - 1 ? '1px solid #e0e0e0' : 'none' }}
                        >
                          <Box>
                            <Typography variant="body2" fontWeight={500}>
                              {item.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {item.sales} units • ${item.revenue?.toFixed(2)}
                            </Typography>
                          </Box>
                          <Typography
                            variant="body2"
                            color={item.change_percent >= 0 ? 'success.main' : 'error.main'}
                          >
                            {item.change_percent >= 0 ? '+' : ''}{item.change_percent}%
                          </Typography>
                        </Box>
                      ))
                    ) : (
                      <Alert severity="info">No product data available.</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Lowest Performers
                </Typography>
                <Card variant="outlined">
                  <CardContent>
                    {worstSellers.length > 0 ? (
                      worstSellers.map((item: any, index: number) => (
                        <Box
                          key={index}
                          display="flex"
                          justifyContent="space-between"
                          alignItems="center"
                          sx={{ py: 1, borderBottom: index < worstSellers.length - 1 ? '1px solid #e0e0e0' : 'none' }}
                        >
                          <Box>
                            <Typography variant="body2" fontWeight={500}>
                              {item.name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {item.sales} units • ${item.revenue?.toFixed(2)}
                            </Typography>
                          </Box>
                          <Typography variant="body2" color="error.main">
                            {item.change_percent >= 0 ? '+' : ''}{item.change_percent}%
                          </Typography>
                        </Box>
                      ))
                    ) : (
                      <Alert severity="info">No product data available.</Alert>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {tabValue === 3 && !isLoading && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Sales by Category
                </Typography>
                {categoryChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={categoryChartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {categoryChartData.map((_entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert severity="info">No category data available.</Alert>
                )}
              </Grid>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>
                  Revenue by Category
                </Typography>
                {categoryChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={categoryChartData} layout="vertical">
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis dataKey="name" type="category" width={100} />
                      <Tooltip formatter={(value: number) => `$${value.toFixed(2)}`} />
                      <Bar dataKey="revenue" fill="#2e7d32" />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <Alert severity="info">No category data available.</Alert>
                )}
              </Grid>
            </Grid>
          )}

          {tabValue === 4 && <ThirtyDayForecastTab storeId={storeId} />}
        </CardContent>
      </Card>
    </Box>
  )
}

export default AnalyticsPage
