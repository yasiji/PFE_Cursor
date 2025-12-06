import { Outlet } from 'react-router-dom'
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  ListSubheader,
  Chip,
} from '@mui/material'
import { useNavigate, useLocation } from 'react-router-dom'
import DashboardIcon from '@mui/icons-material/Dashboard'
import InventoryIcon from '@mui/icons-material/Inventory'
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart'
import SettingsIcon from '@mui/icons-material/Settings'
import StoreIcon from '@mui/icons-material/Store'
import AddShoppingCartIcon from '@mui/icons-material/AddShoppingCart'
import TimelineIcon from '@mui/icons-material/Timeline'
import InsightsIcon from '@mui/icons-material/Insights'
import SmartToyIcon from '@mui/icons-material/SmartToy'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { useAuthStore } from '../../store/authStore'
import NotificationCenter from '../notifications/NotificationCenter'

const DRAWER_WIDTH = 280

const primaryMenu = [
  { text: 'Business Overview', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Forecast Outlook', icon: <TimelineIcon />, path: '/forecast' },
  { text: 'Refill Plan', icon: <AddShoppingCartIcon />, path: '/refill' },
  { text: 'Inventory & Expiry', icon: <InventoryIcon />, path: '/inventory' },
]

const secondaryMenu = [
  { text: 'Products', icon: <StoreIcon />, path: '/products' },
  { text: 'Orders', icon: <ShoppingCartIcon />, path: '/orders' },
  { text: 'Analytics (Legacy)', icon: <InsightsIcon />, path: '/analytics' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
]

// ML Dashboard opens in new tab (Streamlit)
const ML_DASHBOARD_URL = 'http://localhost:8501'

const MainLayout = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar
        position="fixed"
        sx={{
          width: `calc(100% - ${DRAWER_WIDTH}px)`,
          ml: `${DRAWER_WIDTH}px`,
          backgroundColor: '#1976d2',
        }}
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Store Manager Platform
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2">
              {user?.username} ({user?.role})
            </Typography>
            <NotificationCenter />
          </Box>
        </Toolbar>
      </AppBar>
      <Drawer
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            🛒 Replenishment
          </Typography>
        </Toolbar>
        <Box sx={{ overflow: 'auto', mt: 2 }}>
          <List
            subheader={
              <ListSubheader component="div" sx={{ lineHeight: 1.5 }}>
                Daily Operations
              </ListSubheader>
            }
          >
            {primaryMenu.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                  sx={{
                    '&.Mui-selected': {
                      backgroundColor: 'primary.light',
                      color: 'white',
                      '&:hover': {
                        backgroundColor: 'primary.main',
                      },
                      '& .MuiListItemIcon-root': {
                        color: 'white',
                      },
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: location.pathname === item.path ? 'white' : 'inherit',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          <Divider sx={{ my: 2 }} />
          <List
            subheader={
              <ListSubheader component="div" sx={{ lineHeight: 1.5 }}>
                More
              </ListSubheader>
            }
          >
            {secondaryMenu.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  selected={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                  sx={{
                    '&.Mui-selected': {
                      backgroundColor: 'primary.light',
                      color: 'white',
                      '&:hover': {
                        backgroundColor: 'primary.main',
                      },
                      '& .MuiListItemIcon-root': {
                        color: 'white',
                      },
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: location.pathname === item.path ? 'white' : 'inherit',
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          <Divider sx={{ my: 2 }} />
          <List
            subheader={
              <ListSubheader component="div" sx={{ lineHeight: 1.5 }}>
                Machine Learning
              </ListSubheader>
            }
          >
            <ListItem disablePadding>
              <ListItemButton
                onClick={() => window.open(ML_DASHBOARD_URL, '_blank')}
                sx={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  mx: 1,
                  borderRadius: 1,
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%)',
                  },
                  '& .MuiListItemIcon-root': {
                    color: 'white',
                  },
                }}
              >
                <ListItemIcon sx={{ color: 'white' }}>
                  <SmartToyIcon />
                </ListItemIcon>
                <ListItemText 
                  primary="ML Dashboard" 
                  secondary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)' }}>
                        Opens in new tab
                      </Typography>
                      <OpenInNewIcon sx={{ fontSize: 12, color: 'rgba(255,255,255,0.8)' }} />
                    </Box>
                  }
                />
                <Chip 
                  label="NEW" 
                  size="small" 
                  sx={{ 
                    bgcolor: '#ff9800', 
                    color: 'white', 
                    fontWeight: 'bold',
                    fontSize: '0.65rem',
                    height: 20
                  }} 
                />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
        <Box sx={{ p: 2, mt: 'auto' }}>
          <Typography variant="body2" color="text.secondary">
            Store: {user?.store_id || 'N/A'}
          </Typography>
        </Box>
      </Drawer>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          width: `calc(100% - ${DRAWER_WIDTH}px)`,
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}

export default MainLayout

