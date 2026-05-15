import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  PenLine,
  CalendarDays,
  Users,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface MobileNavItem {
  to: string
  label: string
  icon: React.ElementType
}

const items: MobileNavItem[] = [
  { to: '/dashboard', label: '首页', icon: LayoutDashboard },
  { to: '/create', label: '创作', icon: PenLine },
  { to: '/calendar', label: '日历', icon: CalendarDays },
  { to: '/competitors', label: '竞品', icon: Users },
  { to: '/settings', label: '设置', icon: Settings },
]

export function MobileNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-stone-200 bg-white/95 backdrop-blur-sm md:hidden">
      <div className="flex h-14 items-center justify-around px-2">
        {items.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 rounded-lg px-3 py-1 text-[10px] font-medium transition-colors',
                isActive
                  ? 'text-[#c2714f]'
                  : 'text-stone-400 active:text-stone-600',
              )
            }
          >
            <Icon size={20} strokeWidth={1.6} />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
      {/* Safe area spacer for iOS */}
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}
