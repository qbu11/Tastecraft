import { useState, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, Save, Globe, Send as SendIcon } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { TiptapEditor } from '@/components/editor/TiptapEditor'
import { CreativeChat, type ChatMessage } from '@/components/chat/CreativeChat'
import { StyleControls, defaultStyles, type StyleParam } from '@/components/editor/StyleControls'
import { useStreamingGeneration } from '@/hooks/useStreamingGeneration'
import { rewriteSection, adjustStyle, sendCreativeChat } from '@/services/content'

export function Create() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [editorContent, setEditorContent] = useState('')
  const [editorText, setEditorText] = useState('')
  const [platform, setPlatform] = useState<'xiaohongshu' | 'wechat'>('xiaohongshu')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isChatTyping, setIsChatTyping] = useState(false)
  const [styleValues, setStyleValues] = useState<StyleParam[]>(defaultStyles)
  const [isSaved, setIsSaved] = useState(true)
  const [splitRatio, setSplitRatio] = useState(60)
  const [isMobileChatOpen, setIsMobileChatOpen] = useState(false)
  const dragRef = useRef<boolean>(false)
  const containerRef = useRef<HTMLDivElement>(null)

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
          content: '抱歉，我暂时无法回应。请稍后再试。',
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

  // Generate from topic (used when user sends initial topic via chat)
  const handleGenerateFromTopic = useCallback(
    (topic: string) => {
      setEditorContent('')
      startGeneration({ topic, platform })
    },
    [platform, startGeneration],
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

  return (
    <div className="flex h-[calc(100vh-64px)] flex-col -mx-10 -my-8">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-stone-200 bg-white px-4 py-2.5">
        <button
          onClick={() => navigate(-1)}
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
          placeholder="输入内容标题..."
          className="flex-1 text-base font-semibold text-stone-900 placeholder-stone-300 outline-none"
        />

        {/* Auto-save indicator */}
        <div className="flex items-center gap-1 text-xs text-stone-400">
          <Save size={12} />
          <span>{isSaved ? '已保存' : '未保存'}</span>
        </div>

        {/* Platform badge */}
        <button
          onClick={() =>
            setPlatform((p) => (p === 'xiaohongshu' ? 'wechat' : 'xiaohongshu'))
          }
          className="flex items-center gap-1 rounded-lg border border-stone-200 px-2.5 py-1 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300"
        >
          <Globe size={12} />
          {platform === 'xiaohongshu' ? '小红书' : '微信公众号'}
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
          发布
        </button>
      </div>

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
    </div>
  )
}
