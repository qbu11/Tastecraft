import { api } from './api'

/* ── Streaming Generation ── */

export interface GenerateStreamParams {
  topic?: string
  direction?: string
  platform?: string
  tasteContextIds?: string[]
  systemPrompt?: string
  userPrompt?: string
}

export interface RewriteSectionParams {
  contentId: string
  originalText: string
  instruction: string
}

export interface StyleParams {
  formality: number
  length: number
  emotion: number
  expertise: number
}

export interface AdjustStyleParams {
  contentId: string
  styleParams: StyleParams
}

/* ── Variant Generation Types ── */

export interface ContentVariant {
  id: string
  angle: string
  hook: string
  outline: string[]
  tone: string
}

export interface VariantRequestParams {
  topic: string
  direction?: string
  platform?: string
  num_variants?: number
  taste_context_ids?: string[]
}

export interface VariantResponse {
  topic: string
  platform: string
  variants: ContentVariant[]
}

export interface ExpandVariantParams {
  variant_id: string
  topic: string
  angle: string
  hook: string
  outline: string[]
  tone: string
  platform?: string
  taste_context_ids?: string[]
}

/**
 * Start a streaming generation session.
 * Returns a ReadableStream via fetch (not axios, as axios doesn't support SSE well).
 */
export function generateContentStream(
  params: GenerateStreamParams,
  token?: string,
): { response: Promise<Response>; abort: () => void } {
  const controller = new AbortController()

  const response = fetch('/api/v1/generate/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
    signal: controller.signal,
  })

  return {
    response,
    abort: () => controller.abort(),
  }
}

/**
 * Rewrite a specific section of content.
 */
export async function rewriteSection(params: RewriteSectionParams) {
  const { data } = await api.post<{ rewritten: string }>(
    '/v1/generate/rewrite',
    params,
  )
  return data.rewritten
}

/**
 * Regenerate content with adjusted style parameters.
 */
export async function adjustStyle(params: AdjustStyleParams) {
  const { data } = await api.post<{ content: string }>(
    '/v1/generate/adjust-style',
    params,
  )
  return data.content
}

/**
 * Send a chat message in the creative workspace context.
 */
export async function sendCreativeChat(params: {
  contentId?: string
  message: string
  editorContent?: string
  platform?: string
}) {
  const { data } = await api.post<{
    reply: string
    suggestion?: { type: string; label: string; targetSection?: string }
  }>('/v1/generate/chat', params)
  return data
}

/* ── Variant Generation ── */

/**
 * Generate 2-3 content variants/approaches for a topic.
 */
export async function generateVariants(
  params: VariantRequestParams,
): Promise<VariantResponse> {
  const { data } = await api.post<VariantResponse>(
    '/v1/generate/variants',
    params,
  )
  return data
}

/**
 * Expand a chosen variant into full content via SSE streaming.
 * Returns a fetch response + abort controller (not axios — SSE requires fetch).
 */
export function expandVariantStream(
  params: ExpandVariantParams,
  token?: string,
): { response: Promise<Response>; abort: () => void } {
  const controller = new AbortController()

  const response = fetch('/api/v1/generate/expand-variant', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(params),
    signal: controller.signal,
  })

  return {
    response,
    abort: () => controller.abort(),
  }
}
