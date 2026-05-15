import { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Palette, Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { CardStyle, StylePreset } from '@/services/visual'

interface StylePickerProps {
  presets: StylePreset[]
  value: CardStyle
  onChange: (style: CardStyle) => void
  className?: string
}

const DEFAULT_STYLE: CardStyle = {
  background_color: '#1a1a2e',
  accent_color: '#c2714f',
  text_color: '#ffffff',
  font_name: 'NotoSansSC',
  title_size: 72,
  body_size: 36,
  card_width: 1080,
  card_height: 1440,
  padding: 80,
}

export function StylePicker({
  presets,
  value,
  onChange,
  className,
}: StylePickerProps) {
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null)
  const [customAccent, setCustomAccent] = useState(value.accent_color)

  // Detect which preset is active
  useEffect(() => {
    const match = presets.find(
      (p) =>
        p.style.background_color === value.background_color &&
        p.style.text_color === value.text_color,
    )
    setSelectedPreset(match?.name ?? null)
    setCustomAccent(value.accent_color)
  }, [value, presets])

  const handleSelectPreset = useCallback(
    (preset: StylePreset) => {
      setSelectedPreset(preset.name)
      onChange({ ...preset.style })
    },
    [onChange],
  )

  const handleAccentChange = useCallback(
    (color: string) => {
      setCustomAccent(color)
      onChange({ ...value, accent_color: color })
    },
    [onChange, value],
  )

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 text-sm font-semibold text-stone-700">
        <Palette size={16} className="text-stone-400" />
        视觉风格
      </div>

      {/* Preset thumbnails */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {presets.map((preset) => {
          const isSelected = selectedPreset === preset.name
          return (
            <motion.button
              key={preset.name}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => handleSelectPreset(preset)}
              className={cn(
                'relative overflow-hidden rounded-xl border-2 p-0 transition-all',
                isSelected
                  ? 'border-[#c87b5a] ring-2 ring-[#c87b5a]/20'
                  : 'border-stone-200 hover:border-stone-300',
              )}
            >
              {/* Mini card preview */}
              <div
                className="flex h-28 flex-col items-start justify-between p-3"
                style={{ backgroundColor: preset.style.background_color }}
              >
                {/* Accent bar */}
                <div
                  className="h-1 w-8 rounded-full"
                  style={{ backgroundColor: preset.style.accent_color }}
                />

                {/* Sample text */}
                <div className="space-y-1">
                  <div
                    className="h-2 w-16 rounded-sm"
                    style={{
                      backgroundColor: preset.style.text_color,
                      opacity: 0.9,
                    }}
                  />
                  <div
                    className="h-1.5 w-12 rounded-sm"
                    style={{
                      backgroundColor: preset.style.text_color,
                      opacity: 0.5,
                    }}
                  />
                </div>
              </div>

              {/* Label */}
              <div className="bg-white px-3 py-2 text-left">
                <p className="text-xs font-medium text-stone-700">
                  {preset.label}
                </p>
                <p className="mt-0.5 text-[10px] text-stone-400">
                  {preset.description}
                </p>
              </div>

              {/* Selected indicator */}
              {isSelected && (
                <div className="absolute right-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-[#c87b5a]">
                  <Check size={12} className="text-white" />
                </div>
              )}
            </motion.button>
          )
        })}
      </div>

      {/* Accent colour picker */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-stone-500">自定义强调色</span>
        <div className="relative">
          <input
            type="color"
            value={customAccent}
            onChange={(e) => handleAccentChange(e.target.value)}
            className="h-8 w-8 cursor-pointer rounded-md border border-stone-200"
          />
        </div>
        <span className="text-xs font-mono text-stone-400">{customAccent}</span>
      </div>
    </div>
  )
}

export { DEFAULT_STYLE }
