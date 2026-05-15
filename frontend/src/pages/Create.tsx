import { useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Save, Globe, Send as SendIcon, Clock } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { TiptapEditor } from '@/components/editor/TiptapEditor'
import { VariantPicker, type ContentVariant } from '@/components/editor/VariantPicker'
import { CreativeChat, type ChatMessage } from '@/components/chat/CreativeChat'
import { StyleControls, defaultStyles, type StyleParam } from '@/components/editor/StyleControls'
import { VersionHistory } from '@/components/editor/VersionHistory'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import {
  rewriteSection,
  adjustStyle,
  sendCreativeChat,
  generateVariants,
  expandVariantStream,
} from '@/services/content'
import { useAuthStore } from '@/stores/authStore'

type CreationPhase = 'topic' | 'variants' | 'editor'

export function Create() {
  const navigate = useNavigate()
  const token = useAuthStore.getState().token
  const [title, setTitle] = useState('')
  const [editorContent, setEditorContent] = useState('')
  const [editorText, setEditorText] = useState('')
  const [platform, setPlatform] = useState<'xiaohongshu' | 'wechat' | 'weibo'>('xiaohongshu')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isChatTyping, setIsChatTyping] = useState(false)
  const [styleValues, setStyleValues] = useState<StyleParam[]>(defaultStyles)
  const [isSaved, setIsSaved] = useState(true)
  const [splitRatio, setSplitRatio] = useState(60)
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false)
  const dragRef = useRef<boolean>(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Variant picker state
  const [phase, setPhase] = useState<CreationPhase>('topic')
  const [currentTopic, setCurrentTopic] = useState('')
  const [variants, setVariants] = useState<ContentVariant[]>([])
  const [isLoadingVariants, setIsLoadingVariants] = useState(false)
  const expandAbortRef = useRef<(() => void) | null>(null)

  // Version history state
  const [isVersionHistoryOpen, setIsVersionHistoryOpen] = useState(false)
  const [currentContentId] = useState<number | null>(null) // Set when content is saved/generated

  const { isGenerating, cancel, startGeneration } = useStreamingGeneration({
    onChunk: (chunk) => {
      setEditorContent((prev) => prev + chunk)
    },
    onComplete: () => {
      setIsSaved(false)
    },
  })

  // Editor change handler
  const handleEditorChange = useCallback((html: string, text: string) => {
    setEditorContent(html)
    setEditorText(text)
    setIsSaved(false)
  }, [])

  // Rewrite request from floating toolbar
  const handleRewriteRequest = useCallback(
    async (text: string, action: string) => {
      try {
        const result = await rewriteSection({
          contentId: 'current',
          originalText: text,
          instruction: action,
        })
        // The rewritten content replaces the selection in the editor
        setEditorContent((prev) => prev.replace(text, result))
        setIsSaved(false)
      } catch {
        // Silently handle error
      }
    },
    [],
  )

  // ── Variant Generation Flow ─────────────────────────────────────────

  const handleGenerateVariants = useCallback(
    async (topic: string) => {
      setCurrentTopic(topic)
      setIsLoadingVariants(true)
      setPhase('variants')
      setVariants([])

      try {
        const result = await generateVariants({
          topic,
          platform,
          num_variants: 3,
        })
        setVariants(result.variants)
      } catch {
        // Fallback: skip variant step, go direct to editor generation
        setPhase('editor')
        setEditorContent('')
        startGeneration({ topic, platform })
      } finally {
        setIsLoadingVariants(false)
      }
    },
    [platform, startGeneration],
  )

  const handleRegenerateVariants = useCallback(() => {
    if (currentTopic) {
      handleGenerateVariants(currentTopic)
    }
  }, [currentTopic, handleGenerateVariants])

  const handleExpandVariant = useCallback(
    async (variant: ContentVariant) => {
      setPhase('editor')
      setEditorContent('')

      const { response, abort } = expandVariantStream(
        {
          variant_id: variant.id,
          topic: currentTopic,
          angle: variant.angle,
          hook: variant.hook,
          outline: variant.outline,
          tone: variant.tone,
          platform,
        },
        token ?? undefined,
      )
      expandAbortRef.current = abort

      try {
        const res = await response
        if (!res.ok) {
          throw new Error(`Expand failed: ${res.status}`)
        }

        const reader = res.body?.getReader()
        if (!reader) throw new Error('No response body')

        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data === '[DONE]') {
                setIsSaved(false)
                return
              }
              try {
                const parsed = JSON.parse(data) as { type: string; content?: string }
                if (parsed.type === 'content' && parsed.content) {
                  setEditorContent((prev) => prev + parsed.content)
                }
              } catch {
                // Non-JSON data
              }
            }
          }
        }
        setIsSaved(false)
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          // On error, keep whatever content was streamed
          setIsSaved(false)
        }
      }
    },
    [currentTopic, platform, token],
  )

  // ── Chat / Generation handlers ──────────────────────────────────────

  // Chat message handler
  const handleSendChatMessage = useCallback(
    async (content: string) => {
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content,
        timestamp: Date.now(),
      }
      setChatMessages((prev) => [...prev, userMsg])
      setIsChatTyping(true)

      try {
        const reply = await sendCreativeChat({
          message: content,
          editorContent: editorText,
          platform,
        })

        const aiMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: reply.reply,
          suggestion: reply.suggestion
            ? {
                type: 'change' as const,
                label: reply.suggestion.label,
                targetSection: reply.suggestion.targetSection,
              }
            : undefined,
          timestamp: Date.now(),
        }
        setChatMessages((prev) => [...prev, aiMsg])
      } catch {
        const errorMsg: ChatMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: '\u62b1\u6b49\uff0c\u6211\u6682\u65f6\u65e0\u6cd5\u56de\u5e94\u3002\u8bf7\u7a0d\u540e\u518d\u8bd5\u3002',
          timestamp: Date.now(),
        }
        setChatMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsChatTyping(false)
      }
    },
    [editorText, platform],
  )

  // Style change handler
  const handleStyleChange = useCallback(
    async (id: string, value: number) => {
      setStyleValues((prev) =>
        prev.map((p) => (p.id === id ? { ...p, value } : p)),
      )

      // Debounced style adjustment (in real app, debounce this)
      const params = Object.fromEntries(
        styleValues.map((p) => [p.id, p.id === id ? value : p.value]),
      ) as { formality: number; length: number; emotion: number; expertise: number }

      try {
        const result = await adjustStyle({
          contentId: 'current',
          styleParams: params,
        })
        setEditorContent(result)
        setIsSaved(false)
      } catch {
        // Silently handle
      }
    },
    [styleValues],
  )

  // Resizable split handler
  const handleMouseDown = useCallback(() => {
    dragRef.current = true
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const ratio = ((e.clientX - rect.left) / rect.width) * 100
      setSplitRatio(Math.max(40, Math.min(75, ratio)))
    }

    const handleMouseUp = () => {
      dragRef.current = false
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [])

  // Publish handler
  const handlePublish = useCallback(() => {
    if (isGenerating) {
      cancel()
    }
    // TODO: integrate with publish pipeline
  }, [isGenerating, cancel])

  // Version rollback handler
  const handleVersionRollback = useCallback((newTitle: string, newBody: string) => {
    setTitle(newTitle)
    setEditorContent(newBody)
    setIsSaved(false)
  }, [])

  // Generate from topic — now routes through variant picker
  const handleGenerateFromTopic = useCallback(
    (topic: string) => {
      handleGenerateVariants(topic)
    },
    [handleGenerateVariants],
  )

  // Handle suggestion clicks from chat (e.g., "查看变更")
  const handleSuggestionClick = useCallback(
    (suggestion: { type: string; label: string; targetSection?: string } | undefined) => {
      if (!suggestion) return
      if (suggestion.type === 'generate' && suggestion.targetSection) {
        handleGenerateFromTopic(suggestion.targetSection)
      }
      // For 'change' type, scroll to relevant section in editor (future enhancement)
    },
    [handleGenerateFromTopic],
  )

  // Platform cycle now includes weibo
  const cyclePlatform = useCallback(() => {
    setPlatform((p) => {
      if (p === 'xiaohongshu') return 'wechat'
      if (p === 'wechat') return 'weibo'
      return 'xiaohongshu'
    })
  }, [])

  const platformLabel = platform === 'xiaohongshu'
    ? '\u5c0f\u7ea2\u4e66'
    : platform === 'wechat'
      ? '\u5fae\u4fe1\u516c\u4f17\u53f7'
      : '\u5fae\u535a'

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col -mx-10 -my-8">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-stone-200 bg-white px-4 py-2.5">
        <button
          onClick={() => {
            if (phase === 'variants') {
              setPhase('topic')
              setVariants([])
            } else if (phase === 'editor' && variants.length > 0) {
              setPhase('variants')
              setEditorContent('')
              expandAbortRef.current?.()
            } else {
              navigate(-1)
            }
          }}
          className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-100 hover:text-stone-700"
        >
          <ArrowLeft size={18} />
        </button>

        <input
          type="text"
          value={title}
          onChange={(e) => {
            setTitle(e.target.value)
            setIsSaved(false)
          }}
          placeholder="\u8f93\u5165\u5185\u5bb9\u6807\u9898..."
          className="flex-1 text-base font-semibold text-stone-900 placeholder-stone-300 outline-none"
        />

        {/* Auto-save indicator */}
        <div className="flex items-center gap-1 text-xs text-stone-400">
          <Save size={12} />
          <span>{isSaved ? '\u5df2\u4fdd\u5b58' : '\u672a\u4fdd\u5b58'}</span>
        </div>

        {/* Version history button */}
        <button
          onClick={() => setIsVersionHistoryOpen(true)}
          className="flex items-center gap-1 rounded-lg border border-stone-200 px-2.5 py-1 text-xs font-medium text-stone-500 transition-colors hover:border-stone-300 hover:text-stone-700"
        >
          <Clock size={12} />
          {'\u7248\u672c\u5386\u53f2'}
        </button>

        {/* Platform badge */}
        <button
          onClick={cyclePlatform}
          className="flex items-center gap-1 rounded-lg border border-stone-200 px-2.5 py-1 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300"
        >
          <Globe size={12} />
          {platformLabel}
        </button>

        {/* Mobile chat toggle */}
        <button
          onClick={() => setIsMobileChatOpen((v) => !v)}
          className="rounded-lg border border-stone-200 p-1.5 text-stone-500 transition-colors hover:bg-stone-100 md:hidden"
        >
          <SendIcon size={14} />
        </button>

        {/* Publish button */}
        <button
          onClick={handlePublish}
          className="rounded-lg bg-[#c87b5a] px-4 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-[#b06a4a]"
        >
          {'\u53d1\u5e03'}
        </button>
      </div>

      {/* ── Variant Picker Phase ── */}
      {phase === 'variants' && (
        <div className="flex-1 overflow-y-auto bg-stone-50">
          <VariantPicker
            variants={variants}
            isLoading={isLoadingVariants}
            onExpand={handleExpandVariant}
            onRegenerate={handleRegenerateVariants}
            topic={currentTopic}
          />
        </div>
      )}

      {/* ── Topic Input Phase (initial state) ── */}
      {phase === 'topic' && (
        <div className="flex flex-1 items-center justify-center bg-stone-50">
          <div className="mx-auto w-full max-w-md px-6">
            <h2 className="mb-2 text-center text-lg font-semibold text-stone-800">
              {'\u8f93\u5165\u4f60\u7684\u9009\u9898'}
            </h2>
            <p className="mb-6 text-center text-sm text-stone-500">
              {'\u6211\u4eec\u4f1a\u4e3a\u4f60\u751f\u6210 2-3 \u4e2a\u4e0d\u540c\u7684\u521b\u4f5c\u65b9\u5411'}
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                const input = (e.target as HTMLFormElement).elements.namedItem(
                  'topic',
                ) as HTMLInputElement
                const topic = input.value.trim()
                if (topic) {
                  handleGenerateVariants(topic)
                }
              }}
              className="flex gap-3"
            >
              <input
                name="topic"
                type="text"
                autoFocus
                placeholder={'\u4f8b\u5982\uff1aAI \u521b\u4e1a\u7684 5 \u4e2a\u5173\u952e\u5efa\u8bae'}
                className="flex-1 rounded-lg border border-stone-200 px-4 py-2.5 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-[#c87b5a] focus:ring-1 focus:ring-[#c87b5a]/20"
              />
              <button
                type="submit"
                className="rounded-lg bg-[#c87b5a] px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#b06a4a]"
              >
                {'\u751f\u6210'}
              </button>
            </form>
            <button
              onClick={() => setPhase('editor')}
              className="mt-4 w-full text-center text-xs text-stone-400 transition-colors hover:text-stone-600"
            >
              {'\u8df3\u8fc7\uff0c\u76f4\u63a5\u5199\u4f5c'}
            </button>
          </div>
        </div>
      )}

      {/* ── Editor Phase ── */}
      {phase === 'editor' && (
        <>
          {/* Main workspace area */}
          <div ref={containerRef} className="flex flex-1 overflow-hidden">
            {/* Editor Panel */}
            <div
              className="flex flex-col overflow-hidden bg-white"
              style={{ width: `${splitRatio}%` }}
            >
              <TiptapEditor
                content={editorContent}
                onChange={handleEditorChange}
                onRewriteRequest={handleRewriteRequest}
                isGenerating={isGenerating}
                className="flex-1"
              />
            </div>

            {/* Drag Handle */}
            <div
              onMouseDown={handleMouseDown}
              className="group relative z-10 hidden w-1 cursor-col-resize md:block"
            >
              <div className="absolute inset-y-0 -left-0.5 w-2 transition-colors group-hover:bg-[#c87b5a]/20" />
            </div>

            {/* Chat Panel — Desktop */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="hidden flex-1 overflow-hidden md:flex"
            >
              <CreativeChat
                messages={chatMessages}
                onSendMessage={handleSendChatMessage}
                onSuggestionClick={handleSuggestionClick}
                isTyping={isChatTyping}
                className="w-full"
              />
            </motion.div>

            {/* Chat Panel — Mobile Slide-over */}
            {isMobileChatOpen && (
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                className="fixed inset-y-0 right-0 z-50 w-[85vw] max-w-[400px] shadow-2xl md:hidden"
              >
                <CreativeChat
                  messages={chatMessages}
                  onSendMessage={handleSendChatMessage}
                  onSuggestionClick={handleSuggestionClick}
                  isTyping={isChatTyping}
                  className="h-full"
                />
              </motion.div>
            )}
          </div>

          {/* Style Controls — Bottom Bar */}
          <StyleControls
            values={styleValues}
            onChange={handleStyleChange}
          />
        </>
      )}

      {/* Version History Panel */}
      <VersionHistory
        contentId={currentContentId}
        isOpen={isVersionHistoryOpen}
        onClose={() => setIsVersionHistoryOpen(false)}
        onRollback={handleVersionRollback}
      />
    </div>
  )
}
