import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

interface Tier {
  name: string
  price: string
  period: string
  features: string[]
  cta: string
  href: string
  recommended?: boolean
  comingSoon?: boolean
}

const tiers: Tier[] = [
  {
    name: '体验版',
    price: '免费',
    period: '',
    features: [
      '每月 10 篇内容生成',
      '基础风格分析',
      '首周可发布体验',
      '单项目',
    ],
    cta: '开始体验',
    href: '/login',
  },
  {
    name: '基础版',
    price: '¥49',
    period: '/月',
    features: [
      '无限内容生成',
      '1 个平台发布',
      '品味持续学习',
      '内容日历',
      '基础数据分析',
    ],
    cta: '立即订阅',
    href: '/login',
    recommended: true,
  },
  {
    name: '专业版',
    price: '¥149',
    period: '/月',
    features: [
      '全部基础版功能',
      '6 平台同步发布',
      '竞品监控',
      '高级数据分析',
      '多项目管理',
      '优先客服',
    ],
    cta: '敬请期待',
    href: '#',
    comingSoon: true,
  },
]

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.5, ease: 'easeOut' as const },
  }),
}

export function PricingCards() {
  return (
    <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-3 md:items-end">
      {tiers.map((tier, i) => (
        <motion.div
          key={tier.name}
          custom={i}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-40px' }}
          variants={cardVariants}
          className={`relative rounded-2xl border p-6 transition-shadow ${
            tier.recommended
              ? 'z-10 border-[var(--color-accent)]/30 bg-white shadow-lg md:-mb-4 md:p-8'
              : 'border-stone-200/60 bg-white/70'
          } ${tier.comingSoon ? 'opacity-75' : ''}`}
        >
          {tier.recommended && (
            <span className="absolute -top-3 left-6 rounded-full bg-[var(--color-accent)] px-3 py-0.5 text-[11px] font-semibold text-white">
              推荐
            </span>
          )}
          {tier.comingSoon && (
            <span className="absolute -top-3 left-6 rounded-full bg-stone-400 px-3 py-0.5 text-[11px] font-semibold text-white">
              即将上线
            </span>
          )}

          <h3 className="text-lg font-semibold text-stone-800">
            {tier.name}
          </h3>
          <div className="mt-3 flex items-baseline gap-0.5">
            <span
              className={`text-3xl font-bold ${tier.recommended ? 'text-[var(--color-accent)]' : 'text-stone-900'}`}
            >
              {tier.price}
            </span>
            {tier.period && (
              <span className="text-sm text-stone-500">{tier.period}</span>
            )}
          </div>

          <ul className="mt-5 space-y-2.5">
            {tier.features.map((feature) => (
              <li
                key={feature}
                className="flex items-start gap-2 text-sm text-stone-600"
              >
                <span className="mt-0.5 block h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-accent)]/60" />
                {feature}
              </li>
            ))}
          </ul>

          <Link
            to={tier.href}
            className={`mt-6 block rounded-lg py-2.5 text-center text-sm font-medium transition-opacity ${
              tier.recommended
                ? 'bg-[var(--color-accent)] text-white hover:opacity-90'
                : tier.comingSoon
                  ? 'pointer-events-none cursor-not-allowed bg-stone-100 text-stone-400'
                  : 'bg-stone-900 text-white hover:bg-stone-800'
            }`}
          >
            {tier.cta}
          </Link>
        </motion.div>
      ))}
    </div>
  )
}
