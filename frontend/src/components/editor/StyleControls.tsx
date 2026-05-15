import { useCallback } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface StyleParam {
  id: string
  label: [string, string] // [left label, right label]
  value: number // 0-100
}

interface StyleControlsProps {
  values: StyleParam[]
  onChange: (id: string, value: number) => void
  className?: string
}

const defaultStyles: StyleParam[] = [
  { id: 'formality', label: ['正式', '随意'], value: 50 },
  { id: 'length', label: ['长', '短'], value: 50 },
  { id: 'emotion', label: ['理性', '感性'], value: 50 },
  { id: 'expertise', label: ['专业', '通俗'], value: 50 },
]

export function StyleControls({
  values = defaultStyles,
  onChange,
  className,
}: StyleControlsProps) {
  const handleChange = useCallback(
    (id: string, rawValue: string) => {
      onChange(id, Number(rawValue))
    },
    [onChange],
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex items-center gap-6 border-t border-stone-200 bg-stone-50 px-6 py-3',
        className,
      )}
    >
      {values.map((param) => (
        <div key={param.id} className="flex flex-1 items-center gap-2">
          <span className="w-8 text-right text-xs font-medium text-stone-500">
            {param.label[0]}
          </span>
          <div className="relative flex-1">
            <input
              type="range"
              min={0}
              max={100}
              value={param.value}
              onChange={(e) => handleChange(param.id, e.target.value)}
              className={cn(
                'w-full cursor-pointer appearance-none bg-transparent',
                // Track
                '[&::-webkit-slider-runnable-track]:h-1.5 [&::-webkit-slider-runnable-track]:rounded-full [&::-webkit-slider-runnable-track]:bg-stone-200',
                // Thumb
                '[&::-webkit-slider-thumb]:mt-[-5px] [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-[#c87b5a] [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110',
                // Firefox
                '[&::-moz-range-track]:h-1.5 [&::-moz-range-track]:rounded-full [&::-moz-range-track]:bg-stone-200',
                '[&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-[#c87b5a] [&::-moz-range-thumb]:shadow-sm',
              )}
            />
          </div>
          <span className="w-8 text-xs font-medium text-stone-500">
            {param.label[1]}
          </span>
        </div>
      ))}
    </motion.div>
  )
}

export { defaultStyles }
export type { StyleParam }
