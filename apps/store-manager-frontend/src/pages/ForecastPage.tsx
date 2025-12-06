import { useState } from 'react'
import { Box, Typography, TextField, FormControl, InputLabel, Select, MenuItem } from '@mui/material'
import { format, addDays } from 'date-fns'
import { useAuthStore } from '../store/authStore'
import ForecastInsightsSection from '../components/dashboard/ForecastInsightsSection'
import EnhancedForecastInsights from '../components/dashboard/EnhancedForecastInsights'
import ThirtyDayForecastTab from './components/ThirtyDayForecastTab'

const ForecastPage = () => {
  const { user } = useAuthStore()
  const storeId = user?.store_id?.toString() || '235'
  const [startDate, setStartDate] = useState<string>(format(new Date(), 'yyyy-MM-dd'))
  const [windowDays, setWindowDays] = useState<number>(30)
  const maxSelectableDate = format(addDays(new Date(), 29), 'yyyy-MM-dd')

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 1, fontWeight: 600 }}>
        Forecast Outlook
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        See the profit outlook for the next few days, understand the factors driving demand, and review the
        30-day revenue/loss projection so you can plan ahead.
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          label="Start from"
          type="date"
          size="small"
          value={startDate}
          onChange={(e) => setStartDate(e.target.value)}
          InputLabelProps={{ shrink: true }}
          inputProps={{ min: format(new Date(), 'yyyy-MM-dd'), max: maxSelectableDate }}
          helperText="Shift the forecast windows to a different focus date"
        />
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>Window Size</InputLabel>
          <Select
            label="Window Size"
            value={windowDays}
            onChange={(e) => setWindowDays(Number(e.target.value))}
          >
            <MenuItem value={7}>7 days</MenuItem>
            <MenuItem value={14}>14 days</MenuItem>
            <MenuItem value={30}>30 days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      <ForecastInsightsSection storeId={storeId} horizonDays={windowDays} />

      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Next 7 Days Breakdown
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Detailed view of the coming week with drivers such as weather, weekends, and holidays.
        </Typography>
        <EnhancedForecastInsights storeId={storeId} startDate={startDate} />
      </Box>

      <Box>
        <Typography variant="h6" gutterBottom>
          {windowDays}-Day Financial Outlook
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Daily revenue, profit, loss, and factor visibility for the next month.
        </Typography>
        <ThirtyDayForecastTab storeId={storeId} startDate={startDate} windowDays={windowDays} />
      </Box>
    </Box>
  )
}

export default ForecastPage

