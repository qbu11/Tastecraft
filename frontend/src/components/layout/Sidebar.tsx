import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  PenLine,
  CalendarDays,
  BarChart3,
  Settings,
  LogOut,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'

interface NavItem {
  to: string
  label: string
  icon: React.ElementType
}

const navItems: NavItem[] = [
  { to: '/dashboard', label: '工作台', icon: LayoutDashboard },
  { to: '/create', label: '创作', icon: PenLine },
  { to: '/calendar', label: '日历', icon: CalendarDays },
  { to: '/analytics', label: '数据', icon: BarChart3 },
  { to: '/settings', label: '设置', icon: Settings },
]

function TasteScoreRing({ score }: { score: number }) {
  const radius = 18
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference

  return (
    <svg width="44" height="44" className="shrink-0">
      <circle
        cx="22"
        cy="22"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        className="text-slate-700"
      />
      <circle
        cx="22"
        cy="22"
        r={radius}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className="origin-center -rotate-90"
        style={{ transformOrigin: '22px 22px' }}
      />
      <text
        x="22"
        y="22"
        textAnchor="middle"
        dominantBaseline="central"
        className="fill-stone-200 text-[10px] font-semibold"
      >
        {score}
      </text>
    </svg>
  )
}

export function Sidebar() {
  const { user, logout } = useAuthStore()
  const displayName = user?.name ?? '品味匠人'
  const tasteScore = user?.tasteScore ?? 72

  return (
    <aside className="flex h-screen flex-col bg-slate-900 text-stone-300">
      {/* Brand */}
      <div className="px-6 pt-7 pb-6">
        <span className="text-lg font-semibold tracking-tight text-stone-100">
          TasteCraft
        </span>
        <span className="ml-1.5 text-xs font-light text-stone-500">
          品味工坊
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-3">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-slate-800 text-stone-100'
                  : 'text-stone-400 hover:bg-slate-800/60 hover:text-stone-200',
              )
            }
          >
            <Icon size={18} strokeWidth={1.8} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + Taste Score */}
      <div className="border-t border-slate-800 px-4 py-4">
        <div className="flex items-center gap-3">
          <TasteScoreRing score={tasteScore} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-stone-200">
              {displayName}
            </p>
            <p className="text-xs text-stone-500">品味分 {tasteScore}</p>
          </div>
          <button
            onClick={logout}
            className="rounded-md p-1.5 text-stone-500 transition-colors hover:bg-slate-800 hover:text-stone-300"
            title="退出登录"
          >
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  )
}
