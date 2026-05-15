import { CalendarDays } from 'lucide-react'

const DAYS = ['一', '二', '三', '四', '五', '六', '日']

function CalendarGrid() {
  const today = new Date()
  const year = today.getFullYear()
  const month = today.getMonth()
  const firstDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  // Monday-based offset (0=Mon ... 6=Sun)
  const offset = firstDay === 0 ? 6 : firstDay - 1

  const cells: (number | null)[] = [
    ...Array.from<null>({ length: offset }).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]

  return (
    <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl border border-stone-200 bg-stone-200">
      {/* Day headers */}
      {DAYS.map((d) => (
        <div
          key={d}
          className="bg-stone-100 py-2 text-center text-xs font-medium text-stone-500"
        >
          {d}
        </div>
      ))}
      {/* Date cells */}
      {cells.map((day, i) => (
        <div
          key={i}
          className="flex h-20 flex-col bg-white p-2 text-xs text-stone-500 transition-colors hover:bg-stone-50"
        >
          {day !== null && (
            <span
              className={
                day === today.getDate()
                  ? 'flex h-5 w-5 items-center justify-center rounded-full bg-stone-900 text-white'
                  : ''
              }
            >
              {day}
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

export function Calendar() {
  const today = new Date()
  const monthName = today.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900">
          内容日历
        </h1>
        <span className="text-sm text-stone-500">{monthName}</span>
      </div>

      <CalendarGrid />

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100">
          <CalendarDays size={24} className="text-stone-400" />
        </div>
        <p className="mt-4 text-sm font-medium text-stone-700">
          规划你的内容节奏
        </p>
        <p className="mt-1 max-w-xs text-xs text-stone-400">
          将内容排入日历，系统会在最佳时间自动发布
        </p>
      </div>
    </div>
  )
}
