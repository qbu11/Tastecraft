import { useEffect, useState } from 'react'
import {
  Settings as SettingsIcon,
  Users,
  Code2,
  CreditCard,
  AlertTriangle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TeamManagement } from '@/components/settings/TeamManagement'
import { DeveloperSettings } from '@/components/settings/DeveloperSettings'
import { UsageMeter, PlanComparison } from '@/components/billing'
import {
  getSubscription,
  getUsageSummary,
  getPlans,
  getOverage,
  getPaymentHistory,
  upgradePlan,
  cancelSubscription,
} from '@/services/billing'
import type {
  SubscriptionResponse,
  UsageSummary,
  PlanInfo,
  OverageBill,
  PaymentRecord,
} from '@/services/billing'

type SettingsTab = 'billing' | 'team' | 'developer'

interface TabItem {
  id: SettingsTab
  label: string
  icon: React.ElementType
}

const tabs: TabItem[] = [
  { id: 'billing', label: 'Plan & Billing', icon: CreditCard },
  { id: 'team', label: '团队管理', icon: Users },
  { id: 'developer', label: '开发者', icon: Code2 },
]

/* ── Plan label helper ── */

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  basic: 'Basic',
  pro: 'Pro',
  enterprise: 'Enterprise',
}

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
  trial: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
  cancelled: 'bg-red-500/10 text-red-400 border-red-500/30',
  expired: 'bg-stone-500/10 text-stone-400 border-stone-500/30',
}

/* ── Main component ── */

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('billing')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <SettingsIcon size={20} className="text-stone-500" />
        <h1 className="text-lg font-semibold text-stone-900">Settings</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 rounded-lg border border-stone-200 bg-white p-1">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={cn(
              'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
              activeTab === id
                ? 'bg-stone-100 text-stone-900'
                : 'text-stone-500 hover:text-stone-700',
            )}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="rounded-lg border border-stone-200 bg-white p-6">
        {activeTab === 'billing' && <BillingTab />}
        {activeTab === 'team' && <TeamManagement />}
        {activeTab === 'developer' && <DeveloperSettings />}
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════════════
   Billing Tab
   ══════════════════════════════════════════════════════════════════════════════ */

function BillingTab() {
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null)
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [plans, setPlans] = useState<PlanInfo[]>([])
  const [overage, setOverage] = useState<OverageBill | null>(null)
  const [payments, setPayments] = useState<PaymentRecord[]>([])
  const [showPlans, setShowPlans] = useState(false)
  const [loading, setLoading] = useState(true)
  const [upgrading, setUpgrading] = useState(false)

  useEffect(() => {
    loadBillingData()
  }, [])

  async function loadBillingData() {
    setLoading(true)
    try {
      const [subData, usageData, plansData, overageData, payData] = await Promise.all([
        getSubscription(),
        getUsageSummary(),
        getPlans(),
        getOverage(),
        getPaymentHistory(),
      ])
      setSubscription(subData)
      setUsage(usageData)
      setPlans(plansData)
      setOverage(overageData)
      setPayments(payData)
    } catch {
      // Silently handle — user may not have a subscription yet
    } finally {
      setLoading(false)
    }
  }

  async function handleSelectPlan(planName: string) {
    setUpgrading(true)
    try {
      await upgradePlan(planName)
      await loadBillingData()
      setShowPlans(false)
    } catch {
      // Error handled by API interceptor
    } finally {
      setUpgrading(false)
    }
  }

  async function handleCancel() {
    if (
      !confirm(
        'Are you sure you want to cancel? Your subscription will remain active until the end of the billing period.',
      )
    ) {
      return
    }
    try {
      await cancelSubscription()
      await loadBillingData()
    } catch {
      // Error handled by API interceptor
    }
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-stone-300 border-t-stone-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Current Plan Card */}
      <div className="rounded-xl border border-stone-200 bg-stone-50 p-5">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-base font-semibold text-stone-800">Current Plan</h2>
            <div className="mt-2 flex items-center gap-3">
              <span className="text-2xl font-bold text-stone-900">
                {PLAN_LABELS[subscription?.plan ?? 'free'] ?? subscription?.plan}
              </span>
              {subscription?.status && (
                <span
                  className={cn(
                    'rounded-full border px-2.5 py-0.5 text-xs font-medium',
                    STATUS_COLORS[subscription.status] ?? STATUS_COLORS.active,
                  )}
                >
                  {subscription.status}
                </span>
              )}
            </div>
            {subscription?.current_period_end && (
              <p className="mt-1 text-xs text-stone-500">
                Period ends:{' '}
                {new Date(subscription.current_period_end).toLocaleDateString('zh-CN')}
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowPlans(!showPlans)}
              className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-stone-800"
            >
              {showPlans ? 'Hide Plans' : 'Upgrade'}
            </button>
            {subscription?.status === 'active' && subscription.plan !== 'free' && (
              <button
                onClick={handleCancel}
                className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:border-red-300 hover:text-red-600"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Plan Comparison (expandable) */}
      {showPlans && (
        <div className="rounded-xl border border-stone-200 p-5">
          <h2 className="mb-4 text-base font-semibold text-stone-800">Choose a Plan</h2>
          <PlanComparison plans={plans} onSelect={handleSelectPlan} loading={upgrading} />
        </div>
      )}

      {/* Usage Meters */}
      {usage && (
        <div className="rounded-xl border border-stone-200 p-5">
          <h2 className="mb-4 text-base font-semibold text-stone-800">Usage This Period</h2>
          <div className="space-y-5">
            <UsageMeter
              label="Content Generated"
              current={usage.posts_generated}
              limit={usage.post_limit}
            />
            <UsageMeter
              label="Content Published"
              current={usage.posts_published}
              limit={usage.post_limit}
            />
            <UsageMeter
              label="Platforms Used"
              current={usage.platforms_used.length}
              limit={usage.platform_limit}
            />
            <UsageMeter
              label="Content Lines"
              current={usage.content_lines_used.length}
              limit={usage.content_line_limit}
            />
          </div>
        </div>
      )}

      {/* Overage Warning */}
      {overage && overage.total_cents > 0 && (
        <div className="rounded-xl border border-amber-300 bg-amber-50 p-5">
          <div className="flex items-start gap-3">
            <AlertTriangle size={20} className="mt-0.5 shrink-0 text-amber-600" />
            <div>
              <h3 className="font-semibold text-amber-800">Overage Charges</h3>
              <p className="mt-1 text-sm text-stone-600">
                You have exceeded your plan limits. Additional charges will apply:
              </p>
              <ul className="mt-3 space-y-1.5">
                {overage.items.map((item) => (
                  <li
                    key={item.resource}
                    className="flex items-center justify-between text-sm"
                  >
                    <span className="text-stone-700">
                      {item.resource}: {item.used}/{item.limit} (+{item.overage} over)
                    </span>
                    <span className="font-medium text-amber-700">
                      +{'\u00A5'}{(item.total_cents / 100).toFixed(2)}
                    </span>
                  </li>
                ))}
              </ul>
              <div className="mt-3 flex items-center justify-between border-t border-amber-200 pt-3">
                <span className="font-medium text-stone-700">Total overage</span>
                <span className="text-lg font-bold text-amber-800">
                  {'\u00A5'}{(overage.total_cents / 100).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment History */}
      <div className="rounded-xl border border-stone-200 p-5">
        <h2 className="mb-4 text-base font-semibold text-stone-800">Payment History</h2>
        {payments.length === 0 ? (
          <p className="text-sm text-stone-500">No payments yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-stone-200 text-left text-stone-500">
                <th className="pb-2 font-medium">Date</th>
                <th className="pb-2 font-medium">Description</th>
                <th className="pb-2 font-medium">Method</th>
                <th className="pb-2 text-right font-medium">Amount</th>
                <th className="pb-2 text-right font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {payments.map((p) => (
                <tr key={p.id} className="text-stone-700">
                  <td className="py-2.5">
                    {new Date(p.created_at).toLocaleDateString('zh-CN')}
                  </td>
                  <td className="py-2.5">{p.description ?? '--'}</td>
                  <td className="py-2.5 text-stone-500">{p.method}</td>
                  <td className="py-2.5 text-right tabular-nums">
                    {'\u00A5'}{(p.amount_cents / 100).toFixed(2)}
                  </td>
                  <td className="py-2.5 text-right">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                        p.status === 'paid'
                          ? 'bg-emerald-50 text-emerald-600'
                          : p.status === 'pending'
                            ? 'bg-amber-50 text-amber-600'
                            : 'bg-red-50 text-red-600',
                      )}
                    >
                      {p.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
