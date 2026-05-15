import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Download, RefreshCw, ChevronLeft, ChevronRight, X, Maximize2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SlideInfo, CardStyle } from '@/services/visual'

interface CarouselPreviewProps {
  slides: SlideInfo[]
  style: CardStyle
  onRegenerate?: (index: number) => void
  onDownloadAll?: () => void
  className?: string
}

export function CarouselPreview({
  slides,
  style: _style,
  onRegenerate,
  onDownloadAll,
  className,
}: CarouselPreviewProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null)
  const [scrollOffset, setScrollOffset] = useState(0)

  const scrollLeft = useCallback(() => {
    setScrollOffset((prev) => Math.max(prev - 280, 0))
  }, [])

  const scrollRight = useCallback(() => {
    const maxOffset = Math.max((slides.length - 3) * 280, 0)
    setScrollOffset((prev) => Math.min(prev + 280, maxOffset))
  }, [slides.length])

  if (slides.length === 0) {
    return (
      <div
        className={cn(
          'flex h-64 items-center justify-center rounded-xl border-2 border-dashed border-stone-300 bg-stone-50 text-stone-400',
          className,
        )}
      >
        <p className="text-sm">生成轮播图后在此预览</p>
      </div>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-stone-700">
          轮播图预览
          <span className="ml-2 text-xs font-normal text-stone-400">
            {slides.length} 页
          </span>
        </h3>
        {onDownloadAll && (
          <button
            onClick={onDownloadAll}
            className="flex items-center gap-1.5 rounded-lg bg-stone-100 px-3 py-1.5 text-xs font-medium text-stone-600 transition-colors hover:bg-stone-200"
          >
            <Download size={14} />
            全部下载
          </button>
        )}
      </div>

      {/* Scrollable card strip */}
      <div className="relative">
        {/* Left arrow */}
        {scrollOffset > 0 && (
          <button
            onClick={scrollLeft}
            className="absolute -left-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white shadow-md transition-colors hover:bg-stone-50"
          >
            <ChevronLeft size={16} />
          </button>
        )}

        {/* Cards container */}
        <div className="overflow-hidden rounded-xl">
          <motion.div
            className="flex gap-4"
            animate={{ x: -scrollOffset }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            {slides.map((slide) => (
              <div
                key={slide.index}
                className="group relative flex-shrink-0"
                style={{ width: 270 }}
              >
                {/* Thumbnail — 1/4 size of 1080x1440 = 270x360 */}
                <div className="relative overflow-hidden rounded-lg shadow-sm transition-shadow group-hover:shadow-md">
                  <img
                    src={slide.image_url}
                    alt={`Slide ${slide.index + 1}`}
                    className="h-[360px] w-[270px] object-cover"
                  />

                  {/* Overlay actions */}
                  <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/0 opacity-0 transition-all group-hover:bg-black/30 group-hover:opacity-100">
                    <button
                      onClick={() => setExpandedIndex(slide.index)}
                      className="flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-stone-700 transition-colors hover:bg-white"
                      title="放大查看"
                    >
                      <Maximize2 size={16} />
                    </button>
                    {onRegenerate && (
                      <button
                        onClick={() => onRegenerate(slide.index)}
                        className="flex h-9 w-9 items-center justify-center rounded-full bg-white/90 text-stone-700 transition-colors hover:bg-white"
                        title="重新生成"
                      >
                        <RefreshCw size={16} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Slide label */}
                <p className="mt-2 truncate text-center text-xs text-stone-400">
                  {slide.index === 0
                    ? '封面'
                    : slide.index === slides.length - 1
                      ? 'CTA'
                      : `第 ${slide.index} 页`}
                </p>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right arrow */}
        {scrollOffset < (slides.length - 3) * 280 && slides.length > 3 && (
          <button
            onClick={scrollRight}
            className="absolute -right-3 top-1/2 z-10 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full bg-white shadow-md transition-colors hover:bg-stone-50"
          >
            <ChevronRight size={16} />
          </button>
        )}
      </div>

      {/* Expanded overlay */}
      <AnimatePresence>
        {expandedIndex !== null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setExpandedIndex(null)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="relative max-h-[90vh] max-w-[90vw]"
              onClick={(e) => e.stopPropagation()}
            >
              <img
                src={slides[expandedIndex]?.image_url}
                alt={`Slide ${expandedIndex + 1} expanded`}
                className="max-h-[85vh] rounded-lg shadow-2xl"
              />
              <button
                onClick={() => setExpandedIndex(null)}
                className="absolute -right-3 -top-3 flex h-8 w-8 items-center justify-center rounded-full bg-white shadow-md transition-colors hover:bg-stone-100"
              >
                <X size={16} />
              </button>

              {/* Navigation in expanded view */}
              <div className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-3">
                <button
                  onClick={() =>
                    setExpandedIndex((prev) =>
                      prev !== null && prev > 0 ? prev - 1 : prev,
                    )
                  }
                  disabled={expandedIndex === 0}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-white/90 shadow disabled:opacity-40"
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="rounded-full bg-white/90 px-3 py-1 text-sm font-medium text-stone-700 shadow">
                  {expandedIndex + 1} / {slides.length}
                </span>
                <button
                  onClick={() =>
                    setExpandedIndex((prev) =>
                      prev !== null && prev < slides.length - 1
                        ? prev + 1
                        : prev,
                    )
                  }
                  disabled={expandedIndex === slides.length - 1}
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-white/90 shadow disabled:opacity-40"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
