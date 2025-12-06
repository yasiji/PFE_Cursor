import { useState } from 'react'
import {
  Drawer,
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  IconButton,
  Chip,
  Button,
  Divider,
  Badge,
} from '@mui/material'
import {
  Close,
  Info,
  CheckCircle,
  Warning,
  Error,
  Notifications,
  NotificationsNone,
} from '@mui/icons-material'
import { useNotificationStore, Notification } from '../../store/notificationStore'
import { format } from 'date-fns'

const NotificationCenter = () => {
  const [open, setOpen] = useState(false)
  const { notifications, unreadCount, markAsRead, markAllAsRead, removeNotification } =
    useNotificationStore()

  const getIcon = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle color="success" />
      case 'warning':
        return <Warning color="warning" />
      case 'error':
        return <Error color="error" />
      default:
        return <Info color="info" />
    }
  }

  return (
    <>
      <IconButton color="inherit" onClick={() => setOpen(true)}>
        <Badge badgeContent={unreadCount} color="error">
          <Notifications />
        </Badge>
      </IconButton>

      <Drawer anchor="right" open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 400, height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* Header */}
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box display="flex" alignItems="center" gap={1}>
                <Notifications color="primary" />
                <Typography variant="h6">Notifications</Typography>
                {unreadCount > 0 && (
                  <Chip label={unreadCount} size="small" color="error" />
                )}
              </Box>
              <IconButton size="small" onClick={() => setOpen(false)}>
                <Close />
              </IconButton>
            </Box>
            {unreadCount > 0 && (
              <Button
                size="small"
                onClick={markAllAsRead}
                sx={{ mt: 1 }}
                startIcon={<NotificationsNone />}
              >
                Mark all as read
              </Button>
            )}
          </Box>

          {/* Notifications List */}
          <Box sx={{ flex: 1, overflow: 'auto' }}>
            {notifications.length === 0 ? (
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  p: 3,
                }}
              >
                <NotificationsNone sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="body1" color="text.secondary">
                  No notifications
                </Typography>
              </Box>
            ) : (
              <List>
                {notifications.map((notification, index) => (
                  <Box key={notification.id}>
                    <ListItem
                      sx={{
                        backgroundColor: notification.read ? 'inherit' : 'action.hover',
                        '&:hover': { backgroundColor: 'action.selected' },
                        cursor: 'pointer',
                      }}
                      onClick={() => {
                        if (!notification.read) {
                          markAsRead(notification.id)
                        }
                      }}
                    >
                      <ListItemIcon>{getIcon(notification.type)}</ListItemIcon>
                      <ListItemText
                        primary={
                          <Box display="flex" alignItems="center" gap={1}>
                            <Typography
                              variant="subtitle2"
                              fontWeight={notification.read ? 400 : 600}
                            >
                              {notification.title}
                            </Typography>
                            {!notification.read && (
                              <Chip label="New" size="small" color="primary" />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              {notification.message}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                              {format(notification.timestamp, 'MMM dd, yyyy HH:mm')}
                            </Typography>
                          </Box>
                        }
                      />
                      <IconButton
                        size="small"
                        onClick={(e) => {
                          e.stopPropagation()
                          removeNotification(notification.id)
                        }}
                      >
                        <Close fontSize="small" />
                      </IconButton>
                    </ListItem>
                    {index < notifications.length - 1 && <Divider />}
                  </Box>
                ))}
              </List>
            )}
          </Box>
        </Box>
      </Drawer>
    </>
  )
}

export default NotificationCenter

