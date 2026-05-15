import { useState, useCallback, useRef } from 'react'
import { useAuthStore } from '@/stores/authStore'

interface StreamingState {
  isGenerating: boolean
  progress: string
  error: string | null
}

interface UseStreamingGenerationOptions {
  onChunk?: (chunk: string) => void
  onComplete?: (fullText: string) => void
  onError?: (error: string) => void
}

export function useStreamingGeneration(options?: UseStreamingGenerationOptions) {
  const [state, setState] = useState<StreamingState>({
    isGenerating: false,
    progress: '',
    error: null,
  })
  const abortRef = useRef<AbortController | null>(null)
  const token = useAuthStore.getState().token

  const startGeneration = useCallback(
    async (params: {
      topic?: string
      direction?: string
      platform?: string
      tasteContextIds?: string[]
      systemPrompt?: string
      userPrompt?: string
    }) => {
      // Cancel any existing generation
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setState({ isGenerating: true, progress: '', error: null })
      let fullText = ''

      try {
        const response = await fetch('/api/v1/generate/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(params),
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Generation failed: ${response.status}`)
        }

        const reader = response.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') {
                setState((s) => ({ ...s, isGenerating: false }))
                options?.onComplete?.(fullText)
                return fullText
              }
              try {
                const parsed = JSON.parse(data) as { type: string; content?: string; error?: string }
                if (parsed.type === 'content' && parsed.content) {
                  fullText += parsed.content
                  setState((s) => ({ ...s, progress: fullText }))
                  options?.onChunk?.(parsed.content)
                } else if (parsed.type === 'error') {
                  throw new Error(parsed.error ?? 'Unknown error')
                }
              } catch (parseErr) {
                // Non-JSON SSE data, treat as raw text
                if (!data.startsWith('{')) {
                  fullText += data
                  setState((s) => ({ ...s, progress: fullText }))
                  options?.onChunk?.(data)
                }
              }
            }
          }
        }

        setState((s) => ({ ...s, isGenerating: false }))
        options?.onComplete?.(fullText)
        return fullText
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          setState((s) => ({ ...s, isGenerating: false }))
          return fullText
        }
        const errorMsg = (err as Error).message
        setState({ isGenerating: false, progress: fullText, error: errorMsg })
        options?.onError?.(errorMsg)
        return null
      }
    },
    [token, options],
  )

  const cancel = useCallback(() => {
    abortRef.current?.abort()
    setState((s) => ({ ...s, isGenerating: false }))
  }, [])

  return {
    isGenerating: state.isGenerating,
    progress: state.progress,
    error: state.error,
    startGeneration,
    cancel,
  }
}
