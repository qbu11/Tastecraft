import { api } from './api'

/* ── Types ── */

export interface ContentVersion {
  id: number
  content_id: number
  version_number: number
  title: string
  body: string
  platform: string
  created_by: 'ai_generated' | 'user_edited' | 'style_adjusted' | 'variant_expanded'
  created_at: string
}

export interface DiffLine {
  type: 'addition' | 'deletion' | 'unchanged'
  content: string
  line_number_old: number | null
  line_number_new: number | null
}

export interface VersionDiff {
  version_from: number
  version_to: number
  title_changed: boolean
  body_lines: DiffLine[]
  additions: number
  deletions: number
}

export interface PartialRollbackPayload {
  from_version: number
  sections: string[]
}

/* ── API Functions ── */

export async function listVersions(contentId: number | string) {
  const { data } = await api.get<ContentVersion[]>(
    `/v1/content/${contentId}/versions`,
  )
  return data
}

export async function getVersionDiff(
  contentId: number | string,
  v1: number,
  v2: number,
) {
  const { data } = await api.get<VersionDiff>(
    `/v1/content/${contentId}/versions/${v1}/diff/${v2}`,
  )
  return data
}

export async function rollbackToVersion(
  contentId: number | string,
  versionNumber: number,
) {
  const { data } = await api.post<ContentVersion>(
    `/v1/content/${contentId}/versions/${versionNumber}/rollback`,
  )
  return data
}

export async function partialRollback(
  contentId: number | string,
  payload: PartialRollbackPayload,
) {
  const { data } = await api.post<ContentVersion>(
    `/v1/content/${contentId}/versions/partial-rollback`,
    payload,
  )
  return data
}
