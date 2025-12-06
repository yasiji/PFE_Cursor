import { useState } from 'react'
import {
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  Grid,
  Switch,
  FormControlLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Alert,
  Snackbar,
  CircularProgress,
} from '@mui/material'
import { Save, Refresh, Logout } from '@mui/icons-material'
import { useAuthStore } from '../store/authStore'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { settingsAPI } from '../services/api'

const SettingsPage = () => {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  // Fetch current settings
  const { data: settingsData, isLoading } = useQuery(
    ['userSettings'],
    async () => {
      const response = await settingsAPI.getSettings()
      return response.data.settings
    },
    {
      staleTime: 60000,
    }
  )

  // Local state for form
  const [localSettings, setLocalSettings] = useState<any>(null)

  // Initialize local settings when data loads
  if (settingsData && !localSettings) {
    setLocalSettings(settingsData)
  }

  // Update settings mutation
  const updateMutation = useMutation(
    (settings: any) => settingsAPI.updateSettings(settings),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['userSettings'])
        setSnackbar({ open: true, message: 'Settings saved successfully', severity: 'success' })
      },
      onError: () => {
        setSnackbar({ open: true, message: 'Error saving settings', severity: 'error' })
      },
    }
  )

  // Reset settings mutation
  const resetMutation = useMutation(
    () => settingsAPI.resetSettings(),
    {
      onSuccess: (response) => {
        queryClient.invalidateQueries(['userSettings'])
        setLocalSettings(response.data.settings)
        setSnackbar({ open: true, message: 'Settings reset to defaults', severity: 'success' })
      },
      onError: () => {
        setSnackbar({ open: true, message: 'Error resetting settings', severity: 'error' })
      },
    }
  )

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleSave = () => {
    if (localSettings) {
      updateMutation.mutate(localSettings)
    }
  }

  const handleReset = () => {
    if (confirm('Are you sure you want to reset all settings to defaults?')) {
      resetMutation.mutate()
    }
  }

  const updateSetting = (section: string, key: string, value: any) => {
    setLocalSettings((prev: any) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value,
      },
    }))
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    )
  }

  const settings = localSettings || settingsData || {}

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Settings
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleReset}
            disabled={resetMutation.isLoading}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={updateMutation.isLoading}
          >
            Save Changes
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* User Information */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                User Information
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  <strong>Username:</strong> {user?.username}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Email:</strong> {user?.email}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Role:</strong> {user?.role}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  <strong>Store ID:</strong> {user?.store_id || 'N/A'}
                </Typography>
              </Box>
              <Button
                variant="contained"
                color="error"
                startIcon={<Logout />}
                onClick={handleLogout}
                sx={{ mt: 3 }}
              >
                Logout
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Notification Settings
              </Typography>
              <Box sx={{ mt: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.email_enabled ?? true}
                      onChange={(e) => updateSetting('notifications', 'email_enabled', e.target.checked)}
                    />
                  }
                  label="Email Notifications"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.push_enabled ?? true}
                      onChange={(e) => updateSetting('notifications', 'push_enabled', e.target.checked)}
                    />
                  }
                  label="Push Notifications"
                />
                <Divider sx={{ my: 2 }} />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.low_stock_alerts ?? true}
                      onChange={(e) => updateSetting('notifications', 'low_stock_alerts', e.target.checked)}
                    />
                  }
                  label="Low Stock Alerts"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.expiry_alerts ?? true}
                      onChange={(e) => updateSetting('notifications', 'expiry_alerts', e.target.checked)}
                    />
                  }
                  label="Expiry Alerts"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.order_alerts ?? true}
                      onChange={(e) => updateSetting('notifications', 'order_alerts', e.target.checked)}
                    />
                  }
                  label="Order Alerts"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.notifications?.daily_summary ?? true}
                      onChange={(e) => updateSetting('notifications', 'daily_summary', e.target.checked)}
                    />
                  }
                  label="Daily Summary"
                />
                <TextField
                  label="Low Stock Threshold"
                  type="number"
                  size="small"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={settings.notifications?.alert_threshold_low_stock ?? 10}
                  onChange={(e) => updateSetting('notifications', 'alert_threshold_low_stock', parseInt(e.target.value))}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Dashboard Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dashboard Settings
              </Typography>
              <Box sx={{ mt: 2 }}>
                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                  <InputLabel>Default Time Range</InputLabel>
                  <Select
                    value={settings.dashboard?.default_time_range ?? '7d'}
                    label="Default Time Range"
                    onChange={(e) => updateSetting('dashboard', 'default_time_range', e.target.value)}
                  >
                    <MenuItem value="7d">Last 7 Days</MenuItem>
                    <MenuItem value="30d">Last 30 Days</MenuItem>
                    <MenuItem value="90d">Last 90 Days</MenuItem>
                    <MenuItem value="1y">Last Year</MenuItem>
                  </Select>
                </FormControl>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.dashboard?.show_profit ?? true}
                      onChange={(e) => updateSetting('dashboard', 'show_profit', e.target.checked)}
                    />
                  }
                  label="Show Profit"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.dashboard?.show_loss ?? true}
                      onChange={(e) => updateSetting('dashboard', 'show_loss', e.target.checked)}
                    />
                  }
                  label="Show Loss"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.dashboard?.auto_refresh ?? true}
                      onChange={(e) => updateSetting('dashboard', 'auto_refresh', e.target.checked)}
                    />
                  }
                  label="Auto Refresh"
                />
                <TextField
                  label="Refresh Interval (seconds)"
                  type="number"
                  size="small"
                  fullWidth
                  sx={{ mt: 2 }}
                  value={settings.dashboard?.refresh_interval_seconds ?? 30}
                  onChange={(e) => updateSetting('dashboard', 'refresh_interval_seconds', parseInt(e.target.value))}
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Display Settings */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Display Settings
              </Typography>
              <Box sx={{ mt: 2 }}>
                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                  <InputLabel>Currency</InputLabel>
                  <Select
                    value={settings.display?.currency ?? 'USD'}
                    label="Currency"
                    onChange={(e) => updateSetting('display', 'currency', e.target.value)}
                  >
                    <MenuItem value="USD">USD ($)</MenuItem>
                    <MenuItem value="EUR">EUR (€)</MenuItem>
                    <MenuItem value="GBP">GBP (£)</MenuItem>
                    <MenuItem value="CAD">CAD (C$)</MenuItem>
                  </Select>
                </FormControl>
                <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                  <InputLabel>Theme</InputLabel>
                  <Select
                    value={settings.display?.theme ?? 'light'}
                    label="Theme"
                    onChange={(e) => updateSetting('display', 'theme', e.target.value)}
                  >
                    <MenuItem value="light">Light</MenuItem>
                    <MenuItem value="dark">Dark</MenuItem>
                    <MenuItem value="system">System</MenuItem>
                  </Select>
                </FormControl>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.display?.compact_mode ?? false}
                      onChange={(e) => updateSetting('display', 'compact_mode', e.target.checked)}
                    />
                  }
                  label="Compact Mode"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Forecast Settings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Forecast Settings
              </Typography>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6} md={3}>
                  <TextField
                    label="Default Horizon (days)"
                    type="number"
                    size="small"
                    fullWidth
                    value={settings.forecast?.default_horizon_days ?? 7}
                    onChange={(e) => updateSetting('forecast', 'default_horizon_days', parseInt(e.target.value))}
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.forecast?.show_uncertainty_bounds ?? true}
                        onChange={(e) => updateSetting('forecast', 'show_uncertainty_bounds', e.target.checked)}
                      />
                    }
                    label="Show Uncertainty Bounds"
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.forecast?.include_weather ?? true}
                        onChange={(e) => updateSetting('forecast', 'include_weather', e.target.checked)}
                      />
                    }
                    label="Include Weather (Open-Meteo)"
                  />
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={settings.forecast?.include_holidays ?? true}
                        onChange={(e) => updateSetting('forecast', 'include_holidays', e.target.checked)}
                      />
                    }
                    label="Include Holidays (Nager.Date)"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* API Info */}
        <Grid item xs={12}>
          <Alert severity="info">
            <Typography variant="subtitle2">Real-Time Data Sources</Typography>
            <Typography variant="body2">
              • Weather data: Open-Meteo API (free, no API key required)
              <br />
              • Holiday data: Nager.Date API (free, no API key required)
              <br />
              • All forecast factors are calculated using real-time data
            </Typography>
          </Alert>
        </Grid>
      </Grid>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        message={snackbar.message}
      />
    </Box>
  )
}

export default SettingsPage
