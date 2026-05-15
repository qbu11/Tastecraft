import { useEffect, useState, useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'

interface PlatformSession {
  user_id: string
  platform: string
  health: 'active' | 'expiring' | 'expired' | 'not_found' | 'error'
  last_verified: string | null
  expires_at: string | null
  error: string | null
}

interface SessionStatusProps {
  className?: string
  onConnectClick?: (platform: string) => void
}

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: '\u5C0F\u7EA2\u4E66',
  wechat: '\u5FAE\u4FE1\u516C\u4F17\u53F7',
}

const HEALTH_CONFIG: Record<
  PlatformSession['health'],
  { dot: string; label: string; textColor: string }
> = {
  active: { dot: 'bg-green-500', label: '\u5DF2\u8FDE\u63A5', textColor: 'text-green-700' },
  expiring: {
    dot: 'bg-yellow-500',
    label: '\u5373\u5C06\u8FC7\u671F',
    textColor: 'text-yellow-700',
  },
  expired: { dot: 'bg-red-500', label: '\u9700\u8981\u91CD\u65B0\u767B\u5F55', textColor: 'text-red-600' },
  not_found: { dot: 'bg-gray-300', label: '\u672A\u8FDE\u63A5', textColor: 'text-gray-500' },
  error: { dot: 'bg-red-500', label: '\u72B6\u6001\u5F02\u5E38', textColor: 'text-red-600' },
}

/**
 * Shows connection status for each platform.
 *
 * - Green dot + "已连接" for active sessions
 * - Yellow dot + "即将过期" for expiring sessions
 * - Red dot + "需要重新登录" for expired
 * - Gray dot + "连接" button for unconnected platforms
 */
export function SessionStatus({ className, onConnectClick }: SessionStatusProps) {
  const [sessions, setSessions] = useState<PlatformSession[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState<string | null>(null)

  const fetchSessions = useCallback(async () => {
    try {
      const { data } = await api.get<{ sessions: PlatformSession[] }>('/v1/sessions/')
      setSessions(data.sessions)
    } catch {
      // Silently fail — status display is non-critical
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  const handleRefresh = async (platform: string) => {
    setRefreshing(platform)
    try {
      await api.post(`/v1/sessions/${platform}/refresh`)
      await fetchSessions()
    } finally {
      setRefreshing(null)
    }
  }

  if (loading) {
    return (
      <div className={cn('animate-pulse space-y-2', className)}>
        {[1, 2].map((i) => (
          <div key={i} className="h-12 rounded-lg bg-gray-100" />
        ))}
      </div>
    )
  }

  return (
    <div className={cn('space-y-2', className)}>
      {sessions.map((session) => {
        const config = HEALTH_CONFIG[session.health] ?? HEALTH_CONFIG.error
        const label = PLATFORM_LABELS[session.platform] ?? session.platform
        const isRefreshing = refreshing === session.platform
        const needsConnect = session.health === 'not_found' || session.health === 'expired'

        return (
          <div
            key={session.platform}
            className="flex items-center justify-between rounded-lg border border-gray-100 bg-white px-4 py-3"
          >
            {/* Left: platform name + status */}
            <div className="flex items-center gap-3">
              <span
                className={cn('inline-block h-2.5 w-2.5 rounded-full', config.dot)}
                aria-label={config.label}
              />
              <div>
                <p className="text-sm font-medium text-gray-900">{label}</p>
                <p className={cn('text-xs', config.textColor)}>{config.label}</p>
              </div>
            </div>

            {/* Right: action button */}
            <div className="flex items-center gap-2">
              {/* Refresh button (only for active/expiring) */}
              {!needsConnect && session.health !== 'not_found' && (
                <button
                  onClick={() => handleRefresh(session.platform)}
                  disabled={isRefreshing}
                  className="rounded p-1.5 text-gray-400 hover:bg-gray-50 hover:text-gray-600 transition-colors disabled:opacity-50"
                  title={'\u5237\u65B0\u72B6\u6001'}
                >
                  <RefreshCw
                    size={14}
                    className={cn(isRefreshing && 'animate-spin')}
                  />
                </button>
              )}

              {/* Connect button (for not_found/expired) */}
              {needsConnect && (
                <button
                  onClick={() => onConnectClick?.(session.platform)}
                  className={cn(
                    'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                    session.platform === 'xiaohongshu'
                      ? 'bg-red-50 text-red-600 hover:bg-red-100'
                      : 'bg-green-50 text-green-600 hover:bg-green-100',
                  )}
                >
                  {'\u8FDE\u63A5'}
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
