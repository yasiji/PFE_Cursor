import { create } from 'zustand'

export type NotificationType = 'info' | 'success' | 'warning' | 'error'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message: string
  timestamp: Date
  read: boolean
  actionUrl?: string
}

interface NotificationState {
  notifications: Notification[]
  unreadCount: number
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'> | Notification) => void
  setNotifications: (notifications: Notification[]) => void
  markAsRead: (id: string) => void
  markAllAsRead: () => void
  removeNotification: (id: string) => void
  clearAll: () => void
}

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  unreadCount: 0,
  addNotification: (notification) => {
    const newNotification: Notification = {
      ...notification,
      id: (notification as Notification).id || Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: (notification as Notification).timestamp || new Date(),
      read: (notification as Notification).read || false,
    }
    set((state) => {
      // Check if notification already exists
      if (state.notifications.some(n => n.id === newNotification.id)) {
        return state
      }
      return {
        notifications: [newNotification, ...state.notifications],
        unreadCount: newNotification.read ? state.unreadCount : state.unreadCount + 1,
      }
    })
  },
  setNotifications: (notifications) => {
    set({
      notifications,
      unreadCount: notifications.filter(n => !n.read).length,
    })
  },
  markAsRead: (id) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    }))
  },
  markAllAsRead: () => {
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    }))
  },
  removeNotification: (id) => {
    set((state) => {
      const notification = state.notifications.find((n) => n.id === id)
      return {
        notifications: state.notifications.filter((n) => n.id !== id),
        unreadCount: notification && !notification.read ? state.unreadCount - 1 : state.unreadCount,
      }
    })
  },
  clearAll: () => {
    set({
      notifications: [],
      unreadCount: 0,
    })
  },
}))

