import { create } from 'zustand'
import type { NotificationItem } from '@/services/notifications'
import {
  fetchNotifications,
  fetchUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
} from '@/services/notifications'

interface NotificationState {
  notifications: NotificationItem[]
  unreadCount: number
  loading: boolean

  fetchNotifications: () => Promise<void>
  fetchUnreadCount: () => Promise<void>
  markRead: (id: number) => Promise<void>
  markAllRead: () => Promise<void>
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  unreadCount: 0,
  loading: false,

  fetchNotifications: async () => {
    set({ loading: true })
    try {
      const result = await fetchNotifications(0, 20)
      set({
        notifications: result.items,
        unreadCount: result.unread,
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  fetchUnreadCount: async () => {
    try {
      const result = await fetchUnreadCount()
      set({ unreadCount: result.count })
    } catch {
      /* silent */
    }
  },

  markRead: async (id: number) => {
    await markNotificationRead(id)
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n,
      ),
      unreadCount: Math.max(0, state.unreadCount - 1),
    }))
  },

  markAllRead: async () => {
    await markAllNotificationsRead()
    set((state) => ({
      notifications: state.notifications.map((n) => ({
        ...n,
        is_read: true,
      })),
      unreadCount: 0,
    }))
  },
}))
