import { useState } from 'react'
import { Lightbulb, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TasteIndicatorProps {
  rule: string
  dimension: string
  confidence: number
  editNumber: number
  className?: string
}

/**
 * Inline attribution indicator for AI-generated text.
 * Shows on hover to explain which taste preference influenced the content.
 */
export function TasteIndicator({
  rule,
  dimension,
  confidence,
  editNumber,
  className,
}: TasteIndicatorProps) {
  const [visible, setVisible] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  const confidencePercent = Math.round(confidence * 100)
  const confidenceColor =
    confidence >= 0.7
      ? 'text-emerald-600'
      : confidence >= 0.5
        ? 'text-amber-600'
        : 'text-slate-500'

  return (
    <span
      className={cn('relative inline-flex items-center', className)}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <Lightbulb
        className="inline h-3.5 w-3.5 text-amber-400 cursor-pointer"
        aria-label="Taste preference indicator"
      />

      {visible && (
        <span
          className={cn(
            'absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50',
            'w-64 rounded-lg bg-slate-900 text-white text-xs p-3 shadow-xl',
            'animate-in fade-in-0 zoom-in-95 duration-150',
          )}
          role="tooltip"
        >
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              setDismissed(true)
            }}
            className="absolute top-1.5 right-1.5 text-slate-400 hover:text-white"
            aria-label="Dismiss"
          >
            <X className="h-3 w-3" />
          </button>

          <span className="block font-medium text-amber-300 mb-1">
            {rule}
          </span>

          <span className="block text-slate-300">
            {dimension} — 来自你第{editNumber}次修改
          </span>

          <span className={cn('block mt-1', confidenceColor)}>
            置信度 {confidencePercent}%
          </span>

          {/* Tooltip arrow */}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-900" />
        </span>
      )}
    </span>
  )
}
