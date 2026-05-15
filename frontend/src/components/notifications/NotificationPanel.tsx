import { useEffect } from 'react'
import {
  CheckCheck,
  BarChart3,
  Send,
  AlertTriangle,
  Sparkles,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useNotificationStore } from '@/stores/notificationStore'

const typeConfig: Record<
  string,
  { icon: React.ElementType; color: string; label: string }
> = {
  daily_digest: {
    icon: BarChart3,
    color: 'text-blue-500 bg-blue-50',
    label: '每日速览',
  },
  publish_status: {
    icon: Send,
    color: 'text-green-500 bg-green-50',
    label: '发布状态',
  },
  competitor_alert: {
    icon: AlertTriangle,
    color: 'text-amber-500 bg-amber-50',
    label: '竞品动态',
  },
  taste_evolution: {
    icon: Sparkles,
    color: 'text-purple-500 bg-purple-50',
    label: '品味进化',
  },
  session_expiry: {
    icon: Clock,
    color: 'text-red-500 bg-red-50',
    label: '登录过期',
  },
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  return `${days} 天前`
}

interface Props {
  onClose?: () => void
}

export function NotificationPanel(_props: Props) {
  const { notifications, loading, unreadCount, fetchNotifications, markRead, markAllRead } =
    useNotificationStore()

  useEffect(() => {
    fetchNotifications()
  }, [fetchNotifications])

  return (
    <div className="absolute right-0 top-full z-50 mt-2 w-96 rounded-xl border border-stone-200 bg-white shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-stone-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-stone-900">通知</h3>
        {unreadCount > 0 && (
          <button
            onClick={() => markAllRead()}
            className="flex items-center gap-1 text-xs text-stone-500 transition-colors hover:text-stone-700"
          >
            <CheckCheck size={14} />
            全部已读
          </button>
        )}
      </div>

      {/* List */}
      <div className="max-h-96 overflow-y-auto">
        {loading && notifications.length === 0 ? (
          <div className="py-8 text-center text-sm text-stone-400">
            加载中...
          </div>
        ) : notifications.length === 0 ? (
          <div className="py-8 text-center text-sm text-stone-400">
            暂无通知
          </div>
        ) : (
          notifications.map((notif) => {
            const config = typeConfig[notif.type] ?? {
              icon: BarChart3,
              color: 'text-stone-500 bg-stone-50',
              label: notif.type,
            }
            const Icon = config.icon

            return (
              <button
                key={notif.id}
                onClick={() => {
                  if (!notif.is_read) markRead(notif.id)
                }}
                className={cn(
                  'flex w-full gap-3 px-4 py-3 text-left transition-colors hover:bg-stone-50',
                  !notif.is_read && 'bg-blue-50/40',
                )}
              >
                <div
                  className={cn(
                    'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                    config.color,
                  )}
                >
                  <Icon size={16} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-medium text-stone-900">
                      {notif.title}
                    </p>
                    {!notif.is_read && (
                      <span className="h-2 w-2 shrink-0 rounded-full bg-blue-500" />
                    )}
                  </div>
                  <p className="mt-0.5 line-clamp-2 text-xs text-stone-500">
                    {notif.body}
                  </p>
                  <p className="mt-1 text-[11px] text-stone-400">
                    {timeAgo(notif.created_at)}
                  </p>
                </div>
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
