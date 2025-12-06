import { Box, Typography, Card, CardContent, Grid, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Alert } from '@mui/material'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import { useQuery } from 'react-query'
import { storeAPI } from '../../services/api'

interface Props {
  storeId: string
  startDate?: string
}

const EnhancedForecastInsights = ({ storeId, startDate }: Props) => {
  const { data: forecastData } = useQuery(
    ['extendedForecast7Days', storeId],
    async () => {
      const response = await storeAPI.getExtendedForecast(storeId)
      return response.data
    },
    {
      enabled: !!storeId,
      refetchInterval: 300000, // 5 minutes
    }
  )

  if (!forecastData) return null

  let filteredForecasts = forecastData.daily_forecasts
  if (startDate) {
    const startTime = new Date(startDate).getTime()
    if (!Number.isNaN(startTime)) {
      filteredForecasts = filteredForecasts.filter((f: any) => new Date(f.date).getTime() >= startTime)
    }
  }

  const next7Days = filteredForecasts.slice(0, 7)

  if (next7Days.length === 0) {
    return (
      <Alert severity="info">
        No forecast data available for the selected date. Try choosing an earlier date.
      </Alert>
    )
  }

  const chartData = next7Days.map((f: any) => ({
    date: format(new Date(f.date), 'EEE'),
    revenue: f.predicted_revenue,
    profit: f.predicted_profit,
    margin: f.predicted_margin,
  }))

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          7-Day Forecast Breakdown
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="revenue" stroke="#1976d2" name="Revenue" />
                <Line type="monotone" dataKey="profit" stroke="#2e7d32" name="Profit" />
              </LineChart>
            </ResponsiveContainer>
          </Grid>
          <Grid item xs={12} md={4}>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Day</TableCell>
                    <TableCell align="right">Revenue</TableCell>
                    <TableCell align="right">Margin</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {next7Days.map((forecast: any) => (
                    <TableRow key={forecast.date}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2">
                            {format(new Date(forecast.date), 'EEE, MMM dd')}
                          </Typography>
                          <Box display="flex" gap={0.5} mt={0.5}>
                            {forecast.factors.is_weekend && (
                              <Chip label="Weekend" size="small" color="primary" />
                            )}
                            {forecast.factors.weather !== 'normal' && (
                              <Chip label={forecast.factors.weather} size="small" color="info" />
                            )}
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell align="right">${forecast.predicted_revenue.toFixed(0)}</TableCell>
                      <TableCell align="right">{forecast.predicted_margin.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  )
}

export default EnhancedForecastInsights

