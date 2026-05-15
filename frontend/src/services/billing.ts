import { api } from './api'

// ── Types ──

export interface PlanFeatures {
  price: number | null
  posts: number
  platforms: number
  lines: number
  competitors: number
  publish_trial_days: number | null
}

export interface PlanInfo {
  name: string
  label: string
  features: PlanFeatures
  is_current: boolean
}

export interface SubscriptionResponse {
  id: number
  plan: string
  status: string
  trial_ends_at: string | null
  current_period_start: string
  current_period_end: string
  monthly_post_limit: number
  platform_limit: number
  content_line_limit: number
  competitor_account_limit: number
  created_at: string
  updated_at: string
}

export interface UsageSummary {
  posts_generated: number
  posts_published: number
  post_limit: number
  platforms_used: string[]
  platform_limit: number
  content_lines_used: string[]
  content_line_limit: number
  period_start: string
  period_end: string
  usage_percent: number
}

export interface OverageLineItem {
  resource: string
  used: number
  limit: number
  overage: number
  unit_price_cents: number
  total_cents: number
}

export interface OverageBill {
  items: OverageLineItem[]
  total_cents: number
  currency: string
}

export interface PaymentIntent {
  payment_id: string
  amount_cents: number
  currency: string
  method: string
  payment_url: string
  expires_at: string
}

export interface PaymentRecord {
  id: number
  amount_cents: number
  currency: string
  method: string
  status: string
  description: string | null
  paid_at: string | null
  created_at: string
}

// ── API Functions ──

export async function getSubscription() {
  const { data } = await api.get<SubscriptionResponse>('/v1/billing/subscription')
  return data
}

export async function subscribe(plan: string) {
  const { data } = await api.post<SubscriptionResponse>('/v1/billing/subscribe', { plan })
  return data
}

export async function upgradePlan(newPlan: string) {
  const { data } = await api.post<SubscriptionResponse>('/v1/billing/upgrade', {
    new_plan: newPlan,
  })
  return data
}

export async function cancelSubscription() {
  const { data } = await api.post<SubscriptionResponse>('/v1/billing/cancel')
  return data
}

export async function getUsageSummary() {
  const { data } = await api.get<UsageSummary>('/v1/billing/usage')
  return data
}

export async function getOverage() {
  const { data } = await api.get<OverageBill>('/v1/billing/overage')
  return data
}

export async function getPlans() {
  const { data } = await api.get<PlanInfo[]>('/v1/billing/plans')
  return data
}

export async function createPayment(amountCents: number, method = 'wechat_pay', description?: string) {
  const { data } = await api.post<PaymentIntent>('/v1/billing/pay', {
    amount_cents: amountCents,
    method,
    description,
  })
  return data
}

export async function getPaymentHistory() {
  const { data } = await api.get<PaymentRecord[]>('/v1/billing/payments')
  return data
}
