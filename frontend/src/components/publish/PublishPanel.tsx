/**
 * PublishPanel — platform selector + WeChat MP draft/publish workflow.
 *
 * Shows when the user clicks the "publish" button from the editor.
 * Flow: select platform -> preview -> push to draft box -> confirm publish.
 */

import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  FileText,
  CheckCircle2,
  XCircle,
  Loader2,
  ExternalLink,
  Trash2,
} from 'lucide-react'
import clsx from 'clsx'

import {
  createWeChatDraft,
  publishWeChatDraft,
  deleteWeChatDraft,
  publishWeiboPost,
  saveWeiboDraft,
  type WeChatDraftResponse,
  type PublishStatus,
  type WeiboPublishResponse,
} from '@/services/publish'

// ── Types ──────────────────────────────────────────────────────────────────

type PlatformId = 'wechat' | 'xiaohongshu' | 'weibo'

interface PlatformOption {
  id: PlatformId
  label: string
  connected: boolean
  icon: string
}

type Step = 'select' | 'preview' | 'drafting' | 'drafted' | 'publishing' | 'success' | 'failed'

interface PublishPanelProps {
  /** Article title from the editor */
  title: string
  /** Article body in Markdown */
  contentMd: string
  /** Author name */
  author?: string
  /** Optional summary / digest */
  digest?: string
  /** Callback when panel is dismissed */
  onClose: () => void
}

// ── Component ──────────────────────────────────────────────────────────────

const PLATFORMS: PlatformOption[] = [
  { id: 'wechat', label: '\u5fae\u4fe1\u516c\u4f17\u53f7', connected: true, icon: '\ud83d\udcac' },
  { id: 'xiaohongshu', label: '\u5c0f\u7ea2\u4e66', connected: false, icon: '\ud83d\udcd5' },
  { id: 'weibo', label: '\u5fae\u535a', connected: true, icon: '\ud83c\udf10' },
]

const WEIBO_MAX_CHARS = 140

export default function PublishPanel({
  title,
  contentMd,
  author = '',
  digest = '',
  onClose,
}: PublishPanelProps) {
  const [_platform, setPlatform] = useState<PlatformId | null>(null)
  const [step, setStep] = useState<Step>('select')
  const [draft, setDraft] = useState<WeChatDraftResponse | null>(null)
  const [publishResult, setPublishResult] = useState<PublishStatus | null>(null)
  const [weiboResult, setWeiboResult] = useState<WeiboPublishResponse | null>(null)
  const [error, setError] = useState('')

  // ── Push to draft box (WeChat) ──────────────────────────────────────

  const handlePushDraft = useCallback(async () => {
    setStep('drafting')
    setError('')
    try {
      const res = await createWeChatDraft({
        title,
        content_md: contentMd,
        author,
        digest,
      })
      setDraft(res)
      setStep('drafted')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setStep('failed')
    }
  }, [title, contentMd, author, digest])

  // ── Confirm publish (WeChat) ────────────────────────────────────────

  const handlePublish = useCallback(async () => {
    if (!draft) return
    setStep('publishing')
    setError('')
    try {
      const res = await publishWeChatDraft(draft.media_id)
      setPublishResult(res)
      setStep(res.status === 'success' ? 'success' : 'failed')
      if (res.error) setError(res.error)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setStep('failed')
    }
  }, [draft])

  // ── Delete draft (cancel WeChat) ────────────────────────────────────

  const handleDeleteDraft = useCallback(async () => {
    if (!draft) return
    try {
      await deleteWeChatDraft(draft.media_id)
    } catch {
      // Non-critical — draft stays in MP backend
    }
    setDraft(null)
    setStep('preview')
  }, [draft])

  // ── Weibo publish ───────────────────────────────────────────────────

  const handleWeiboPublish = useCallback(async () => {
    setStep('publishing')
    setError('')
    try {
      const res = await publishWeiboPost({ content: contentMd.slice(0, WEIBO_MAX_CHARS) })
      setWeiboResult(res)
      setStep(res.success ? 'success' : 'failed')
      if (res.error) setError(res.error)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setStep('failed')
    }
  }, [contentMd])

  const handleWeiboDraft = useCallback(async () => {
    setStep('drafting')
    setError('')
    try {
      const res = await saveWeiboDraft({ content: contentMd.slice(0, WEIBO_MAX_CHARS) })
      setWeiboResult(res)
      setStep(res.success ? 'drafted' : 'failed')
      if (res.error) setError(res.error)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setError(msg)
      setStep('failed')
    }
  }, [contentMd])

  // ── Render helpers ───────────────────────────────────────────────────

  const isLoading = step === 'drafting' || step === 'publishing'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      className="rounded-xl border border-neutral-200 bg-white p-6 shadow-lg"
    >
      {/* Header */}
      <div className="mb-5 flex items-center justify-between">
        <h3 className="text-lg font-semibold text-neutral-900">发布内容</h3>
        <button
          onClick={onClose}
          className="rounded-md p-1 text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-600"
          aria-label="Close"
        >
          <XCircle size={20} />
        </button>
      </div>

      <AnimatePresence mode="wait">
        {/* Step 1: Platform selection */}
        {step === 'select' && (
          <motion.div key="select" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <p className="mb-3 text-sm text-neutral-500">选择发布平台</p>
            <div className="flex gap-3">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  disabled={!p.connected}
                  onClick={() => {
                    setPlatform(p.id)
                    setStep('preview')
                  }}
                  className={clsx(
                    'flex flex-1 flex-col items-center gap-2 rounded-lg border p-4 transition',
                    p.connected
                      ? 'cursor-pointer border-neutral-200 hover:border-blue-400 hover:bg-blue-50'
                      : 'cursor-not-allowed border-neutral-100 bg-neutral-50 opacity-50',
                  )}
                >
                  <span className="text-2xl">{p.icon}</span>
                  <span className="text-sm font-medium text-neutral-700">{p.label}</span>
                  <span
                    className={clsx(
                      'text-xs',
                      p.connected ? 'text-green-600' : 'text-neutral-400',
                    )}
                  >
                    {p.connected ? '已连接' : '未连接'}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Step 2: Preview */}
        {step === 'preview' && (
          <motion.div key="preview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="mb-4 rounded-lg border border-neutral-100 bg-neutral-50 p-4">
              {_platform === 'weibo' ? (
                <>
                  <div className="mb-1 flex items-center justify-between">
                    <p className="text-xs text-neutral-400">{'\u5fae\u535a\u5185\u5bb9'}</p>
                    <span
                      className={clsx(
                        'text-xs font-medium',
                        contentMd.length > WEIBO_MAX_CHARS
                          ? 'text-red-500'
                          : 'text-neutral-400',
                      )}
                    >
                      {contentMd.length}/{WEIBO_MAX_CHARS}
                    </span>
                  </div>
                  <p className="text-sm text-neutral-600">
                    {contentMd.slice(0, WEIBO_MAX_CHARS)}
                    {contentMd.length > WEIBO_MAX_CHARS && (
                      <span className="text-red-400">
                        ...({'\u5c06\u622a\u65ad\u81f3'} {WEIBO_MAX_CHARS} {'\u5b57'})
                      </span>
                    )}
                  </p>
                </>
              ) : (
                <>
                  <p className="mb-1 text-xs text-neutral-400">{'\u6807\u9898'}</p>
                  <p className="text-sm font-medium text-neutral-800">{title || '(\u65e0\u6807\u9898)'}</p>
                  {digest && (
                    <>
                      <p className="mb-1 mt-3 text-xs text-neutral-400">{'\u6458\u8981'}</p>
                      <p className="text-sm text-neutral-600">{digest}</p>
                    </>
                  )}
                  <p className="mb-1 mt-3 text-xs text-neutral-400">{'\u6b63\u6587\u9884\u89c8'}</p>
                  <p className="line-clamp-4 text-sm text-neutral-600">
                    {contentMd.slice(0, 300)}
                    {contentMd.length > 300 && '...'}
                  </p>
                </>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep('select')}
                className="rounded-lg border border-neutral-200 px-4 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
              >
                {'\u8fd4\u56de'}
              </button>
              {_platform === 'weibo' ? (
                <>
                  <button
                    onClick={handleWeiboDraft}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-green-200 px-4 py-2 text-sm font-medium text-green-700 transition hover:bg-green-50"
                  >
                    <FileText size={16} />
                    {'\u5b58\u8349\u7a3f'}
                  </button>
                  <button
                    onClick={handleWeiboPublish}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
                  >
                    <Send size={16} />
                    {'\u53d1\u5fae\u535a'}
                  </button>
                </>
              ) : (
                <button
                  onClick={handlePushDraft}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
                >
                  <FileText size={16} />
                  {'\u63a8\u9001\u5230\u8349\u7a3f\u7bb1'}
                </button>
              )}
            </div>
          </motion.div>
        )}

        {/* Step 3: Drafting / Publishing loader */}
        {isLoading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-3 py-8"
          >
            <Loader2 size={32} className="animate-spin text-blue-500" />
            <p className="text-sm text-neutral-500">
              {step === 'drafting' ? '正在推送到草稿箱...' : '正在发布...'}
            </p>
          </motion.div>
        )}

        {/* Step 4: Draft created — confirm publish */}
        {step === 'drafted' && (draft || weiboResult) && (
          <motion.div key="drafted" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
              <CheckCircle2 size={18} className="text-green-600" />
              <span className="text-sm text-green-800">
                {_platform === 'weibo'
                  ? '\u8349\u7a3f\u5df2\u4fdd\u5b58\u5230\u5fae\u535a'
                  : '\u8349\u7a3f\u5df2\u63a8\u9001\u5230\u516c\u4f17\u53f7\u540e\u53f0'}
              </span>
            </div>

            {_platform === 'weibo' ? (
              <div className="mb-4 rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-sm text-neutral-600">
                <p>
                  <span className="text-neutral-400">status: </span>
                  <code className="text-xs">{weiboResult?.status ?? 'saved'}</code>
                </p>
              </div>
            ) : draft ? (
              <div className="mb-4 rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-sm text-neutral-600">
                <p>
                  <span className="text-neutral-400">media_id: </span>
                  <code className="text-xs">{draft.media_id}</code>
                </p>
                <a
                  href={draft.manage_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-blue-600 hover:underline"
                >
                  {'\u5728\u516c\u4f17\u53f7\u540e\u53f0\u67e5\u770b'} <ExternalLink size={14} />
                </a>
              </div>
            ) : null}

            <div className="flex gap-3">
              {_platform === 'weibo' ? (
                <button
                  onClick={onClose}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-neutral-200 px-4 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
                >
                  {'\u5173\u95ed'}
                </button>
              ) : (
                <>
                  <button
                    onClick={handleDeleteDraft}
                    className="flex items-center gap-1 rounded-lg border border-red-200 px-4 py-2 text-sm text-red-600 transition hover:bg-red-50"
                  >
                    <Trash2 size={14} />
                    {'\u5220\u9664\u8349\u7a3f'}
                  </button>
                  <button
                    onClick={handlePublish}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
                  >
                    <Send size={16} />
                    {'\u786e\u8ba4\u53d1\u5e03'}
                  </button>
                </>
              )}
            </div>
          </motion.div>
        )}

        {/* Step 5: Success */}
        {step === 'success' && (
          <motion.div
            key="success"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-3 py-6"
          >
            <CheckCircle2 size={40} className="text-green-500" />
            <p className="text-sm font-medium text-neutral-800">
              {_platform === 'weibo' ? '\u53d1\u5e03\u6210\u529f' : '\u53d1\u5e03\u6210\u529f'}
            </p>
            {publishResult?.published_url && (
              <a
                href={publishResult.published_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                {'\u67e5\u770b\u6587\u7ae0'} <ExternalLink size={14} />
              </a>
            )}
            {weiboResult?.url && (
              <a
                href={weiboResult.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                {'\u67e5\u770b\u5fae\u535a'} <ExternalLink size={14} />
              </a>
            )}
            <button
              onClick={onClose}
              className="mt-2 rounded-lg border border-neutral-200 px-6 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
            >
              {'\u5173\u95ed'}
            </button>
          </motion.div>
        )}

        {/* Step 6: Failed */}
        {step === 'failed' && (
          <motion.div
            key="failed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center gap-3 py-6"
          >
            <XCircle size={40} className="text-red-500" />
            <p className="text-sm font-medium text-neutral-800">发布失败</p>
            {error && (
              <p className="max-w-sm text-center text-xs text-red-500">{error}</p>
            )}
            <button
              onClick={() => setStep(draft ? 'drafted' : 'preview')}
              className="mt-2 rounded-lg border border-neutral-200 px-6 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
            >
              重试
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
