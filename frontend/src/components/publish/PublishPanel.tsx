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
  type WeChatDraftResponse,
  type PublishStatus,
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
  { id: 'wechat', label: '微信公众号', connected: true, icon: '💬' },
  { id: 'xiaohongshu', label: '小红书', connected: false, icon: '📕' },
  { id: 'weibo', label: '微博', connected: false, icon: '🌐' },
]

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
  const [error, setError] = useState('')

  // ── Push to draft box ────────────────────────────────────────────────

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

  // ── Confirm publish ──────────────────────────────────────────────────

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

  // ── Delete draft (cancel) ────────────────────────────────────────────

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
              <p className="mb-1 text-xs text-neutral-400">标题</p>
              <p className="text-sm font-medium text-neutral-800">{title || '(无标题)'}</p>
              {digest && (
                <>
                  <p className="mb-1 mt-3 text-xs text-neutral-400">摘要</p>
                  <p className="text-sm text-neutral-600">{digest}</p>
                </>
              )}
              <p className="mb-1 mt-3 text-xs text-neutral-400">正文预览</p>
              <p className="line-clamp-4 text-sm text-neutral-600">
                {contentMd.slice(0, 300)}
                {contentMd.length > 300 && '...'}
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep('select')}
                className="rounded-lg border border-neutral-200 px-4 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
              >
                返回
              </button>
              <button
                onClick={handlePushDraft}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700"
              >
                <FileText size={16} />
                推送到草稿箱
              </button>
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
        {step === 'drafted' && draft && (
          <motion.div key="drafted" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="mb-4 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 p-3">
              <CheckCircle2 size={18} className="text-green-600" />
              <span className="text-sm text-green-800">
                草稿已推送到公众号后台
              </span>
            </div>

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
                在公众号后台查看 <ExternalLink size={14} />
              </a>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleDeleteDraft}
                className="flex items-center gap-1 rounded-lg border border-red-200 px-4 py-2 text-sm text-red-600 transition hover:bg-red-50"
              >
                <Trash2 size={14} />
                删除草稿
              </button>
              <button
                onClick={handlePublish}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-700"
              >
                <Send size={16} />
                确认发布
              </button>
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
            <p className="text-sm font-medium text-neutral-800">发布成功</p>
            {publishResult?.published_url && (
              <a
                href={publishResult.published_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                查看文章 <ExternalLink size={14} />
              </a>
            )}
            <button
              onClick={onClose}
              className="mt-2 rounded-lg border border-neutral-200 px-6 py-2 text-sm text-neutral-600 transition hover:bg-neutral-50"
            >
              关闭
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
