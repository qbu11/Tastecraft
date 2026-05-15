/**
 * Onboarding store — manages conversational onboarding state via Zustand.
 */

import { create } from 'zustand'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  quickReplies?: string[]
  showImportUI?: boolean
  showCompetitorUI?: boolean
}

export interface ImportedContent {
  url: string
  addedAt: number
}

export interface Competitor {
  url: string
  addedAt: number
}

interface OnboardingState {
  // Session
  sessionId: string | null
  currentStep: string
  stepIndex: number
  totalSteps: number
  completionPercent: number
  isComplete: boolean

  // Conversation
  messages: ChatMessage[]
  isLoading: boolean

  // Import & competitors
  importedContent: ImportedContent[]
  competitors: Competitor[]
  styleAnalysis: {
    tone: string
    summary: string
  } | null

  // Generated content (aha moment)
  generatedContent: string | null

  // Actions
  setSession: (sessionId: string, step: string, stepIndex: number) => void
  addMessage: (message: ChatMessage) => void
  setLoading: (loading: boolean) => void
  updateStep: (step: string, stepIndex: number) => void
  addImportedContent: (urls: string[]) => void
  addCompetitors: (urls: string[]) => void
  setStyleAnalysis: (analysis: { tone: string; summary: string }) => void
  setGeneratedContent: (content: string) => void
  setComplete: (complete: boolean) => void
  reset: () => void
}

const initialState = {
  sessionId: null,
  currentStep: 'lane_positioning',
  stepIndex: 0,
  totalSteps: 5,
  completionPercent: 0,
  isComplete: false,
  messages: [],
  isLoading: false,
  importedContent: [],
  competitors: [],
  styleAnalysis: null,
  generatedContent: null,
}

export const useOnboardingStore = create<OnboardingState>()((set) => ({
  ...initialState,

  setSession: (sessionId, step, stepIndex) =>
    set({ sessionId, currentStep: step, stepIndex }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setLoading: (loading) => set({ isLoading: loading }),

  updateStep: (step, stepIndex) =>
    set({
      currentStep: step,
      stepIndex,
      completionPercent: Math.round((stepIndex / 5) * 100),
    }),

  addImportedContent: (urls) =>
    set((state) => ({
      importedContent: [
        ...state.importedContent,
        ...urls.map((url) => ({ url, addedAt: Date.now() })),
      ],
    })),

  addCompetitors: (urls) =>
    set((state) => ({
      competitors: [
        ...state.competitors,
        ...urls.map((url) => ({ url, addedAt: Date.now() })),
      ],
    })),

  setStyleAnalysis: (analysis) => set({ styleAnalysis: analysis }),

  setGeneratedContent: (content) => set({ generatedContent: content }),

  setComplete: (complete) =>
    set({ isComplete: complete, completionPercent: complete ? 100 : 0 }),

  reset: () => set(initialState),
}))
