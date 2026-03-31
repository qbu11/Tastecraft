import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Bot,
  ArrowRight,
  ArrowLeft,
  Check,
  Palette,
  Target,
  MessageSquare,
  Share2,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  步骤数据                                                           */
/* ------------------------------------------------------------------ */

const niches = [
  'AI / 科技', '创业 / 商业', '职场 / 成长', '教育 / 学习',
  '健康 / 健身', '美食 / 烹饪', '旅行 / 生活', '时尚 / 美妆',
  '金融 / 理财', '设计 / 创意', '游戏 / 电竞', '母婴 / 育儿',
]

const audiences = [
  '大学生 / 应届生', '职场新人 (1-3年)', '中层管理者', '创业者 / 老板',
  '自由职业者', '宝妈 / 家庭主妇', '技术开发者', '设计师 / 创意人',
]

const tones = [
  { label: '专业严谨', desc: '数据驱动，逻辑清晰，有理有据' },
  { label: '轻松幽默', desc: '段子手风格，有梗有料' },
  { label: '温暖治愈', desc: '共情力强，像朋友聊天' },
  { label: '犀利毒舌', desc: '观点鲜明，敢说真话' },
  { label: '知识科普', desc: '深入浅出，把复杂的事说简单' },
  { label: '故事叙事', desc: '善于讲故事，代入感强' },
]

const platformOptions = [
  { id: 'xiaohongshu', name: '小红书', desc: '种草分享' },
  { id: 'wechat', name: '微信公众号', desc: '深度长文' },
  { id: 'weibo', name: '微博', desc: '热点快讯' },
  { id: 'zhihu', name: '知乎', desc: '专业问答' },
  { id: 'douyin', name: '抖音', desc: '短视频脚本' },
  { id: 'bilibili', name: 'B站', desc: '知识视频' },
]

const steps = [
  { icon: Target, label: '选赛道' },
  { icon: Palette, label: '定客户' },
  { icon: MessageSquare, label: '录品味' },
  { icon: Share2, label: '选平台' },
]

/* ------------------------------------------------------------------ */
/*  组件                                                               */
/* ------------------------------------------------------------------ */

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {steps.map((step, i) => (
        <div key={step.label} className="flex items-center gap-2">
          <div
            className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition-colors ${
              i < current
                ? 'bg-blue-600 text-white'
                : i === current
                  ? 'bg-blue-100 text-blue-700 ring-2 ring-blue-600'
                  : 'bg-gray-100 text-gray-400'
            }`}
          >
            {i < current ? <Check className="h-4 w-4" /> : <step.icon className="h-4 w-4" />}
          </div>
          <span
            className={`hidden text-xs font-medium sm:block ${
              i <= current ? 'text-gray-900' : 'text-gray-400'
            }`}
          >
            {step.label}
          </span>
          {i < steps.length - 1 && (
            <div className={`h-px w-8 ${i < current ? 'bg-blue-600' : 'bg-gray-200'}`} />
          )}
        </div>
      ))}
    </div>
  )
}

function SelectableGrid({
  items,
  selected,
  onToggle,
  multi = false,
}: {
  items: string[]
  selected: string[]
  onToggle: (item: string) => void
  multi?: boolean
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {items.map((item) => {
        const isSelected = selected.includes(item)
        return (
          <button
            key={item}
            type="button"
            onClick={() => onToggle(item)}
            className={`rounded-xl border px-4 py-3 text-sm font-medium transition-all ${
              isSelected
                ? 'border-blue-600 bg-blue-50 text-blue-700 shadow-sm'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300 hover:shadow-sm'
            }`}
          >
            {multi && isSelected && <Check className="mb-1 inline h-3.5 w-3.5" />} {item}
          </button>
        )
      })}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Onboarding Page                                                    */
/* ------------------------------------------------------------------ */

export function OnboardingPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [niche, setNiche] = useState<string[]>([])
  const [audience, setAudience] = useState<string[]>([])
  const [tone, setTone] = useState<string[]>([])
  const [selectedPlatforms, setSelectedPlatforms] = useState<string[]>([])

  const toggleItem = (list: string[], setList: (v: string[]) => void, item: string, multi = true) => {
    if (multi) {
      setList(list.includes(item) ? list.filter((i) => i !== item) : [...list, item])
    } else {
      setList([item])
    }
  }

  const canNext =
    (step === 0 && niche.length > 0) ||
    (step === 1 && audience.length > 0) ||
    (step === 2 && tone.length > 0) ||
    (step === 3 && selectedPlatforms.length > 0)

  const handleFinish = () => {
    // TODO: 调用后端 API 保存 taste profile
    navigate('/dashboard')
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      {/* Nav */}
      <nav className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-blue-600" />
            <span className="text-sm font-semibold text-gray-900">Tastecraft</span>
          </Link>
          <span className="text-xs text-gray-400">
            {step + 1} / {steps.length}
          </span>
        </div>
      </nav>

      {/* Content */}
      <div className="flex flex-1 flex-col items-center px-4 py-10">
        <div className="w-full max-w-2xl">
          <StepIndicator current={step} />

          <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
            {/* Step 0: 赛道 */}
            {step === 0 && (
              <>
                <h2 className="text-xl font-bold text-gray-900">选择你的赛道</h2>
                <p className="mt-2 text-sm text-gray-500">
                  AI 会追踪这些赛道的爆款趋势，为你生成选题。可多选。
                </p>
                <div className="mt-6">
                  <SelectableGrid
                    items={niches}
                    selected={niche}
                    onToggle={(item) => toggleItem(niche, setNiche, item)}
                    multi
                  />
                </div>
              </>
            )}

            {/* Step 1: 目标客户 */}
            {step === 1 && (
              <>
                <h2 className="text-xl font-bold text-gray-900">你的目标读者是谁？</h2>
                <p className="mt-2 text-sm text-gray-500">
                  了解你的受众，AI 会调整内容的语言风格和深度。可多选。
                </p>
                <div className="mt-6">
                  <SelectableGrid
                    items={audiences}
                    selected={audience}
                    onToggle={(item) => toggleItem(audience, setAudience, item)}
                    multi
                  />
                </div>
              </>
            )}

            {/* Step 2: 内容偏好 / Taste */}
            {step === 2 && (
              <>
                <h2 className="text-xl font-bold text-gray-900">
                  录入你的 <span className="text-blue-600">Taste</span>
                </h2>
                <p className="mt-2 text-sm text-gray-500">
                  选择你偏好的内容风格，这是 AI 理解你品味的起点。可多选。
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {tones.map((t) => {
                    const isSelected = tone.includes(t.label)
                    return (
                      <button
                        key={t.label}
                        type="button"
                        onClick={() => toggleItem(tone, setTone, t.label)}
                        className={`rounded-xl border p-4 text-left transition-all ${
                          isSelected
                            ? 'border-blue-600 bg-blue-50 shadow-sm'
                            : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                        }`}
                      >
                        <p className={`text-sm font-semibold ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                          {isSelected && <Check className="mr-1 inline h-3.5 w-3.5" />}
                          {t.label}
                        </p>
                        <p className="mt-1 text-xs text-gray-500">{t.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </>
            )}

            {/* Step 3: 平台选择 */}
            {step === 3 && (
              <>
                <h2 className="text-xl font-bold text-gray-900">选择发布平台</h2>
                <p className="mt-2 text-sm text-gray-500">
                  AI 会自动适配每个平台的调性和格式。可多选。
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {platformOptions.map((p) => {
                    const isSelected = selectedPlatforms.includes(p.id)
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => toggleItem(selectedPlatforms, setSelectedPlatforms, p.id)}
                        className={`flex items-center gap-3 rounded-xl border p-4 transition-all ${
                          isSelected
                            ? 'border-blue-600 bg-blue-50 shadow-sm'
                            : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                        }`}
                      >
                        <div
                          className={`flex h-10 w-10 items-center justify-center rounded-lg text-sm font-bold ${
                            isSelected ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500'
                          }`}
                        >
                          {p.name[0]}
                        </div>
                        <div className="text-left">
                          <p className={`text-sm font-semibold ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                            {p.name}
                          </p>
                          <p className="text-xs text-gray-500">{p.desc}</p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </>
            )}
          </div>

          {/* Navigation */}
          <div className="mt-6 flex items-center justify-between">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowLeft className="h-4 w-4" />
              上一步
            </button>

            {step < steps.length - 1 ? (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                disabled={!canNext}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                下一步
                <ArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleFinish}
                disabled={!canNext}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                开始使用
                <Check className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
