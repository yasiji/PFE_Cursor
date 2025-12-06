import { useState, useMemo } from 'react'
import { useQuery } from 'react-query'
import { storeAPI } from '../services/api'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Tabs,
  Tab,
  Grid,
  Alert,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import { Warning, Inventory, LocalShipping, Delete } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { format } from 'date-fns'

interface InventoryItem {
  sku_id: string
  name: string
  category: string
  current_quantity: number  // Total (for backward compatibility)
  shelf_quantity: number  // Quantity on display shelves
  backroom_quantity: number  // Quantity in backroom/warehouse
  total_quantity: number  // Computed: shelf + backroom
  expiry_date: string
  days_until_expiry: number
  quantity_expiring_1_3_days: number
  quantity_expiring_4_7_days: number
  quantity_expiring_8_plus_days: number
  in_transit: number
  to_be_discarded: number
  status: 'normal' | 'expiring' | 'expired'
}

const InventoryPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const [tabValue, setTabValue] = useState(0)
  const [discardDialogOpen, setDiscardDialogOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null)

  const { data: inventoryData = [], isLoading, error } = useQuery<InventoryItem[]>(
    ['storeInventory', storeId],
    async () => {
      try {
        const response = await storeAPI.getStoreInventory(storeId)
        return response.data.map((item: any) => {
          const baselineQuantity = item.current_quantity ?? 0
          const shelfQuantity = item.shelf_quantity ?? baselineQuantity * 0.7
          const backroomQuantity =
            item.backroom_quantity ?? Math.max(baselineQuantity - shelfQuantity, 0)
          const totalQuantityFromComponents = (shelfQuantity ?? 0) + (backroomQuantity ?? 0)
          const totalQuantity = item.total_quantity ?? (totalQuantityFromComponents || baselineQuantity)

          // Determine status
          let status: 'normal' | 'expiring' | 'expired' = 'normal'
          if (item.days_until_expiry !== null && item.days_until_expiry <= 1) {
            status = 'expired'
          } else if (item.days_until_expiry !== null && item.days_until_expiry <= 3) {
            status = 'expiring'
          } else if (item.current_quantity < 10) {
            status = 'expiring' // Treat low stock as expiring for visibility
          }
          
          return {
            sku_id: item.sku_id,
            name: item.name,
            category: item.category || 'General',
            current_quantity: baselineQuantity,
            shelf_quantity: shelfQuantity,
            backroom_quantity: backroomQuantity,
            total_quantity: totalQuantity,
            expiry_date: item.expiry_date,
            days_until_expiry: item.days_until_expiry,
            quantity_expiring_1_3_days: item.quantity_expiring_1_3_days || 0,
            quantity_expiring_4_7_days: item.quantity_expiring_4_7_days || 0,
            quantity_expiring_8_plus_days: item.quantity_expiring_8_plus_days || 0,
            in_transit: item.in_transit || 0,
            to_be_discarded: item.to_be_discarded || 0,
            status,
          }
        })
      } catch (err) {
        throw new Error('Failed to load inventory data')
      }
    },
    {
      refetchInterval: 60000, // Refetch every minute
      retry: 2,
    }
  )

  const urgentItems = useMemo(
    () => inventoryData.filter((item) => item.days_until_expiry <= 3),
    [inventoryData]
  )

  const itemsToDiscard = useMemo(
    () => inventoryData.filter((item) => item.to_be_discarded > 0),
    [inventoryData]
  )

  const getExpiryColor = (days: number) => {
    if (days <= 1) return 'error'
    if (days <= 3) return 'warning'
    return 'success'
  }

  const getExpiryLabel = (days: number) => {
    if (days <= 1) return 'Expires Today'
    if (days <= 3) return 'Expires Soon'
    return `${days} days remaining`
  }

  const handleDiscard = (item: InventoryItem) => {
    setSelectedItem(item)
    setDiscardDialogOpen(true)
  }

  const totalInventory = inventoryData.reduce((sum, item) => sum + (item.total_quantity || item.current_quantity), 0)
  const totalOnShelves = inventoryData.reduce((sum, item) => sum + (item.shelf_quantity || 0), 0)
  const totalInBackroom = inventoryData.reduce((sum, item) => sum + (item.backroom_quantity || 0), 0)
  const totalInTransit = inventoryData.reduce((sum, item) => sum + item.in_transit, 0)
  const totalToDiscard = inventoryData.reduce((sum, item) => sum + item.to_be_discarded, 0)

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading inventory...</Typography>
      </Box>
    )
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error">Error loading inventory data. Please try again later.</Alert>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Inventory Management
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Inventory color="primary" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Total Inventory
                  </Typography>
                  <Typography variant="h4">{Math.round(totalInventory)} units</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {Math.round(totalOnShelves)} on shelves, {Math.round(totalInBackroom)} in stock
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
                <Inventory color="success" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    On Shelves
                  </Typography>
                  <Typography variant="h4">{Math.round(totalOnShelves)} units</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Inventory color="info" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    In Stock (Backroom)
                  </Typography>
                  <Typography variant="h4">{Math.round(totalInBackroom)} units</Typography>
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
                  <Typography variant="h4">{totalInTransit} units</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Warning color="warning" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    Expiring Soon
                  </Typography>
                  <Typography variant="h4">{urgentItems.length} items</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Delete color="error" />
                <Box>
                  <Typography variant="subtitle2" color="text.secondary">
                    To Discard
                  </Typography>
                  <Typography variant="h4">{totalToDiscard} units</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Alerts */}
      {urgentItems.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          <strong>{urgentItems.length} items</strong> are expiring in the next 3 days. Take action
          immediately!
        </Alert>
      )}

      {/* Tabs */}
      <Card>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
            <Tab label="All Inventory" />
            <Tab
              label={
                <Box display="flex" alignItems="center" gap={1}>
                  <span>Expiring Soon</span>
                  {urgentItems.length > 0 && (
                    <Chip label={urgentItems.length} size="small" color="warning" />
                  )}
                </Box>
              }
            />
            <Tab
              label={
                <Box display="flex" alignItems="center" gap={1}>
                  <span>In Transit</span>
                  {totalInTransit > 0 && (
                    <Chip label={totalInTransit} size="small" color="info" />
                  )}
                </Box>
              }
            />
            <Tab
              label={
                <Box display="flex" alignItems="center" gap={1}>
                  <span>To Discard</span>
                  {totalToDiscard > 0 && (
                    <Chip label={totalToDiscard} size="small" color="error" />
                  )}
                </Box>
              }
            />
          </Tabs>
        </Box>

        <CardContent>
          {tabValue === 0 && (
            <TableContainer>
              <Table>
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
                  {inventoryData.map((item) => (
                    <TableRow key={item.sku_id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight={500}>
                          {item.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          SKU: {item.sku_id}
                        </Typography>
                      </TableCell>
                      <TableCell>{item.category}</TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={500} color="success.main">
                          {Math.round(item.shelf_quantity || 0)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          on display
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={500} color="info.main">
                          {Math.round(item.backroom_quantity || 0)}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          in backroom
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" fontWeight={600}>
                          {Math.round(item.total_quantity || item.current_quantity || 0)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        {item.expiry_date ? format(new Date(item.expiry_date), 'MMM dd, yyyy') : '-'}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getExpiryLabel(item.days_until_expiry)}
                          size="small"
                          color={getExpiryColor(item.days_until_expiry)}
                        />
                      </TableCell>
                      <TableCell>
                        <Box display="flex" gap={0.5} flexWrap="wrap">
                          {item.quantity_expiring_1_3_days > 0 && (
                            <Chip
                              label={`1-3d: ${item.quantity_expiring_1_3_days}`}
                              size="small"
                              color="error"
                            />
                          )}
                          {item.quantity_expiring_4_7_days > 0 && (
                            <Chip
                              label={`4-7d: ${item.quantity_expiring_4_7_days}`}
                              size="small"
                              color="warning"
                            />
                          )}
                          {item.quantity_expiring_8_plus_days > 0 && (
                            <Chip
                              label={`8+d: ${item.quantity_expiring_8_plus_days}`}
                              size="small"
                              color="success"
                            />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell align="right">
                        {item.in_transit > 0 ? (
                          <Chip
                            icon={<LocalShipping />}
                            label={item.in_transit}
                            size="small"
                            color="info"
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="right">
                        {item.to_be_discarded > 0 ? (
                          <Chip
                            icon={<Delete />}
                            label={item.to_be_discarded}
                            size="small"
                            color="error"
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            -
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={item.status === 'expiring' ? 'Expiring' : 'Normal'}
                          size="small"
                          color={item.status === 'expiring' ? 'warning' : 'success'}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {tabValue === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Items Expiring in 1-3 Days (Urgent)
              </Typography>
              {urgentItems.length === 0 ? (
                <Alert severity="success">No items expiring in the next 3 days!</Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Product</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell>Expiry Date</TableCell>
                        <TableCell>Days Left</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {urgentItems.map((item) => (
                        <TableRow key={item.sku_id}>
                          <TableCell>
                            <Typography variant="body2" fontWeight={500}>
                              {item.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">{item.current_quantity}</TableCell>
                          <TableCell>
                            {format(new Date(item.expiry_date), 'MMM dd, yyyy')}
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={`${item.days_until_expiry} days`}
                              size="small"
                              color="error"
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              color="warning"
                              startIcon={<Warning />}
                            >
                              Apply Markdown
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Items In Transit
              </Typography>
              {totalInTransit === 0 ? (
                <Alert severity="info">No items currently in transit.</Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Product</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell>Expected Arrival</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {inventoryData
                        .filter((item) => item.in_transit > 0)
                        .map((item) => (
                          <TableRow key={item.sku_id}>
                            <TableCell>
                              <Typography variant="body2" fontWeight={500}>
                                {item.name}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">{item.in_transit}</TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {format(new Date(Date.now() + 86400000), 'MMM dd, yyyy')}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                icon={<LocalShipping />}
                                label="In Transit"
                                size="small"
                                color="info"
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}

          {tabValue === 3 && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Items To Be Discarded
              </Typography>
              {totalToDiscard === 0 ? (
                <Alert severity="success">No items need to be discarded!</Alert>
              ) : (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Product</TableCell>
                        <TableCell align="right">Quantity</TableCell>
                        <TableCell>Reason</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {itemsToDiscard.map((item) => (
                        <TableRow key={item.sku_id}>
                          <TableCell>
                            <Typography variant="body2" fontWeight={500}>
                              {item.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">{item.to_be_discarded}</TableCell>
                          <TableCell>
                            <Chip label="Expired" size="small" color="error" />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              startIcon={<Delete />}
                              onClick={() => handleDiscard(item)}
                            >
                              Discard
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Discard Confirmation Dialog */}
      <Dialog open={discardDialogOpen} onClose={() => setDiscardDialogOpen(false)}>
        <DialogTitle>Confirm Discard</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to discard {selectedItem?.to_be_discarded} units of{' '}
            {selectedItem?.name}?
          </Typography>
          <Typography variant="body2" color="text.secondary">
            This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDiscardDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => {
              // TODO: Implement discard action
              setDiscardDialogOpen(false)
            }}
          >
            Confirm Discard
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default InventoryPage
