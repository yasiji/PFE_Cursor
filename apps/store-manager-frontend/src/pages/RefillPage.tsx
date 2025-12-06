import { useState } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  CircularProgress,
  Button,
  Tooltip,
  Tabs,
  Tab,
  LinearProgress,
} from '@mui/material'
import {
  Refresh,
  FileDownload,
  ShoppingCart,
  Inventory,
  LocalShipping,
  TrendingUp,
  Warning,
  CheckCircle,
  CalendarMonth,
} from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { useQueries } from 'react-query'
import { storeAPI } from '../services/api'
import { format, addDays } from 'date-fns'

interface RefillItem {
  sku_id: string
  product_name: string
  category?: string
  current_shelf_quantity: number
  current_backroom_quantity: number
  total_quantity?: number
  forecasted_demand_tomorrow: number
  recommended_shelf_quantity: number
  refill_quantity: number
  order_quantity: number
  in_transit_quantity: number
  expected_arrival_date: string | null
  transit_days: number
  days_until_expiry?: number | null
  expiry_date?: string | null
  expiry_buckets?: { '1_3': number; '4_7': number; '8_plus': number } | null
  needs_attention?: boolean
  factors: {
    day_of_week: string
    is_weekend: boolean
    is_holiday: boolean
    weather: string
    temperature: number | null
    seasonality_factor: number
  }
}

interface RefillPlan {
  store_id: string
  target_date: string
  total_items_to_refill: number
  total_items_to_order: number
  total_in_transit: number
  refill_items: RefillItem[]
  generated_at: string
}

interface DaySummary {
  date: Date
  dateStr: string
  dayLabel: string
  plan: RefillPlan | null
  isLoading: boolean
  error: unknown
}

const RefillPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const [selectedDay, setSelectedDay] = useState(0)
  const [inventoryFilter, setInventoryFilter] = useState<'all' | 'expiring' | 'transit' | 'discard'>('all')
  
  // Generate dates for the next 7 days
  const dates = Array.from({ length: 7 }, (_, i) => {
    const date = addDays(new Date(), i + 1)
    return {
      date,
      dateStr: format(date, 'yyyy-MM-dd'),
      dayLabel: i === 0 ? 'Tomorrow' : format(date, 'EEE, MMM d')
    }
  })

  // Fetch refill plans for all 7 days
  const refillQueries = useQueries(
    dates.map(({ dateStr }) => ({
      queryKey: ['refillPlan', storeId, dateStr],
      queryFn: async () => {
        const response = await storeAPI.getRefillPlan(storeId, dateStr)
        return response.data as RefillPlan
      },
      refetchInterval: 300000,
      retry: 1,
    }))
  )

  // Combine data for display
  const daySummaries: DaySummary[] = dates.map((d, i) => ({
    ...d,
    plan: refillQueries[i].data || null,
    isLoading: refillQueries[i].isLoading,
    error: refillQueries[i].error
  }))

  const selectedPlan = daySummaries[selectedDay]?.plan

  const handleExport = () => {
    if (!selectedPlan) return

    const headers = [
      'SKU ID',
      'Product Name',
      'Current Shelf Qty',
      'Current Backroom Qty',
      'Forecast',
      'Recommended Shelf Qty',
      'Refill Qty',
      'Order Qty',
      'In Transit',
      'Day of Week',
      'Weather',
    ]

    const rows = selectedPlan.refill_items.map((item) => [
      item.sku_id,
      item.product_name,
      item.current_shelf_quantity.toFixed(2),
      item.current_backroom_quantity.toFixed(2),
      item.forecasted_demand_tomorrow.toFixed(2),
      item.recommended_shelf_quantity.toFixed(2),
      item.refill_quantity.toFixed(2),
      item.order_quantity.toFixed(2),
      item.in_transit_quantity.toFixed(2),
      item.factors.day_of_week,
      item.factors.weather,
    ])

    const csvContent = [headers, ...rows].map((row) => row.join(',')).join('\n')
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `refill-plan-${daySummaries[selectedDay].dateStr}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const getFactorIcon = (factors: RefillItem['factors']) => {
    const icons = []
    if (factors.is_weekend) {
      icons.push(
        <Tooltip title="Weekend - Higher demand expected" key="weekend">
          <Chip label="Weekend" size="small" color="primary" sx={{ mr: 0.5 }} />
        </Tooltip>
      )
    }
    if (factors.is_holiday) {
      icons.push(
        <Tooltip title="Holiday - Special demand pattern" key="holiday">
          <Chip label="Holiday" size="small" color="warning" sx={{ mr: 0.5 }} />
        </Tooltip>
      )
    }
    if (factors.weather !== 'normal') {
      icons.push(
        <Tooltip title={`Weather: ${factors.weather}`} key="weather">
          <Chip label={factors.weather} size="small" color="info" sx={{ mr: 0.5 }} />
        </Tooltip>
      )
    }
    return icons.length > 0 ? <Box display="flex" gap={0.5}>{icons}</Box> : null
  }

  const getRefillStatus = (item: RefillItem): 'sufficient' | 'needs_refill' | 'needs_order' => {
    if (item.order_quantity > 0) return 'needs_order'
    if (item.refill_quantity > 0) return 'needs_refill'
    return 'sufficient'
  }

  // Calculate 7-day summary
  const weekSummary = {
    totalRefills: daySummaries.reduce((sum, d) => sum + (d.plan?.total_items_to_refill || 0), 0),
    totalOrders: daySummaries.reduce((sum, d) => sum + (d.plan?.total_items_to_order || 0), 0),
    daysNeedingOrders: daySummaries.filter((d) => d.plan && d.plan.total_items_to_order > 0).length,
  }

  const isAnyLoading = refillQueries.some((q) => q.isLoading)

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
            7-Day Refill Plan
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Plan your shelf refills and orders for the next week
          </Typography>
        </Box>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refillQueries.forEach((q) => q.refetch())}
            disabled={isAnyLoading}
          >
            Refresh All
          </Button>
          <Button
            variant="contained"
            startIcon={<FileDownload />}
            onClick={handleExport}
            disabled={!selectedPlan || selectedPlan.refill_items.length === 0}
          >
            Export CSV
          </Button>
        </Box>
      </Box>

      {/* Week Overview Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <CalendarMonth color="primary" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    7-Day Total Refills
                  </Typography>
                  <Typography variant="h4">{weekSummary.totalRefills.toFixed(0)}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    units to move to shelves
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <ShoppingCart color="warning" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    7-Day Total Orders
                  </Typography>
                  <Typography variant="h4">{weekSummary.totalOrders.toFixed(0)}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    units to order from supplier
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Warning color="error" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Days Needing Orders
                  </Typography>
                  <Typography variant="h4">{weekSummary.daysNeedingOrders}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    out of 7 days
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Day Selector Tabs */}
      <Card sx={{ mb: 3 }}>
        <Tabs
          value={selectedDay}
          onChange={(_, newValue) => setSelectedDay(newValue)}
          variant="fullWidth"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          {daySummaries.map((day, index) => (
            <Tab
              key={day.dateStr}
              label={
                <Box textAlign="center">
                  <Typography variant="caption" display="block">
                    {index === 0 ? 'Tomorrow' : format(day.date, 'EEE')}
                  </Typography>
                  <Typography variant="body2" fontWeight={500}>
                    {format(day.date, 'MMM d')}
                  </Typography>
                  {day.isLoading ? (
                    <CircularProgress size={12} />
                  ) : day.plan ? (
                    <Box display="flex" gap={0.5} justifyContent="center" mt={0.5}>
                      {day.plan.total_items_to_refill > 0 && (
                        <Chip
                          label={day.plan.total_items_to_refill.toFixed(0)}
                          size="small"
                          color="warning"
                          sx={{ height: 18, fontSize: 10 }}
                        />
                      )}
                      {day.plan.total_items_to_order > 0 && (
                        <Chip
                          label={day.plan.total_items_to_order.toFixed(0)}
                          size="small"
                          color="error"
                          sx={{ height: 18, fontSize: 10 }}
                        />
                      )}
                      {day.plan.total_items_to_refill === 0 && day.plan.total_items_to_order === 0 && (
                        <CheckCircle color="success" sx={{ fontSize: 16 }} />
                      )}
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary">-</Typography>
                  )}
                </Box>
              }
            />
          ))}
        </Tabs>
        
        {isAnyLoading && <LinearProgress />}
      </Card>

      {/* Selected Day Details */}
      {daySummaries[selectedDay].isLoading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Loading refill plan for {daySummaries[selectedDay].dayLabel}...
          </Typography>
        </Box>
      ) : daySummaries[selectedDay].error ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading refill plan for {daySummaries[selectedDay].dayLabel}. Please try again.
        </Alert>
      ) : !selectedPlan || selectedPlan.refill_items.length === 0 ? (
        <Alert severity="success" icon={<CheckCircle />}>
          <Typography variant="subtitle1" fontWeight={500}>
            All set for {daySummaries[selectedDay].dayLabel}!
          </Typography>
          No refills needed. All shelves are adequately stocked for forecasted demand.
        </Alert>
      ) : (
        <>
          {/* Day Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <Inventory color="primary" />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Items to Refill
                      </Typography>
                      <Typography variant="h4">
                        {selectedPlan.refill_items.filter((item) => item.refill_quantity > 0).length}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {selectedPlan.total_items_to_refill.toFixed(0)} total units
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <ShoppingCart color="warning" />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Items to Order
                      </Typography>
                      <Typography variant="h4">
                        {selectedPlan.refill_items.filter((item) => item.order_quantity > 0).length}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {selectedPlan.total_items_to_order.toFixed(0)} total units
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <LocalShipping color="info" />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        In Transit
                      </Typography>
                      <Typography variant="h4">{selectedPlan.total_in_transit}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Arriving soon
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={3}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={2}>
                    <TrendingUp color="success" />
                    <Box>
                      <Typography variant="subtitle2" color="text.secondary">
                        Forecast for Day
                      </Typography>
                      <Typography variant="h4">
                        {selectedPlan.refill_items
                          .reduce((sum, item) => sum + item.forecasted_demand_tomorrow, 0)
                          .toFixed(0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Total units expected
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Alerts */}
          {selectedPlan.refill_items.filter((item) => item.order_quantity > 0).length > 0 && (
            <Alert severity="warning" sx={{ mb: 3 }}>
              <strong>
                {selectedPlan.refill_items.filter((item) => item.order_quantity > 0).length} products
              </strong>{' '}
              need to be ordered. Backroom stock is insufficient to meet forecasted demand.
            </Alert>
          )}

          {/* Inventory Filter Tabs */}
          <Card sx={{ mb: 3 }}>
            <Tabs
              value={inventoryFilter}
              onChange={(_, newValue) => setInventoryFilter(newValue)}
              sx={{ borderBottom: 1, borderColor: 'divider' }}
            >
              <Tab value="all" label={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography>All Inventory</Typography>
                  <Chip label={selectedPlan.refill_items.length} size="small" />
                </Box>
              } />
              <Tab value="expiring" label={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography>Expiring Soon</Typography>
                  <Chip 
                    label={selectedPlan.refill_items.filter(i => i.days_until_expiry !== null && i.days_until_expiry !== undefined && i.days_until_expiry <= 3).length} 
                    size="small" 
                    color="warning" 
                  />
                </Box>
              } />
              <Tab value="transit" label={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography>In Transit</Typography>
                  <Chip 
                    label={selectedPlan.refill_items.filter(i => i.in_transit_quantity > 0).length} 
                    size="small" 
                    color="info" 
                  />
                </Box>
              } />
              <Tab value="discard" label={
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography>To Discard</Typography>
                  <Chip 
                    label={selectedPlan.refill_items.filter(i => i.days_until_expiry !== null && i.days_until_expiry !== undefined && i.days_until_expiry <= 0).length} 
                    size="small" 
                    color="error" 
                  />
                </Box>
              } />
            </Tabs>
          </Card>

          {/* Refill Table */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Detailed Refill Plan - {daySummaries[selectedDay].dayLabel}
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Product</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell align="right">On Shelves</TableCell>
                      <TableCell align="right">In Stock (Backroom)</TableCell>
                      <TableCell align="right">Total</TableCell>
                      <TableCell>Expiry Date</TableCell>
                      <TableCell>Days Until Expiry</TableCell>
                      <TableCell>Expiry Buckets</TableCell>
                      <TableCell align="right">In Transit</TableCell>
                      <TableCell align="right">To Discard</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selectedPlan.refill_items
                      .filter(item => {
                        if (inventoryFilter === 'all') return true
                        if (inventoryFilter === 'expiring') return item.days_until_expiry !== null && item.days_until_expiry !== undefined && item.days_until_expiry <= 3 && item.days_until_expiry > 0
                        if (inventoryFilter === 'transit') return item.in_transit_quantity > 0
                        if (inventoryFilter === 'discard') return item.days_until_expiry !== null && item.days_until_expiry !== undefined && item.days_until_expiry <= 0
                        return true
                      })
                      .map((item) => {
                      const isExpiring = item.days_until_expiry !== null && item.days_until_expiry !== undefined && item.days_until_expiry <= 3
                      const isExpired = item.days_until_expiry !== null && item.days_until_expiry !== undefined && item.days_until_expiry <= 0
                      
                      return (
                        <TableRow
                          key={item.sku_id}
                          sx={{
                            backgroundColor: isExpired
                              ? 'rgba(211, 47, 47, 0.15)'
                              : isExpiring
                              ? 'rgba(237, 108, 2, 0.08)'
                              : 'transparent',
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={500}>
                              {item.product_name}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              SKU: {item.sku_id}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip label={item.category || 'General'} size="small" variant="outlined" />
                          </TableCell>
                          <TableCell align="right">
                            <Typography color="primary" fontWeight={500}>
                              {item.current_shelf_quantity.toFixed(0)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">on display</Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography color="info.main" fontWeight={500}>
                              {item.current_backroom_quantity.toFixed(0)}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">in backroom</Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography fontWeight={600}>
                              {(item.total_quantity || (item.current_shelf_quantity + item.current_backroom_quantity)).toFixed(0)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {item.expiry_date ? (
                              <Typography variant="body2" color={isExpired ? 'error' : isExpiring ? 'warning.main' : 'text.primary'}>
                                {format(new Date(item.expiry_date), 'MMM dd, yyyy')}
                              </Typography>
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            {item.days_until_expiry !== null && item.days_until_expiry !== undefined ? (
                              <Chip
                                label={item.days_until_expiry <= 0 
                                  ? 'Expires Today' 
                                  : item.days_until_expiry === 1 
                                    ? '1 day remaining' 
                                    : `${item.days_until_expiry} days remaining`}
                                size="small"
                                color={isExpired ? 'error' : isExpiring ? 'warning' : 'success'}
                              />
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            {item.expiry_buckets ? (
                              <Box display="flex" gap={0.5} flexWrap="wrap">
                                {item.expiry_buckets['1_3'] > 0 && (
                                  <Chip label={`1-3d: ${item.expiry_buckets['1_3']}`} size="small" color="error" />
                                )}
                                {item.expiry_buckets['4_7'] > 0 && (
                                  <Chip label={`4-7d: ${item.expiry_buckets['4_7']}`} size="small" color="warning" />
                                )}
                                {item.expiry_buckets['8_plus'] > 0 && (
                                  <Chip label={`8+d: ${item.expiry_buckets['8_plus']}`} size="small" color="success" />
                                )}
                              </Box>
                            ) : (
                              <Typography variant="body2" color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {item.in_transit_quantity > 0 ? (
                              <Tooltip
                                title={
                                  item.expected_arrival_date
                                    ? `Arrives: ${format(new Date(item.expected_arrival_date), 'MMM dd')}`
                                    : 'In transit'
                                }
                              >
                                <Chip
                                  label={item.in_transit_quantity.toFixed(0)}
                                  size="small"
                                  color="info"
                                  icon={<LocalShipping />}
                                />
                              </Tooltip>
                            ) : (
                              <Typography color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {isExpired ? (
                              <Chip label="Discard" size="small" color="error" icon={<Warning />} />
                            ) : (
                              <Typography color="text.secondary">-</Typography>
                            )}
                          </TableCell>
                          <TableCell>
                            {isExpired ? (
                              <Chip icon={<Warning />} label="Expired" size="small" color="error" />
                            ) : isExpiring ? (
                              <Chip icon={<Warning />} label="Expiring" size="small" color="warning" />
                            ) : (
                              <Chip icon={<CheckCircle />} label="Normal" size="small" color="success" />
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  )
}

export default RefillPage
