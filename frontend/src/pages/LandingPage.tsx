import { Link } from 'react-router-dom'
import {
  Bot,
  Sparkles,
  TrendingUp,
  Palette,
  Search,
  PenTool,
  ShieldCheck,
  RefreshCw,
  Send,
  BarChart3,
  ArrowRight,
  Zap,
  Heart,
  ChevronDown,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  平台 SVG Logo 组件                                                  */
/* ------------------------------------------------------------------ */

function XiaohongshuLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#FF2442" />
      <path d="M7 8h4v8H9v-6H7V8zm6 0h4v2h-2v6h-2V8z" fill="#fff" />
    </svg>
  )
}

function WechatLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#07C160" />
      <path d="M9.5 7C7 7 5 8.8 5 11c0 1.2.6 2.3 1.6 3l-.4 1.5 1.7-1c.5.2 1 .3 1.6.3.2 0 .4 0 .6-.1A4.4 4.4 0 0 1 10 13c0-2.5 2.2-4.5 5-4.5h.5C15 7 12.5 7 9.5 7zm5.5 5c-2.2 0-4 1.5-4 3.5s1.8 3.5 4 3.5c.5 0 1-.1 1.4-.2l1.3.7-.3-1.2c.8-.7 1.3-1.6 1.3-2.8 0-2-1.8-3.5-3.7-3.5z" fill="#fff" />
    </svg>
  )
}

function WeiboLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#E6162D" />
      <path d="M10.5 8c3.5-.5 6.5 2 6 5s-4 5-7.5 4.5S3 14 3.5 11s3.5-2.5 7-3zm.5 2c-2.5 0-4.5 1.5-4.5 3.5S8.5 17 11 17s4.5-1.5 4.5-3.5S13.5 10 11 10z" fill="#fff" />
      <circle cx="17" cy="7" r="1.5" fill="#F8B042" />
    </svg>
  )
}

function ZhihuLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#0066FF" />
      <path d="M6 7h5v1.5H8.5v6L10 14l-1 2.5-2.5-3V8.5H6V7zm7 0h1.5l1 4 1.5-4H18l-2.5 7H17l.5 1.5h-4L14 14h1.5l1-3-1.5 3h-1L12 7z" fill="#fff" />
    </svg>
  )
}

function DouyinLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#000" />
      <path d="M15 6c0 2 1.5 3.5 3 4v2c-1.5 0-2.5-.5-3-1v5c0 2.5-2 4.5-4.5 4.5S6 18.5 6 16s2-4.5 4.5-4.5V14c-1.4 0-2.5 1-2.5 2s1.1 2 2.5 2 2.5-1 2.5-2V6h2z" fill="#fff" />
      <path d="M15 6c0 2 1.5 3.5 3 4v2c-1.5 0-2.5-.5-3-1v5c0 2.5-2 4.5-4.5 4.5" stroke="#25F4EE" strokeWidth=".7" fill="none" />
      <path d="M13 11.5V14c-1.4 0-2.5 1-2.5 2s1.1 2 2.5 2" stroke="#FE2C55" strokeWidth=".7" fill="none" />
    </svg>
  )
}

function BilibiliLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect width="24" height="24" rx="6" fill="#00A1D6" />
      <path d="M7.5 7L6 9h12l-1.5-2M5 10h14v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7z" fill="#fff" />
      <circle cx="9" cy="14" r="1.2" fill="#00A1D6" />
      <circle cx="15" cy="14" r="1.2" fill="#00A1D6" />
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/*  平台数据                                                           */
/* ------------------------------------------------------------------ */

const platforms = [
  { name: '小红书', Logo: XiaohongshuLogo, style: '种草体 · 真实分享感' },
  { name: '微信公众号', Logo: WechatLogo, style: '深度长文 · 有温度' },
  { name: '微博', Logo: WeiboLogo, style: '快准狠 · 蹭热点' },
  { name: '知乎', Logo: ZhihuLogo, style: '专业回答 · 有论证' },
  { name: '抖音', Logo: DouyinLogo, style: '口语化 · 快节奏脚本' },
  { name: 'B站', Logo: BilibiliLogo, style: '有梗有料 · 信息密度' },
]

const agents = [
  { icon: Search, name: '选题研究员', desc: '追踪赛道爆款，分析流量趋势', color: 'bg-purple-50 text-purple-600' },
  { icon: PenTool, name: '内容创作者', desc: '用你的风格写出爆款内容', color: 'bg-blue-50 text-blue-600' },
  { icon: ShieldCheck, name: '内容审核员', desc: '质量把关 + 合规检查', color: 'bg-green-50 text-green-600' },
  { icon: RefreshCw, name: '平台适配师', desc: '一份内容适配 6 种平台调性', color: 'bg-orange-50 text-orange-600' },
  { icon: Send, name: '发布员', desc: '定时发布 + 多平台同步', color: 'bg-pink-50 text-pink-600' },
  { icon: BarChart3, name: '数据分析师', desc: '追踪表现，反哺下一轮选题', color: 'bg-cyan-50 text-cyan-600' },
]

const tasteSignals = [
  {
    icon: Heart,
    title: '你的反馈',
    desc: '喜欢或不喜欢，每一次表态都在校准你的 taste profile',
    color: 'bg-rose-50 text-rose-600',
  },
  {
    icon: PenTool,
    title: '你的修改',
    desc: '每次改稿都是一次品味训练，AI 学会你的用词和节奏',
    color: 'bg-blue-50 text-blue-600',
  },
  {
    icon: BarChart3,
    title: '数据信号',
    desc: '粉丝最买账的内容反哺选题，让 taste 和流量对齐',
    color: 'bg-green-50 text-green-600',
  },
]

const faqs = [
  {
    q: '需要自己想选题吗？',
    a: '不需要。你只需在注册时选择赛道和目标客户，AI 会根据赛道爆款 + 你的 taste 自动生成选题。',
  },
  {
    q: 'Taste 是怎么沉淀的？',
    a: '三个渠道：注册时的偏好录入、日常交互中的反馈（喜欢/不喜欢/修改），以及内容发布后的数据表现。系统持续学习，越用越精准。',
  },
  {
    q: '支持哪些平台？',
    a: '小红书、微信公众号、微博、知乎、抖音、B站，共 6 个平台。一份选题自动适配 6 种平台调性。',
  },
  {
    q: '内容会不会千篇一律？',
    a: '不会。每篇内容都基于你独特的 taste profile 生成，不是搬运爆款，而是用你的风格重新演绎。',
  },
]

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <Bot className="h-6 w-6 text-blue-600" />
          <span className="text-lg font-semibold text-gray-900">Tastecraft</span>
          <span className="text-sm text-gray-400">品匠</span>
        </div>
        <div className="hidden items-center gap-8 text-sm text-gray-600 md:flex">
          <a href="#how-it-works" className="transition-colors hover:text-gray-900">工作原理</a>
          <a href="#taste" className="transition-colors hover:text-gray-900">Taste</a>
          <a href="#agents" className="transition-colors hover:text-gray-900">AI 团队</a>
          <a href="#platforms" className="transition-colors hover:text-gray-900">平台</a>
          <a href="#faq" className="transition-colors hover:text-gray-900">FAQ</a>
        </div>
        <Link
          to="/dashboard"
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          进入后台
        </Link>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden bg-gray-50 pb-16 pt-20 sm:pb-24 sm:pt-28">
      {/* 矩形框暗雕装饰 */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -right-16 -top-16 h-64 w-48 rotate-12 rounded-2xl border border-gray-200/40" />
        <div className="absolute -left-8 top-24 h-40 w-72 -rotate-6 rounded-2xl border border-gray-200/30" />
        <div className="absolute bottom-12 right-20 h-52 w-36 rotate-3 rounded-xl border border-blue-200/20" />
        <div className="absolute -bottom-8 left-1/4 h-32 w-56 -rotate-3 rounded-2xl border border-gray-200/25" />
        <div className="absolute right-1/3 top-8 h-28 w-44 rotate-6 rounded-xl border border-blue-100/30" />
        <div className="absolute bottom-1/3 left-12 h-24 w-24 rotate-12 rounded-lg border border-gray-200/20" />
        <div className="absolute -right-4 bottom-1/4 h-36 w-60 -rotate-12 rounded-2xl border border-gray-100/30" />
      </div>

      <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mx-auto max-w-3xl text-center">
          {/* Badge */}
          <div className="mb-6 inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
            <Sparkles className="h-3 w-3" />
            Powered by 6 AI Agents
          </div>

          <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
            告诉我你的赛道
            <br />
            <span className="text-blue-600">AI 团队替你做运营</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-500">
            注册时录入你的
            <span className="font-semibold text-gray-900"> taste</span>
            ，AI 自动追爆款、写内容、发 6 个平台。
            <br />
            越用越懂你的品味，每篇内容都是你的风格。
          </p>

          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              to="/onboarding"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white shadow-sm transition-all hover:bg-blue-700 hover:shadow-md"
            >
              录入我的 Taste
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-6 py-3 text-sm font-medium text-gray-700 transition-colors hover:border-gray-300 hover:text-gray-900"
            >
              看看怎么运作
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function HowItWorks() {
  const steps = [
    {
      num: '01',
      title: '录入你的 Taste',
      desc: '注册时选赛道、定客户、录入你的内容偏好和审美风格。这是 AI 理解你的起点。',
      icon: Palette,
      color: 'bg-purple-50 text-purple-600',
    },
    {
      num: '02',
      title: 'AI 团队接管',
      desc: '6 位 AI Agent 自动追踪赛道爆款，结合你的 taste 生成选题，创作、审核、适配、发布。',
      icon: Bot,
      color: 'bg-blue-50 text-blue-600',
    },
    {
      num: '03',
      title: '越用越懂你',
      desc: '每次反馈、每次修改、每条数据都在沉淀你的 taste profile。内容越来越像你亲手写的。',
      icon: TrendingUp,
      color: 'bg-green-50 text-green-600',
    },
  ]

  return (
    <section id="how-it-works" className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">How it works</p>
          <h2 className="mt-2 text-3xl font-bold text-gray-900">三步开始</h2>
          <p className="mx-auto mt-3 max-w-xl text-gray-500">
            不需要想选题、不需要写文案、不需要逐个平台发布
          </p>
        </div>

        <div className="mt-14 grid gap-8 md:grid-cols-3">
          {steps.map((step) => (
            <div key={step.num} className="relative rounded-xl border border-gray-200 bg-white p-6 transition-shadow hover:shadow-md">
              <span className="text-xs font-bold text-gray-300">{step.num}</span>
              <div className={`mt-3 inline-flex rounded-lg p-2.5 ${step.color}`}>
                <step.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-gray-900">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-500">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function TasteSection() {
  return (
    <section id="taste" className="bg-gray-50 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Your Taste, Your Content</p>
          <h2 className="mt-2 text-3xl font-bold text-gray-900">
            不是搬运爆款，是
            <span className="text-blue-600"> 你的 Taste</span>
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-gray-500">
            每个创作者都有独特的品味和审美。Tastecraft 不生产千篇一律的内容，
            而是持续学习你的 taste，用你的风格重新演绎赛道热点。
          </p>
        </div>

        {/* Taste 进化时间线 */}
        <div className="mx-auto mt-14 max-w-2xl">
          <div className="rounded-xl border border-gray-200 bg-white p-6 sm:p-8">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Taste Evolution</h3>
            <div className="mt-6 space-y-8">
              {[
                { day: 'Day 1', label: '通用风格', desc: 'AI 根据赛道爆款模式生成内容，风格偏通用', dot: 'bg-gray-300' },
                { day: 'Day 7', label: '学会你的偏好', desc: '你说"不喜欢这个标题"、"这段太营销了"，AI 全部记住', dot: 'bg-blue-400' },
                { day: 'Day 30', label: '完全是你的 Taste', desc: '每篇内容都像你亲手写的，品味和流量完美对齐', dot: 'bg-blue-600' },
              ].map((item, i) => (
                <div key={item.day} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className={`h-3 w-3 rounded-full ${item.dot}`} />
                    {i < 2 && <div className="w-px flex-1 bg-gray-200" />}
                  </div>
                  <div className="pb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-blue-600">{item.day}</span>
                      <span className="text-sm font-semibold text-gray-900">{item.label}</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Taste 信号来源 */}
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {tasteSignals.map((signal) => (
            <div key={signal.title} className="rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md">
              <div className={`inline-flex rounded-lg p-2.5 ${signal.color}`}>
                <signal.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-sm font-semibold text-gray-900">{signal.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-500">{signal.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function AgentsSection() {
  return (
    <section id="agents" className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Your AI Team</p>
          <h2 className="mt-2 text-3xl font-bold text-gray-900">6 位 AI Agent，各司其职</h2>
          <p className="mx-auto mt-3 max-w-xl text-gray-500">
            从选题研究到数据分析，每个环节都有专属 Agent 负责
          </p>
        </div>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <div key={agent.name} className="flex items-start gap-4 rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md">
              <div className={`flex-shrink-0 rounded-lg p-2.5 ${agent.color}`}>
                <agent.icon className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{agent.name}</h3>
                <p className="mt-1 text-sm text-gray-500">{agent.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* 工作流简图 */}
        <div className="mx-auto mt-12 max-w-3xl">
          <div className="flex flex-wrap items-center justify-center gap-2 text-sm">
            {['选题研究', '内容创作', '智能审核', '平台适配', '定时发布', '数据分析'].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <span className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 font-medium text-gray-700">
                  {step}
                </span>
                {i < 5 && <ArrowRight className="h-3.5 w-3.5 text-gray-300" />}
              </div>
            ))}
          </div>
          <p className="mt-4 text-center text-xs text-gray-400">
            全流程自动化，数据反哺下一轮选题
          </p>
        </div>
      </div>
    </section>
  )
}

function PlatformsSection() {
  return (
    <section id="platforms" className="bg-gray-50 py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">Platforms</p>
          <h2 className="mt-2 text-3xl font-bold text-gray-900">一份 Taste，六种表达</h2>
          <p className="mx-auto mt-3 max-w-xl text-gray-500">
            同一个选题，AI 自动适配每个平台的调性和格式
          </p>
        </div>

        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {platforms.map((p) => (
            <div key={p.name} className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 transition-shadow hover:shadow-md">
              <span className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gray-50">
                <p.Logo className="h-8 w-8" />
              </span>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{p.name}</h3>
                <p className="mt-0.5 text-sm text-gray-500">{p.style}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function StatsSection() {
  return (
    <section className="bg-white py-16">
      <div className="mx-auto grid max-w-4xl grid-cols-3 gap-8 px-4 text-center sm:px-6">
        {[
          { value: '80%', label: '运营时间节省' },
          { value: '6', label: '平台同步覆盖' },
          { value: '∞', label: 'Taste 持续进化' },
        ].map((stat) => (
          <div key={stat.label}>
            <p className="text-3xl font-bold text-gray-900 sm:text-4xl">{stat.value}</p>
            <p className="mt-1 text-sm text-gray-500">{stat.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function FAQSection() {
  return (
    <section id="faq" className="bg-gray-50 py-20 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-blue-600">FAQ</p>
          <h2 className="mt-2 text-3xl font-bold text-gray-900">常见问题</h2>
        </div>

        <div className="mt-12 space-y-4">
          {faqs.map((faq) => (
            <details key={faq.q} className="group rounded-xl border border-gray-200 bg-white">
              <summary className="flex cursor-pointer items-center justify-between px-5 py-4 text-sm font-semibold text-gray-900">
                {faq.q}
                <ChevronDown className="h-4 w-4 text-gray-400 transition-transform group-open:rotate-180" />
              </summary>
              <div className="border-t border-gray-100 px-5 py-4 text-sm leading-relaxed text-gray-500">
                {faq.a}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}

function CTASection() {
  return (
    <section className="bg-white py-20 sm:py-24">
      <div className="mx-auto max-w-3xl px-4 text-center sm:px-6">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
          <Zap className="h-3 w-3" />
          Ready to start
        </div>
        <h2 className="mt-4 text-3xl font-bold text-gray-900">
          录入你的 Taste
          <br />
          让 AI 替你运营
        </h2>
        <p className="mx-auto mt-4 max-w-lg text-gray-500">
          选赛道、定客户、录品味。剩下的交给你的 AI 团队。
        </p>
        <Link
          to="/onboarding"
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-8 py-3.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-blue-700 hover:shadow-md"
        >
          免费开始
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-gray-200 bg-white py-8">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-blue-600" />
          <span className="text-sm font-semibold text-gray-900">Tastecraft</span>
          <span className="text-xs text-gray-400">品匠</span>
        </div>
        <p className="text-xs text-gray-400">Powered by CrewAI + Claude</p>
      </div>
    </footer>
  )
}

/* ------------------------------------------------------------------ */
/*  Landing Page                                                       */
/* ------------------------------------------------------------------ */

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <NavBar />
      <Hero />
      <HowItWorks />
      <TasteSection />
      <AgentsSection />
      <PlatformsSection />
      <StatsSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </div>
  )
}
