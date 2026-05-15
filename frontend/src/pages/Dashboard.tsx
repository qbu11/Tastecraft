import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { PenLine, TrendingUp, CheckCircle2, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { ConflictResolver, type PreferenceConflict } from '@/components/taste'
import { getTasteConflicts, resolveTasteConflict } from '@/services/api'

interface StatCardProps {
  label: string
  value: string | number
  icon: React.ElementType
  accent?: boolean
}

function StatCard({ label, value, icon: Icon, accent }: StatCardProps) {
  return (
    <div
      className={cn(
        'flex items-start gap-4 rounded-xl border border-stone-200 bg-white px-5 py-4',
        accent && 'border-[var(--color-accent)]/30 bg-[var(--color-accent-muted)]',
      )}
    >
      <div
        className={cn(
          'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
          accent ? 'bg-[var(--color-accent)]/10 text-[var(--color-accent)]' : 'bg-stone-100 text-stone-500',
        )}
      >
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-semibold tracking-tight text-stone-900">{value}</p>
        <p className="mt-0.5 text-sm text-stone-500">{label}</p>
      </div>
    </div>
  )
}

const recentItems = [
  { id: '1', title: 'AI 创业者的 5 个生存法则', platform: '小红书', status: '已发布', date: '05-15' },
  { id: '2', title: '深度学习在内容创作中的应用', platform: '微信公众号', status: '待审阅', date: '05-14' },
  { id: '3', title: '如何用 AI 工具提升写作效率', platform: '小红书', status: '草稿', date: '05-13' },
]

const statusColor: Record<string, string> = {
  '已发布': 'text-emerald-600 bg-emerald-50',
  '待审阅': 'text-amber-600 bg-amber-50',
  '草稿': 'text-stone-500 bg-stone-100',
}

export function Dashboard() {
  const navigate = useNavigate()
  const displayName = useAuthStore((s) => s.user?.name) ?? '品味匠人'
  const [conflicts, setConflicts] = useState<PreferenceConflict[]>([])
  const [showConflicts, setShowConflicts] = useState(true)

  // Fetch conflicts on mount
  useEffect(() => {
    getTasteConflicts()
      .then((data) => setConflicts(data))
      .catch(() => {
        /* silent — conflicts are non-critical */
      })
  }, [])

  async function handleResolveConflict(
    conflictId: string,
    resolution: 'keep_first' | 'keep_second' | 'context_split',
    contextNote?: string,
  ) {
    const conflict = conflicts.find((c) => c.id === conflictId)
    if (!conflict) return

    await resolveTasteConflict(conflictId, {
      conflict_id: conflictId,
      preference_a_id: conflict.preference_a_id,
      preference_b_id: conflict.preference_b_id,
      resolution,
      context_note: contextNote,
    })

    // Remove resolved conflict from local state
    setConflicts((prev) => prev.filter((c) => c.id !== conflictId))
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-stone-900">
            {displayName}，今日灵感如何？
          </h1>
          <p className="mt-1 text-stone-500">
            本周已创作 3 篇内容，品味持续进化中
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => navigate('/create')}
          className="flex items-center gap-2 rounded-lg bg-stone-900 px-5 py-2.5 text-sm font-medium text-stone-100 transition-colors hover:bg-stone-800"
        >
          <Sparkles size={16} />
          开始创作
        </motion.button>
      </div>

      {/* Stats row — asymmetric grid */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="本月内容" value={12} icon={PenLine} />
        <StatCard label="品味匹配度" value="87%" icon={TrendingUp} accent />
        <StatCard label="发布成功率" value="96%" icon={CheckCircle2} />
      </div>

      {/* Taste conflicts alert (v2) */}
      {conflicts.length > 0 && showConflicts && (
        <motion.section
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-amber-200 bg-amber-50/50 p-5"
        >
          <ConflictResolver
            conflicts={conflicts}
            onResolve={handleResolveConflict}
            onDismiss={() => setShowConflicts(false)}
          />
        </motion.section>
      )}

      {/* Recent content */}
      <section>
        <h2 className="mb-4 text-lg font-semibold text-stone-800">近期内容</h2>
        <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-stone-100 text-xs uppercase tracking-wider text-stone-400">
                <th className="px-5 py-3 font-medium">标题</th>
                <th className="px-5 py-3 font-medium">平台</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">日期</th>
              </tr>
            </thead>
            <tbody>
              {recentItems.map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-stone-50 transition-colors last:border-0 hover:bg-stone-50/60"
                >
                  <td className="px-5 py-3.5 font-medium text-stone-800">
                    {item.title}
                  </td>
                  <td className="px-5 py-3.5 text-stone-500">{item.platform}</td>
                  <td className="px-5 py-3.5">
                    <span
                      className={cn(
                        'inline-block rounded-full px-2.5 py-0.5 text-xs font-medium',
                        statusColor[item.status] ?? 'text-stone-500 bg-stone-100',
                      )}
                    >
                      {item.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-stone-400">{item.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
