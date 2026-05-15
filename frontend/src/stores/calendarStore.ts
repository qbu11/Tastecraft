import { create } from 'zustand'
import {
  fetchCalendar,
  scheduleContent,
  cancelSchedule,
  rescheduleContent,
  fetchUpcoming,
  fetchSuggestTimes,
  type CalendarView,
  type ScheduleResponse,
  type SuggestedTime,
} from '@/services/calendar'

type ViewMode = 'month' | 'week'

interface CalendarState {
  /* View state */
  currentDate: Date
  viewMode: ViewMode

  /* Data */
  calendarView: CalendarView | null
  upcoming: ScheduleResponse[]
  suggestedTimes: SuggestedTime[]
  loading: boolean
  error: string | null

  /* Actions — view */
  setViewMode: (mode: ViewMode) => void
  goToToday: () => void
  goToPrev: () => void
  goToNext: () => void

  /* Actions — data */
  fetchCalendar: (start: string, end: string) => Promise<void>
  fetchUpcoming: () => Promise<void>
  fetchSuggestTimes: (platform: string) => Promise<void>
  scheduleContent: (payload: {
    content_id: number
    platform: string
    scheduled_at: string
    timezone?: string
  }) => Promise<ScheduleResponse | null>
  cancelSchedule: (scheduleId: number) => Promise<boolean>
  rescheduleContent: (
    scheduleId: number,
    payload: { scheduled_at: string; timezone?: string },
  ) => Promise<ScheduleResponse | null>
}

export const useCalendarStore = create<CalendarState>()((set, get) => ({
  currentDate: new Date(),
  viewMode: 'month',
  calendarView: null,
  upcoming: [],
  suggestedTimes: [],
  loading: false,
  error: null,

  setViewMode: (mode) => set({ viewMode: mode }),

  goToToday: () => set({ currentDate: new Date() }),

  goToPrev: () => {
    const { currentDate, viewMode } = get()
    const d = new Date(currentDate)
    if (viewMode === 'month') {
      d.setMonth(d.getMonth() - 1)
    } else {
      d.setDate(d.getDate() - 7)
    }
    set({ currentDate: d })
  },

  goToNext: () => {
    const { currentDate, viewMode } = get()
    const d = new Date(currentDate)
    if (viewMode === 'month') {
      d.setMonth(d.getMonth() + 1)
    } else {
      d.setDate(d.getDate() + 7)
    }
    set({ currentDate: d })
  },

  fetchCalendar: async (start, end) => {
    set({ loading: true, error: null })
    try {
      const view = await fetchCalendar(start, end)
      set({ calendarView: view, loading: false })
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to load calendar',
        loading: false,
      })
    }
  },

  fetchUpcoming: async () => {
    try {
      const result = await fetchUpcoming(7)
      set({ upcoming: result.items })
    } catch {
      /* non-critical */
    }
  },

  fetchSuggestTimes: async (platform) => {
    try {
      const result = await fetchSuggestTimes(platform)
      set({ suggestedTimes: result.suggestions })
    } catch {
      /* non-critical */
    }
  },

  scheduleContent: async (payload) => {
    set({ loading: true, error: null })
    try {
      const result = await scheduleContent(payload)
      set({ loading: false })
      return result
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to schedule',
        loading: false,
      })
      return null
    }
  },

  cancelSchedule: async (scheduleId) => {
    try {
      await cancelSchedule(scheduleId)
      return true
    } catch {
      return false
    }
  },

  rescheduleContent: async (scheduleId, payload) => {
    try {
      const result = await rescheduleContent(scheduleId, payload)
      return result
    } catch {
      return null
    }
  },
}))
