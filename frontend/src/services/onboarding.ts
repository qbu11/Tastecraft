/**
 * Onboarding API service — handles all communication with the onboarding backend.
 */

import { api } from './api'

// ── Types ──────────────────────────────────────────────────────────────────

export interface OnboardingSessionResponse {
  session_id: string
  first_message: string
  current_step: string
  step_index: number
  total_steps: number
  quick_replies: string[]
  created_at: string
}

export interface AIResponse {
  message: string
  current_step: string
  step_index: number
  total_steps: number
  quick_replies: string[]
  show_import_ui: boolean
  show_competitor_ui: boolean
  is_complete: boolean
  generated_content: string | null
}

export interface OnboardingStatus {
  session_id: string
  current_step: string
  step_index: number
  total_steps: number
  completion_percent: number
  imported_content_count: number
  competitors_added: number
  is_complete: boolean
}

export interface StyleAnalysis {
  sentence_avg_length: number
  paragraph_avg_length: number
  tone: string
  vocabulary_level: string
  structure_preference: string
  topic_distribution: Record<string, number>
  signature_phrases: string[]
  summary: string
}

// ── API Calls ──────────────────────────────────────────────────────────────

export async function startOnboarding(
  projectName?: string,
): Promise<OnboardingSessionResponse> {
  const { data } = await api.post<OnboardingSessionResponse>(
    '/v1/onboarding/start',
    { project_name: projectName },
  )
  return data
}

export async function sendMessage(
  sessionId: string,
  message: string,
): Promise<AIResponse> {
  const { data } = await api.post<AIResponse>('/v1/onboarding/message', {
    session_id: sessionId,
    message,
  })
  return data
}

export async function importContent(
  sessionId: string,
  urls: string[],
): Promise<StyleAnalysis> {
  const { data } = await api.post<StyleAnalysis>('/v1/onboarding/import-content', {
    session_id: sessionId,
    urls,
  })
  return data
}

export async function addCompetitors(
  sessionId: string,
  urls: string[],
  notes?: string,
): Promise<{ success: boolean; competitors_added: number; message: string }> {
  const { data } = await api.post('/v1/onboarding/add-competitors', {
    session_id: sessionId,
    urls,
    notes,
  })
  return data
}

export async function getOnboardingStatus(
  sessionId: string,
): Promise<OnboardingStatus> {
  const { data } = await api.get<OnboardingStatus>('/v1/onboarding/status', {
    params: { session_id: sessionId },
  })
  return data
}

export async function completeOnboarding(
  sessionId: string,
): Promise<{ success: boolean; vault: unknown; first_content: string; message: string }> {
  const { data } = await api.post('/v1/onboarding/complete', {
    session_id: sessionId,
  })
  return data
}
