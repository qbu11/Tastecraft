import { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  Send,
  SkipForward,
  Upload,
  Link,
  Plus,
  Check,
  Sparkles,
  MessageCircle,
  Target,
  Palette,
  FileText,
  Users,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useOnboardingStore, type ChatMessage } from '@/stores/onboardingStore'
import {
  startOnboarding,
  sendMessage,
  importContent,
  importFromProfile,
  addCompetitors,
  completeOnboarding,
} from '@/services/onboarding'

// ── Step Config ────────────────────────────────────────────────────────────

const STEPS = [
  { id: 'lane_positioning', label: '赛道定位', icon: Target },
  { id: 'style_dialogue', label: '风格对话', icon: Palette },
  { id: 'content_import', label: '内容导入', icon: FileText },
  { id: 'competitor_setup', label: '竞品设置', icon: Users },
  { id: 'first_generation', label: '首篇生成', icon: Zap },
]

// ── Style Samples (for step 2) ─────────────────────────────────────────────

const STYLE_SAMPLES = [
  {
    id: 'A',
    title: '干货流',
    description: '直接给答案，条理清晰，数据说话',
    sample: '3 个信号说明 AI 正在改变内容创作：1) 效率提升 10x 2) 个性化成为标配 3) 分发逻辑重构...',
  },
  {
    id: 'B',
    title: '故事流',
    description: '亲身经历切入，感性共鸣，最后点题',
    sample: '上周和朋友吃饭时聊到一个话题，他说自从用了 AI 写文案后，每天多出 3 小时...',
  },
  {
    id: 'C',
    title: '观点流',
    description: '犀利洞察，敢于反共识，金句频出',
    sample: '所有人都在说 AI 替代人类，但真相是：不会用 AI 的人替代不会用 AI 的人...',
  },
  {
    id: 'D',
    title: '教程流',
    description: '手把手拆解，step by step，小白友好',
    sample: '今天教你 5 分钟搭建一个 AI 内容工厂。第一步：打开 XX 工具，点击左上角...',
  },
]

// ── Components ─────────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      <motion.div
        className="h-2 w-2 rounded-full bg-stone-400"
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, delay: 0 }}
      />
      <motion.div
        className="h-2 w-2 rounded-full bg-stone-400"
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, delay: 0.2 }}
      />
      <motion.div
        className="h-2 w-2 rounded-full bg-stone-400"
        animate={{ opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 1.2, repeat: Infinity, delay: 0.4 }}
      />
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}
    >
      <div
        className={cn(
          'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isUser
            ? 'bg-[#c2714f] text-white'
            : 'bg-stone-100 text-stone-800',
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </motion.div>
  )
}

function StyleSampleCard({
  sample,
  onSelect,
}: {
  sample: (typeof STYLE_SAMPLES)[0]
  onSelect: (id: string) => void
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onSelect(sample.id)}
      className="flex flex-col gap-2 rounded-xl border border-stone-200 bg-white p-4 text-left transition-colors hover:border-[#c2714f]/40 hover:shadow-sm"
    >
      <div className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#c2714f]/10 text-xs font-semibold text-[#c2714f]">
          {sample.id}
        </span>
        <span className="text-sm font-medium text-stone-800">
          {sample.title}
        </span>
      </div>
      <p className="text-xs text-stone-500">{sample.description}</p>
      <p className="mt-1 rounded-lg bg-stone-50 px-3 py-2 text-xs italic text-stone-600">
        "{sample.sample}"
      </p>
    </motion.button>
  )
}

// ── Platform detection helpers ────────────────────────────────────────────

const PLATFORM_PATTERNS: Record<string, { regex: RegExp; label: string; icon: string }> = {
  xiaohongshu: { regex: /xiaohongshu\.com|xhslink\.com/i, label: '小红书', icon: '📕' },
  weibo: { regex: /weibo\.com/i, label: '微博', icon: '🔴' },
  zhihu: { regex: /zhihu\.com/i, label: '知乎', icon: '🔵' },
  douyin: { regex: /douyin\.com/i, label: '抖音', icon: '🎵' },
}

function detectPlatformFromUrl(url: string): { platform: string; label: string; icon: string } | null {
  for (const [platform, info] of Object.entries(PLATFORM_PATTERNS)) {
    if (info.regex.test(url)) {
      return { platform, ...info }
    }
  }
  return null
}

// ── Profile Import Section (v2 — primary) ─────────────────────────────────

function ProfileImportSection({
  onProfileImport,
  onUrlImport,
  isLoading,
  importProgress,
}: {
  onProfileImport: (profileUrl: string, platform?: string) => void
  onUrlImport: (urls: string[]) => void
  isLoading: boolean
  importProgress: string | null
}) {
  const [profileUrl, setProfileUrl] = useState('')
  const [detectedPlatform, setDetectedPlatform] = useState<{
    platform: string
    label: string
    icon: string
  } | null>(null)
  const [showManualImport, setShowManualImport] = useState(false)
  const [manualUrls, setManualUrls] = useState('')

  // Auto-detect platform from URL input
  const handleProfileUrlChange = (value: string) => {
    setProfileUrl(value)
    if (value.trim()) {
      setDetectedPlatform(detectPlatformFromUrl(value.trim()))
    } else {
      setDetectedPlatform(null)
    }
  }

  const handleProfileSubmit = () => {
    if (!profileUrl.trim() || isLoading) return
    onProfileImport(profileUrl.trim(), detectedPlatform?.platform)
  }

  const handleManualSubmit = () => {
    const parsed = manualUrls
      .split('\n')
      .map((u) => u.trim())
      .filter(Boolean)
    if (parsed.length > 0) {
      onUrlImport(parsed)
      setManualUrls('')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-3"
    >
      {/* Primary: Profile URL auto-import */}
      <div className="rounded-xl border-2 border-[#c2714f]/30 bg-gradient-to-br from-[#c2714f]/5 to-transparent p-4">
        <div className="mb-3 flex items-center gap-2">
          <Upload size={16} className="text-[#c2714f]" />
          <span className="text-sm font-medium text-stone-700">
            粘贴你的主页链接
          </span>
          <span className="rounded-full bg-[#c2714f]/10 px-2 py-0.5 text-[10px] font-medium text-[#c2714f]">
            推荐
          </span>
        </div>
        <p className="mb-3 text-xs text-stone-500">
          粘贴主页链接，AI 会自动获取你的近期内容并分析写作风格
        </p>

        <div className="relative mb-3">
          <input
            type="text"
            value={profileUrl}
            onChange={(e) => handleProfileUrlChange(e.target.value)}
            placeholder="https://www.xiaohongshu.com/user/profile/..."
            className="w-full rounded-lg border border-stone-200 bg-white px-3 py-2.5 pr-16 text-xs text-stone-700 placeholder-stone-400 outline-none focus:border-[#c2714f]/40"
            disabled={isLoading}
          />
          {detectedPlatform && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs text-stone-600">
              <span>{detectedPlatform.icon}</span>
              <span>{detectedPlatform.label}</span>
            </span>
          )}
        </div>

        {/* Progress indicator */}
        {isLoading && importProgress && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="mb-3 flex items-center gap-2 rounded-lg bg-stone-50 px-3 py-2"
          >
            <motion.div
              className="h-3 w-3 rounded-full border-2 border-[#c2714f] border-t-transparent"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
            <span className="text-xs text-stone-600">{importProgress}</span>
          </motion.div>
        )}

        <button
          onClick={handleProfileSubmit}
          disabled={!profileUrl.trim() || isLoading}
          className="flex items-center gap-1.5 rounded-lg bg-[#c2714f] px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-[#a85d3f] disabled:opacity-50"
        >
          <Link size={12} />
          {isLoading ? '分析中...' : '自动导入并分析'}
        </button>
      </div>

      {/* Secondary: Manual URL import (collapsible) */}
      <button
        onClick={() => setShowManualImport(!showManualImport)}
        className="flex items-center gap-1 text-xs text-stone-400 transition-colors hover:text-stone-600"
      >
        <Plus size={10} />
        {showManualImport ? '收起手动导入' : '或手动粘贴文章链接'}
      </button>

      <AnimatePresence>
        {showManualImport && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden rounded-xl border border-stone-200 bg-white p-4"
          >
            <textarea
              value={manualUrls}
              onChange={(e) => setManualUrls(e.target.value)}
              placeholder="每行一个文章链接..."
              rows={3}
              className="mb-3 w-full resize-none rounded-lg border border-stone-200 px-3 py-2 text-xs text-stone-700 placeholder-stone-400 outline-none focus:border-[#c2714f]/40"
            />
            <button
              onClick={handleManualSubmit}
              disabled={!manualUrls.trim() || isLoading}
              className="flex items-center gap-1.5 rounded-lg bg-stone-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-stone-800 disabled:opacity-50"
            >
              <Link size={12} />
              {isLoading ? '分析中...' : '开始分析'}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function StyleFeaturesDisplay({
  features,
  onConfirm,
  onReject,
}: {
  features: string[]
  onConfirm: () => void
  onReject: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-stone-200 bg-white p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <Sparkles size={16} className="text-[#c2714f]" />
        <span className="text-sm font-medium text-stone-700">
          发现的风格特征
        </span>
      </div>
      <div className="mb-4 space-y-2">
        {features.map((feature, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-stone-600">
            <Check size={12} className="mt-0.5 shrink-0 text-emerald-500" />
            <span>{feature}</span>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <button
          onClick={onConfirm}
          className="flex items-center gap-1 rounded-lg bg-stone-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-stone-800"
        >
          <Check size={12} />
          很准确
        </button>
        <button
          onClick={onReject}
          className="flex items-center gap-1 rounded-lg border border-stone-200 px-4 py-2 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-50"
        >
          有偏差，我来补充
        </button>
      </div>
    </motion.div>
  )
}

function CompetitorSection({
  onAdd,
}: {
  onAdd: (urls: string[]) => void
}) {
  const [urls, setUrls] = useState('')

  const handleSubmit = () => {
    const parsed = urls
      .split('\n')
      .map((u) => u.trim())
      .filter(Boolean)
    if (parsed.length > 0) {
      onAdd(parsed)
      setUrls('')
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-stone-200 bg-white p-4"
    >
      <div className="mb-3 flex items-center gap-2">
        <Users size={16} className="text-[#c2714f]" />
        <span className="text-sm font-medium text-stone-700">
          添加竞品账号
        </span>
      </div>
      <p className="mb-3 text-xs text-stone-500">
        分享你欣赏或想对标的同领域账号，帮助找到差异化方向
      </p>
      <textarea
        value={urls}
        onChange={(e) => setUrls(e.target.value)}
        placeholder="每行一个账号链接..."
        rows={2}
        className="mb-3 w-full resize-none rounded-lg border border-stone-200 px-3 py-2 text-xs text-stone-700 placeholder-stone-400 outline-none focus:border-[#c2714f]/40"
      />
      <button
        onClick={handleSubmit}
        disabled={!urls.trim()}
        className="flex items-center gap-1.5 rounded-lg bg-stone-900 px-4 py-2 text-xs font-medium text-white transition-colors hover:bg-stone-800 disabled:opacity-50"
      >
        <Plus size={12} />
        添加
      </button>
    </motion.div>
  )
}

function GeneratedContentPreview({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4 }}
      className="rounded-xl border border-[#c2714f]/20 bg-gradient-to-br from-[#c2714f]/5 to-transparent p-5"
    >
      <div className="mb-3 flex items-center gap-2">
        <Sparkles size={16} className="text-[#c2714f]" />
        <span className="text-sm font-semibold text-stone-800">
          你的第一篇内容
        </span>
      </div>
      <div className="whitespace-pre-wrap rounded-lg bg-white p-4 text-sm leading-relaxed text-stone-700 shadow-sm">
        {content}
      </div>
    </motion.div>
  )
}

// ── Main Page Component ────────────────────────────────────────────────────

export function Onboarding() {
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [showStyleSamples, setShowStyleSamples] = useState(false)
  const [importProgress, setImportProgress] = useState<string | null>(null)
  const [styleFeatures, setStyleFeatures] = useState<string[]>([])

  const {
    sessionId,
    currentStep,
    stepIndex,
    messages,
    isLoading,
    importedContent,
    competitors,
    generatedContent,
    isComplete,
    setSession,
    addMessage,
    setLoading,
    updateStep,
    addImportedContent,
    addCompetitors: storeAddCompetitors,
    setStyleAnalysis,
    setGeneratedContent,
    setComplete,
  } = useOnboardingStore()

  // Auto-scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping, scrollToBottom])

  // Initialize onboarding session
  useEffect(() => {
    if (!sessionId) {
      initSession()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function initSession() {
    try {
      setLoading(true)
      const resp = await startOnboarding()
      setSession(resp.session_id, resp.current_step, resp.step_index)

      // Simulate typing delay for first message
      setIsTyping(true)
      await delay(800)
      setIsTyping(false)

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: resp.first_message,
        timestamp: Date.now(),
        quickReplies: resp.quick_replies,
      })
    } catch (err) {
      // Fallback message if API unavailable
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content:
          '你好！我是你的品味顾问。接下来几分钟，我会通过对话了解你的创作风格。\n\n先聊聊基础的 —— 你平时主要在哪些平台发内容？',
        timestamp: Date.now(),
        quickReplies: ['小红书', '微信公众号', '小红书 + 公众号', '其他平台'],
      })
      setSession('local-fallback', 'lane_positioning', 0)
    } finally {
      setLoading(false)
    }
  }

  async function handleSend(text?: string) {
    const messageText = text || input.trim()
    if (!messageText || isLoading) return

    // Add user message
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: messageText,
      timestamp: Date.now(),
    })
    setInput('')

    // Show typing indicator
    setIsTyping(true)
    setLoading(true)

    try {
      if (!sessionId || sessionId === 'local-fallback') {
        // Fallback mode
        await delay(1000)
        setIsTyping(false)
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '收到！让我们继续聊聊你的内容领域和目标读者吧。',
          timestamp: Date.now(),
          quickReplies: [],
        })
        return
      }

      const resp = await sendMessage(sessionId, messageText)

      // Simulate typing delay
      await delay(300 + Math.random() * 500)
      setIsTyping(false)

      // Update step if changed
      if (resp.step_index !== stepIndex) {
        updateStep(resp.current_step, resp.step_index)
      }

      // Show style samples when entering style_dialogue step
      if (resp.current_step === 'style_dialogue' && !showStyleSamples) {
        setShowStyleSamples(true)
      } else if (resp.current_step !== 'style_dialogue') {
        setShowStyleSamples(false)
      }

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: resp.message,
        timestamp: Date.now(),
        quickReplies: resp.quick_replies,
        showImportUI: resp.show_import_ui,
        showCompetitorUI: resp.show_competitor_ui,
      })

      // Handle completion
      if (resp.is_complete) {
        await handleComplete()
      }
    } catch {
      setIsTyping(false)
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '网络有点小问题，能再说一次吗？',
        timestamp: Date.now(),
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleProfileImport(profileUrl: string, platform?: string) {
    if (!sessionId) return
    setLoading(true)
    setImportProgress('正在连接平台获取内容...')
    try {
      const result = await importFromProfile(sessionId, profileUrl, platform)

      if (!result.success) {
        setImportProgress(null)
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `导入遇到问题：${result.error || '未知错误'}。你可以手动粘贴文章链接，或继续对话。`,
          timestamp: Date.now(),
          quickReplies: ['手动粘贴链接', '跳过这一步'],
        })
        return
      }

      setImportProgress(`正在分析你的 ${result.post_count} 篇内容...`)
      await delay(500) // Brief visual pause

      // Store style features for confirmation UI
      if (result.style_features.length > 0) {
        setStyleFeatures(result.style_features)
      }

      if (result.style_analysis) {
        addImportedContent(
          Array.from({ length: result.post_count }, (_, i) => `auto-import-${i}`),
        )
        setStyleAnalysis({
          tone: result.style_analysis.tone,
          summary: result.style_analysis.summary,
        })

        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `已分析你的 ${result.post_count} 篇内容！\n\n语气：${result.style_analysis.tone}\n结构偏好：${result.style_analysis.structure_preference}\n词汇水平：${result.style_analysis.vocabulary_level}\n\n总结：${result.style_analysis.summary}`,
          timestamp: Date.now(),
          quickReplies: ['很准确', '有些偏差，我来补充', '继续下一步'],
        })
      }
    } catch {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '自动导入遇到网络问题，你可以手动粘贴文章链接或跳过。',
        timestamp: Date.now(),
        quickReplies: ['手动粘贴链接', '跳过这一步'],
      })
    } finally {
      setImportProgress(null)
      setLoading(false)
    }
  }

  async function handleImport(urls: string[]) {
    if (!sessionId) return
    setLoading(true)
    try {
      const analysis = await importContent(sessionId, urls)
      addImportedContent(urls)
      setStyleAnalysis({ tone: analysis.tone, summary: analysis.summary })

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `分析完成！你的写作风格特征：\n\n语气：${analysis.tone}\n结构偏好：${analysis.structure_preference}\n词汇水平：${analysis.vocabulary_level}\n\n总结：${analysis.summary}`,
        timestamp: Date.now(),
        quickReplies: ['很准确', '有些偏差，我来补充', '继续下一步'],
      })
    } catch {
      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '内容分析遇到问题，我们可以稍后再试。先继续对话吧！',
        timestamp: Date.now(),
        quickReplies: ['好的，继续'],
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleAddCompetitors(urls: string[]) {
    if (!sessionId) return
    try {
      await addCompetitors(sessionId, urls)
      storeAddCompetitors(urls)

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `已添加 ${urls.length} 个竞品账号，会在后台分析他们的内容风格。\n\n接下来，让我为你生成第一篇内容！你想聊什么主题？`,
        timestamp: Date.now(),
        quickReplies: [],
      })
    } catch {
      // Silent fail for competitors (non-critical)
    }
  }

  async function handleComplete() {
    if (!sessionId) return
    try {
      const result = await completeOnboarding(sessionId)
      setGeneratedContent(result.first_content)
      setComplete(true)
    } catch {
      // Still mark as complete even on error
      setComplete(true)
    }
  }

  function handleSkipStep() {
    handleSend('跳过这一步')
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Get the last message's quick replies and special UI flags
  const lastMessage = messages[messages.length - 1]
  const quickReplies = lastMessage?.quickReplies || []
  const showImportUI = lastMessage?.showImportUI || false
  const showCompetitorUI = lastMessage?.showCompetitorUI || false

  return (
    <div className="flex h-screen bg-stone-50" style={{ fontFamily: "'Outfit', 'Noto Sans SC', sans-serif" }}>
      {/* ── Left Sidebar: Progress ── */}
      <aside className="flex w-72 flex-col justify-between border-r border-stone-200 bg-white px-6 py-8">
        <div>
          <div className="mb-8">
            <h1 className="text-xl font-semibold text-stone-900">TasteCraft</h1>
            <p className="mt-0.5 text-xs text-stone-500">品味画像建设中</p>
          </div>

          {/* Step indicators */}
          <div className="space-y-4">
            {STEPS.map((step, i) => {
              const Icon = step.icon
              const isActive = i === stepIndex
              const isDone = i < stepIndex || isComplete

              return (
                <div key={step.id} className="flex items-center gap-3">
                  <div
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-all duration-300',
                      isDone
                        ? 'bg-[#c2714f] text-white'
                        : isActive
                          ? 'border-2 border-[#c2714f] text-[#c2714f]'
                          : 'border border-stone-200 text-stone-400',
                    )}
                  >
                    {isDone ? <Check size={14} /> : <Icon size={14} />}
                  </div>
                  <span
                    className={cn(
                      'text-sm transition-colors',
                      isActive
                        ? 'font-medium text-stone-900'
                        : isDone
                          ? 'text-stone-600'
                          : 'text-stone-400',
                    )}
                  >
                    {step.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Imported content & competitors summary */}
        <div className="space-y-3">
          {importedContent.length > 0 && (
            <div className="rounded-lg bg-stone-50 px-3 py-2">
              <p className="text-xs text-stone-500">
                已导入 {importedContent.length} 篇内容
              </p>
            </div>
          )}
          {competitors.length > 0 && (
            <div className="rounded-lg bg-stone-50 px-3 py-2">
              <p className="text-xs text-stone-500">
                已添加 {competitors.length} 个竞品
              </p>
            </div>
          )}
          <div className="flex items-center gap-2">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-stone-100">
              <motion.div
                className="h-full rounded-full bg-[#c2714f]"
                initial={{ width: 0 }}
                animate={{ width: `${Math.max((stepIndex / 5) * 100, 5)}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
            <span className="text-xs text-stone-500">
              {stepIndex}/{STEPS.length}
            </span>
          </div>
        </div>
      </aside>

      {/* ── Main Chat Area ── */}
      <main className="flex flex-1 flex-col">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-stone-100 px-8 py-4">
          <div className="flex items-center gap-2">
            <MessageCircle size={16} className="text-[#c2714f]" />
            <span className="text-sm font-medium text-stone-700">
              品味对话 — {STEPS[stepIndex]?.label || '完成'}
            </span>
          </div>
          {!isComplete && currentStep !== 'first_generation' && (
            <button
              onClick={handleSkipStep}
              className="flex items-center gap-1 text-xs text-stone-400 transition-colors hover:text-stone-600"
            >
              <SkipForward size={12} />
              跳过此步
            </button>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-8 py-6">
          <div className="mx-auto max-w-2xl space-y-4">
            <AnimatePresence mode="popLayout">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>

            {/* Typing indicator */}
            {isTyping && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className="rounded-2xl bg-stone-100">
                  <TypingIndicator />
                </div>
              </motion.div>
            )}

            {/* Style samples (step 2) */}
            {showStyleSamples && currentStep === 'style_dialogue' && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-2 gap-3 pt-2"
              >
                {STYLE_SAMPLES.map((sample) => (
                  <StyleSampleCard
                    key={sample.id}
                    sample={sample}
                    onSelect={(id) => handleSend(`我偏好 ${id} - ${STYLE_SAMPLES.find((s) => s.id === id)?.title}`)}
                  />
                ))}
              </motion.div>
            )}

            {/* Import UI (v2: profile auto-import + manual fallback) */}
            {showImportUI && (
              <ProfileImportSection
                onProfileImport={handleProfileImport}
                onUrlImport={handleImport}
                isLoading={isLoading}
                importProgress={importProgress}
              />
            )}

            {/* Style features confirmation (v2) */}
            {styleFeatures.length > 0 && (
              <StyleFeaturesDisplay
                features={styleFeatures}
                onConfirm={() => {
                  setStyleFeatures([])
                  handleSend('很准确，继续下一步')
                }}
                onReject={() => {
                  setStyleFeatures([])
                  handleSend('有偏差，我来补充')
                }}
              />
            )}

            {/* Competitor UI */}
            {showCompetitorUI && (
              <CompetitorSection onAdd={handleAddCompetitors} />
            )}

            {/* Generated content preview */}
            {generatedContent && (
              <GeneratedContentPreview content={generatedContent} />
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* ── Input Area ── */}
        <div className="border-t border-stone-100 bg-white px-8 py-4">
          <div className="mx-auto max-w-2xl">
            {/* Quick replies */}
            {quickReplies.length > 0 && !isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-3 flex flex-wrap gap-2"
              >
                {quickReplies.map((reply) => (
                  <motion.button
                    key={reply}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => handleSend(reply)}
                    className="rounded-full border border-stone-200 bg-white px-3.5 py-1.5 text-xs text-stone-600 transition-colors hover:border-[#c2714f]/40 hover:text-[#c2714f]"
                  >
                    {reply}
                  </motion.button>
                ))}
              </motion.div>
            )}

            {/* Completion state */}
            {isComplete ? (
              <motion.button
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => navigate('/dashboard')}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#c2714f] px-6 py-3.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#a85d3f]"
              >
                <Sparkles size={16} />
                开始使用 TasteCraft
              </motion.button>
            ) : (
              <div className="flex items-end gap-3">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="输入你的回答..."
                  rows={1}
                  className="flex-1 resize-none rounded-xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-[#c2714f]/40 focus:bg-white"
                  style={{ minHeight: '44px', maxHeight: '120px' }}
                />
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isLoading}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-stone-900 text-white transition-colors hover:bg-stone-800 disabled:opacity-40"
                >
                  <Send size={16} />
                </motion.button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

// ── Utilities ──────────────────────────────────────────────────────────────

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
