import { api } from './api'

/* ── Types ── */

export interface NotificationItem {
  id: number
  type: string
  title: string
  body: string
  metadata_json: Record<string, unknown> | null
  is_read: boolean
  created_at: string
}

export interface NotificationList {
  items: NotificationItem[]
  total: number
  unread: number
}

export interface UnreadCount {
  count: number
}

/* ── API calls ── */

export async function fetchNotifications(skip = 0, limit = 20) {
  const { data } = await api.get<NotificationList>('/v1/notifications/', {
    params: { skip, limit },
  })
  return data
}

export async function fetchUnreadCount() {
  const { data } = await api.get<UnreadCount>(
    '/v1/notifications/unread-count',
  )
  return data
}

export async function markNotificationRead(id: number) {
  const { data } = await api.put(`/v1/notifications/${id}/read`)
  return data
}

export async function markAllNotificationsRead() {
  const { data } = await api.put('/v1/notifications/read-all')
  return data
}

export async function deleteNotification(id: number) {
  const { data } = await api.delete(`/v1/notifications/${id}`)
  return data
}
