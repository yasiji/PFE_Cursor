import { useEffect } from 'react'
import { useQuery } from 'react-query'
import { useAuthStore } from '../../store/authStore'
import { useNotificationStore } from '../../store/notificationStore'
import { notificationAPI } from '../../services/api'

interface ApiNotification {
  id: number
  user_id: number
  store_id: number | null
  type: string
  severity: string
  title: string
  message: string
  data: any
  read: boolean
  created_at: string
}

const NotificationProvider = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, user } = useAuthStore()
  const { addNotification, notifications } = useNotificationStore()

  // Fetch notifications from API
  const { data: apiNotifications, refetch } = useQuery<ApiNotification[]>(
    ['notifications'],
    async () => {
      const response = await notificationAPI.getNotifications(false, undefined, 50)
      return response.data
    },
    {
      enabled: isAuthenticated,
      refetchInterval: 30000, // Poll every 30 seconds
      retry: 1,
    }
  )

  // Sync API notifications to store
  useEffect(() => {
    if (!apiNotifications || !isAuthenticated) return

    // Get current notification IDs
    const currentIds = new Set(notifications.map(n => n.id))

    // Add new notifications
    apiNotifications.forEach((apiNotif) => {
      if (!currentIds.has(apiNotif.id.toString())) {
        // Map API severity to notification type
        let type: 'info' | 'success' | 'warning' | 'error' = 'info'
        if (apiNotif.severity === 'warning') type = 'warning'
        else if (apiNotif.severity === 'error' || apiNotif.severity === 'critical') type = 'error'
        else if (apiNotif.severity === 'success') type = 'success'

        addNotification({
          id: apiNotif.id.toString(),
          type,
          title: apiNotif.title,
          message: apiNotif.message,
          timestamp: new Date(apiNotif.created_at),
          read: apiNotif.read,
        })
      }
    })
  }, [apiNotifications, isAuthenticated, notifications, addNotification])

  // Generate notifications for store on mount
  useEffect(() => {
    if (!isAuthenticated || !user?.store_id) return

    // Generate notifications for this store
    const generateNotifications = async () => {
      try {
        await notificationAPI.generateNotifications(user.store_id!.toString())
        refetch()
      } catch (error) {
        console.error('Error generating notifications:', error)
      }
    }

    // Generate on mount and then every 15 minutes
    generateNotifications()
    const interval = setInterval(generateNotifications, 15 * 60 * 1000) // 15 minutes

    return () => clearInterval(interval)
  }, [isAuthenticated, user?.store_id, refetch])

  return <>{children}</>
}

export default NotificationProvider

