import { useMemo, useState } from 'react'
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
} from '@mui/material'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { useQuery } from 'react-query'
import { storeAPI } from '../../services/api'
import { format } from 'date-fns'
import { FileDownload } from '@mui/icons-material'

interface DailyForecast {
  date: string
  predicted_demand: number
  predicted_revenue: number
  predicted_profit: number
  predicted_loss: number
  net_profit: number
  predicted_margin: number
  factors: {
    day_of_week: string
    is_weekend: boolean
    is_holiday: boolean
    weather: string
    seasonality_factor: number
  }
}

interface ExtendedForecast {
  store_id: string
  forecast_period: string
  daily_forecasts: DailyForecast[]
  summary: {
    total_revenue: number
    total_profit: number
    total_loss: number
    net_profit: number
    average_margin: number
  }
}

interface ThirtyDayForecastTabProps {
  storeId: string
  startDate?: string
  windowDays?: number
}

const ThirtyDayForecastTab = ({ storeId, startDate, windowDays = 30 }: ThirtyDayForecastTabProps) => {
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [productFilter, setProductFilter] = useState<string>('')

  const { data: forecastData, isLoading, error } = useQuery<ExtendedForecast>(
    ['extendedForecast', storeId, categoryFilter, productFilter],
    async () => {
      const response = await storeAPI.getExtendedForecast(storeId, categoryFilter || undefined, productFilter || undefined)
      return response.data
    },
    {
      refetchInterval: 300000, // 5 minutes
      retry: 1,
    }
  )

  const filteredForecasts = useMemo(() => {
    if (!forecastData) return []
    if (!startDate) return forecastData.daily_forecasts
    const startTime = new Date(startDate).getTime()
    if (Number.isNaN(startTime)) return forecastData.daily_forecasts
    return forecastData.daily_forecasts.filter((f) => new Date(f.date).getTime() >= startTime)
  }, [forecastData, startDate])

  const visibleForecasts = filteredForecasts.slice(0, windowDays)

  const handleExport = () => {
    if (!forecastData) return

    const headers = ['Date', 'Demand', 'Revenue', 'Profit', 'Loss', 'Net Profit', 'Margin %', 'Day of Week', 'Weather']
    const rows = visibleForecasts.map((f) => [
      f.date,
      f.predicted_demand.toFixed(2),
      f.predicted_revenue.toFixed(2),
      f.predicted_profit.toFixed(2),
      f.predicted_loss.toFixed(2),
      f.net_profit.toFixed(2),
      f.predicted_margin.toFixed(2),
      f.factors.day_of_week,
      f.factors.weather,
    ])

    const csvContent = [headers, ...rows].map((row) => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `30-day-forecast-${format(new Date(), 'yyyy-MM-dd')}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>
          Loading 30-day forecast...
        </Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error">
        Error loading 30-day forecast. Please try again.
      </Alert>
    )
  }

  if (!forecastData) {
    return <Alert severity="info">No forecast data available.</Alert>
  }

  if (visibleForecasts.length === 0) {
    return <Alert severity="info">No forecast data available for the selected date.</Alert>
  }

  const chartData = visibleForecasts.map((f) => ({
    date: format(new Date(f.date), 'MMM dd'),
    revenue: f.predicted_revenue,
    profit: f.predicted_profit,
    loss: f.predicted_loss,
    netProfit: f.net_profit,
    margin: f.predicted_margin,
  }))

  const summary = visibleForecasts.reduce(
    (acc, forecast) => {
      acc.total_revenue += forecast.predicted_revenue
      acc.total_profit += forecast.predicted_profit
      acc.total_loss += forecast.predicted_loss
      acc.net_profit += forecast.net_profit
      return acc
    },
    { total_revenue: 0, total_profit: 0, total_loss: 0, net_profit: 0 }
  )
  const averageMargin =
    visibleForecasts.reduce((sum, forecast) => sum + forecast.predicted_margin, 0) /
    visibleForecasts.length

  return (
    <Box>
      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Revenue ({windowDays}d view)
              </Typography>
              <Typography variant="h4" color="primary">
                ${summary.total_revenue.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Profit ({windowDays}d view)
              </Typography>
              <Typography variant="h4" color="success.main">
                ${summary.total_profit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Total Loss ({windowDays}d view)
              </Typography>
              <Typography variant="h4" color="error.main">
                ${summary.total_loss.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary">
                Net Profit ({windowDays}d view)
              </Typography>
              <Typography variant="h4" color={summary.net_profit >= 0 ? 'success.main' : 'error.main'}>
                ${summary.net_profit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Avg Margin: {averageMargin.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters and Export */}
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box display="flex" gap={2}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Category</InputLabel>
            <Select value={categoryFilter} label="Category" onChange={(e) => setCategoryFilter(e.target.value)}>
              <MenuItem value="">All Categories</MenuItem>
              <MenuItem value="Fruits">Fruits</MenuItem>
              <MenuItem value="Vegetables">Vegetables</MenuItem>
              <MenuItem value="Dairy">Dairy</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Product</InputLabel>
            <Select value={productFilter} label="Product" onChange={(e) => setProductFilter(e.target.value)}>
              <MenuItem value="">All Products</MenuItem>
            </Select>
          </FormControl>
        </Box>
        <Button variant="outlined" startIcon={<FileDownload />} onClick={handleExport}>
          Export CSV
        </Button>
      </Box>

      {/* Charts */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Revenue, Profit, and Loss (Window)
              </Typography>
              <ResponsiveContainer width="100%" height={400}>
                <AreaChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="revenue" stackId="1" stroke="#1976d2" fill="#1976d2" fillOpacity={0.6} />
                  <Area type="monotone" dataKey="profit" stackId="2" stroke="#2e7d32" fill="#2e7d32" fillOpacity={0.6} />
                  <Area type="monotone" dataKey="loss" stackId="3" stroke="#d32f2f" fill="#d32f2f" fillOpacity={0.6} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Net Profit Trend
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="netProfit" stroke="#2e7d32" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Margin Percentage
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="margin" fill="#0288d1" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Detailed Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Day-by-Day Forecast Details
          </Typography>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell align="right">Demand</TableCell>
                  <TableCell align="right">Revenue</TableCell>
                  <TableCell align="right">Profit</TableCell>
                  <TableCell align="right">Loss</TableCell>
                  <TableCell align="right">Net Profit</TableCell>
                  <TableCell align="right">Margin %</TableCell>
                  <TableCell>Day</TableCell>
                  <TableCell>Factors</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {visibleForecasts.map((forecast) => (
                  <TableRow key={forecast.date}>
                    <TableCell>{format(new Date(forecast.date), 'MMM dd, yyyy')}</TableCell>
                    <TableCell align="right">{forecast.predicted_demand.toFixed(1)}</TableCell>
                    <TableCell align="right">${forecast.predicted_revenue.toFixed(2)}</TableCell>
                    <TableCell align="right" sx={{ color: 'success.main' }}>
                      ${forecast.predicted_profit.toFixed(2)}
                    </TableCell>
                    <TableCell align="right" sx={{ color: 'error.main' }}>
                      ${forecast.predicted_loss.toFixed(2)}
                    </TableCell>
                    <TableCell align="right" sx={{ color: forecast.net_profit >= 0 ? 'success.main' : 'error.main', fontWeight: 600 }}>
                      ${forecast.net_profit.toFixed(2)}
                    </TableCell>
                    <TableCell align="right">{forecast.predicted_margin.toFixed(1)}%</TableCell>
                    <TableCell>{forecast.factors.day_of_week}</TableCell>
                    <TableCell>
                      <Box display="flex" gap={0.5}>
                        {forecast.factors.is_weekend && <Chip label="Weekend" size="small" color="primary" />}
                        {forecast.factors.is_holiday && <Chip label="Holiday" size="small" color="warning" />}
                        {forecast.factors.weather !== 'normal' && (
                          <Chip label={forecast.factors.weather} size="small" color="info" />
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  )
}

export default ThirtyDayForecastTab

