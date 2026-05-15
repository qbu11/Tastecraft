import { useCallback, useRef, useState } from 'react'
import { api } from '@/services/api'

interface DiffCaptureState {
  lastCapturedAt: Date | null
  editCount: number
  capturing: boolean
}

interface CaptureEditResponse {
  edit_id: number
  classification: {
    edit_type: string
    details: string
    word_count_delta: number
    similarity_ratio: number
  }
  new_preferences_extracted: number
  total_edits: number
}

const DEBOUNCE_MS = 2000

/**
 * Hook that wraps editor onChange to capture diffs.
 * Debounced (2s after last keystroke) — captures original vs modified
 * and sends to backend /taste/capture-edit.
 */
export function useDiffCapture(contentId: string, platform: string) {
  const [state, setState] = useState<DiffCaptureState>({
    lastCapturedAt: null,
    editCount: 0,
    capturing: false,
  })

  const originalRef = useRef<string>('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /**
   * Set the original (AI-generated) text that edits are compared against.
   * Call this when content is first loaded from the server.
   */
  const setOriginal = useCallback((text: string) => {
    originalRef.current = text
  }, [])

  /**
   * Notify the hook that content has changed.
   * Debounces by 2s — only sends capture request after user stops typing.
   */
  const onContentChange = useCallback(
    (modified: string) => {
      // Clear any pending capture
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }

      // Don't capture if no original set or content unchanged
      if (!originalRef.current || modified === originalRef.current) {
        return
      }

      timerRef.current = setTimeout(async () => {
        setState((prev) => ({ ...prev, capturing: true }))

        try {
          const { data } = await api.put<CaptureEditResponse>(
            '/taste/capture-edit',
            {
              original: originalRef.current,
              modified,
              platform,
              content_line_id: contentId ? Number(contentId) : null,
            },
            { params: { content_id: contentId || undefined } },
          )

          setState({
            lastCapturedAt: new Date(),
            editCount: data.total_edits,
            capturing: false,
          })

          // Update the original to the new modified version
          // so subsequent edits are compared against the latest save
          originalRef.current = modified
        } catch {
          setState((prev) => ({ ...prev, capturing: false }))
        }
      }, DEBOUNCE_MS)
    },
    [contentId, platform],
  )

  return {
    ...state,
    setOriginal,
    onContentChange,
  }
}
