import { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function Login() {
  const navigate = useNavigate()
  const loginAction = useAuthStore((s) => s.login)
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [codeSent, setCodeSent] = useState(false)

  const handleSendCode = () => {
    if (phone.length < 11) return
    setCodeSent(true)
  }

  const handleLogin = () => {
    // Mock login
    loginAction('mock-token', {
      id: '1',
      name: '品味匠人',
      phone,
      tasteScore: 72,
    })
    navigate('/dashboard')
  }

  return (
    <div className="grid min-h-screen grid-cols-[1.4fr_1fr]">
      {/* Left — branding */}
      <div className="flex flex-col justify-between bg-slate-900 px-14 py-12">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-stone-100">
            TasteCraft
          </h1>
          <p className="mt-2 text-lg text-stone-500">品味工坊</p>
        </div>

        <div className="max-w-md space-y-4">
          <p className="text-2xl font-light leading-relaxed text-stone-300">
            AI 不替你写作，
            <br />
            而是帮你找到自己的声音。
          </p>
          <p className="text-sm text-stone-600">
            品味驱动的内容创作引擎
          </p>
        </div>

        <p className="text-xs text-stone-700">TasteCraft v0.1</p>
      </div>

      {/* Right — form */}
      <div className="flex items-center justify-center bg-stone-50 px-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-sm space-y-6"
        >
          <div>
            <h2 className="text-xl font-semibold text-stone-900">登录</h2>
            <p className="mt-1 text-sm text-stone-500">
              输入手机号开始创作之旅
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-stone-600">
                手机号
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="请输入手机号"
                maxLength={11}
                className="w-full rounded-lg border border-stone-200 bg-white px-3.5 py-2.5 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-stone-400"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-stone-600">
                验证码
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder="6 位验证码"
                  maxLength={6}
                  className="flex-1 rounded-lg border border-stone-200 bg-white px-3.5 py-2.5 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-stone-400"
                />
                <button
                  onClick={handleSendCode}
                  disabled={phone.length < 11 || codeSent}
                  className="shrink-0 rounded-lg border border-stone-200 bg-white px-4 py-2.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {codeSent ? '已发送' : '获取验证码'}
                </button>
              </div>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleLogin}
            className="w-full rounded-lg bg-stone-900 py-2.5 text-sm font-medium text-stone-100 transition-colors hover:bg-stone-800"
          >
            登录
          </motion.button>

          <p className="text-center text-xs text-stone-400">
            登录即同意服务条款和隐私政策
          </p>
        </motion.div>
      </div>
    </div>
  )
}
