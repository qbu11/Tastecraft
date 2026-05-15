import { useState, useEffect, useCallback } from 'react'
import { Key, Webhook, Plus, Trash2, Send, Copy, AlertTriangle } from 'lucide-react'
import { api } from '@/services/api'

// ── Types ────────────────────────────────────────────────────────────────

interface APIKeyItem {
  id: number
  name: string
  key_prefix: string
  permissions: string[]
  last_used_at: string | null
  created_at: string
  is_active: boolean
}

interface WebhookItem {
  id: number
  url: string
  events: string[]
  is_active: boolean
  created_at: string
}

const EVENT_OPTIONS = [
  { value: 'content.generated', label: '内容生成' },
  { value: 'content.published', label: '内容发布' },
  { value: 'content.failed', label: '发布失败' },
  { value: 'taste.preference_learned', label: '品味学习' },
  { value: 'competitor.viral_detected', label: '竞品爆款' },
]

// ── Main Component ───────────────────────────────────────────────────────

export function DeveloperSettings() {
  return (
    <div className="space-y-8">
      <APIKeysSection />
      <WebhooksSection />
    </div>
  )
}

// ── API Keys Section ─────────────────────────────────────────────────────

function APIKeysSection() {
  const [keys, setKeys] = useState<APIKeyItem[]>([])
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchKeys = useCallback(async () => {
    try {
      const { data } = await api.get<APIKeyItem[]>('/v1/developer/api-keys')
      setKeys(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchKeys()
  }, [fetchKeys])

  const handleCreate = async () => {
    if (!newKeyName.trim()) return
    try {
      const { data } = await api.post<{ key: string; api_key: APIKeyItem }>(
        '/v1/developer/api-keys',
        { name: newKeyName, permissions: [] },
      )
      setCreatedKey(data.key)
      setNewKeyName('')
      await fetchKeys()
    } catch {
      /* ignore */
    }
  }

  const handleRevoke = async (id: number) => {
    try {
      await api.delete(`/v1/developer/api-keys/${id}`)
      await fetchKeys()
    } catch {
      /* ignore */
    }
  }

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Key size={16} className="text-stone-500" />
        <h3 className="text-sm font-semibold text-stone-800">API Keys</h3>
      </div>

      {/* Created key warning */}
      {createdKey && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-amber-700">
            <AlertTriangle size={12} />
            请立即复制此密钥，关闭后将无法再次查看
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 break-all rounded bg-white px-2 py-1 text-xs text-stone-800">
              {createdKey}
            </code>
            <button
              onClick={() => handleCopy(createdKey)}
              className="rounded p-1 text-stone-500 hover:bg-stone-100"
            >
              <Copy size={14} />
            </button>
          </div>
          <button
            onClick={() => setCreatedKey(null)}
            className="mt-2 text-xs text-amber-600 underline"
          >
            我已保存，关闭
          </button>
        </div>
      )}

      {/* Create form */}
      <div className="flex gap-2">
        <input
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          placeholder="密钥名称（如 My App）"
          className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-[#c2714f]"
        />
        <button
          onClick={handleCreate}
          disabled={!newKeyName.trim()}
          className="flex items-center gap-1 rounded-lg bg-[#c2714f] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b06a4a] disabled:opacity-50"
        >
          <Plus size={14} />
          创建
        </button>
      </div>

      {/* Keys list */}
      {loading ? (
        <p className="text-xs text-stone-400">加载中...</p>
      ) : keys.length === 0 ? (
        <p className="text-xs text-stone-400">暂无 API 密钥</p>
      ) : (
        <div className="divide-y divide-stone-100 rounded-lg border border-stone-200">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center gap-3 px-4 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-stone-800">{k.name}</p>
                <p className="text-xs text-stone-400">
                  {k.key_prefix}... &middot; 创建于{' '}
                  {new Date(k.created_at).toLocaleDateString('zh-CN')}
                  {k.last_used_at && (
                    <>
                      {' '}&middot; 最后使用{' '}
                      {new Date(k.last_used_at).toLocaleDateString('zh-CN')}
                    </>
                  )}
                </p>
              </div>
              <button
                onClick={() => handleRevoke(k.id)}
                className="rounded p-1 text-stone-400 transition-colors hover:bg-red-50 hover:text-red-500"
                title="撤销密钥"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Webhooks Section ─────────────────────────────────────────────────────

function WebhooksSection() {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([])
  const [url, setUrl] = useState('')
  const [secret, setSecret] = useState('')
  const [selectedEvents, setSelectedEvents] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [testResults, setTestResults] = useState<Record<number, { success: boolean; message: string }>>({})

  const fetchWebhooks = useCallback(async () => {
    try {
      const { data } = await api.get<WebhookItem[]>('/v1/developer/webhooks')
      setWebhooks(data)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWebhooks()
  }, [fetchWebhooks])

  const toggleEvent = (ev: string) => {
    setSelectedEvents((prev) =>
      prev.includes(ev) ? prev.filter((e) => e !== ev) : [...prev, ev],
    )
  }

  const handleCreate = async () => {
    if (!url.trim() || !secret.trim() || selectedEvents.length === 0) return
    try {
      await api.post('/v1/developer/webhooks', {
        url,
        events: selectedEvents,
        secret,
      })
      setUrl('')
      setSecret('')
      setSelectedEvents([])
      await fetchWebhooks()
    } catch {
      /* ignore */
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/v1/developer/webhooks/${id}`)
      await fetchWebhooks()
    } catch {
      /* ignore */
    }
  }

  const handleTest = async (id: number) => {
    try {
      const { data } = await api.post<{ success: boolean; message: string }>(
        `/v1/developer/webhooks/${id}/test`,
      )
      setTestResults((prev) => ({ ...prev, [id]: data }))
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: { success: false, message: '测试请求失败' } }))
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Webhook size={16} className="text-stone-500" />
        <h3 className="text-sm font-semibold text-stone-800">Webhooks</h3>
      </div>

      {/* Create form */}
      <div className="space-y-3 rounded-lg border border-stone-200 p-4">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Webhook URL（如 https://example.com/hook）"
          className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-[#c2714f]"
        />
        <input
          value={secret}
          onChange={(e) => setSecret(e.target.value)}
          placeholder="签名密钥"
          type="password"
          className="w-full rounded-lg border border-stone-200 px-3 py-2 text-sm outline-none focus:border-[#c2714f]"
        />
        <div>
          <p className="mb-1.5 text-xs font-medium text-stone-600">监听事件</p>
          <div className="flex flex-wrap gap-2">
            {EVENT_OPTIONS.map((ev) => (
              <button
                key={ev.value}
                onClick={() => toggleEvent(ev.value)}
                className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                  selectedEvents.includes(ev.value)
                    ? 'bg-[#c2714f] text-white'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {ev.label}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={handleCreate}
          disabled={!url.trim() || !secret.trim() || selectedEvents.length === 0}
          className="flex items-center gap-1 rounded-lg bg-[#c2714f] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b06a4a] disabled:opacity-50"
        >
          <Plus size={14} />
          添加 Webhook
        </button>
      </div>

      {/* Webhooks list */}
      {loading ? (
        <p className="text-xs text-stone-400">加载中...</p>
      ) : webhooks.length === 0 ? (
        <p className="text-xs text-stone-400">暂无 Webhook</p>
      ) : (
        <div className="divide-y divide-stone-100 rounded-lg border border-stone-200">
          {webhooks.map((wh) => (
            <div key={wh.id} className="px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-stone-800">{wh.url}</p>
                  <p className="mt-0.5 text-xs text-stone-400">
                    {wh.events.join(', ')}
                  </p>
                </div>
                <button
                  onClick={() => handleTest(wh.id)}
                  className="rounded p-1 text-stone-400 transition-colors hover:bg-blue-50 hover:text-blue-500"
                  title="测试"
                >
                  <Send size={14} />
                </button>
                <button
                  onClick={() => handleDelete(wh.id)}
                  className="rounded p-1 text-stone-400 transition-colors hover:bg-red-50 hover:text-red-500"
                  title="删除"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              {testResults[wh.id] && (
                <p
                  className={`mt-1 text-xs ${
                    testResults[wh.id].success ? 'text-green-600' : 'text-red-500'
                  }`}
                >
                  {testResults[wh.id].message}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
