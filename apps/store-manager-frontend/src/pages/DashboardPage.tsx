import { Grid, Card, CardContent, Typography, Box, Alert, CircularProgress } from '@mui/material'
import { TrendingUp, TrendingDown, Inventory, ShoppingCart, Warning } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { useQuery } from 'react-query'
import { storeAPI } from '../services/api'
import EnhancedForecastInsights from '../components/dashboard/EnhancedForecastInsights'
import SalesChart from '../components/dashboard/SalesChart'
import TopProducts from '../components/dashboard/TopProducts'
import AlertsList from '../components/dashboard/AlertsList'
import ForecastInsightsSection from '../components/dashboard/ForecastInsightsSection'

interface DashboardStats {
  salesToday: number
  revenueToday: number
  profitToday: number
  marginPercent: number
  itemsSold: number
  itemsOnShelves: number
  itemsInStock: number  // Items in backroom
  totalItems: number  // Total items (shelf + stock)
  itemsExpiring: number
  lowStockItems: number
  emptyShelves: number
  lossesToday: {
    waste_loss: number
    markdown_loss: number
    expiry_loss: number
    total_loss: number
  }
}

const DashboardPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'

  const { data: stats, isLoading, error } = useQuery<DashboardStats>(
    ['storeStats', storeId],
    async () => {
      const response = await storeAPI.getStoreStats(storeId)
      return {
        salesToday: response.data.sales_today || 0,
        revenueToday: response.data.revenue_today || 0,
        profitToday: response.data.profit_today || 0,
        marginPercent: response.data.margin_percent || 0,
        itemsSold: response.data.items_sold || 0,
        itemsOnShelves: response.data.items_on_shelves || 0,
        itemsInStock: response.data.items_in_stock || 0,
        totalItems: response.data.total_items || response.data.items_on_shelves || 0,
        itemsExpiring: response.data.items_expiring || 0,
        lowStockItems: response.data.low_stock_items || 0,
        emptyShelves: response.data.empty_shelves || 0,
        lossesToday: response.data.losses_today || {
          waste_loss: 0,
          markdown_loss: 0,
          expiry_loss: 0,
          total_loss: 0,
        },
      }
    },
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      retry: 2,
      staleTime: 10000, // Consider data stale after 10 seconds
    }
  )

  const statCards = [
    {
      title: 'Revenue Today',
      value: `$${(stats?.revenueToday ?? 0).toFixed(2)}`,
      change: '+12.5%',
      trend: 'up' as const,
      icon: <TrendingUp />,
      color: '#2e7d32',
    },
    {
      title: 'Profit Today',
      value: `$${(stats?.profitToday ?? 0).toFixed(2)}`,
      change: `${(stats?.marginPercent ?? 0).toFixed(1)}% margin`,
      trend: 'up' as const,
      icon: <TrendingUp />,
      color: '#1b5e20',
    },
    {
      title: 'Items Sold',
      value: stats?.itemsSold || 0,
      change: '+8.2%',
      trend: 'up' as const,
      icon: <ShoppingCart />,
      color: '#1976d2',
    },
    {
      title: 'On Shelves',
      value: `${stats?.itemsOnShelves || 0}`,
      change: `${stats?.itemsInStock || 0} in stock`,
      trend: 'up' as const,
      icon: <Inventory />,
      color: '#0288d1',
    },
    {
      title: 'Margin %',
      value: `${(stats?.marginPercent ?? 0).toFixed(1)}%`,
      change: 'Profitability',
      trend: 'up' as const,
      icon: <TrendingUp />,
      color: '#388e3c',
    },
    {
      title: 'Expiring Soon',
      value: stats?.itemsExpiring || 0,
      change: 'Urgent',
      trend: 'warning' as const,
      icon: <Warning />,
      color: '#ed6c02',
    },
    {
      title: 'Losses Today',
      value: `$${(stats?.lossesToday?.total_loss ?? 0).toFixed(2)}`,
      change: `Waste: $${(stats?.lossesToday?.waste_loss ?? 0).toFixed(2)}`,
      trend: 'down' as const,
      icon: <Warning />,
      color: '#d32f2f',
    },
  ]

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="body2" sx={{ ml: 2 }}>
          Loading dashboard...
        </Typography>
      </Box>
    )
  }

  if (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 3 }}>
          <Typography variant="subtitle1" fontWeight="bold">
            Error loading dashboard data
          </Typography>
          <Typography variant="body2">
            {errorMessage.includes('401') 
              ? 'Session expired. Please log in again.'
              : errorMessage.includes('Network Error')
              ? 'Cannot connect to API server. Make sure the backend is running on port 8000.'
              : `API Error: ${errorMessage}`
            }
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Tip: Run `start.bat` to start all services, or check the API at http://localhost:8000/docs
          </Typography>
        </Alert>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
        Business Overview
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Track how the fresh department performed yesterday, where you lost money, and which products drove
        results before moving to tomorrow’s refill plan.
      </Typography>

      {/* Alert Banner */}
      {(stats?.lowStockItems || 0) > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          {stats?.lowStockItems} items are running low on stock. {stats?.emptyShelves} shelves are empty.
        </Alert>
      )}

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={4} lg={2} key={index}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      {card.title}
                    </Typography>
                    <Typography variant="h4" component="div" sx={{ fontWeight: 600 }}>
                      {card.value}
                    </Typography>
                    {card.title === 'On Shelves' && stats && (
                      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                        {stats.itemsInStock || 0} in stock • {stats.totalItems || 0} total
                      </Typography>
                    )}
                    <Box display="flex" alignItems="center" gap={1} mt={1}>
                      {card.trend === 'up' && <TrendingUp fontSize="small" color="success" />}
                      {card.trend === 'down' && <TrendingDown fontSize="small" color="error" />}
                      {card.trend === 'warning' && <Warning fontSize="small" color="warning" />}
                      <Typography
                        variant="body2"
                        color={card.trend === 'up' ? 'success.main' : card.trend === 'warning' ? 'warning.main' : 'error.main'}
                      >
                        {card.change}
                      </Typography>
                    </Box>
                  </Box>
                  <Box
                    sx={{
                      backgroundColor: `${card.color}15`,
                      borderRadius: 2,
                      p: 1.5,
                      color: card.color,
                    }}
                  >
                    {card.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Loss Breakdown (Today)
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Total Loss
                  </Typography>
                  <Typography variant="h5" color="error.main">
                    ${stats?.lossesToday?.total_loss?.toFixed(2) ?? '0.00'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Waste / Expiry
                  </Typography>
                  <Typography variant="body1">
                    ${stats?.lossesToday?.waste_loss?.toFixed(2) ?? '0.00'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Expired or discarded items
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={4}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Markdown Loss
                  </Typography>
                  <Typography variant="body1">
                    ${stats?.lossesToday?.markdown_loss?.toFixed(2) ?? '0.00'}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Discounts to clear stock
                  </Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <ForecastInsightsSection storeId={storeId} />
        </Grid>
      </Grid>
      
      {/* Enhanced 7-Day Forecast Breakdown */}
      <Box sx={{ mt: 3 }}>
        <EnhancedForecastInsights storeId={storeId} />
      </Box>

      {/* Charts and Lists */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sales vs Forecast (Last 7 Days)
              </Typography>
              <SalesChart />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Top Products
              </Typography>
              <TopProducts />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Active Alerts
              </Typography>
              <AlertsList />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default DashboardPage

