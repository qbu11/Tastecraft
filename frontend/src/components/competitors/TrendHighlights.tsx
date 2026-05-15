import { TrendingUp, Flame, Hash } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { TrendingTopic, ViralAlert } from '@/services/competitors'

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: '小红书',
  wechat: '微信',
  weibo: '微博',
  zhihu: '知乎',
  douyin: '抖音',
}

interface TrendHighlightsProps {
  topics: TrendingTopic[]
  viralPosts: ViralAlert[]
  summary: string
  isLoading?: boolean
}

export function TrendHighlights({
  topics,
  viralPosts,
  summary,
  isLoading = false,
}: TrendHighlightsProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-24 animate-pulse rounded-xl bg-stone-100" />
        <div className="grid grid-cols-2 gap-4">
          <div className="h-40 animate-pulse rounded-xl bg-stone-100" />
          <div className="h-40 animate-pulse rounded-xl bg-stone-100" />
        </div>
      </div>
    )
  }

  const hasData = topics.length > 0 || viralPosts.length > 0

  if (!hasData) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-stone-200 bg-white py-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-stone-100">
          <TrendingUp size={22} className="text-stone-400" />
        </div>
        <p className="mt-3 text-sm font-medium text-stone-700">暂无趋势数据</p>
        <p className="mt-1 max-w-xs text-xs text-stone-400">
          添加竞品并同步后，系统将自动分析赛道趋势
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      {summary && (
        <div className="rounded-xl border border-stone-200 bg-[var(--color-accent-muted,#faf5f0)] px-5 py-4">
          <p className="text-sm leading-relaxed text-stone-700">{summary}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Top Topics */}
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-medium text-stone-700">
            <Hash size={15} className="text-stone-400" />
            热门话题
          </div>
          <div className="mt-3 space-y-2">
            {topics.slice(0, 5).map((topic, i) => (
              <div
                key={topic.topic}
                className="flex items-center justify-between text-sm"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className={cn(
                      'flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-bold',
                      i < 3
                        ? 'bg-[var(--color-accent,#c69c6d)]/10 text-[var(--color-accent,#c69c6d)]'
                        : 'bg-stone-100 text-stone-400',
                    )}
                  >
                    {i + 1}
                  </span>
                  <span className="truncate text-stone-800">{topic.topic}</span>
                </div>
                <div className="flex shrink-0 items-center gap-3 text-xs text-stone-400">
                  <span>{topic.frequency} 篇</span>
                  <span>{Math.round(topic.avg_engagement)} 互动</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Viral Posts */}
        <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
          <div className="flex items-center gap-2 text-sm font-medium text-stone-700">
            <Flame size={15} className="text-orange-400" />
            爆款内容
          </div>
          <div className="mt-3 space-y-3">
            {viralPosts.slice(0, 3).map((post) => (
              <div key={post.post_id} className="text-sm">
                <p className="truncate font-medium text-stone-800">
                  {post.title || '无标题'}
                </p>
                <div className="mt-0.5 flex items-center gap-2 text-xs text-stone-400">
                  <span className={cn(
                    'inline-flex rounded-full px-1.5 py-0.5',
                    'bg-stone-100 text-stone-500',
                  )}>
                    {PLATFORM_LABELS[post.platform] ?? post.platform}
                  </span>
                  <span>{post.competitor_name}</span>
                  <span>|</span>
                  <span className="text-orange-500 font-medium">
                    {post.engagement_ratio.toFixed(1)}x
                  </span>
                  <span>{post.likes} 赞</span>
                </div>
              </div>
            ))}
            {viralPosts.length === 0 && (
              <p className="text-xs text-stone-400">暂无爆款内容</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
