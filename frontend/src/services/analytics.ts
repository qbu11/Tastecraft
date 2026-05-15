import { api } from './api'

/* ── Types ── */

export interface PeriodDelta {
  current: number
  previous: number
  delta_pct: number
}

export interface PerformanceSummary {
  period_days: number
  total_views: PeriodDelta
  total_likes: PeriodDelta
  total_comments: PeriodDelta
  total_shares: PeriodDelta
  total_saves: PeriodDelta
  avg_engagement_rate: PeriodDelta
  total_published: PeriodDelta
}

export interface ContentMetrics {
  content_id: number
  platform: string
  title: string | null
  views: number
  likes: number
  comments: number
  shares: number
  saves: number
  engagement_rate: number
  collection_type: string | null
  collected_at: string | null
}

export interface TasteCorrelation {
  dimension: string
  rule: string
  metric: string
  avg_with: number
  avg_without: number
  lift_pct: number
  sample_size: number
}

export interface TimeSlot {
  day_of_week: number
  hour: number
  avg_engagement: number
  sample_size: number
}

export interface PlatformStats {
  platform: string
  total_published: number
  total_views: number
  total_likes: number
  avg_engagement_rate: number
  best_content_title: string | null
  best_content_id: number | null
}

export interface PlatformComparison {
  platforms: PlatformStats[]
}

/* ── API calls ── */

export async function fetchAnalyticsSummary(days: number = 7) {
  const { data } = await api.get<PerformanceSummary>('/v1/analytics/summary', {
    params: { days },
  })
  return data
}

export async function fetchContentMetrics(contentId: number) {
  const { data } = await api.get<ContentMetrics[]>(
    `/v1/analytics/content/${contentId}`,
  )
  return data
}

export async function fetchCorrelations() {
  const { data } = await api.get<TasteCorrelation[]>(
    '/v1/analytics/correlations',
  )
  return data
}

export async function fetchBestTimes(platform?: string) {
  const { data } = await api.get<TimeSlot[]>('/v1/analytics/best-times', {
    params: platform ? { platform } : undefined,
  })
  return data
}

export async function fetchPlatformComparison() {
  const { data } = await api.get<PlatformComparison>(
    '/v1/analytics/comparison',
  )
  return data
}
