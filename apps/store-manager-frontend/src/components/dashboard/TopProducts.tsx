import { List, ListItem, ListItemText, Chip, Box, CircularProgress, Typography, Alert } from '@mui/material'
import { TrendingUp, TrendingDown } from '@mui/icons-material'
import { useQuery } from 'react-query'
import { analyticsAPI } from '../../services/api'
import { useAuthStore } from '../../store/authStore'

const TopProducts = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'

  // Fetch real top products data from API
  const { data, isLoading, error } = useQuery(
    ['topProductsDashboard', storeId],
    async () => {
      const response = await analyticsAPI.getTopProducts(storeId, 5, 'revenue', 30)
      return response.data
    },
    {
      refetchInterval: 120000, // Refetch every 2 minutes
      retry: 2,
      staleTime: 60000,
    }
  )

  const products = data?.best_sellers || []

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress size={24} />
        <Typography variant="body2" sx={{ ml: 1 }}>Loading...</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="warning" sx={{ m: 1 }}>
        Unable to load top products.
      </Alert>
    )
  }

  if (!products.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
        No product data available.
      </Typography>
    )
  }

  return (
    <List>
      {products.map((product: any, index: number) => (
        <ListItem
          key={index}
          sx={{
            borderBottom: index < products.length - 1 ? '1px solid #e0e0e0' : 'none',
            py: 1.5,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <Chip
              label={index + 1}
              size="small"
              sx={{ mr: 2, minWidth: 32, fontWeight: 600 }}
              color={index < 3 ? 'primary' : 'default'}
            />
            <ListItemText
              primary={product.name}
              secondary={`${product.sales} units • $${product.revenue?.toFixed(2) || '0.00'}`}
              sx={{ flex: 1 }}
            />
            <Chip
              icon={product.change_percent >= 0 ? <TrendingUp /> : <TrendingDown />}
              label={`${product.change_percent >= 0 ? '+' : ''}${product.change_percent}%`}
              size="small"
              color={product.change_percent >= 0 ? 'success' : 'error'}
            />
          </Box>
        </ListItem>
      ))}
    </List>
  )
}

export default TopProducts
