import { Card, CardContent, Typography, Grid, Box, CircularProgress, Alert } from '@mui/material'
import { useQuery } from 'react-query'
import { storeAPI } from '../../services/api'

interface ForecastInsightsSectionProps {
  storeId: string
  horizonDays?: number
}

const ForecastInsightsSection = ({ storeId, horizonDays = 30 }: ForecastInsightsSectionProps) => {
  const { data: insights, isLoading, error } = useQuery(
    ['forecastInsights', storeId, horizonDays],
    async () => {
      const response = await storeAPI.getForecastInsights(storeId, horizonDays)
      return response.data
    },
    {
      refetchInterval: 300000,
      staleTime: 120000,
      retry: 2,
    }
  )

  if (isLoading) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Forecast Insights
          </Typography>
          <Box display="flex" justifyContent="center" p={3}>
            <CircularProgress size={24} />
          </Box>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Forecast Insights
          </Typography>
          <Alert severity="warning">Unable to load forecast insights.</Alert>
        </CardContent>
      </Card>
    )
  }

  if (!insights || !insights.tomorrow || !insights.next_week || !insights.next_month) {
    return null
  }

  const tomorrow = insights.tomorrow || {}
  const nextWeek = insights.next_week || {}
  const nextMonth = insights.next_month || {}

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Forecast Insights
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ bgcolor: 'primary.light', color: 'primary.contrastText' }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Tomorrow
                </Typography>
                <Typography variant="h5" gutterBottom>
                  {tomorrow.forecasted_items || 0} items
                </Typography>
                <Typography variant="body2">
                  Revenue: ${(tomorrow.forecasted_revenue || 0).toFixed(2)}
                </Typography>
                <Typography variant="body2">
                  Profit: ${(tomorrow.forecasted_profit || 0).toFixed(2)} ({(tomorrow.forecasted_margin || 0).toFixed(1)}% margin)
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ bgcolor: 'success.light', color: 'success.contrastText' }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Next Week (Daily Avg)
                </Typography>
                <Typography variant="h5" gutterBottom>
                  {nextWeek.daily_avg_items || 0} items/day
                </Typography>
                <Typography variant="body2">
                  Revenue: ${(nextWeek.daily_avg_revenue || 0).toFixed(2)}/day
                </Typography>
                <Typography variant="body2">
                  Profit: ${(nextWeek.daily_avg_profit || 0).toFixed(2)}/day ({(nextWeek.daily_avg_margin || 0).toFixed(1)}% margin)
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={4}>
            <Card variant="outlined" sx={{ bgcolor: 'warning.light', color: 'warning.contrastText' }}>
              <CardContent>
                <Typography variant="subtitle2" gutterBottom>
                  Next Month (Daily Avg)
                </Typography>
                <Typography variant="h5" gutterBottom>
                  {nextMonth.daily_avg_items || 0} items/day
                </Typography>
                <Typography variant="body2">
                  Revenue: ${(nextMonth.daily_avg_revenue || 0).toFixed(2)}/day
                </Typography>
                <Typography variant="body2">
                  Profit: ${(nextMonth.daily_avg_profit || 0).toFixed(2)}/day ({(nextMonth.daily_avg_margin || 0).toFixed(1)}% margin)
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {insights.insights && Array.isArray(insights.insights) && insights.insights.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Key Insights
            </Typography>
            {insights.insights.map((insight: any, index: number) => (
              <Alert
                key={index}
                severity={
                  insight.severity === 'success'
                    ? 'success'
                    : insight.severity === 'warning'
                    ? 'warning'
                    : 'info'
                }
                sx={{ mt: 1 }}
              >
                <Typography variant="body2">
                  <strong>{insight.title || 'Insight'}:</strong> {insight.message || ''}
                </Typography>
              </Alert>
            ))}
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

export default ForecastInsightsSection

