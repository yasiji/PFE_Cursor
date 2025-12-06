import { useState } from 'react'
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
} from '@mui/material'
import { Clear } from '@mui/icons-material'

interface FilterBarProps {
  onCategoryChange?: (category: string) => void
  onProductChange?: (product: string) => void
  onStoreChange?: (store: string) => void
  showStore?: boolean
  showProduct?: boolean
  showCategory?: boolean
  categories?: string[]
  products?: Array<{ id: string; name: string }>
  stores?: Array<{ id: string; name: string }>
}

const FilterBar = ({
  onCategoryChange,
  onProductChange,
  onStoreChange,
  showStore = false,
  showProduct = false,
  showCategory = false,
  categories = [],
  products = [],
  stores = [],
}: FilterBarProps) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  const [selectedProduct, setSelectedProduct] = useState<string>('')
  const [selectedStore, setSelectedStore] = useState<string>('')

  const handleCategoryChange = (value: string) => {
    setSelectedCategory(value)
    onCategoryChange?.(value)
  }

  const handleProductChange = (value: string) => {
    setSelectedProduct(value)
    onProductChange?.(value)
  }

  const handleStoreChange = (value: string) => {
    setSelectedStore(value)
    onStoreChange?.(value)
  }

  const hasActiveFilters = selectedCategory || selectedProduct || selectedStore

  const clearFilters = () => {
    setSelectedCategory('')
    setSelectedProduct('')
    setSelectedStore('')
    onCategoryChange?.('')
    onProductChange?.('')
    onStoreChange?.('')
  }

  return (
    <Box display="flex" gap={2} alignItems="center" flexWrap="wrap" sx={{ mb: 2 }}>
      {showCategory && (
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Category</InputLabel>
          <Select
            value={selectedCategory}
            label="Category"
            onChange={(e) => handleCategoryChange(e.target.value)}
          >
            <MenuItem value="">All Categories</MenuItem>
            {categories.map((cat) => (
              <MenuItem key={cat} value={cat}>
                {cat}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {showProduct && (
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Product</InputLabel>
          <Select
            value={selectedProduct}
            label="Product"
            onChange={(e) => handleProductChange(e.target.value)}
          >
            <MenuItem value="">All Products</MenuItem>
            {products.map((product) => (
              <MenuItem key={product.id} value={product.id}>
                {product.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {showStore && (
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Store</InputLabel>
          <Select
            value={selectedStore}
            label="Store"
            onChange={(e) => handleStoreChange(e.target.value)}
          >
            <MenuItem value="">All Stores</MenuItem>
            {stores.map((store) => (
              <MenuItem key={store.id} value={store.id}>
                {store.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}

      {hasActiveFilters && (
        <Box display="flex" alignItems="center" gap={1}>
          {selectedCategory && (
            <Chip
              label={`Category: ${selectedCategory}`}
              size="small"
              onDelete={() => handleCategoryChange('')}
            />
          )}
          {selectedProduct && (
            <Chip
              label={`Product: ${selectedProduct}`}
              size="small"
              onDelete={() => handleProductChange('')}
            />
          )}
          {selectedStore && (
            <Chip
              label={`Store: ${selectedStore}`}
              size="small"
              onDelete={() => handleStoreChange('')}
            />
          )}
          <IconButton size="small" onClick={clearFilters} title="Clear all filters">
            <Clear />
          </IconButton>
        </Box>
      )}
    </Box>
  )
}

export default FilterBar

