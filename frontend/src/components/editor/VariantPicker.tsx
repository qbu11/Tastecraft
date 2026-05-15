/**
 * VariantPicker — Card-based selection UI for content variant approaches.
 *
 * Shows 2-3 cards side by side. Each card displays the variant's angle title,
 * hook preview, tone badge, and outline. Click to select, then expand.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, ChevronRight, Loader2, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

// ── Types ──────────────────────────────────────────────────────────────────

export interface ContentVariant {
  id: string
  angle: string
  hook: string
  outline: string[]
  tone: string
}

interface VariantPickerProps {
  /** The generated variants to display */
  variants: ContentVariant[]
  /** Whether variants are currently loading */
  isLoading: boolean
  /** Called when user selects a variant and clicks expand */
  onExpand: (variant: ContentVariant) => void
  /** Called to regenerate variants */
  onRegenerate: () => void
  /** Topic being generated for (display only) */
  topic: string
}

// ── Tone color mapping ─────────────────────────────────────────────────────

const TONE_COLORS: Record<string, string> = {
  default: 'bg-stone-100 text-stone-600',
}

function getToneColor(tone: string): string {
  // Match partial keywords for common tones
  if (tone.includes('专业') || tone.includes('理性')) return 'bg-blue-50 text-blue-700'
  if (tone.includes('轻松') || tone.includes('口语')) return 'bg-green-50 text-green-700'
  if (tone.includes('故事') || tone.includes('叙事')) return 'bg-purple-50 text-purple-700'
  if (tone.includes('情感') || tone.includes('感性')) return 'bg-rose-50 text-rose-700'
  if (tone.includes('幽默') || tone.includes('搞笑')) return 'bg-amber-50 text-amber-700'
  if (tone.includes('干货') || tone.includes('实用')) return 'bg-cyan-50 text-cyan-700'
  return TONE_COLORS.default
}

// ── Component ──────────────────────────────────────────────────────────────

export function VariantPicker({
  variants,
  isLoading,
  onExpand,
  onRegenerate,
  topic,
}: VariantPickerProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const selectedVariant = variants.find((v) => v.id === selectedId) ?? null

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-16">
        <Loader2 size={32} className="animate-spin text-[#c87b5a]" />
        <p className="text-sm text-stone-500">
          正在为「{topic}」生成创作方向...
        </p>
      </div>
    )
  }

  if (variants.length === 0) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto w-full max-w-4xl px-6 py-8"
    >
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-stone-900">
            选择创作方向
          </h2>
          <p className="mt-1 text-sm text-stone-500">
            为「{topic}」生成了 {variants.length} 个不同角度，选择你最喜欢的方向
          </p>
        </div>
        <button
          onClick={onRegenerate}
          className="flex items-center gap-1.5 rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300 hover:bg-stone-50"
        >
          <RefreshCw size={12} />
          换一批
        </button>
      </div>

      {/* Variant Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {variants.map((variant, idx) => {
          const isSelected = selectedId === variant.id
          return (
            <motion.button
              key={variant.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              onClick={() => setSelectedId(isSelected ? null : variant.id)}
              className={clsx(
                'group relative flex flex-col items-start rounded-xl border-2 p-5 text-left transition-all',
                isSelected
                  ? 'border-[#c87b5a] bg-[#c87b5a]/5 shadow-md'
                  : 'border-stone-200 bg-white hover:border-stone-300 hover:shadow-sm',
              )}
            >
              {/* Angle title */}
              <div className="mb-2 flex w-full items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-stone-900">
                  {variant.angle}
                </h3>
                <span
                  className={clsx(
                    'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium',
                    getToneColor(variant.tone),
                  )}
                >
                  {variant.tone}
                </span>
              </div>

              {/* Hook preview */}
              <p className="mb-3 line-clamp-2 text-sm leading-relaxed text-stone-600">
                {variant.hook}
              </p>

              {/* Outline */}
              <ul className="mb-4 w-full space-y-1">
                {variant.outline.slice(0, 4).map((point, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-1.5 text-xs text-stone-500"
                  >
                    <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-stone-300" />
                    <span className="line-clamp-1">{point}</span>
                  </li>
                ))}
                {variant.outline.length > 4 && (
                  <li className="text-xs text-stone-400">
                    +{variant.outline.length - 4} more...
                  </li>
                )}
              </ul>

              {/* Selection indicator */}
              {isSelected && (
                <div className="absolute -right-px -top-px rounded-bl-lg rounded-tr-xl bg-[#c87b5a] px-2 py-0.5 text-[10px] font-medium text-white">
                  已选择
                </div>
              )}
            </motion.button>
          )
        })}
      </div>

      {/* Expand button */}
      {selectedVariant && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 flex justify-center"
        >
          <button
            onClick={() => onExpand(selectedVariant)}
            className="flex items-center gap-2 rounded-lg bg-[#c87b5a] px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-[#b06a4a]"
          >
            <Sparkles size={16} />
            展开这个方向
            <ChevronRight size={14} />
          </button>
        </motion.div>
      )}
    </motion.div>
  )
}
