import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Send, Wand2, Image, Hash, Type } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

const seedMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content: '你好！我是你的品味创作助手。输入一个选题方向，我来帮你生成初稿。',
  },
]

function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>(seedMessages)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    // Simulate AI response
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '正在为你构思内容...',
        },
      ])
    }, 600)
  }

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto px-4 pt-4 pb-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
              msg.role === 'user'
                ? 'ml-auto bg-stone-900 text-stone-100'
                : 'bg-stone-100 text-stone-700',
            )}
          >
            {msg.content}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-stone-200 p-3">
        <div className="flex items-center gap-2 rounded-xl bg-stone-100 px-3 py-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入选题或修改意见..."
            className="flex-1 bg-transparent text-sm text-stone-800 placeholder-stone-400 outline-none"
          />
          <button
            onClick={handleSend}
            className="rounded-lg p-1.5 text-stone-500 transition-colors hover:bg-stone-200 hover:text-stone-700"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}

function StyleControls() {
  const controls = [
    { icon: Type, label: '风格' },
    { icon: Hash, label: '话题' },
    { icon: Image, label: '配图' },
    { icon: Wand2, label: '润色' },
  ]

  return (
    <div className="flex items-center gap-2 border-t border-stone-200 px-5 py-3">
      {controls.map(({ icon: Icon, label }) => (
        <button
          key={label}
          className="flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:border-stone-300 hover:bg-stone-50"
        >
          <Icon size={14} />
          {label}
        </button>
      ))}
    </div>
  )
}

export function Create() {
  return (
    <div className="flex h-[calc(100vh-64px)] gap-0 -mx-10 -my-8">
      {/* Editor Panel — 60% */}
      <div className="flex w-3/5 flex-col border-r border-stone-200 bg-white">
        <div className="border-b border-stone-200 px-6 py-4">
          <input
            type="text"
            placeholder="输入标题..."
            className="w-full text-xl font-semibold text-stone-900 placeholder-stone-300 outline-none"
          />
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="prose prose-stone max-w-none">
            <p className="text-stone-400">
              在这里编写内容，或通过右侧对话让 AI 帮你生成初稿...
            </p>
          </div>
        </div>

        <StyleControls />
      </div>

      {/* Chat Panel — 40% */}
      <motion.div
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex w-2/5 flex-col bg-stone-50"
      >
        <div className="border-b border-stone-200 px-4 py-3">
          <h2 className="text-sm font-semibold text-stone-700">创作助手</h2>
          <p className="text-xs text-stone-400">对话驱动，品味共创</p>
        </div>
        <ChatPanel />
      </motion.div>
    </div>
  )
}
