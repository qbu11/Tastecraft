import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Link } from 'react-router-dom'
import axios from 'axios'

interface TasteTestResult {
  style_features: string[]
  imitation: string
  similarity_score: number
}

type Phase = 'input' | 'loading' | 'result'

export function TasteTestDemo({ compact = false }: { compact?: boolean }) {
  const [text, setText] = useState('')
  const [phase, setPhase] = useState<Phase>('input')
  const [result, setResult] = useState<TasteTestResult | null>(null)
  const [error, setError] = useState('')

  const charCount = text.length
  const isValid = charCount >= 50 && charCount <= 500

  const handleAnalyze = useCallback(async () => {
    if (!isValid) return
    setPhase('loading')
    setError('')

    try {
      const { data } = await axios.post<TasteTestResult>(
        '/api/v1/demo/taste-test',
        { text },
      )
      setResult(data)
      setPhase('result')
    } catch (err: unknown) {
      if (axios.isAxiosError(err) && err.response?.status === 429) {
        setError('每小时最多体验 3 次，注册后可无限使用')
      } else {
        setError('分析失败，请稍后再试')
      }
      setPhase('input')
    }
  }, [text, isValid])

  const handleReset = () => {
    setText('')
    setResult(null)
    setPhase('input')
    setError('')
  }

  return (
    <div
      className={`rounded-2xl border border-stone-200/60 bg-white/80 backdrop-blur-sm ${compact ? 'p-5' : 'p-6 lg:p-8'}`}
    >
      <AnimatePresence mode="wait">
        {/* ---------- INPUT ---------- */}
        {phase === 'input' && (
          <motion.div
            key="input"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
          >
            <p className="mb-3 text-sm font-medium text-stone-700">
              粘贴你写过的一段内容
            </p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="把你最满意的一段文字粘贴到这里，AI 会分析你的风格并尝试模仿..."
              rows={compact ? 4 : 5}
              maxLength={500}
              className="w-full resize-none rounded-xl border border-stone-200 bg-stone-50/50 px-4 py-3 text-sm leading-relaxed text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-[var(--color-accent)] focus:bg-white"
            />
            <div className="mt-2 flex items-center justify-between">
              <span
                className={`text-xs ${charCount < 50 ? 'text-stone-400' : charCount > 500 ? 'text-red-500' : 'text-stone-500'}`}
              >
                {charCount}/500
                {charCount > 0 && charCount < 50 && (
                  <span className="ml-1.5 text-stone-400">
                    (至少 50 字)
                  </span>
                )}
              </span>
              <motion.button
                whileHover={isValid ? { scale: 1.03 } : {}}
                whileTap={isValid ? { scale: 0.97 } : {}}
                onClick={handleAnalyze}
                disabled={!isValid}
                className="rounded-lg bg-[var(--color-accent)] px-5 py-2 text-sm font-medium text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-40"
              >
                分析我的风格
              </motion.button>
            </div>
            {error && (
              <p className="mt-2 text-xs text-red-500">{error}</p>
            )}
          </motion.div>
        )}

        {/* ---------- LOADING ---------- */}
        {phase === 'loading' && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-12"
          >
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-stone-200 border-t-[var(--color-accent)]" />
            <p className="text-sm text-stone-500">
              正在分析你的风格特征...
            </p>
          </motion.div>
        )}

        {/* ---------- RESULT ---------- */}
        {phase === 'result' && result && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="space-y-5"
          >
            {/* Style features */}
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-stone-500">
                你的风格特征
              </p>
              <div className="flex flex-wrap gap-2">
                {result.style_features.map((f, i) => (
                  <span
                    key={i}
                    className="rounded-full border border-[var(--color-accent)]/20 bg-[var(--color-accent-muted)] px-3 py-1 text-xs font-medium text-[var(--color-accent)]"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>

            {/* Side-by-side */}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-stone-200 bg-stone-50/50 p-4">
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-stone-400">
                  你的原文
                </p>
                <p className="text-sm leading-relaxed text-stone-700">
                  {text.length > 200 ? text.slice(0, 200) + '...' : text}
                </p>
              </div>
              <div className="rounded-xl border border-[var(--color-accent)]/20 bg-[var(--color-accent-muted)] p-4">
                <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-[var(--color-accent)]">
                  AI 模仿
                </p>
                <p className="text-sm leading-relaxed text-stone-700">
                  {result.imitation}
                </p>
              </div>
            </div>

            {/* Score */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-24 overflow-hidden rounded-full bg-stone-200">
                  <motion.div
                    className="h-full rounded-full bg-[var(--color-accent)]"
                    initial={{ width: 0 }}
                    animate={{ width: `${result.similarity_score}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
                <span className="text-xs text-stone-500">
                  相似度 {Math.round(result.similarity_score)}%
                </span>
              </div>
              <button
                onClick={handleReset}
                className="text-xs text-stone-400 underline-offset-2 transition-colors hover:text-stone-600 hover:underline"
              >
                再试一次
              </button>
            </div>

            {/* CTA */}
            <Link
              to="/login"
              className="block rounded-lg bg-[var(--color-accent)] py-2.5 text-center text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              注册后获得完整品味画像
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
