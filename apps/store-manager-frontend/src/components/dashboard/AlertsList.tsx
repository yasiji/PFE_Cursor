import { List, ListItem, ListItemIcon, ListItemText, Chip } from '@mui/material'
import { Warning, Error, Info } from '@mui/icons-material'

const alerts = [
  { type: 'error', message: 'Shelf A3 is empty - Bananas', time: '5 min ago' },
  { type: 'warning', message: 'Milk stock below threshold (12 units)', time: '15 min ago' },
  { type: 'warning', message: '23 items expiring in next 3 days', time: '1 hour ago' },
  { type: 'info', message: 'Order #1234 delivered successfully', time: '2 hours ago' },
]

const AlertsList = () => {
  const getIcon = (type: string) => {
    switch (type) {
      case 'error':
        return <Error color="error" />
      case 'warning':
        return <Warning color="warning" />
      default:
        return <Info color="info" />
    }
  }

  const getChipColor = (type: string): 'error' | 'warning' | 'info' => {
    return type as 'error' | 'warning' | 'info'
  }

  return (
    <List>
      {alerts.map((alert, index) => (
        <ListItem
          key={index}
          sx={{
            borderBottom: index < alerts.length - 1 ? '1px solid #e0e0e0' : 'none',
            py: 1.5,
          }}
        >
          <ListItemIcon>{getIcon(alert.type)}</ListItemIcon>
          <ListItemText
            primary={alert.message}
            secondary={alert.time}
            sx={{ flex: 1 }}
          />
          <Chip
            label={alert.type.toUpperCase()}
            size="small"
            color={getChipColor(alert.type)}
            sx={{ ml: 2 }}
          />
        </ListItem>
      ))}
    </List>
  )
}

export default AlertsList

