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
