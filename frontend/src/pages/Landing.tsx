import { useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { TasteTestDemo, PricingCards, HowItWorks } from '@/components/landing'

/* ------------------------------------------------------------------
 * Section wrapper with scroll-triggered fade
 * ----------------------------------------------------------------*/
function Section({
  children,
  id,
  className = '',
}: {
  children: React.ReactNode
  id?: string
  className?: string
}) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 32 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className={`px-6 lg:px-12 ${className}`}
    >
      {children}
    </motion.section>
  )
}

/* ------------------------------------------------------------------
 * Nav
 * ----------------------------------------------------------------*/
function Nav() {
  return (
    <nav className="fixed inset-x-0 top-0 z-50 border-b border-stone-200/40 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6 lg:px-12">
        <Link to="/" className="flex items-baseline gap-2">
          <span className="text-lg font-bold tracking-tight text-stone-900">
            TasteCraft
          </span>
          <span className="text-[11px] text-stone-400">品味工坊</span>
        </Link>

        <div className="flex items-center gap-6">
          <a
            href="#how"
            className="hidden text-sm text-stone-500 transition-colors hover:text-stone-800 sm:inline"
          >
            工作原理
          </a>
          <a
            href="#pricing"
            className="hidden text-sm text-stone-500 transition-colors hover:text-stone-800 sm:inline"
          >
            价格
          </a>
          <Link
            to="/login"
            className="rounded-lg bg-[var(--color-accent)] px-4 py-1.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            登录
          </Link>
        </div>
      </div>
    </nav>
  )
}

/* ------------------------------------------------------------------
 * 1. Hero — asymmetric split
 * ----------------------------------------------------------------*/
function Hero() {
  return (
    <section className="relative min-h-[90vh] overflow-hidden bg-gradient-to-br from-[#faf8f5] via-white to-[#faf8f5] pt-14">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-20 lg:grid-cols-[1.2fr_1fr] lg:gap-16 lg:px-12 lg:py-28">
        {/* Left 55% — copy */}
        <motion.div
          initial={{ opacity: 0, x: -24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6 }}
        >
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-stone-900 sm:text-5xl lg:text-[3.4rem] lg:leading-[1.15]">
            越用越懂你的
            <br />
            <span className="text-[var(--color-accent)]">内容合伙人</span>
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-stone-500 sm:text-lg">
            别人的 AI 千篇一律，你的 AI 只有你的味道。
            <br className="hidden sm:inline" />
            TasteCraft 从你的风格出发，越写越像你自己。
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/login"
              className="rounded-lg bg-[var(--color-accent)] px-6 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              免费开始
            </Link>
            <a
              href="#demo"
              className="rounded-lg border border-stone-200 bg-white px-6 py-2.5 text-sm font-medium text-stone-700 transition-colors hover:border-stone-300 hover:bg-stone-50"
            >
              先试试看
            </a>
          </div>

          {/* Trust line */}
          <p className="mt-10 text-xs text-stone-400">
            无需信用卡 &middot; 5 分钟上手 &middot; 数据本地化
          </p>
        </motion.div>

        {/* Right 45% — interactive demo */}
        <motion.div
          initial={{ opacity: 0, x: 24 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <TasteTestDemo compact />
        </motion.div>
      </div>

      {/* Decorative warm blob */}
      <div className="pointer-events-none absolute -right-40 -top-40 h-[480px] w-[480px] rounded-full bg-[var(--color-accent)]/[0.04] blur-3xl" />
    </section>
  )
}

/* ------------------------------------------------------------------
 * 2. Problem Statement
 * ----------------------------------------------------------------*/
function ProblemStatement() {
  const pains = [
    {
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="2" y="3" width="16" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
          <path d="M6 8h8M6 11h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
      text: 'AI 生成的内容读起来都一个味',
    },
    {
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
          <path d="M10 7v4l2.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
      text: '反复修改 prompt 浪费大量时间',
    },
    {
      icon: (
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path d="M4 16l4-4m0 0l4-4m-4 4L4 8m4 4l4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M14 6v8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ),
      text: '内容质量忽高忽低，无法稳定输出',
    },
  ]

  return (
    <Section className="mx-auto max-w-3xl py-20 text-center lg:py-28">
      <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-accent)]">
        痛点
      </p>
      <h2 className="mt-3 text-2xl font-bold text-stone-900 sm:text-3xl">
        AI 写的内容都一个味？
      </h2>
      <p className="mx-auto mt-3 max-w-lg text-base text-stone-500">
        你需要的不是又一个写作工具，是一个懂你品味的内容搭档。
      </p>

      <div className="mx-auto mt-10 grid max-w-xl gap-5 sm:grid-cols-3">
        {pains.map((p, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="flex flex-col items-center gap-3 rounded-xl border border-stone-200/60 bg-white/70 p-5"
          >
            <span className="text-[var(--color-accent)]">{p.icon}</span>
            <p className="text-sm leading-snug text-stone-600">{p.text}</p>
          </motion.div>
        ))}
      </div>
    </Section>
  )
}

/* ------------------------------------------------------------------
 * 4. Full-width Taste Test repeat
 * ----------------------------------------------------------------*/
function TasteTestSection() {
  return (
    <Section id="demo" className="mx-auto max-w-2xl py-20 lg:py-28">
      <div className="mb-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-accent)]">
          即刻体验
        </p>
        <h2 className="mt-3 text-2xl font-bold text-stone-900 sm:text-3xl">
          品味测试
        </h2>
        <p className="mx-auto mt-3 max-w-md text-base text-stone-500">
          粘贴一段你写过的内容，看看 AI 怎么模仿你
        </p>
      </div>
      <TasteTestDemo />
    </Section>
  )
}

/* ------------------------------------------------------------------
 * 6. Waitlist / Social proof
 * ----------------------------------------------------------------*/
function Waitlist() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (email.includes('@')) setSubmitted(true)
  }

  return (
    <Section className="mx-auto max-w-xl py-20 text-center lg:py-28">
      <span className="inline-block rounded-full border border-[var(--color-accent)]/20 bg-[var(--color-accent-muted)] px-3 py-1 text-xs font-medium text-[var(--color-accent)]">
        即将上线
      </span>
      <h2 className="mt-4 text-2xl font-bold text-stone-900 sm:text-3xl">
        加入等候名单
      </h2>
      <p className="mt-3 text-base text-stone-500">
        首批用户享受终身折扣
      </p>

      {submitted ? (
        <motion.p
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 text-sm text-[var(--color-accent)]"
        >
          已加入等候名单，我们会尽快联系你
        </motion.p>
      ) : (
        <form
          onSubmit={handleSubmit}
          className="mx-auto mt-6 flex max-w-sm gap-2"
        >
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="你的邮箱"
            className="flex-1 rounded-lg border border-stone-200 bg-white px-4 py-2.5 text-sm text-stone-800 placeholder-stone-400 outline-none transition-colors focus:border-[var(--color-accent)]"
          />
          <button
            type="submit"
            className="shrink-0 rounded-lg bg-[var(--color-accent)] px-5 py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            加入
          </button>
        </form>
      )}
    </Section>
  )
}

/* ------------------------------------------------------------------
 * 7. Footer
 * ----------------------------------------------------------------*/
function Footer() {
  return (
    <footer className="border-t border-stone-200/40 bg-stone-50 py-10">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 sm:flex-row lg:px-12">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-stone-800">TasteCraft</span>
          <span className="text-[10px] text-stone-400">品味工坊</span>
        </div>
        <div className="flex items-center gap-5 text-xs text-stone-400">
          <a href="#" className="transition-colors hover:text-stone-600">
            服务条款
          </a>
          <a href="#" className="transition-colors hover:text-stone-600">
            隐私政策
          </a>
          <a href="#" className="transition-colors hover:text-stone-600">
            联系我们
          </a>
        </div>
        <p className="text-[11px] text-stone-400">
          &copy; {new Date().getFullYear()} TasteCraft. All rights reserved.
        </p>
      </div>
    </footer>
  )
}

/* ------------------------------------------------------------------
 * Landing Page (assembled)
 * ----------------------------------------------------------------*/
export function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-white">
      <Nav />
      <Hero />
      <ProblemStatement />

      {/* 3. How It Works */}
      <Section id="how" className="py-20 lg:py-28">
        <div className="mb-12 text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-accent)]">
            工作原理
          </p>
          <h2 className="mt-3 text-2xl font-bold text-stone-900 sm:text-3xl">
            三步，让 AI 成为你的内容合伙人
          </h2>
        </div>
        <HowItWorks />
      </Section>

      {/* 4. Taste Test (full-width repeat) */}
      <TasteTestSection />

      {/* 5. Pricing */}
      <Section id="pricing" className="bg-stone-50/50 py-20 lg:py-28">
        <div className="mb-12 text-center">
          <p className="text-xs font-semibold uppercase tracking-widest text-[var(--color-accent)]">
            价格
          </p>
          <h2 className="mt-3 text-2xl font-bold text-stone-900 sm:text-3xl">
            简单透明的定价
          </h2>
          <p className="mx-auto mt-3 max-w-md text-base text-stone-500">
            从免费开始，按需升级
          </p>
        </div>
        <PricingCards />
      </Section>

      {/* 6. Waitlist */}
      <Waitlist />

      {/* 7. Footer */}
      <Footer />
    </div>
  )
}
