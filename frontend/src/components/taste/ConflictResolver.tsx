import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ArrowRight, Check, GitBranch, X } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ─────────────────────────────────────────────────────────────────

export interface PreferenceConflict {
  id: string
  preference_a_id: number
  preference_b_id: number
  preference_a_rule: string
  preference_b_rule: string
  preference_a_platform: string | null
  preference_b_platform: string | null
  dimension: string
  context: string
  suggested_resolution: string
}

type Resolution = 'keep_first' | 'keep_second' | 'context_split'

// ── Single Conflict Card ──────────────────────────────────────────────────

function ConflictCard({
  conflict,
  onResolve,
  isResolving,
}: {
  conflict: PreferenceConflict
  onResolve: (conflictId: string, resolution: Resolution, contextNote?: string) => void
  isResolving: boolean
}) {
  const [expanded, setExpanded] = useState(false)

  const platformA = conflict.preference_a_platform || '通用'
  const platformB = conflict.preference_b_platform || '通用'
  const hasDifferentPlatforms = platformA !== platformB

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="rounded-xl border border-amber-200 bg-white p-4"
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-start gap-3 text-left"
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
          <AlertTriangle size={16} />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-stone-800">
            {conflict.dimension} 维度冲突
          </p>
          <p className="mt-0.5 text-xs text-stone-500 line-clamp-2">
            {conflict.context || `"${conflict.preference_a_rule}" 与 "${conflict.preference_b_rule}" 存在矛盾`}
          </p>
        </div>
        <motion.span
          animate={{ rotate: expanded ? 180 : 0 }}
          className="mt-1 text-stone-400"
        >
          <ArrowRight size={14} className="rotate-90" />
        </motion.span>
      </button>

      {/* Expanded details + resolution options */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 space-y-3 border-t border-stone-100 pt-4">
              {/* Preference A */}
              <div className="rounded-lg bg-stone-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700">
                    偏好 A
                  </span>
                  <span className="text-[10px] text-stone-400">{platformA}</span>
                </div>
                <p className="text-xs text-stone-700">{conflict.preference_a_rule}</p>
              </div>

              {/* Preference B */}
              <div className="rounded-lg bg-stone-50 p-3">
                <div className="mb-1 flex items-center gap-2">
                  <span className="rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-medium text-purple-700">
                    偏好 B
                  </span>
                  <span className="text-[10px] text-stone-400">{platformB}</span>
                </div>
                <p className="text-xs text-stone-700">{conflict.preference_b_rule}</p>
              </div>

              {/* AI suggestion */}
              {conflict.context && (
                <p className="text-xs italic text-stone-500">
                  AI 分析：{conflict.context}
                </p>
              )}

              {/* Resolution buttons */}
              <div className="flex flex-wrap gap-2 pt-1">
                {hasDifferentPlatforms && (
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    disabled={isResolving}
                    onClick={() =>
                      onResolve(
                        conflict.id,
                        'context_split',
                        `${platformA} vs ${platformB}`,
                      )
                    }
                    className="flex items-center gap-1.5 rounded-lg border border-[#c2714f]/30 bg-[#c2714f]/5 px-3 py-2 text-xs font-medium text-[#c2714f] transition-colors hover:bg-[#c2714f]/10 disabled:opacity-50"
                  >
                    <GitBranch size={12} />
                    按平台区分
                  </motion.button>
                )}

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  disabled={isResolving}
                  onClick={() => onResolve(conflict.id, 'keep_second')}
                  className="flex items-center gap-1.5 rounded-lg border border-stone-200 px-3 py-2 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-50 disabled:opacity-50"
                >
                  <Check size={12} />
                  保留最近的
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  disabled={isResolving}
                  onClick={() => onResolve(conflict.id, 'keep_first')}
                  className="flex items-center gap-1.5 rounded-lg border border-stone-200 px-3 py-2 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-50 disabled:opacity-50"
                >
                  <Check size={12} />
                  保留最早的
                </motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Main ConflictResolver Component ───────────────────────────────────────

interface ConflictResolverProps {
  conflicts: PreferenceConflict[]
  onResolve: (conflictId: string, resolution: Resolution, contextNote?: string) => Promise<void>
  onDismiss?: () => void
  className?: string
}

export function ConflictResolver({
  conflicts,
  onResolve,
  onDismiss,
  className,
}: ConflictResolverProps) {
  const [resolvingId, setResolvingId] = useState<string | null>(null)
  const [resolvedIds, setResolvedIds] = useState<Set<string>>(new Set())

  const unresolvedConflicts = conflicts.filter((c) => !resolvedIds.has(c.id))

  if (unresolvedConflicts.length === 0) return null

  async function handleResolve(
    conflictId: string,
    resolution: Resolution,
    contextNote?: string,
  ) {
    setResolvingId(conflictId)
    try {
      await onResolve(conflictId, resolution, contextNote)
      setResolvedIds((prev) => new Set([...prev, conflictId]))
    } finally {
      setResolvingId(null)
    }
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle size={16} className="text-amber-500" />
          <span className="text-sm font-medium text-stone-800">
            品味冲突检测到
          </span>
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
            {unresolvedConflicts.length}
          </span>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-stone-400 transition-colors hover:text-stone-600"
          >
            <X size={14} />
          </button>
        )}
      </div>

      {/* Conflict cards */}
      <AnimatePresence mode="popLayout">
        {unresolvedConflicts.map((conflict) => (
          <ConflictCard
            key={conflict.id}
            conflict={conflict}
            onResolve={handleResolve}
            isResolving={resolvingId === conflict.id}
          />
        ))}
      </AnimatePresence>
    </div>
  )
}
