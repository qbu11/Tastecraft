import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, RefreshCw, Users, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { CompetitorCard, TrendHighlights } from '@/components/competitors'
import {
  listCompetitors,
  addCompetitor,
  removeCompetitor,
  syncCompetitor,
  syncAllCompetitors,
  getTrends,
  getCompetitorPosts,
  type CompetitorPost,
} from '@/services/competitors'

const PLATFORMS = [
  { value: 'xiaohongshu', label: '小红书' },
  { value: 'wechat', label: '微信' },
  { value: 'weibo', label: '微博' },
  { value: 'zhihu', label: '知乎' },
  { value: 'douyin', label: '抖音' },
]

export function Competitors() {
  const queryClient = useQueryClient()
  const [showAddDialog, setShowAddDialog] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [syncingIds, setSyncingIds] = useState<Set<number>>(new Set())

  // Form state
  const [formPlatform, setFormPlatform] = useState('xiaohongshu')
  const [formAccountId, setFormAccountId] = useState('')
  const [formAccountName, setFormAccountName] = useState('')
  const [formAccountUrl, setFormAccountUrl] = useState('')

  // Queries
  const competitorsQuery = useQuery({
    queryKey: ['competitors'],
    queryFn: () => listCompetitors(),
  })

  const trendsQuery = useQuery({
    queryKey: ['competitor-trends'],
    queryFn: () => getTrends({ period_days: 7 }),
  })

  const expandedPostsQuery = useQuery({
    queryKey: ['competitor-posts', expandedId],
    queryFn: () => (expandedId ? getCompetitorPosts(expandedId, { limit: 10 }) : null),
    enabled: expandedId !== null,
  })

  // Mutations
  const addMutation = useMutation({
    mutationFn: addCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      setShowAddDialog(false)
      resetForm()
    },
  })

  const removeMutation = useMutation({
    mutationFn: removeCompetitor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      queryClient.invalidateQueries({ queryKey: ['competitor-trends'] })
    },
  })

  const syncOneMutation = useMutation({
    mutationFn: syncCompetitor,
    onMutate: (id) => {
      setSyncingIds((prev) => new Set(prev).add(id))
    },
    onSettled: (_data, _err, id) => {
      setSyncingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      queryClient.invalidateQueries({ queryKey: ['competitor-trends'] })
    },
  })

  const syncAllMutation = useMutation({
    mutationFn: syncAllCompetitors,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['competitors'] })
      queryClient.invalidateQueries({ queryKey: ['competitor-trends'] })
    },
  })

  function resetForm() {
    setFormPlatform('xiaohongshu')
    setFormAccountId('')
    setFormAccountName('')
    setFormAccountUrl('')
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!formAccountId.trim() || !formAccountName.trim()) return
    addMutation.mutate({
      platform: formPlatform,
      account_id: formAccountId.trim(),
      account_name: formAccountName.trim(),
      account_url: formAccountUrl.trim() || undefined,
    })
  }

  const competitors = competitorsQuery.data?.items ?? []
  const trends = trendsQuery.data

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-stone-900">
          竞品监控
        </h1>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className={cn(
              'inline-flex items-center gap-1.5 rounded-lg border border-stone-200 px-3 py-1.5 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-50',
              syncAllMutation.isPending && 'pointer-events-none opacity-60',
            )}
            onClick={() => syncAllMutation.mutate()}
            disabled={syncAllMutation.isPending}
          >
            <RefreshCw
              size={14}
              className={cn(syncAllMutation.isPending && 'animate-spin')}
            />
            全部同步
          </button>
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-stone-800"
            onClick={() => setShowAddDialog(true)}
          >
            <Plus size={14} />
            添加竞品
          </button>
        </div>
      </div>

      {/* Trend Highlights */}
      <TrendHighlights
        topics={trends?.top_topics ?? []}
        viralPosts={trends?.viral_posts ?? []}
        summary={trends?.summary ?? ''}
        isLoading={trendsQuery.isLoading}
      />

      {/* Competitor List */}
      {competitors.length === 0 && !competitorsQuery.isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100">
            <Users size={24} className="text-stone-400" />
          </div>
          <p className="mt-4 text-sm font-medium text-stone-700">
            还没有添加竞品
          </p>
          <p className="mt-1 max-w-xs text-xs text-stone-400">
            添加竞品账号后，系统会每日自动同步内容并分析赛道趋势
          </p>
          <button
            type="button"
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-stone-900 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-stone-800"
            onClick={() => setShowAddDialog(true)}
          >
            <Plus size={14} />
            添加竞品
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {competitors.map((competitor) => (
            <div key={competitor.id}>
              <CompetitorCard
                competitor={competitor}
                onSync={(id) => syncOneMutation.mutate(id)}
                onRemove={(id) => removeMutation.mutate(id)}
                onExpand={(id) =>
                  setExpandedId(expandedId === id ? null : id)
                }
                isSyncing={syncingIds.has(competitor.id)}
                isExpanded={expandedId === competitor.id}
              />
              <AnimatePresence>
                {expandedId === competitor.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="ml-6 border-l border-stone-200 pl-6 pt-2 pb-4">
                      {expandedPostsQuery.isLoading ? (
                        <div className="space-y-2">
                          {[1, 2, 3].map((i) => (
                            <div
                              key={i}
                              className="h-12 animate-pulse rounded-lg bg-stone-50"
                            />
                          ))}
                        </div>
                      ) : (
                        <PostList
                          posts={expandedPostsQuery.data?.items ?? []}
                        />
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      )}

      {/* Add Competitor Dialog */}
      <AnimatePresence>
        {showAddDialog && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowAddDialog(false)}
          >
            <motion.div
              className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-stone-900">
                  添加竞品账号
                </h2>
                <button
                  type="button"
                  className="rounded-md p-1 text-stone-400 hover:text-stone-600"
                  onClick={() => setShowAddDialog(false)}
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="mt-5 space-y-4">
                {/* Platform */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-stone-700">
                    平台
                  </label>
                  <select
                    value={formPlatform}
                    onChange={(e) => setFormPlatform(e.target.value)}
                    className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-900 outline-none focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
                  >
                    {PLATFORMS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Account Name */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-stone-700">
                    账号名称
                  </label>
                  <input
                    type="text"
                    value={formAccountName}
                    onChange={(e) => setFormAccountName(e.target.value)}
                    placeholder="例如: 设计师小王"
                    className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
                  />
                </div>

                {/* Account ID */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-stone-700">
                    账号 ID
                  </label>
                  <input
                    type="text"
                    value={formAccountId}
                    onChange={(e) => setFormAccountId(e.target.value)}
                    placeholder="平台用户 ID"
                    className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
                  />
                </div>

                {/* Account URL */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-stone-700">
                    主页链接
                    <span className="ml-1 text-stone-400">(可选)</span>
                  </label>
                  <input
                    type="url"
                    value={formAccountUrl}
                    onChange={(e) => setFormAccountUrl(e.target.value)}
                    placeholder="https://..."
                    className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-stone-400 focus:ring-1 focus:ring-stone-400"
                  />
                </div>

                {/* Submit */}
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    className="rounded-lg border border-stone-200 px-4 py-2 text-sm font-medium text-stone-600 transition-colors hover:bg-stone-50"
                    onClick={() => setShowAddDialog(false)}
                  >
                    取消
                  </button>
                  <button
                    type="submit"
                    disabled={
                      addMutation.isPending ||
                      !formAccountId.trim() ||
                      !formAccountName.trim()
                    }
                    className="rounded-lg bg-stone-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-stone-800 disabled:opacity-50"
                  >
                    {addMutation.isPending ? '添加中...' : '添加'}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/* ── Inline sub-component ── */

function PostList({ posts }: { posts: CompetitorPost[] }) {
  if (posts.length === 0) {
    return (
      <p className="text-xs text-stone-400">暂无已追踪的帖子</p>
    )
  }

  return (
    <div className="space-y-2">
      {posts.map((post) => (
        <div
          key={post.id}
          className={cn(
            'flex items-center justify-between rounded-lg border border-stone-100 bg-stone-50/50 px-4 py-2.5',
            post.is_viral && 'border-orange-200 bg-orange-50/30',
          )}
        >
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm text-stone-800">
              {post.is_viral && (
                <span className="mr-1.5 text-orange-500 text-xs font-bold">VIRAL</span>
              )}
              {post.title || post.content_text?.slice(0, 60) || '无标题'}
            </p>
            <div className="mt-0.5 flex items-center gap-3 text-xs text-stone-400">
              {post.tags && post.tags.length > 0 && (
                <span className="truncate max-w-[200px]">
                  {post.tags.slice(0, 3).join(', ')}
                </span>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-3 text-xs text-stone-400 ml-4">
            <span>{post.likes} 赞</span>
            <span>{post.comments} 评</span>
            <span>{post.shares} 转</span>
          </div>
        </div>
      ))}
    </div>
  )
}
