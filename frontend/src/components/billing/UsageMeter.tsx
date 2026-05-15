import { cn } from '@/lib/utils'

interface UsageMeterProps {
  label: string
  current: number
  limit: number
  unit?: string
  className?: string
}

export function UsageMeter({ label, current, limit, unit = '', className }: UsageMeterProps) {
  const isUnlimited = limit === -1
  const percent = isUnlimited ? 0 : limit === 0 ? 100 : Math.min(100, (current / limit) * 100)
  const isWarning = percent >= 80
  const isDanger = percent >= 95

  const displayLimit = isUnlimited ? 'Unlimited' : `${limit}`
  const displayText = `${current}/${displayLimit}${unit ? ` ${unit}` : ''}`

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-stone-700">{label}</span>
        <span
          className={cn(
            'tabular-nums',
            isDanger
              ? 'font-semibold text-red-600'
              : isWarning
                ? 'font-medium text-amber-600'
                : 'text-stone-500',
          )}
        >
          {displayText}
        </span>
      </div>

      <div className="h-2 overflow-hidden rounded-full bg-stone-200">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            isDanger
              ? 'bg-gradient-to-r from-red-500 to-red-400'
              : isWarning
                ? 'bg-gradient-to-r from-amber-500 to-amber-400'
                : 'bg-gradient-to-r from-emerald-500 to-emerald-400',
          )}
          style={{ width: isUnlimited ? '0%' : `${percent}%` }}
        />
      </div>

      {isWarning && !isUnlimited && (
        <p
          className={cn(
            'text-xs',
            isDanger ? 'text-red-600' : 'text-amber-600',
          )}
        >
          {isDanger
            ? 'Limit almost reached! Upgrade your plan to avoid interruptions.'
            : 'Approaching limit. Consider upgrading your plan.'}
        </p>
      )}
    </div>
  )
}
