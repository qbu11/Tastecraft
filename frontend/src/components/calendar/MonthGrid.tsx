import { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus } from 'lucide-react'
import type { ScheduleResponse } from '@/services/calendar'
import { clsx } from 'clsx'

const DAY_LABELS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const PLATFORM_COLORS: Record<string, string> = {
  xiaohongshu: 'bg-red-400',
  wechat: 'bg-green-500',
  weibo: 'bg-yellow-400',
  zhihu: 'bg-blue-500',
  douyin: 'bg-pink-500',
  bilibili: 'bg-sky-400',
}

const STATUS_COLORS: Record<string, string> = {
  published: 'bg-emerald-400',
  pending: 'bg-blue-400',
  draft: 'bg-stone-300',
  failed: 'bg-red-500',
  cancelled: 'bg-stone-200',
}

interface MonthGridProps {
  currentDate: Date
  entriesByDate: Record<string, ScheduleResponse[]>
  onDayClick: (date: Date) => void
  onAddClick: (date: Date) => void
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

function formatDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function MonthGrid({
  currentDate,
  entriesByDate,
  onDayClick,
  onAddClick,
}: MonthGridProps) {
  const today = useMemo(() => new Date(), [])
  const [expandedDay, setExpandedDay] = useState<string | null>(null)

  const { cells, year, month } = useMemo(() => {
    const y = currentDate.getFullYear()
    const m = currentDate.getMonth()
    const firstDay = new Date(y, m, 1).getDay()
    const daysInMonth = new Date(y, m + 1, 0).getDate()
    const offset = firstDay === 0 ? 6 : firstDay - 1

    const result: (Date | null)[] = [
      ...Array.from<null>({ length: offset }).fill(null),
      ...Array.from({ length: daysInMonth }, (_, i) => new Date(y, m, i + 1)),
    ]

    // Pad to fill complete rows
    const remainder = result.length % 7
    if (remainder > 0) {
      result.push(...Array.from<null>({ length: 7 - remainder }).fill(null))
    }

    return { cells: result, year: y, month: m }
  }, [currentDate])

  const handleDayClick = (date: Date) => {
    const key = formatDateKey(date)
    if (expandedDay === key) {
      setExpandedDay(null)
    } else {
      setExpandedDay(key)
      onDayClick(date)
    }
  }

  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-stone-200">
      {/* Day headers */}
      <div className="grid grid-cols-7 gap-px">
        {DAY_LABELS.map((d) => (
          <div
            key={d}
            className="bg-stone-100 py-2.5 text-center text-xs font-medium text-stone-500"
          >
            {d}
          </div>
        ))}
      </div>

      {/* Date cells */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${year}-${month}`}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="grid grid-cols-7 gap-px"
        >
          {cells.map((date, i) => {
            if (!date) {
              return (
                <div key={`empty-${i}`} className="h-24 bg-stone-50" />
              )
            }

            const key = formatDateKey(date)
            const entries = entriesByDate[key] ?? []
            const isToday = isSameDay(date, today)
            const isExpanded = expandedDay === key

            return (
              <div
                key={key}
                onClick={() => handleDayClick(date)}
                className={clsx(
                  'group relative flex min-h-24 cursor-pointer flex-col bg-white p-2 text-xs transition-all',
                  isToday && 'ring-2 ring-inset ring-[#c2714f]',
                  isExpanded && 'bg-stone-50',
                  !isToday && 'hover:bg-stone-50',
                )}
              >
                {/* Date number */}
                <div className="flex items-center justify-between">
                  <span
                    className={clsx(
                      'flex h-6 w-6 items-center justify-center rounded-full text-xs',
                      isToday
                        ? 'bg-[#c2714f] font-semibold text-white'
                        : 'text-stone-600',
                    )}
                  >
                    {date.getDate()}
                  </span>
                  {/* Add button on hover */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onAddClick(date)
                    }}
                    className="flex h-5 w-5 items-center justify-center rounded-full text-stone-300 opacity-0 transition-opacity hover:bg-stone-200 hover:text-stone-500 group-hover:opacity-100"
                  >
                    <Plus size={12} />
                  </button>
                </div>

                {/* Content dots */}
                {entries.length > 0 && !isExpanded && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {entries.slice(0, 4).map((entry, idx) => (
                      <div
                        key={`${entry.id}-${idx}`}
                        className={clsx(
                          'h-1.5 w-1.5 rounded-full',
                          STATUS_COLORS[entry.status] ?? 'bg-stone-300',
                        )}
                        title={`${entry.content_title} (${entry.platform})`}
                      />
                    ))}
                    {entries.length > 4 && (
                      <span className="text-[10px] text-stone-400">
                        +{entries.length - 4}
                      </span>
                    )}
                  </div>
                )}

                {/* Expanded entry list */}
                {isExpanded && entries.length > 0 && (
                  <div className="mt-1.5 space-y-1 overflow-y-auto">
                    {entries.map((entry, idx) => (
                      <div
                        key={`${entry.id}-${idx}`}
                        className="flex items-center gap-1 rounded px-1 py-0.5 hover:bg-stone-100"
                      >
                        <div
                          className={clsx(
                            'h-1.5 w-1.5 shrink-0 rounded-full',
                            PLATFORM_COLORS[entry.platform] ?? 'bg-stone-400',
                          )}
                        />
                        <span className="truncate text-[10px] text-stone-600">
                          {entry.content_title || '无标题'}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Expanded empty */}
                {isExpanded && entries.length === 0 && (
                  <p className="mt-2 text-center text-[10px] text-stone-400">
                    暂无内容
                  </p>
                )}
              </div>
            )
          })}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
