import axios from 'axios'
import { useAuthStore } from '@/stores/authStore'

export const api = axios.create({
  baseURL: '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

/* ── Auth ── */

interface LoginPayload {
  phone: string
  code: string
}

interface LoginResponse {
  token: string
  user: {
    id: string
    name: string
    phone: string
    avatar?: string
    tasteScore: number
  }
}

export async function login(payload: LoginPayload) {
  const { data } = await api.post<LoginResponse>('/auth/login', payload)
  return data
}

export async function sendVerificationCode(phone: string) {
  const { data } = await api.post('/auth/send-code', { phone })
  return data
}

/* ── Content ── */

interface GenerateContentPayload {
  topic: string
  platform: string
  style?: string
}

interface ContentItem {
  id: string
  title: string
  body: string
  platform: string
  status: 'draft' | 'queued' | 'published'
  tasteScore: number
  createdAt: string
}

export async function generateContent(payload: GenerateContentPayload) {
  const { data } = await api.post<ContentItem>('/content/generate', payload)
  return data
}

export async function getContent(id: string) {
  const { data } = await api.get<ContentItem>(`/content/${id}`)
  return data
}

export async function updateContent(
  id: string,
  payload: Partial<ContentItem>,
) {
  const { data } = await api.put<ContentItem>(`/content/${id}`, payload)
  return data
}

export async function listContent(params?: {
  status?: string
  page?: number
  limit?: number
}) {
  const { data } = await api.get<{ items: ContentItem[]; total: number }>(
    '/content',
    { params },
  )
  return data
}

/* ── Publish ── */

export async function publishContent(contentId: string, platform: string) {
  const { data } = await api.post('/publish', { contentId, platform })
  return data
}

/* ── Taste Profile ── */

interface TasteProfile {
  score: number
  dimensions: Record<string, number>
  updatedAt: string
}

export async function getTasteProfile() {
  const { data } = await api.get<TasteProfile>('/taste/profile')
  return data
}

/* ── Analytics ── */

interface AnalyticsSummary {
  totalPosts: number
  totalViews: number
  avgEngagement: number
  platformBreakdown: Record<string, number>
}

export async function getAnalyticsSummary(period?: string) {
  const { data } = await api.get<AnalyticsSummary>('/analytics/summary', {
    params: { period },
  })
  return data
}
