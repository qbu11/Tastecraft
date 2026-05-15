import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, SkipForward } from 'lucide-react'
import { cn } from '@/lib/utils'

interface OnboardingStep {
  id: number
  question: string
  placeholder: string
  hint: string
}

const steps: OnboardingStep[] = [
  {
    id: 1,
    question: '你主要在哪些平台发布内容？',
    placeholder: '例如：小红书、微信公众号...',
    hint: '我们会根据平台特性调整内容风格',
  },
  {
    id: 2,
    question: '你的内容领域是什么？',
    placeholder: '例如：AI 科技、生活方式、商业分析...',
    hint: '帮助我理解你的专长和兴趣',
  },
  {
    id: 3,
    question: '你喜欢什么样的写作风格？',
    placeholder: '例如：专业严谨、轻松有趣、深度思考...',
    hint: '品味画像的起点，后续会不断进化',
  },
  {
    id: 4,
    question: '分享一篇你认为写得好的文章（可选）',
    placeholder: '粘贴链接或描述它好在哪里...',
    hint: '帮助 AI 更精准地理解你的品味偏好',
  },
]

export function Onboarding() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<number, string>>({})

  const step = steps[currentStep]
  const isLast = currentStep === steps.length - 1

  const handleNext = () => {
    if (isLast) {
      navigate('/dashboard')
      return
    }
    setCurrentStep((s) => s + 1)
  }

  const handleSkip = () => {
    navigate('/dashboard')
  }

  return (
    <div className="grid min-h-screen grid-cols-[1fr_1.2fr]">
      {/* Left — Progress + branding */}
      <div className="flex flex-col justify-between bg-slate-900 px-10 py-10">
        <div>
          <h1 className="text-2xl font-semibold text-stone-100">TasteCraft</h1>
          <p className="mt-1 text-sm text-stone-500">品味工坊</p>
        </div>

        <div className="space-y-3">
          {steps.map((s, i) => (
            <div key={s.id} className="flex items-center gap-3">
              <div
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-medium',
                  i < currentStep
                    ? 'bg-[var(--color-accent)] text-white'
                    : i === currentStep
                      ? 'border-2 border-[var(--color-accent)] text-[var(--color-accent)]'
                      : 'border border-slate-700 text-slate-600',
                )}
              >
                {i + 1}
              </div>
              <span
                className={cn(
                  'text-sm',
                  i <= currentStep ? 'text-stone-300' : 'text-stone-600',
                )}
              >
                {s.question.slice(0, 12)}...
              </span>
            </div>
          ))}
        </div>

        <p className="text-xs text-stone-600">
          {currentStep + 1} / {steps.length}
        </p>
      </div>

      {/* Right — Conversation */}
      <div className="flex flex-col justify-center px-16 py-10">
        <AnimatePresence mode="wait">
          {step && (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
              className="max-w-lg space-y-6"
            >
              {/* AI message bubble */}
              <div className="rounded-2xl bg-stone-100 px-5 py-4">
                <p className="text-base font-medium text-stone-800">
                  {step.question}
                </p>
                <p className="mt-1 text-sm text-stone-500">{step.hint}</p>
              </div>

              {/* Input */}
              <textarea
                value={answers[step.id] ?? ''}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [step.id]: e.target.value }))
                }
                placeholder={step.placeholder}
                rows={3}
                className="w-full resize-none rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-stone-400"
              />

              {/* Actions */}
              <div className="flex items-center justify-between">
                <button
                  onClick={handleSkip}
                  className="flex items-center gap-1 text-sm text-stone-400 transition-colors hover:text-stone-600"
                >
                  <SkipForward size={14} />
                  跳过设置
                </button>

                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleNext}
                  className="flex items-center gap-1.5 rounded-lg bg-stone-900 px-5 py-2.5 text-sm font-medium text-stone-100 transition-colors hover:bg-stone-800"
                >
                  {isLast ? '开始使用' : '继续'}
                  <ChevronRight size={16} />
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
