import { motion } from 'framer-motion'

interface Step {
  number: string
  title: string
  description: string
  icon: React.ReactNode
}

/* Minimal SVG icons rendered inline — no external assets */
function ChatIcon() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      className="text-[var(--color-accent)]"
    >
      <rect
        x="4"
        y="6"
        width="28"
        height="20"
        rx="4"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="M12 26l-4 6v-6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      <circle cx="13" cy="16" r="1.5" fill="currentColor" />
      <circle cx="18" cy="16" r="1.5" fill="currentColor" />
      <circle cx="23" cy="16" r="1.5" fill="currentColor" />
    </svg>
  )
}

function CoCreateIcon() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      className="text-[var(--color-accent)]"
    >
      <path
        d="M8 28V12a4 4 0 014-4h12a4 4 0 014 4v10a4 4 0 01-4 4H12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M14 16h8M14 20h5"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M26 18l4-2v10l-4-2"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
      />
    </svg>
  )
}

function EvolveIcon() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 36 36"
      fill="none"
      className="text-[var(--color-accent)]"
    >
      <path
        d="M18 6v24"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path
        d="M10 22l8 8 8-8"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="18" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
      <path
        d="M6 18c4-6 8-6 12 0s8 6 12 0"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.4"
      />
    </svg>
  )
}

const steps: Step[] = [
  {
    number: '01',
    title: '对话',
    description: '5 分钟自然对话，系统捕捉你的表达偏好、价值观和审美取向',
    icon: <ChatIcon />,
  },
  {
    number: '02',
    title: '共创',
    description: 'AI 起草初稿，你调整润色。每次互动都在教 AI 更像你',
    icon: <CoCreateIcon />,
  },
  {
    number: '03',
    title: '进化',
    description: '品味画像持续迭代，越用越懂你。最终 AI 输出≈你亲手写的',
    icon: <EvolveIcon />,
  },
]

const stepVariant = {
  hidden: { opacity: 0, y: 32 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' as const },
  },
}

export function HowItWorks() {
  return (
    <div className="relative mx-auto max-w-2xl">
      {/* Connecting line */}
      <div className="absolute left-1/2 top-0 hidden h-full w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-stone-200 to-transparent md:block" />

      <div className="space-y-16 md:space-y-20">
        {steps.map((step, i) => {
          const isEven = i % 2 === 1
          return (
            <motion.div
              key={step.number}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: '-60px' }}
              variants={stepVariant}
              transition={{ delay: i * 0.15 }}
              className={`relative flex flex-col items-start gap-5 md:flex-row md:items-center md:gap-10 ${
                isEven ? 'md:flex-row-reverse md:text-right' : ''
              }`}
            >
              {/* Number dot on the line */}
              <div className="absolute left-1/2 top-0 z-10 hidden -translate-x-1/2 md:block">
                <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-[var(--color-accent)]/30 bg-white text-xs font-bold text-[var(--color-accent)]">
                  {step.number}
                </div>
              </div>

              {/* Content card */}
              <div
                className={`w-full rounded-2xl border border-stone-200/60 bg-white/80 p-6 backdrop-blur-sm md:w-[calc(50%-3rem)] ${
                  isEven ? 'md:mr-auto' : 'md:ml-auto'
                }`}
              >
                <div className="mb-3 flex items-center gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--color-accent-muted)] md:hidden">
                    <span className="text-xs font-bold text-[var(--color-accent)]">
                      {step.number}
                    </span>
                  </span>
                  <div className="hidden md:block">{step.icon}</div>
                  <h3 className="text-lg font-semibold text-stone-800">
                    {step.title}
                  </h3>
                </div>
                <p className="text-sm leading-relaxed text-stone-600">
                  {step.description}
                </p>
              </div>

              {/* Spacer for the other side */}
              <div className="hidden w-[calc(50%-3rem)] md:block" />
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
