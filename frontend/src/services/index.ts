export {
  api,
  login,
  sendVerificationCode,
  generateContent,
  getContent,
  updateContent,
  listContent,
  publishContent,
  getTasteProfile,
  getAnalyticsSummary,
} from './api'

export {
  fetchCalendar,
  scheduleContent,
  rescheduleContent,
  cancelSchedule,
  fetchUpcoming,
  fetchSuggestTimes,
} from './calendar'

export {
  startOnboarding,
  sendMessage,
  importContent,
  importFromProfile,
  addCompetitors,
  getOnboardingStatus,
  completeOnboarding,
} from './onboarding'

export {
  addCompetitor,
  listCompetitors,
  removeCompetitor,
  syncCompetitor,
  syncAllCompetitors,
  getTrends,
  getCompetitorPosts,
  getViralPosts,
} from './competitors'
export type {
  Competitor,
  CompetitorPost,
  TrendingTopic,
  ViralAlert,
  TrendReport,
  SyncResult,
} from './competitors'

export {
  fetchAnalyticsSummary,
  fetchContentMetrics,
  fetchCorrelations,
  fetchBestTimes,
  fetchPlatformComparison,
} from './analytics'
export type {
  PerformanceSummary,
  PeriodDelta,
  ContentMetrics,
  TasteCorrelation,
  TimeSlot,
  PlatformStats,
  PlatformComparison,
} from './analytics'

export {
  fetchNotifications,
  fetchUnreadCount,
  markNotificationRead,
  markAllNotificationsRead,
  deleteNotification,
} from './notifications'
export type {
  NotificationItem,
  NotificationList,
  UnreadCount,
} from './notifications'

export {
  getSubscription,
  subscribe,
  upgradePlan,
  cancelSubscription,
  getUsageSummary,
  getOverage,
  getPlans,
  createPayment,
  getPaymentHistory,
} from './billing'
export type {
  SubscriptionResponse,
  UsageSummary,
  OverageBill,
  PlanInfo,
  PaymentIntent,
  PaymentRecord,
} from './billing'
