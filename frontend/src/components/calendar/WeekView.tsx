import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import type { ScheduleResponse } from '@/services/calendar'

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const HOURS = Array.from({ length: 16 }, (_, i) => i + 7) // 07:00 – 22:00

const PLATFORM_BADGES: Record<string, { label: string; color: string }> = {
  xiaohongshu: { label: '小红书', color: 'bg-red-50 text-red-600 ring-red-200' },
  wechat: { label: '微信', color: 'bg-green-50 text-green-700 ring-green-200' },
  weibo: { label: '微博', color: 'bg-yellow-50 text-yellow-700 ring-yellow-200' },
  zhihu: { label: '知乎', color: 'bg-blue-50 text-blue-600 ring-blue-200' },
  douyin: { label: '抖音', color: 'bg-pink-50 text-pink-600 ring-pink-200' },
  bilibili: { label: 'B站', color: 'bg-sky-50 text-sky-600 ring-sky-200' },
}

const STATUS_BG: Record<string, string> = {
  published: 'border-l-emerald-400 bg-emerald-50/50',
  pending: 'border-l-blue-400 bg-blue-50/50',
  draft: 'border-l-stone-300 bg-stone-50',
  failed: 'border-l-red-400 bg-red-50/50',
}

interface WeekViewProps {
  currentDate: Date
  entriesByDate: Record<string, ScheduleResponse[]>
  onSlotClick: (date: Date, hour: number) => void
}

function getWeekDates(refDate: Date): Date[] {
  const d = new Date(refDate)
  const dayOfWeek = d.getDay()
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(d)
  monday.setDate(d.getDate() + mondayOffset)

  return Array.from({ length: 7 }, (_, i) => {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    return day
  })
}

function formatDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function WeekView({
  currentDate,
  entriesByDate,
  onSlotClick,
}: WeekViewProps) {
  const today = useMemo(() => new Date(), [])
  const weekDates = useMemo(() => getWeekDates(currentDate), [currentDate])

  const weekKey = formatDateKey(weekDates[0])

  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
      {/* Header row: day labels + dates */}
      <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-stone-200">
        <div className="bg-stone-50" />
        {weekDates.map((d, i) => {
          const isToday = isSameDay(d, today)
          return (
            <div
              key={i}
              className={clsx(
                'flex flex-col items-center gap-0.5 border-l border-stone-200 py-2',
                isToday ? 'bg-[#c2714f]/5' : 'bg-stone-50',
              )}
            >
              <span className="text-[10px] text-stone-500">
                {DAY_LABELS[i]}
              </span>
              <span
                className={clsx(
                  'flex h-7 w-7 items-center justify-center rounded-full text-sm',
                  isToday
                    ? 'bg-[#c2714f] font-semibold text-white'
                    : 'text-stone-700',
                )}
              >
                {d.getDate()}
              </span>
            </div>
          )
        })}
      </div>

      {/* Time grid */}
      <AnimatePresence mode="wait">
        <motion.div
          key={weekKey}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="max-h-[600px] overflow-y-auto"
        >
          {HOURS.map((hour) => (
            <div
              key={hour}
              className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-stone-100 last:border-b-0"
            >
              {/* Time label */}
              <div className="flex items-start justify-end pr-2 pt-1 text-[10px] text-stone-400">
                {String(hour).padStart(2, '0')}:00
              </div>

              {/* Day columns */}
              {weekDates.map((d, dayIdx) => {
                const key = formatDateKey(d)
                const dayEntries = entriesByDate[key] ?? []
                const hourEntries = dayEntries.filter((e) => {
                  const h = new Date(e.scheduled_at).getHours()
                  return h === hour
                })
                const isToday = isSameDay(d, today)

                return (
                  <div
                    key={dayIdx}
                    onClick={() => onSlotClick(d, hour)}
                    className={clsx(
                      'group relative min-h-12 cursor-pointer border-l border-stone-100 px-1 py-0.5 transition-colors',
                      isToday ? 'bg-[#c2714f]/[0.02]' : 'hover:bg-stone-50',
                    )}
                  >
                    {hourEntries.map((entry, idx) => {
                      const badge = PLATFORM_BADGES[entry.platform]
                      return (
                        <div
                          key={`${entry.id}-${idx}`}
                          className={clsx(
                            'mb-0.5 rounded border-l-2 px-1.5 py-1 text-[10px]',
                            STATUS_BG[entry.status] ?? 'border-l-stone-300 bg-stone-50',
                          )}
                        >
                          <p className="truncate font-medium text-stone-700">
                            {entry.content_title || '无标题'}
                          </p>
                          {badge && (
                            <span
                              className={clsx(
                                'mt-0.5 inline-block rounded-full px-1.5 py-0.5 text-[8px] font-medium ring-1',
                                badge.color,
                              )}
                            >
                              {badge.label}
                            </span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })}
            </div>
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
