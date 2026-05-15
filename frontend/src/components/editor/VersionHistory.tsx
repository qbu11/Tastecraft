import { useState, useCallback, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  X,
  Clock,
  RotateCcw,
  ChevronRight,
  Bot,
  Pencil,
  Palette,
  GitBranch,
} from 'lucide-react'
import {
  listVersions,
  getVersionDiff,
  rollbackToVersion,
  partialRollback,
  type ContentVersion,
  type VersionDiff,
  type DiffLine,
} from '@/services/versions'

interface VersionHistoryProps {
  contentId: number | string | null
  isOpen: boolean
  onClose: () => void
  onRollback?: (title: string, body: string) => void
}

const CREATED_BY_CONFIG: Record<
  string,
  { label: string; icon: typeof Bot; color: string }
> = {
  ai_generated: { label: 'AI', icon: Bot, color: 'bg-violet-100 text-violet-700' },
  user_edited: { label: '手动', icon: Pencil, color: 'bg-sky-100 text-sky-700' },
  style_adjusted: { label: '风格', icon: Palette, color: 'bg-amber-100 text-amber-700' },
  variant_expanded: { label: '变体', icon: GitBranch, color: 'bg-emerald-100 text-emerald-700' },
}

function CreatedByBadge({ type }: { type: string }) {
  const config = CREATED_BY_CONFIG[type] ?? CREATED_BY_CONFIG.user_edited
  const Icon = config.icon
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium ${config.color}`}
    >
      <Icon size={10} />
      {config.label}
    </span>
  )
}

function DiffView({ diff }: { diff: VersionDiff }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 text-xs">
      {/* Summary bar */}
      <div className="flex items-center gap-3 border-b border-stone-200 px-3 py-2 text-[11px] text-stone-500">
        <span>
          v{diff.version_from} {'-->'} v{diff.version_to}
        </span>
        {diff.title_changed && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-amber-700">
            标题已更改
          </span>
        )}
        <span className="text-green-600">+{diff.additions}</span>
        <span className="text-red-500">-{diff.deletions}</span>
      </div>

      {/* Diff lines */}
      <div className="max-h-[400px] overflow-y-auto font-mono">
        {diff.body_lines.map((line, idx) => (
          <DiffLineRow key={idx} line={line} />
        ))}
        {diff.body_lines.length === 0 && (
          <div className="px-3 py-4 text-center text-stone-400">
            内容无差异
          </div>
        )}
      </div>
    </div>
  )
}

function DiffLineRow({ line }: { line: DiffLine }) {
  const bgClass =
    line.type === 'addition'
      ? 'bg-green-50'
      : line.type === 'deletion'
        ? 'bg-red-50'
        : ''
  const textClass =
    line.type === 'addition'
      ? 'text-green-800'
      : line.type === 'deletion'
        ? 'text-red-800'
        : 'text-stone-600'
  const prefix =
    line.type === 'addition' ? '+' : line.type === 'deletion' ? '-' : ' '

  return (
    <div className={`flex ${bgClass}`}>
      <span className="w-8 shrink-0 select-none border-r border-stone-200 px-1 text-right text-stone-400">
        {line.line_number_old ?? ''}
      </span>
      <span className="w-8 shrink-0 select-none border-r border-stone-200 px-1 text-right text-stone-400">
        {line.line_number_new ?? ''}
      </span>
      <span className={`w-4 shrink-0 select-none text-center ${textClass}`}>
        {prefix}
      </span>
      <span className={`flex-1 whitespace-pre-wrap break-all px-2 py-0.5 ${textClass}`}>
        {line.content}
      </span>
    </div>
  )
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()

  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`

  return d.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function VersionHistory({
  contentId,
  isOpen,
  onClose,
  onRollback,
}: VersionHistoryProps) {
  const [versions, setVersions] = useState<ContentVersion[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null)
  const [diff, setDiff] = useState<VersionDiff | null>(null)
  const [isDiffLoading, setIsDiffLoading] = useState(false)
  const [isRollingBack, setIsRollingBack] = useState(false)

  // Fetch versions when panel opens
  useEffect(() => {
    if (!isOpen || !contentId) return

    setIsLoading(true)
    listVersions(contentId)
      .then((data) => {
        setVersions(data)
        setSelectedVersion(null)
        setDiff(null)
      })
      .catch(() => {
        setVersions([])
      })
      .finally(() => setIsLoading(false))
  }, [isOpen, contentId])

  // Load diff when a version is selected
  const handleSelectVersion = useCallback(
    async (versionNumber: number) => {
      if (!contentId || versions.length < 2) return

      setSelectedVersion(versionNumber)
      setIsDiffLoading(true)

      // Find the latest version to diff against
      const latestVersion = versions[0]?.version_number
      if (!latestVersion || versionNumber === latestVersion) {
        setDiff(null)
        setIsDiffLoading(false)
        return
      }

      try {
        const d = await getVersionDiff(contentId, versionNumber, latestVersion)
        setDiff(d)
      } catch {
        setDiff(null)
      } finally {
        setIsDiffLoading(false)
      }
    },
    [contentId, versions],
  )

  // Rollback handler
  const handleRollback = useCallback(
    async (versionNumber: number) => {
      if (!contentId) return

      setIsRollingBack(true)
      try {
        const result = await rollbackToVersion(contentId, versionNumber)
        // Notify parent to update editor content
        onRollback?.(result.title, result.body)
        // Refresh version list
        const updated = await listVersions(contentId)
        setVersions(updated)
        setSelectedVersion(null)
        setDiff(null)
      } catch {
        // silently handle
      } finally {
        setIsRollingBack(false)
      }
    },
    [contentId, onRollback],
  )

  // Partial rollback: use opening from old version
  const handlePartialRollback = useCallback(
    async (versionNumber: number, sections: string[]) => {
      if (!contentId) return

      setIsRollingBack(true)
      try {
        const result = await partialRollback(contentId, {
          from_version: versionNumber,
          sections,
        })
        onRollback?.(result.title, result.body)
        const updated = await listVersions(contentId)
        setVersions(updated)
        setSelectedVersion(null)
        setDiff(null)
      } catch {
        // silently handle
      } finally {
        setIsRollingBack(false)
      }
    },
    [contentId, onRollback],
  )

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.2 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black"
            onClick={onClose}
          />

          {/* Slide-out panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            className="fixed inset-y-0 right-0 z-50 flex w-[420px] max-w-[90vw] flex-col bg-white shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-stone-200 px-4 py-3">
              <div className="flex items-center gap-2">
                <Clock size={16} className="text-stone-500" />
                <h2 className="text-sm font-semibold text-stone-800">
                  版本历史
                </h2>
                {versions.length > 0 && (
                  <span className="rounded-full bg-stone-100 px-2 py-0.5 text-[10px] font-medium text-stone-500">
                    {versions.length} 个版本
                  </span>
                )}
              </div>
              <button
                onClick={onClose}
                className="rounded-lg p-1.5 text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600"
              >
                <X size={16} />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-[#c87b5a]" />
                </div>
              ) : versions.length === 0 ? (
                <div className="px-4 py-12 text-center text-sm text-stone-400">
                  暂无版本记录
                </div>
              ) : (
                <div className="divide-y divide-stone-100">
                  {versions.map((version) => (
                    <div key={version.id} className="px-4 py-3">
                      {/* Version row */}
                      <button
                        onClick={() =>
                          handleSelectVersion(version.version_number)
                        }
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${
                          selectedVersion === version.version_number
                            ? 'bg-stone-100'
                            : 'hover:bg-stone-50'
                        }`}
                      >
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-200 text-xs font-bold text-stone-600">
                          v{version.version_number}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="truncate text-sm font-medium text-stone-700">
                              {version.title || '(无标题)'}
                            </span>
                            <CreatedByBadge type={version.created_by} />
                          </div>
                          <div className="text-[11px] text-stone-400">
                            {formatTime(version.created_at)}
                          </div>
                        </div>
                        <ChevronRight
                          size={14}
                          className={`shrink-0 text-stone-400 transition-transform ${
                            selectedVersion === version.version_number
                              ? 'rotate-90'
                              : ''
                          }`}
                        />
                      </button>

                      {/* Expanded: diff + actions */}
                      <AnimatePresence>
                        {selectedVersion === version.version_number && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 space-y-2 pl-10">
                              {/* Diff view */}
                              {isDiffLoading ? (
                                <div className="flex items-center justify-center py-4">
                                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-stone-300 border-t-[#c87b5a]" />
                                </div>
                              ) : diff ? (
                                <DiffView diff={diff} />
                              ) : (
                                <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-3 text-center text-xs text-stone-400">
                                  这是当前版本
                                </div>
                              )}

                              {/* Rollback actions */}
                              {version.version_number !==
                                versions[0]?.version_number && (
                                <div className="flex flex-wrap gap-2 pb-1">
                                  <button
                                    onClick={() =>
                                      handleRollback(version.version_number)
                                    }
                                    disabled={isRollingBack}
                                    className="flex items-center gap-1 rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-[#c87b5a] hover:text-[#c87b5a] disabled:opacity-50"
                                  >
                                    <RotateCcw size={12} />
                                    回退到此版本
                                  </button>
                                  <button
                                    onClick={() =>
                                      handlePartialRollback(
                                        version.version_number,
                                        ['opening'],
                                      )
                                    }
                                    disabled={isRollingBack}
                                    className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300 disabled:opacity-50"
                                  >
                                    用此版本的开头
                                  </button>
                                  <button
                                    onClick={() =>
                                      handlePartialRollback(
                                        version.version_number,
                                        ['closing'],
                                      )
                                    }
                                    disabled={isRollingBack}
                                    className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300 disabled:opacity-50"
                                  >
                                    用此版本的结尾
                                  </button>
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
