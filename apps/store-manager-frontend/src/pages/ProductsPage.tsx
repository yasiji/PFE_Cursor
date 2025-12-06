import { useState, useMemo } from 'react'
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tabs,
  Tab,
  Alert,
} from '@mui/material'
import { Search, Visibility, ShoppingCart, Warning } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { useQuery } from 'react-query'
import { storeAPI } from '../services/api'
import { format } from 'date-fns'

interface Product {
  sku_id: string
  name: string
  category: string
  price: number
  current_stock: number
  items_sold_today: number
  items_sold_week: number
  items_sold_month: number
  expiry_date?: string
  days_until_expiry?: number
  items_on_shelves: number
  items_to_preorder: number
  items_discarded: number
  status: 'normal' | 'low_stock' | 'expiring' | 'expired'
}

const ProductsPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const [searchTerm, setSearchTerm] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [tabValue, setTabValue] = useState(0)

  const { data: products = [], isLoading } = useQuery<Product[]>(
    ['storeProducts', storeId],
    async () => {
      try {
        const response = await storeAPI.getStoreProducts(storeId)
        return response.data.map((item: any) => {
          // Determine status based on data
          let status: 'normal' | 'low_stock' | 'expiring' | 'expired' = 'normal'
          if (item.days_until_expiry !== null && item.days_until_expiry <= 1) {
            status = 'expired'
          } else if (item.days_until_expiry !== null && item.days_until_expiry <= 3) {
            status = 'expiring'
          } else if (item.current_stock < 10) {
            status = 'low_stock'
          }
          
          return {
            sku_id: item.sku_id,
            name: item.name,
            category: item.category || 'General',
            price: item.price || 0,
            current_stock: item.current_stock || 0,
            items_sold_today: item.items_sold_today || 0,
            items_sold_week: item.items_sold_week || 0,
            items_sold_month: item.items_sold_month || 0,
            expiry_date: item.expiry_date,
            days_until_expiry: item.days_until_expiry,
            items_on_shelves: item.items_on_shelves || 0,
            items_to_preorder: item.items_to_preorder || 0,
            items_discarded: item.items_discarded || 0,
            status,
          }
        })
      } catch (err) {
        throw new Error('Failed to load products data')
      }
    },
    {
      refetchInterval: 60000, // Refetch every minute
      retry: 1,
    }
  )

  const categories = useMemo(() => {
    const cats = new Set(products.map((p) => p.category))
    return Array.from(cats)
  }, [products])

  const filteredProducts = useMemo(() => {
    return products.filter((product) => {
      const matchesSearch =
        product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        product.sku_id.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesCategory =
        categoryFilter === 'all' || product.category === categoryFilter
      const matchesStatus =
        statusFilter === 'all' || product.status === statusFilter
      return matchesSearch && matchesCategory && matchesStatus
    })
  }, [products, searchTerm, categoryFilter, statusFilter])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'expired':
        return 'error'
      case 'expiring':
        return 'warning'
      case 'low_stock':
        return 'warning'
      default:
        return 'success'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'expired':
        return 'Expired'
      case 'expiring':
        return 'Expiring Soon'
      case 'low_stock':
        return 'Low Stock'
      default:
        return 'Normal'
    }
  }

  const getExpiryColor = (days?: number) => {
    if (!days) return 'default'
    if (days <= 1) return 'error'
    if (days <= 3) return 'warning'
    return 'success'
  }

  const handleViewDetails = (product: Product) => {
    setSelectedProduct(product)
    setDetailDialogOpen(true)
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading products...</Typography>
      </Box>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Products Management
      </Typography>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search products..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Search />
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Category</InputLabel>
                <Select
                  value={categoryFilter}
                  label="Category"
                  onChange={(e) => setCategoryFilter(e.target.value)}
                >
                  <MenuItem value="all">All Categories</MenuItem>
                  {categories.map((cat) => (
                    <MenuItem key={cat} value={cat}>
                      {cat}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={statusFilter}
                  label="Status"
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="all">All Status</MenuItem>
                  <MenuItem value="normal">Normal</MenuItem>
                  <MenuItem value="low_stock">Low Stock</MenuItem>
                  <MenuItem value="expiring">Expiring Soon</MenuItem>
                  <MenuItem value="expired">Expired</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Typography variant="body2" color="text.secondary">
                {filteredProducts.length} products
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Products Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>SKU ID</TableCell>
              <TableCell>Product Name</TableCell>
              <TableCell>Category</TableCell>
              <TableCell align="right">Price</TableCell>
              <TableCell align="right">Stock</TableCell>
              <TableCell align="right">Sold Today</TableCell>
              <TableCell>Expiry Date</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredProducts.map((product) => (
              <TableRow
                key={product.sku_id}
                sx={{
                  '&:hover': { backgroundColor: 'action.hover' },
                  backgroundColor:
                    product.status === 'expired'
                      ? 'error.light'
                      : product.status === 'expiring'
                      ? 'warning.light'
                      : 'inherit',
                }}
              >
                <TableCell>{product.sku_id}</TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={500}>
                    {product.name}
                  </Typography>
                </TableCell>
                <TableCell>{product.category}</TableCell>
                <TableCell align="right">${product.price.toFixed(2)}</TableCell>
                <TableCell align="right">
                  <Box display="flex" alignItems="center" justifyContent="flex-end" gap={1}>
                    <Typography variant="body2">{product.current_stock}</Typography>
                    {product.status === 'low_stock' && (
                      <Warning color="warning" fontSize="small" />
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">{product.items_sold_today}</TableCell>
                <TableCell>
                  {product.expiry_date ? (
                    <Box>
                      <Typography variant="body2">
                        {format(new Date(product.expiry_date), 'MMM dd, yyyy')}
                      </Typography>
                      {product.days_until_expiry !== undefined && (
                        <Chip
                          label={`${product.days_until_expiry} days`}
                          size="small"
                          color={getExpiryColor(product.days_until_expiry)}
                          sx={{ mt: 0.5 }}
                        />
                      )}
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary">
                      N/A
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={getStatusLabel(product.status)}
                    size="small"
                    color={getStatusColor(product.status)}
                  />
                </TableCell>
                <TableCell align="center">
                  <IconButton
                    size="small"
                    onClick={() => handleViewDetails(product)}
                    color="primary"
                  >
                    <Visibility />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Product Details Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="h5">
              {selectedProduct?.name} ({selectedProduct?.sku_id})
            </Typography>
            <Chip
              label={selectedProduct ? getStatusLabel(selectedProduct.status) : ''}
              color={selectedProduct ? getStatusColor(selectedProduct.status) : 'default'}
            />
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedProduct && (
            <Box>
              <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)} sx={{ mb: 3 }}>
                <Tab label="Overview" />
                <Tab label="Sales" />
                <Tab label="Inventory" />
                <Tab label="Recommendations" />
              </Tabs>

              {tabValue === 0 && (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Price
                        </Typography>
                        <Typography variant="h5">${selectedProduct.price.toFixed(2)}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Category
                        </Typography>
                        <Typography variant="h6">{selectedProduct.category}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Current Stock
                        </Typography>
                        <Typography variant="h5">{selectedProduct.current_stock} units</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items on Shelves
                        </Typography>
                        <Typography variant="h5">
                          {selectedProduct.items_on_shelves} units
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  {selectedProduct.expiry_date && (
                    <Grid item xs={12}>
                      <Card variant="outlined">
                        <CardContent>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            Expiry Information
                          </Typography>
                          <Box display="flex" alignItems="center" gap={2} mt={1}>
                            <Typography variant="body1">
                              Expiry Date:{' '}
                              {format(new Date(selectedProduct.expiry_date), 'MMMM dd, yyyy')}
                            </Typography>
                            {selectedProduct.days_until_expiry !== undefined && (
                              <Chip
                                label={`${selectedProduct.days_until_expiry} days remaining`}
                                color={getExpiryColor(selectedProduct.days_until_expiry)}
                              />
                            )}
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  )}
                </Grid>
              )}

              {tabValue === 1 && (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items Sold Today
                        </Typography>
                        <Typography variant="h4">{selectedProduct.items_sold_today}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items Sold This Week
                        </Typography>
                        <Typography variant="h4">{selectedProduct.items_sold_week}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items Sold This Month
                        </Typography>
                        <Typography variant="h4">{selectedProduct.items_sold_month}</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Revenue (This Month)
                        </Typography>
                        <Typography variant="h5">
                          ${(selectedProduct.items_sold_month * selectedProduct.price).toFixed(2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              )}

              {tabValue === 2 && (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Current Stock
                        </Typography>
                        <Typography variant="h4">{selectedProduct.current_stock} units</Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items on Shelves
                        </Typography>
                        <Typography variant="h4">
                          {selectedProduct.items_on_shelves} units
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                          Items Discarded (Expiry)
                        </Typography>
                        <Typography variant="h4" color="error">
                          {selectedProduct.items_discarded} units
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  {selectedProduct.expiry_date && (
                    <Grid item xs={12}>
                      <Alert severity={selectedProduct.days_until_expiry && selectedProduct.days_until_expiry <= 3 ? 'warning' : 'info'}>
                        Expiry Date: {format(new Date(selectedProduct.expiry_date), 'MMMM dd, yyyy')}
                        {selectedProduct.days_until_expiry !== undefined && (
                          <> ({selectedProduct.days_until_expiry} days remaining)</>
                        )}
                      </Alert>
                    </Grid>
                  )}
                </Grid>
              )}

              {tabValue === 3 && (
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Card variant="outlined" sx={{ borderColor: 'primary.main' }}>
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={2} mb={2}>
                          <ShoppingCart color="primary" />
                          <Typography variant="h6">Pre-Order Recommendation</Typography>
                        </Box>
                        <Typography variant="body1" gutterBottom>
                          Recommended Order Quantity: <strong>{selectedProduct.items_to_preorder} units</strong>
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Based on forecasted demand and current stock levels
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                  {selectedProduct.days_until_expiry !== undefined &&
                    selectedProduct.days_until_expiry <= 3 && (
                      <Grid item xs={12}>
                        <Card variant="outlined" sx={{ borderColor: 'warning.main' }}>
                          <CardContent>
                            <Box display="flex" alignItems="center" gap={2} mb={2}>
                              <Warning color="warning" />
                              <Typography variant="h6">Markdown Recommendation</Typography>
                            </Box>
                            <Typography variant="body1" gutterBottom>
                              Suggested Discount: <strong>35%</strong>
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Apply discount to prevent waste. Product expires in{' '}
                              {selectedProduct.days_until_expiry} days.
                            </Typography>
                          </CardContent>
                        </Card>
                      </Grid>
                    )}
                </Grid>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
          <Button variant="contained" onClick={() => setDetailDialogOpen(false)}>
            View Full Details
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ProductsPage
