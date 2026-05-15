/**
 * Publish API service — WeChat MP draft & publish operations.
 */

import { api } from './api'

// ── Types ──────────────────────────────────────────────────────────────────

export interface WeChatDraftCreatePayload {
  title: string
  content_md: string
  author?: string
  digest?: string
  thumb_media_id?: string
}

export interface WeChatDraftResponse {
  media_id: string
  title: string
  created_at: string
  manage_url: string
}

export interface WeChatDraftListItem {
  media_id: string
  title: string
  digest: string
  update_time: number
}

export interface WeChatDraftList {
  items: WeChatDraftListItem[]
  total_count: number
  item_count: number
}

export interface PublishStatus {
  status: 'queued' | 'publishing' | 'success' | 'failed'
  platform: string
  media_id: string
  published_url: string
  error: string
  created_at: string
}

export interface ImageUploadResponse {
  media_id: string
  url: string
}

// ── WeChat Draft API ───────────────────────────────────────────────────────

export async function createWeChatDraft(
  payload: WeChatDraftCreatePayload,
): Promise<WeChatDraftResponse> {
  const { data } = await api.post<WeChatDraftResponse>(
    '/v1/publish/wechat/draft',
    payload,
  )
  return data
}

export async function publishWeChatDraft(
  mediaId: string,
): Promise<PublishStatus> {
  const { data } = await api.post<PublishStatus>(
    `/v1/publish/wechat/publish/${mediaId}`,
  )
  return data
}

export async function listWeChatDrafts(
  offset = 0,
  count = 20,
): Promise<WeChatDraftList> {
  const { data } = await api.get<WeChatDraftList>('/v1/publish/wechat/drafts', {
    params: { offset, count },
  })
  return data
}

export async function uploadWeChatImage(
  file: File,
): Promise<ImageUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<ImageUploadResponse>(
    '/v1/publish/wechat/upload-image',
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function deleteWeChatDraft(mediaId: string): Promise<void> {
  await api.delete(`/v1/publish/wechat/${mediaId}`)
}

// ── Weibo Publish API ─────────────────────────────────────────────────────

export interface WeiboPublishPayload {
  content: string
  images?: string[]
}

export interface WeiboPublishResponse {
  success: boolean
  post_id?: string | null
  draft_id?: string | null
  url?: string | null
  status?: string | null
  error?: string | null
}

export interface WeiboSessionStatus {
  logged_in: boolean
  platform: string
  message: string
}

export interface WeiboInitLoginResponse {
  qr_url?: string | null
  ws_url?: string | null
  message: string
}

export async function publishWeiboPost(
  payload: WeiboPublishPayload,
): Promise<WeiboPublishResponse> {
  const { data } = await api.post<WeiboPublishResponse>(
    '/v1/publish/weibo/publish',
    payload,
  )
  return data
}

export async function saveWeiboDraft(
  payload: WeiboPublishPayload,
): Promise<WeiboPublishResponse> {
  const { data } = await api.post<WeiboPublishResponse>(
    '/v1/publish/weibo/draft',
    payload,
  )
  return data
}

export async function getWeiboSessionStatus(): Promise<WeiboSessionStatus> {
  const { data } = await api.get<WeiboSessionStatus>(
    '/v1/publish/weibo/session-status',
  )
  return data
}

export async function initWeiboLogin(): Promise<WeiboInitLoginResponse> {
  const { data } = await api.post<WeiboInitLoginResponse>(
    '/v1/publish/weibo/init-login',
  )
  return data
}
