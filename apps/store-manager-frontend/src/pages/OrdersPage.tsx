import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  IconButton,
  Checkbox,
  Snackbar,
} from '@mui/material'
import { CheckCircle, Cancel, Visibility, ShoppingCart, Warning } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { storeAPI, orderAPI, analyticsAPI } from '../services/api'
import { format } from 'date-fns'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface Recommendation {
  id: number
  sku_id: string
  name: string
  order_quantity: number
  current_stock: number
  forecasted_demand: number
  markdown?: {
    discount_percent: number
    effective_date: string
    reason: string
  }
  confidence: number
  status: string
}

const OrdersPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const queryClient = useQueryClient()
  const [selectedRecommendation, setSelectedRecommendation] = useState<Recommendation | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [selectedItems, setSelectedItems] = useState<Set<number>>(new Set())
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  // Fetch recommendations from API
  const { data: recommendations = [], isLoading } = useQuery<Recommendation[]>(
    ['recommendations', storeId],
    async () => {
      const response = await storeAPI.getRecommendations(storeId, 'pending')
      return response.data || []
    },
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      retry: 2,
    }
  )

  // Approve order mutation
  const approveMutation = useMutation(
    ({ orderId, notes }: { orderId: number; notes?: string }) =>
      orderAPI.approveOrder(orderId, notes),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', storeId])
        setSnackbar({ open: true, message: 'Order approved successfully', severity: 'success' })
        setSelectedItems(new Set())
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message: error.response?.data?.detail || 'Error approving order',
          severity: 'error',
        })
      },
    }
  )

  // Reject order mutation
  const rejectMutation = useMutation(
    ({ orderId, reason }: { orderId: number; reason: string }) =>
      orderAPI.rejectOrder(orderId, reason),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['recommendations', storeId])
        setSnackbar({ open: true, message: 'Order rejected successfully', severity: 'success' })
        setSelectedItems(new Set())
      },
      onError: (error: any) => {
        setSnackbar({
          open: true,
          message: error.response?.data?.detail || 'Error rejecting order',
          severity: 'error',
        })
      },
    }
  )

  const handleApprove = (orderId: number) => {
    approveMutation.mutate({ orderId })
  }

  const handleReject = (orderId: number) => {
    const reason = prompt('Please provide a reason for rejection:')
    if (reason) {
      rejectMutation.mutate({ orderId, reason })
    }
  }

  const handleBulkApprove = () => {
    selectedItems.forEach((orderId) => {
      approveMutation.mutate({ orderId })
    })
  }

  const toggleSelection = (orderId: number) => {
    const newSelection = new Set(selectedItems)
    if (newSelection.has(orderId)) {
      newSelection.delete(orderId)
    } else {
      newSelection.add(orderId)
    }
    setSelectedItems(newSelection)
  }

  const totalOrderValue = recommendations.reduce(
    (sum, rec) => sum + rec.order_quantity,
    0
  )

  // Fetch real forecast data for detail dialog (from real-time APIs)
  const { data: forecastChartData = [] } = useQuery(
    ['recommendationForecast', storeId, selectedRecommendation?.id],
    async () => {
      if (!selectedRecommendation) return []
      const response = await analyticsAPI.getForecastChart(storeId, 7)
      const chartData = response.data?.chart_data || []
      // Scale the forecast data based on the product's forecasted demand
      const scaleFactor = selectedRecommendation.forecasted_demand / 
        (chartData.reduce((sum: number, d: any) => sum + d.forecast, 0) || 1)
      return chartData.map((d: any) => ({
        day: d.day,
        demand: Math.round(d.forecast * scaleFactor),
        weather: d.weather,
        isHoliday: d.is_holiday
      }))
    },
    {
      enabled: !!selectedRecommendation && detailDialogOpen,
      staleTime: 60000
    }
  )

  const forecastData = forecastChartData.length > 0 
    ? forecastChartData 
    : (selectedRecommendation 
        ? Array.from({ length: 7 }, (_, i) => ({
            day: i === 0 ? 'Today' : `Day ${i}`,
            demand: Math.round(selectedRecommendation.forecasted_demand / 7),
          }))
        : [])

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading recommendations...</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Orders & Recommendations
        </Typography>
        {selectedItems.size > 0 && (
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircle />}
            onClick={handleBulkApprove}
            disabled={approveMutation.isLoading}
          >
            Approve Selected ({selectedItems.size})
          </Button>
        )}
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Total Recommendations
              </Typography>
              <Typography variant="h4">{recommendations.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Total Units to Order
              </Typography>
              <Typography variant="h4">{totalOrderValue} units</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Markdown Recommendations
              </Typography>
              <Typography variant="h4">
                {recommendations.filter((r) => r.markdown).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recommendations Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Today's Recommendations
          </Typography>
          {recommendations.length === 0 ? (
            <Alert severity="info">No pending recommendations at this time.</Alert>
          ) : (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        indeterminate={
                          selectedItems.size > 0 && selectedItems.size < recommendations.length
                        }
                        checked={selectedItems.size === recommendations.length && recommendations.length > 0}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedItems(new Set(recommendations.map((r) => r.id)))
                          } else {
                            setSelectedItems(new Set())
                          }
                        }}
                      />
                    </TableCell>
                    <TableCell>Product</TableCell>
                    <TableCell align="right">Current Stock</TableCell>
                    <TableCell align="right">Forecasted Demand</TableCell>
                    <TableCell align="right">Order Quantity</TableCell>
                    <TableCell>Confidence</TableCell>
                    <TableCell>Markdown</TableCell>
                    <TableCell align="center">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recommendations.map((rec) => (
                    <TableRow key={rec.id} hover>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={selectedItems.has(rec.id)}
                          onChange={() => toggleSelection(rec.id)}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {rec.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          SKU: {rec.sku_id}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">{rec.current_stock}</TableCell>
                      <TableCell align="right">{rec.forecasted_demand.toFixed(1)}</TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={500}>
                          {rec.order_quantity}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={`${(rec.confidence * 100).toFixed(0)}%`}
                          size="small"
                          color={rec.confidence > 0.8 ? 'success' : rec.confidence > 0.6 ? 'warning' : 'error'}
                        />
                      </TableCell>
                      <TableCell>
                        {rec.markdown ? (
                          <Chip
                            label={`${rec.markdown.discount_percent}% off`}
                            size="small"
                            color="warning"
                            icon={<Warning />}
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <Box display="flex" gap={1} justifyContent="center">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => {
                              setSelectedRecommendation(rec)
                              setDetailDialogOpen(true)
                            }}
                          >
                            <Visibility />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="success"
                            onClick={() => handleApprove(rec.id)}
                            disabled={approveMutation.isLoading || rejectMutation.isLoading}
                          >
                            <CheckCircle />
                          </IconButton>
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleReject(rec.id)}
                            disabled={approveMutation.isLoading || rejectMutation.isLoading}
                          >
                            <Cancel />
                          </IconButton>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Recommendation Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h5">
              {selectedRecommendation?.name} - Order Recommendation
            </Typography>
            <Chip
              label={`${selectedRecommendation ? (selectedRecommendation.confidence * 100).toFixed(0) : 0}% confidence`}
              color={selectedRecommendation && selectedRecommendation.confidence > 0.8 ? 'success' : 'warning'}
            />
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedRecommendation && (
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Current Stock
                    </Typography>
                    <Typography variant="h4">{selectedRecommendation.current_stock} units</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} md={6}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Forecasted Demand (7 days)
                    </Typography>
                    <Typography variant="h4">
                      {selectedRecommendation.forecasted_demand.toFixed(1)} units
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12}>
                <Card variant="outlined" sx={{ borderColor: 'primary.main' }}>
                  <CardContent>
                    <Box display="flex" alignItems="center" gap={2} mb={2}>
                      <ShoppingCart color="primary" />
                      <Typography variant="h6">Recommended Order Quantity</Typography>
                    </Box>
                    <Typography variant="h3" color="primary" gutterBottom>
                      {selectedRecommendation.order_quantity} units
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Based on forecasted demand and current inventory levels
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
              {selectedRecommendation.markdown && (
                <Grid item xs={12}>
                  <Alert severity="warning" icon={<Warning />}>
                    <Typography variant="subtitle2" gutterBottom>
                      Markdown Recommendation
                    </Typography>
                    <Typography variant="body2">
                      Apply <strong>{selectedRecommendation.markdown.discount_percent}% discount</strong>{' '}
                      starting {format(new Date(selectedRecommendation.markdown.effective_date), 'MMM dd, yyyy')}
                    </Typography>
                    <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                      Reason: {selectedRecommendation.markdown.reason}
                    </Typography>
                  </Alert>
                </Grid>
              )}
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>
                  7-Day Demand Forecast
                </Typography>
                <ResponsiveContainer width="100%" height={250}>
                  <LineChart data={forecastData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="demand"
                      stroke="#1976d2"
                      strokeWidth={2}
                      name="Forecasted Demand"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<Cancel />}
            onClick={() => {
              handleReject(selectedRecommendation!.id)
              setDetailDialogOpen(false)
            }}
            disabled={approveMutation.isLoading || rejectMutation.isLoading}
          >
            Reject
          </Button>
          <Button
            variant="contained"
            color="success"
            startIcon={<CheckCircle />}
            onClick={() => {
              handleApprove(selectedRecommendation!.id)
              setDetailDialogOpen(false)
            }}
            disabled={approveMutation.isLoading || rejectMutation.isLoading}
          >
            Approve Order
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  )
}

export default OrdersPage
