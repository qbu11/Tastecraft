import { api } from './api'

/* ── Types ── */

export interface ScheduleResponse {
  id: number
  content_id: number
  content_title: string
  platform: string
  scheduled_at: string
  timezone: string
  status: 'pending' | 'published' | 'failed' | 'cancelled' | 'draft'
  published_at: string | null
  error_message: string | null
  created_at: string
}

export interface CalendarEntry {
  date: string
  entries: ScheduleResponse[]
}

export interface CalendarStats {
  total: number
  published: number
  scheduled: number
  draft: number
}

export interface CalendarView {
  start_date: string
  end_date: string
  entries: CalendarEntry[]
  stats: CalendarStats
}

export interface UpcomingSummary {
  items: ScheduleResponse[]
  total: number
}

export interface SuggestedTime {
  time: string
  reason: string
}

export interface SuggestTimesResponse {
  platform: string
  suggestions: SuggestedTime[]
}

/* ── API calls ── */

export async function fetchCalendar(
  startDate: string,
  endDate: string,
): Promise<CalendarView> {
  const { data } = await api.get<CalendarView>('/v1/calendar/', {
    params: { start_date: startDate, end_date: endDate },
  })
  return data
}

export async function scheduleContent(payload: {
  content_id: number
  platform: string
  scheduled_at: string
  timezone?: string
}): Promise<ScheduleResponse> {
  const { data } = await api.post<ScheduleResponse>(
    '/v1/calendar/schedule',
    payload,
  )
  return data
}

export async function rescheduleContent(
  scheduleId: number,
  payload: { scheduled_at: string; timezone?: string },
): Promise<ScheduleResponse> {
  const { data } = await api.put<ScheduleResponse>(
    `/v1/calendar/schedule/${scheduleId}`,
    payload,
  )
  return data
}

export async function cancelSchedule(scheduleId: number): Promise<void> {
  await api.delete(`/v1/calendar/schedule/${scheduleId}`)
}

export async function fetchUpcoming(
  days: number = 7,
): Promise<UpcomingSummary> {
  const { data } = await api.get<UpcomingSummary>('/v1/calendar/upcoming', {
    params: { days },
  })
  return data
}

export async function fetchSuggestTimes(
  platform: string,
): Promise<SuggestTimesResponse> {
  const { data } = await api.get<SuggestTimesResponse>(
    '/v1/calendar/suggest-times',
    { params: { platform } },
  )
  return data
}
