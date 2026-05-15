import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, ArrowRight } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  suggestion?: {
    type: 'change'
    label: string
    targetSection?: string
  }
  timestamp: number
}

interface CreativeChatProps {
  messages: ChatMessage[]
  onSendMessage: (content: string) => void
  onSuggestionClick?: (suggestion: ChatMessage['suggestion']) => void
  isTyping?: boolean
  className?: string
}

const seedMessages: ChatMessage[] = [
  {
    id: 'seed-1',
    role: 'assistant',
    content: '我根据你的品味画像生成了这篇内容。开头的反常识切入你觉得够吸引吗？',
    timestamp: Date.now(),
  },
]

export function CreativeChat({
  messages: externalMessages,
  onSendMessage,
  onSuggestionClick,
  isTyping = false,
  className,
}: CreativeChatProps) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const messages = externalMessages.length > 0 ? externalMessages : seedMessages

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed) return
    onSendMessage(trimmed)
    setInput('')
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
    }
  }, [input, onSendMessage])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    // Auto-resize textarea
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  return (
    <div className={cn('flex h-full flex-col bg-slate-800', className)}>
      {/* Header */}
      <div className="border-b border-slate-700 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-100">创作助手</h2>
        <p className="text-xs text-slate-400">对话驱动，品味共创</p>
      </div>

      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 pt-4 pb-2">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={cn(
                'max-w-[88%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'ml-auto bg-[#c87b5a] text-white'
                  : 'bg-slate-700 text-slate-100',
              )}
            >
              <p>{msg.content}</p>
              {msg.suggestion && (
                <button
                  onClick={() => onSuggestionClick?.(msg.suggestion)}
                  className="mt-2 flex items-center gap-1 rounded-lg bg-slate-600/50 px-2.5 py-1 text-xs text-slate-300 transition-colors hover:bg-slate-600 hover:text-white"
                >
                  <ArrowRight size={12} />
                  {msg.suggestion.label}
                </button>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing Indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="flex items-center gap-1.5 px-1"
            >
              <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:0ms]" />
              <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:150ms]" />
              <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-500 [animation-delay:300ms]" />
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700 p-3">
        <div className="flex items-end gap-2 rounded-xl bg-slate-700 px-3 py-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="输入修改意见或创作指令..."
            rows={1}
            className="max-h-[120px] flex-1 resize-none bg-transparent text-sm text-slate-100 placeholder-slate-400 outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className={cn(
              'flex-shrink-0 rounded-lg p-1.5 transition-colors',
              input.trim()
                ? 'text-[#c87b5a] hover:bg-slate-600'
                : 'text-slate-500',
            )}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
