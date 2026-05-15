import { api } from './api'

/* ── Types ── */

export interface Competitor {
  id: number
  user_id: number
  project_id: number | null
  platform: string
  account_id: string
  account_name: string
  account_url: string | null
  last_synced_at: string | null
  total_posts_tracked: number
  created_at: string
}

export interface CompetitorPost {
  id: number
  competitor_id: number
  platform_post_id: string
  title: string | null
  content_text: string | null
  media_urls: string[] | null
  tags: string[] | null
  likes: number
  comments: number
  shares: number
  views: number
  published_at: string | null
  fetched_at: string
  is_viral: boolean
}

export interface TrendingTopic {
  topic: string
  frequency: number
  avg_engagement: number
  example_titles: string[]
}

export interface ViralAlert {
  post_id: number
  competitor_name: string
  platform: string
  title: string | null
  likes: number
  comments: number
  shares: number
  views: number
  published_at: string | null
  engagement_ratio: number
}

export interface TrendReport {
  project_id: number | null
  generated_at: string
  period_days: number
  top_topics: TrendingTopic[]
  viral_posts: ViralAlert[]
  total_posts_analyzed: number
  summary: string
}

export interface SyncResult {
  competitor_id: number
  competitor_name: string
  platform: string
  new_posts: number
  updated_posts: number
  viral_detected: number
  error: string | null
}

interface CompetitorCreatePayload {
  platform: string
  account_id: string
  account_name: string
  account_url?: string
  project_id?: number
}

/* ── API functions ── */

export async function addCompetitor(payload: CompetitorCreatePayload) {
  const { data } = await api.post<Competitor>('/v1/competitors/', payload)
  return data
}

export async function listCompetitors(params?: {
  project_id?: number
  platform?: string
  skip?: number
  limit?: number
}) {
  const { data } = await api.get<{ items: Competitor[]; total: number }>(
    '/v1/competitors/',
    { params },
  )
  return data
}

export async function removeCompetitor(id: number) {
  await api.delete(`/v1/competitors/${id}`)
}

export async function syncCompetitor(id: number) {
  const { data } = await api.post<SyncResult>(`/v1/competitors/${id}/sync`)
  return data
}

export async function syncAllCompetitors() {
  const { data } = await api.post<SyncResult[]>('/v1/competitors/sync-all')
  return data
}

export async function getTrends(params?: {
  project_id?: number
  period_days?: number
}) {
  const { data } = await api.get<TrendReport>('/v1/competitors/trends', {
    params,
  })
  return data
}

export async function getCompetitorPosts(
  competitorId: number,
  params?: { skip?: number; limit?: number; viral_only?: boolean },
) {
  const { data } = await api.get<{ items: CompetitorPost[]; total: number }>(
    `/v1/competitors/${competitorId}/posts`,
    { params },
  )
  return data
}

export async function getViralPosts(params?: {
  project_id?: number
  limit?: number
}) {
  const { data } = await api.get<ViralAlert[]>('/v1/competitors/viral', {
    params,
  })
  return data
}
