import { BarChart3 } from 'lucide-react'

function PlaceholderChart({
  label,
  height = 160,
}: {
  label: string
  height?: number
}) {
  return (
    <div
      className="flex items-end justify-between rounded-xl border border-stone-200 bg-white px-5 pb-4 pt-5"
      style={{ height }}
    >
      <div className="flex flex-col justify-between h-full">
        <p className="text-sm font-medium text-stone-700">{label}</p>
        <p className="text-xs text-stone-400">暂无数据</p>
      </div>
      {/* Decorative bars */}
      <div className="flex items-end gap-1.5">
        {[40, 65, 30, 80, 55, 70, 45].map((h, i) => (
          <div
            key={i}
            className="w-4 rounded-t bg-stone-100"
            style={{ height: `${h}%` }}
          />
        ))}
      </div>
    </div>
  )
}

export function Analytics() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight text-stone-900">
        数据分析
      </h1>

      {/* Charts grid — asymmetric */}
      <div className="grid grid-cols-[1.5fr_1fr] gap-4">
        <PlaceholderChart label="阅读趋势" height={200} />
        <PlaceholderChart label="平台分布" height={200} />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <PlaceholderChart label="互动率" />
        <PlaceholderChart label="品味匹配度" />
        <PlaceholderChart label="内容评分" />
      </div>

      {/* Empty state */}
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-stone-100">
          <BarChart3 size={24} className="text-stone-400" />
        </div>
        <p className="mt-4 text-sm font-medium text-stone-700">
          发布内容后查看数据
        </p>
        <p className="mt-1 max-w-xs text-xs text-stone-400">
          系统会在发布后 24h、72h、7d 自动采集数据并生成分析报告
        </p>
      </div>
    </div>
  )
}
