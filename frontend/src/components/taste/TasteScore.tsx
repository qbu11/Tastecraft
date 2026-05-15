import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface TasteScoreProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
  label?: string
  className?: string
}

const SIZE_CONFIG = {
  sm: { dimension: 64, stroke: 4, fontSize: 'text-sm', labelSize: 'text-[10px]' },
  md: { dimension: 96, stroke: 5, fontSize: 'text-xl', labelSize: 'text-xs' },
  lg: { dimension: 128, stroke: 6, fontSize: 'text-2xl', labelSize: 'text-sm' },
} as const

/**
 * Circular progress ring (SVG) showing the user's taste match score.
 * Animated fill on mount — used in sidebar and dashboard.
 */
export function TasteScore({
  score,
  size = 'md',
  label = '品味匹配度',
  className,
}: TasteScoreProps) {
  const [animatedScore, setAnimatedScore] = useState(0)
  const config = SIZE_CONFIG[size]

  const radius = (config.dimension - config.stroke * 2) / 2
  const circumference = 2 * Math.PI * radius
  const progress = (animatedScore / 100) * circumference
  const dashOffset = circumference - progress

  // Animate score on mount
  useEffect(() => {
    const clampedScore = Math.max(0, Math.min(100, score))
    const duration = 800 // ms
    const startTime = performance.now()

    function tick(now: number) {
      const elapsed = now - startTime
      const t = Math.min(elapsed / duration, 1)
      // Ease out cubic
      const eased = 1 - Math.pow(1 - t, 3)
      setAnimatedScore(Math.round(eased * clampedScore))
      if (t < 1) {
        requestAnimationFrame(tick)
      }
    }

    requestAnimationFrame(tick)
  }, [score])

  // Color based on score
  const strokeColor =
    animatedScore >= 70
      ? 'stroke-emerald-500'
      : animatedScore >= 40
        ? 'stroke-amber-500'
        : 'stroke-slate-400'

  const textColor =
    animatedScore >= 70
      ? 'text-emerald-600'
      : animatedScore >= 40
        ? 'text-amber-600'
        : 'text-slate-500'

  return (
    <div className={cn('flex flex-col items-center gap-1', className)}>
      <svg
        width={config.dimension}
        height={config.dimension}
        viewBox={`0 0 ${config.dimension} ${config.dimension}`}
        className="transform -rotate-90"
        role="progressbar"
        aria-valuenow={animatedScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${animatedScore}%`}
      >
        {/* Background circle */}
        <circle
          cx={config.dimension / 2}
          cy={config.dimension / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={config.stroke}
          className="text-slate-200 dark:text-slate-700"
        />
        {/* Progress arc */}
        <circle
          cx={config.dimension / 2}
          cy={config.dimension / 2}
          r={radius}
          fill="none"
          strokeWidth={config.stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          className={cn(strokeColor, 'transition-[stroke-dashoffset] duration-200')}
        />
      </svg>

      {/* Score number overlaid in center */}
      <span
        className={cn(
          'absolute font-bold tabular-nums',
          config.fontSize,
          textColor,
        )}
        style={{
          // Position in center of the SVG
          marginTop: `${config.dimension / 2 - (size === 'sm' ? 8 : size === 'md' ? 12 : 16)}px`,
        }}
      >
        {animatedScore}
      </span>

      {/* Label below */}
      <span className={cn('text-slate-500 font-medium', config.labelSize)}>
        {label}
      </span>
    </div>
  )
}
