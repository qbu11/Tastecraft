import { RefreshCw, Trash2, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { Competitor } from '@/services/competitors'

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: '小红书',
  wechat: '微信',
  weibo: '微博',
  zhihu: '知乎',
  douyin: '抖音',
}

const PLATFORM_COLORS: Record<string, string> = {
  xiaohongshu: 'bg-red-50 text-red-600 border-red-200',
  wechat: 'bg-green-50 text-green-600 border-green-200',
  weibo: 'bg-orange-50 text-orange-600 border-orange-200',
  zhihu: 'bg-blue-50 text-blue-600 border-blue-200',
  douyin: 'bg-purple-50 text-purple-600 border-purple-200',
}

interface CompetitorCardProps {
  competitor: Competitor
  onSync: (id: number) => void
  onRemove: (id: number) => void
  onExpand: (id: number) => void
  isSyncing?: boolean
  isExpanded?: boolean
}

export function CompetitorCard({
  competitor,
  onSync,
  onRemove,
  onExpand,
  isSyncing = false,
  isExpanded = false,
}: CompetitorCardProps) {
  const platformLabel = PLATFORM_LABELS[competitor.platform] ?? competitor.platform
  const platformColor = PLATFORM_COLORS[competitor.platform] ?? 'bg-stone-50 text-stone-600 border-stone-200'

  const lastSynced = competitor.last_synced_at
    ? new Date(competitor.last_synced_at).toLocaleDateString('zh-CN', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : '从未同步'

  return (
    <div
      className={cn(
        'rounded-xl border border-stone-200 bg-white transition-shadow',
        isExpanded && 'ring-1 ring-stone-300',
      )}
    >
      <button
        type="button"
        className="flex w-full items-center gap-4 px-5 py-4 text-left"
        onClick={() => onExpand(competitor.id)}
      >
        {/* Avatar placeholder */}
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-stone-100 text-sm font-semibold text-stone-500">
          {competitor.account_name.charAt(0)}
        </div>

        {/* Info */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-stone-900">
              {competitor.account_name}
            </p>
            <span
              className={cn(
                'inline-flex shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium',
                platformColor,
              )}
            >
              {platformLabel}
            </span>
          </div>
          <div className="mt-1 flex items-center gap-3 text-xs text-stone-400">
            <span>{competitor.total_posts_tracked} 篇已追踪</span>
            <span>|</span>
            <span>最后同步: {lastSynced}</span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-1">
          {competitor.account_url && (
            <a
              href={competitor.account_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600"
              title="打开主页"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink size={15} />
            </a>
          )}
          <button
            type="button"
            className={cn(
              'rounded-md p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600',
              isSyncing && 'animate-spin text-[var(--color-accent)]',
            )}
            title="立即同步"
            onClick={(e) => {
              e.stopPropagation()
              onSync(competitor.id)
            }}
            disabled={isSyncing}
          >
            <RefreshCw size={15} />
          </button>
          <button
            type="button"
            className="rounded-md p-1.5 text-stone-400 transition-colors hover:bg-red-50 hover:text-red-500"
            title="删除"
            onClick={(e) => {
              e.stopPropagation()
              onRemove(competitor.id)
            }}
          >
            <Trash2 size={15} />
          </button>
        </div>
      </button>
    </div>
  )
}
