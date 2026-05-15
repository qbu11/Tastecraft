import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  List,
} from 'lucide-react'
import { clsx } from 'clsx'
import { MonthGrid } from '@/components/calendar/MonthGrid'
import { WeekView } from '@/components/calendar/WeekView'
import { ScheduleDialog } from '@/components/calendar/ScheduleDialog'
import { useCalendarStore } from '@/stores/calendarStore'
import type { ScheduleResponse } from '@/services/calendar'

/* ── helpers ── */

function formatDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getMonthRange(d: Date): [string, string] {
  const y = d.getFullYear()
  const m = d.getMonth()
  const start = new Date(y, m, 1)
  const end = new Date(y, m + 1, 0)
  return [formatDateKey(start), formatDateKey(end)]
}

function getWeekRange(d: Date): [string, string] {
  const dayOfWeek = d.getDay()
  const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(d)
  monday.setDate(d.getDate() + mondayOffset)
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return [formatDateKey(monday), formatDateKey(sunday)]
}

/* ── mock drafts for dialog (will come from content API later) ── */

const MOCK_DRAFTS = [
  { id: 1, title: 'AI 创业的 5 个关键建议', platform: 'xiaohongshu' },
  { id: 2, title: '2026 科技趋势深度解读', platform: 'wechat' },
  { id: 3, title: '独立开发者的日常', platform: 'weibo' },
]

/* ── Component ── */

export function Calendar() {
  const {
    currentDate,
    viewMode,
    calendarView,
    loading,
    setViewMode,
    goToToday,
    goToPrev,
    goToNext,
    fetchCalendar,
  } = useCalendarStore()

  /* Schedule dialog state */
  const [dialogOpen, setDialogOpen] = useState(false)
  const [dialogDate, setDialogDate] = useState<Date | undefined>()
  const [dialogHour, setDialogHour] = useState<number | undefined>()

  /* Fetch calendar data when date or view changes */
  useEffect(() => {
    const [start, end] =
      viewMode === 'month'
        ? getMonthRange(currentDate)
        : getWeekRange(currentDate)
    fetchCalendar(start, end)
  }, [currentDate, viewMode, fetchCalendar])

  /* Build entriesByDate lookup */
  const entriesByDate = useMemo<Record<string, ScheduleResponse[]>>(() => {
    if (!calendarView) return {}
    const map: Record<string, ScheduleResponse[]> = {}
    for (const entry of calendarView.entries) {
      map[entry.date] = entry.entries
    }
    return map
  }, [calendarView])

  /* Stats */
  const stats = calendarView?.stats ?? {
    total: 0,
    published: 0,
    scheduled: 0,
    draft: 0,
  }

  /* Display title */
  const title = useMemo(() => {
    if (viewMode === 'month') {
      return currentDate.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: 'long',
      })
    }
    const dayOfWeek = currentDate.getDay()
    const mondayOffset = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
    const monday = new Date(currentDate)
    monday.setDate(currentDate.getDate() + mondayOffset)
    const sunday = new Date(monday)
    sunday.setDate(monday.getDate() + 6)
    const fmt = (d: Date) =>
      d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    return `${fmt(monday)} — ${fmt(sunday)}`
  }, [currentDate, viewMode])

  /* Handlers */
  const handleDayClick = useCallback((_date: Date) => {
    /* expand handled inside MonthGrid */
  }, [])

  const handleAddClick = useCallback((date: Date) => {
    setDialogDate(date)
    setDialogHour(12)
    setDialogOpen(true)
  }, [])

  const handleSlotClick = useCallback((date: Date, hour: number) => {
    setDialogDate(date)
    setDialogHour(hour)
    setDialogOpen(true)
  }, [])

  const handleScheduled = useCallback(() => {
    const [start, end] =
      viewMode === 'month'
        ? getMonthRange(currentDate)
        : getWeekRange(currentDate)
    fetchCalendar(start, end)
  }, [currentDate, viewMode, fetchCalendar])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900">
          内容日历
        </h1>

        <div className="flex items-center gap-3">
          {/* Stats badges */}
          <div className="hidden items-center gap-2 sm:flex">
            <StatBadge
              label="已发布"
              count={stats.published}
              dotColor="bg-emerald-400"
            />
            <StatBadge
              label="待发布"
              count={stats.scheduled}
              dotColor="bg-blue-400"
            />
            <StatBadge
              label="草稿"
              count={stats.draft}
              dotColor="bg-stone-300"
            />
          </div>

          {/* View toggle */}
          <div className="flex rounded-lg border border-stone-200 bg-white p-0.5">
            <button
              onClick={() => setViewMode('month')}
              className={clsx(
                'flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                viewMode === 'month'
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-500 hover:text-stone-700',
              )}
            >
              <LayoutGrid size={12} />
              月
            </button>
            <button
              onClick={() => setViewMode('week')}
              className={clsx(
                'flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all',
                viewMode === 'week'
                  ? 'bg-stone-900 text-white'
                  : 'text-stone-500 hover:text-stone-700',
              )}
            >
              <List size={12} />
              周
            </button>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={goToPrev}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition-colors hover:bg-stone-100"
          >
            <ChevronLeft size={14} />
          </button>
          <button
            onClick={goToNext}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-stone-200 text-stone-500 transition-colors hover:bg-stone-100"
          >
            <ChevronRight size={14} />
          </button>
          <button
            onClick={goToToday}
            className="rounded-lg border border-stone-200 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-100"
          >
            今天
          </button>
        </div>

        <span className="text-sm font-medium text-stone-700">{title}</span>
      </div>

      {/* Calendar body */}
      {loading && Object.keys(entriesByDate).length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-[#c2714f]" />
        </div>
      ) : viewMode === 'month' ? (
        <MonthGrid
          currentDate={currentDate}
          entriesByDate={entriesByDate}
          onDayClick={handleDayClick}
          onAddClick={handleAddClick}
        />
      ) : (
        <WeekView
          currentDate={currentDate}
          entriesByDate={entriesByDate}
          onSlotClick={handleSlotClick}
        />
      )}

      {/* Empty state (when no entries at all) */}
      {!loading && stats.total === 0 && (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100">
            <CalendarDays size={24} className="text-stone-400" />
          </div>
          <p className="mt-4 text-sm font-medium text-stone-700">
            规划你的内容节奏
          </p>
          <p className="mt-1 max-w-xs text-xs text-stone-400">
            将内容排入日历，系统会在最佳时间自动发布
          </p>
          <button
            onClick={() => {
              setDialogDate(new Date())
              setDialogHour(12)
              setDialogOpen(true)
            }}
            className="mt-4 rounded-lg bg-[#c2714f] px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-[#a85d3e]"
          >
            安排第一条内容
          </button>
        </div>
      )}

      {/* Schedule dialog */}
      <ScheduleDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onScheduled={handleScheduled}
        defaultDate={dialogDate}
        defaultHour={dialogHour}
        drafts={MOCK_DRAFTS}
      />
    </div>
  )
}

/* ── Sub-components ── */

function StatBadge({
  label,
  count,
  dotColor,
}: {
  label: string
  count: number
  dotColor: string
}) {
  return (
    <div className="flex items-center gap-1.5 rounded-full border border-stone-200 bg-white px-2.5 py-1 text-xs text-stone-600">
      <div className={clsx('h-1.5 w-1.5 rounded-full', dotColor)} />
      {label}
      <span className="font-semibold text-stone-900">{count}</span>
    </div>
  )
}
