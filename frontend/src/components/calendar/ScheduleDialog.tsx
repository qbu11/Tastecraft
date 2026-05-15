import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Clock, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'
import { useCalendarStore } from '@/stores/calendarStore'
import type { SuggestedTime } from '@/services/calendar'

const PLATFORMS = [
  { value: 'xiaohongshu', label: '小红书', color: 'bg-red-50 text-red-600 ring-red-200' },
  { value: 'wechat', label: '微信公众号', color: 'bg-green-50 text-green-700 ring-green-200' },
  { value: 'weibo', label: '微博', color: 'bg-yellow-50 text-yellow-700 ring-yellow-200' },
  { value: 'zhihu', label: '知乎', color: 'bg-blue-50 text-blue-600 ring-blue-200' },
  { value: 'douyin', label: '抖音', color: 'bg-pink-50 text-pink-600 ring-pink-200' },
  { value: 'bilibili', label: 'B站', color: 'bg-sky-50 text-sky-600 ring-sky-200' },
]

interface DraftItem {
  id: number
  title: string
  platform: string
}

interface ScheduleDialogProps {
  open: boolean
  onClose: () => void
  onScheduled: () => void
  defaultDate?: Date
  defaultHour?: number
  drafts: DraftItem[]
}

function formatDateForInput(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatTimeForInput(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

function formatSuggestedTime(iso: string): string {
  const d = new Date(iso)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

export function ScheduleDialog({
  open,
  onClose,
  onScheduled,
  defaultDate,
  defaultHour,
  drafts,
}: ScheduleDialogProps) {
  const {
    scheduleContent,
    fetchSuggestTimes,
    suggestedTimes,
    loading,
  } = useCalendarStore()

  const [contentId, setContentId] = useState<number | null>(null)
  const [platform, setPlatform] = useState('xiaohongshu')
  const [date, setDate] = useState('')
  const [time, setTime] = useState('12:00')
  const [showSuggestions, setShowSuggestions] = useState(false)

  useEffect(() => {
    if (open && defaultDate) {
      setDate(formatDateForInput(defaultDate))
    }
    if (open && defaultHour !== undefined) {
      setTime(formatTimeForInput(defaultHour))
    }
  }, [open, defaultDate, defaultHour])

  // Reset form on close
  useEffect(() => {
    if (!open) {
      setContentId(null)
      setPlatform('xiaohongshu')
      setShowSuggestions(false)
    }
  }, [open])

  const handleSuggestTimes = useCallback(async () => {
    await fetchSuggestTimes(platform)
    setShowSuggestions(true)
  }, [fetchSuggestTimes, platform])

  const handleApplySuggestion = (suggestion: SuggestedTime) => {
    const d = new Date(suggestion.time)
    setDate(formatDateForInput(d))
    setTime(formatSuggestedTime(suggestion.time))
    setShowSuggestions(false)
  }

  const handleSubmit = async () => {
    if (!contentId || !date || !time) return

    const scheduledAt = `${date}T${time}:00`
    const result = await scheduleContent({
      content_id: contentId,
      platform,
      scheduled_at: scheduledAt,
      timezone: 'Asia/Shanghai',
    })

    if (result) {
      onScheduled()
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
            className="fixed left-1/2 top-1/2 z-50 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white p-6 shadow-xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-stone-900">
                定时发布
              </h2>
              <button
                onClick={onClose}
                className="flex h-8 w-8 items-center justify-center rounded-full text-stone-400 transition-colors hover:bg-stone-100 hover:text-stone-600"
              >
                <X size={16} />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              {/* Content selector */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-stone-600">
                  选择内容
                </label>
                <select
                  value={contentId ?? ''}
                  onChange={(e) =>
                    setContentId(e.target.value ? Number(e.target.value) : null)
                  }
                  className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 outline-none transition-colors focus:border-[#c2714f] focus:ring-1 focus:ring-[#c2714f]/20"
                >
                  <option value="">请选择草稿...</option>
                  {drafts.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.title || `草稿 #${d.id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* Platform selector */}
              <div>
                <label className="mb-1.5 block text-xs font-medium text-stone-600">
                  发布平台
                </label>
                <div className="flex flex-wrap gap-2">
                  {PLATFORMS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => {
                        setPlatform(p.value)
                        setShowSuggestions(false)
                      }}
                      className={clsx(
                        'rounded-full px-3 py-1 text-xs font-medium ring-1 transition-all',
                        platform === p.value
                          ? p.color
                          : 'bg-stone-50 text-stone-500 ring-stone-200 hover:bg-stone-100',
                      )}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Date + Time */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-stone-600">
                    日期
                  </label>
                  <input
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 outline-none transition-colors focus:border-[#c2714f] focus:ring-1 focus:ring-[#c2714f]/20"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-stone-600">
                    时间
                  </label>
                  <input
                    type="time"
                    value={time}
                    onChange={(e) => setTime(e.target.value)}
                    className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 outline-none transition-colors focus:border-[#c2714f] focus:ring-1 focus:ring-[#c2714f]/20"
                  />
                </div>
              </div>

              {/* Suggest times */}
              <div>
                <button
                  onClick={handleSuggestTimes}
                  className="flex items-center gap-1.5 text-xs text-[#c2714f] transition-colors hover:text-[#a85d3e]"
                >
                  <Sparkles size={12} />
                  建议最佳时间
                </button>

                <AnimatePresence>
                  {showSuggestions && suggestedTimes.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-2 overflow-hidden"
                    >
                      <div className="flex flex-wrap gap-2">
                        {suggestedTimes.map((s, i) => (
                          <button
                            key={i}
                            onClick={() => handleApplySuggestion(s)}
                            className="flex items-center gap-1 rounded-lg border border-stone-200 bg-stone-50 px-2.5 py-1.5 text-xs text-stone-600 transition-colors hover:border-[#c2714f]/30 hover:bg-[#c2714f]/5"
                          >
                            <Clock size={10} />
                            {formatSuggestedTime(s.time)}
                            <span className="text-stone-400">
                              {s.reason}
                            </span>
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded-lg px-4 py-2 text-sm text-stone-500 transition-colors hover:bg-stone-100"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!contentId || !date || !time || loading}
                className={clsx(
                  'rounded-lg px-5 py-2 text-sm font-medium transition-all',
                  contentId && date && time && !loading
                    ? 'bg-[#c2714f] text-white hover:bg-[#a85d3e]'
                    : 'cursor-not-allowed bg-stone-200 text-stone-400',
                )}
              >
                {loading ? '调度中...' : '定时发布'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
