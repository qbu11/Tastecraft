import { useEffect, useState } from 'react'
import {
  BarChart3,
  Eye,
  Heart,
  MessageCircle,
  Share2,
  Bookmark,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type {
  PerformanceSummary,
  PeriodDelta,
  TasteCorrelation,
  TimeSlot,
  PlatformStats,
} from '@/services/analytics'
import {
  fetchAnalyticsSummary,
  fetchCorrelations,
  fetchBestTimes,
  fetchPlatformComparison,
} from '@/services/analytics'

/* ── Period selector ── */

const PERIODS = [
  { label: '7 天', days: 7 },
  { label: '30 天', days: 30 },
  { label: '90 天', days: 90 },
] as const

/* ── Stat card ── */

function StatCard({
  label,
  icon: Icon,
  delta,
  format,
}: {
  label: string
  icon: React.ElementType
  delta: PeriodDelta | null
  format?: (v: number) => string
}) {
  const fmt = format ?? ((v: number) => v.toLocaleString())
  const value = delta?.current ?? 0
  const pct = delta?.delta_pct ?? 0
  const positive = pct >= 0

  return (
    <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-stone-500">{label}</span>
        <Icon size={16} className="text-stone-400" />
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-stone-900">
        {fmt(value)}
      </p>
      <div className="mt-1 flex items-center gap-1">
        {positive ? (
          <ArrowUpRight size={14} className="text-emerald-500" />
        ) : (
          <ArrowDownRight size={14} className="text-red-500" />
        )}
        <span
          className={cn(
            'text-xs font-medium',
            positive ? 'text-emerald-600' : 'text-red-600',
          )}
        >
          {pct > 0 ? '+' : ''}
          {pct}%
        </span>
        <span className="text-xs text-stone-400">vs 上一周期</span>
      </div>
    </div>
  )
}

/* ── Mini SVG line chart ── */

function MiniTrend({
  values,
  height = 40,
  className,
}: {
  values: number[]
  height?: number
  className?: string
}) {
  if (values.length < 2) return null
  const max = Math.max(...values, 1)
  const w = 200
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w
      const y = height - (v / max) * (height - 4)
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg
      viewBox={`0 0 ${w} ${height}`}
      className={cn('w-full', className)}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

/* ── Heatmap ── */

const DAY_LABELS = ['一', '二', '三', '四', '五', '六', '日']

function PostingHeatmap({ slots }: { slots: TimeSlot[] }) {
  const grid: Record<string, number> = {}
  let maxEng = 0.01
  for (const s of slots) {
    const key = `${s.day_of_week}-${s.hour}`
    grid[key] = s.avg_engagement
    if (s.avg_engagement > maxEng) maxEng = s.avg_engagement
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-grid gap-0.5" style={{ gridTemplateColumns: `40px repeat(24, 20px)` }}>
        {/* Header row */}
        <div />
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="text-center text-[10px] text-stone-400">
            {h}
          </div>
        ))}

        {/* Data rows */}
        {DAY_LABELS.map((day, di) => (
          <>
            <div key={`label-${di}`} className="flex items-center text-xs text-stone-500">
              {day}
            </div>
            {Array.from({ length: 24 }, (_, h) => {
              const val = grid[`${di}-${h}`] ?? 0
              const intensity = val / maxEng
              return (
                <div
                  key={`${di}-${h}`}
                  className="h-5 w-5 rounded-sm"
                  style={{
                    backgroundColor: `rgba(16, 185, 129, ${Math.max(intensity, 0.05)})`,
                  }}
                  title={`${DAY_LABELS[di]} ${h}:00 — ${val.toFixed(1)}%`}
                />
              )
            })}
          </>
        ))}
      </div>
    </div>
  )
}

/* ── Correlation card ── */

function CorrelationCard({ c }: { c: TasteCorrelation }) {
  const positive = c.lift_pct >= 0
  return (
    <div className="flex items-start gap-3 rounded-lg border border-stone-100 bg-white px-4 py-3">
      <TrendingUp
        size={16}
        className={cn(
          'mt-0.5 shrink-0',
          positive ? 'text-emerald-500' : 'text-red-500',
        )}
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-stone-800">{c.rule}</p>
        <p className="mt-0.5 text-xs text-stone-500">
          {c.dimension} /{' '}
          <span className={positive ? 'text-emerald-600' : 'text-red-600'}>
            {positive ? '+' : ''}
            {c.lift_pct}%
          </span>{' '}
          互动率 (n={c.sample_size})
        </p>
      </div>
    </div>
  )
}

/* ── Platform comparison table ── */

const PLATFORM_LABELS: Record<string, string> = {
  xiaohongshu: '小红书',
  wechat: '微信公众号',
  weibo: '微博',
  zhihu: '知乎',
  douyin: '抖音',
  bilibili: 'B站',
}

function PlatformTable({ platforms }: { platforms: PlatformStats[] }) {
  if (platforms.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-stone-400">暂无跨平台数据</p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-stone-100 text-left text-xs text-stone-500">
            <th className="pb-2 font-medium">平台</th>
            <th className="pb-2 font-medium">发布数</th>
            <th className="pb-2 font-medium">总浏览</th>
            <th className="pb-2 font-medium">总点赞</th>
            <th className="pb-2 font-medium">互动率</th>
            <th className="pb-2 font-medium">最佳内容</th>
          </tr>
        </thead>
        <tbody>
          {platforms.map((p) => (
            <tr
              key={p.platform}
              className="border-b border-stone-50 text-stone-700"
            >
              <td className="py-2 font-medium">
                {PLATFORM_LABELS[p.platform] ?? p.platform}
              </td>
              <td className="py-2">{p.total_published}</td>
              <td className="py-2">{p.total_views.toLocaleString()}</td>
              <td className="py-2">{p.total_likes.toLocaleString()}</td>
              <td className="py-2">{p.avg_engagement_rate.toFixed(1)}%</td>
              <td className="max-w-[160px] truncate py-2 text-stone-500">
                {p.best_content_title ?? '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Main page ── */

export function Analytics() {
  const [days, setDays] = useState(7)
  const [summary, setSummary] = useState<PerformanceSummary | null>(null)
  const [correlations, setCorrelations] = useState<TasteCorrelation[]>([])
  const [bestTimes, setBestTimes] = useState<TimeSlot[]>([])
  const [platforms, setPlatforms] = useState<PlatformStats[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      try {
        const [s, c, t, p] = await Promise.all([
          fetchAnalyticsSummary(days),
          fetchCorrelations(),
          fetchBestTimes(),
          fetchPlatformComparison(),
        ])
        if (!cancelled) {
          setSummary(s)
          setCorrelations(c)
          setBestTimes(t)
          setPlatforms(p.platforms)
        }
      } catch {
        /* API not available yet — show empty state */
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [days])

  const hasData = summary !== null && (summary.total_published.current > 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900">
          数据分析
        </h1>
        <div className="flex gap-1 rounded-lg border border-stone-200 bg-white p-0.5">
          {PERIODS.map((p) => (
            <button
              key={p.days}
              onClick={() => setDays(p.days)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                days === p.days
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-500 hover:text-stone-700',
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-stone-700" />
        </div>
      ) : !hasData ? (
        /* Empty state */
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100">
            <BarChart3 size={24} className="text-stone-400" />
          </div>
          <p className="mt-4 text-sm font-medium text-stone-700">
            发布内容后查看数据
          </p>
          <p className="mt-1 max-w-xs text-xs text-stone-400">
            系统会在发布后 24h、72h、7d 自动采集数据并生成分析报告
          </p>
        </div>
      ) : (
        <>
          {/* Stats overview */}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="浏览量" icon={Eye} delta={summary!.total_views} />
            <StatCard label="点赞" icon={Heart} delta={summary!.total_likes} />
            <StatCard label="评论" icon={MessageCircle} delta={summary!.total_comments} />
            <StatCard
              label="互动率"
              icon={TrendingUp}
              delta={summary!.avg_engagement_rate}
              format={(v) => `${v.toFixed(1)}%`}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <StatCard label="分享" icon={Share2} delta={summary!.total_shares} />
            <StatCard label="收藏" icon={Bookmark} delta={summary!.total_saves} />
            <StatCard
              label="发布数"
              icon={BarChart3}
              delta={summary!.total_published}
            />
          </div>

          {/* Trend chart placeholder */}
          <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
            <p className="text-sm font-medium text-stone-700">浏览趋势</p>
            <div className="mt-3 text-emerald-500">
              <MiniTrend
                values={[30, 45, 38, 60, 55, 70, 65]}
                height={60}
              />
            </div>
            <p className="mt-2 text-xs text-stone-400">
              近 {days} 天趋势（示意）
            </p>
          </div>

          {/* Taste correlations */}
          {correlations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-stone-900">
                品味洞察
              </h2>
              <div className="grid gap-2 md:grid-cols-2">
                {correlations.slice(0, 6).map((c, i) => (
                  <CorrelationCard key={i} c={c} />
                ))}
              </div>
            </div>
          )}

          {/* Best posting times */}
          {bestTimes.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold text-stone-900">
                最佳发布时段
              </h2>
              <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
                <PostingHeatmap slots={bestTimes} />
              </div>
            </div>
          )}

          {/* Cross-platform comparison */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-stone-900">
              跨平台对比
            </h2>
            <div className="rounded-xl border border-stone-200 bg-white px-5 py-4">
              <PlatformTable platforms={platforms} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
