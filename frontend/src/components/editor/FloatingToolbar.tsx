import { motion } from 'framer-motion'
import { RefreshCw, Minus, Plus, Sparkles, UserRound } from 'lucide-react'
import { cn } from '@/lib/utils'

interface FloatingToolbarProps {
  onAction: (action: string) => void
}

const actions = [
  { id: '重写', label: '重写', icon: RefreshCw },
  { id: '缩短', label: '缩短', icon: Minus },
  { id: '扩展', label: '扩展', icon: Plus },
  { id: '换语气', label: '换语气', icon: Sparkles },
  { id: '更像我', label: '更像我', icon: UserRound },
] as const

export function FloatingToolbar({ onAction }: FloatingToolbarProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95, y: 4 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: 4 }}
      transition={{ duration: 0.15 }}
      className="flex items-center gap-0.5 rounded-xl border border-stone-200 bg-white p-1 shadow-lg"
    >
      {actions.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onAction(id)}
          className={cn(
            'flex items-center gap-1 rounded-lg px-2.5 py-1.5',
            'text-xs font-medium text-stone-600',
            'transition-colors duration-100',
            'hover:bg-[#c87b5a]/10 hover:text-[#c87b5a]',
          )}
        >
          <Icon size={13} />
          <span>{label}</span>
        </button>
      ))}
    </motion.div>
  )
}
