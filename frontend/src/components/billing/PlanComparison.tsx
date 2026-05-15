import { cn } from '@/lib/utils'
import { Check } from 'lucide-react'
import type { PlanInfo } from '@/services/billing'

interface PlanComparisonProps {
  plans: PlanInfo[]
  onSelect: (planName: string) => void
  loading?: boolean
}

const FEATURE_ROWS = [
  { key: 'posts', label: '月内容数', format: (v: number) => (v === -1 ? 'Unlimited' : `${v} 篇`) },
  { key: 'platforms', label: '平台数', format: (v: number) => `${v} 个` },
  { key: 'lines', label: '内容线', format: (v: number) => `${v} 条` },
  { key: 'competitors', label: '竞品监控', format: (v: number) => (v === 0 ? '--' : `${v} 个`) },
] as const

function formatPrice(priceCents: number | null): string {
  if (priceCents === null) return 'Custom'
  if (priceCents === 0) return 'Free'
  return `\u00A5${(priceCents / 100).toFixed(0)}`
}

function formatPriceUnit(priceCents: number | null): string {
  if (priceCents === null) return 'Contact us'
  if (priceCents === 0) return 'Forever free'
  return '/month'
}

export function PlanComparison({ plans, onSelect, loading }: PlanComparisonProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {plans
        .filter((p) => p.name !== 'enterprise')
        .map((plan) => {
          const isPro = plan.name === 'pro'
          return (
            <div
              key={plan.name}
              className={cn(
                'relative flex flex-col rounded-xl border p-6 transition-shadow',
                plan.is_current
                  ? 'border-emerald-400 bg-emerald-50 shadow-emerald-100 shadow-lg'
                  : isPro
                    ? 'border-amber-300 bg-amber-50/50 shadow-md'
                    : 'border-stone-200 bg-stone-50',
              )}
            >
              {isPro && !plan.is_current && (
                <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-amber-500 px-3 py-0.5 text-xs font-semibold text-white">
                  Popular
                </span>
              )}

              {/* Header */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-stone-800">{plan.label}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-stone-900">
                    {formatPrice(plan.features.price)}
                  </span>
                  <span className="text-sm text-stone-500">
                    {formatPriceUnit(plan.features.price)}
                  </span>
                </div>
              </div>

              {/* Features */}
              <ul className="mb-6 flex-1 space-y-3">
                {FEATURE_ROWS.map(({ key, label, format }) => {
                  const value = plan.features[key as keyof typeof plan.features] as number
                  return (
                    <li key={key} className="flex items-center gap-2 text-sm text-stone-600">
                      <Check size={14} className="shrink-0 text-emerald-500" />
                      <span>
                        {label}: <span className="font-medium text-stone-800">{format(value)}</span>
                      </span>
                    </li>
                  )
                })}
                {plan.features.publish_trial_days && (
                  <li className="flex items-center gap-2 text-sm text-stone-500">
                    <Check size={14} className="shrink-0 text-stone-400" />
                    <span>Publishing: first {plan.features.publish_trial_days} days only</span>
                  </li>
                )}
              </ul>

              {/* CTA */}
              <button
                onClick={() => onSelect(plan.name)}
                disabled={plan.is_current || loading}
                className={cn(
                  'w-full rounded-lg px-4 py-2.5 text-sm font-medium transition-colors',
                  plan.is_current
                    ? 'cursor-default border border-emerald-300 bg-emerald-50 text-emerald-700'
                    : isPro
                      ? 'bg-amber-500 text-white hover:bg-amber-600 disabled:opacity-50'
                      : 'bg-stone-900 text-white hover:bg-stone-800 disabled:opacity-50',
                )}
              >
                {plan.is_current ? 'Current Plan' : 'Select'}
              </button>
            </div>
          )
        })}
    </div>
  )
}
