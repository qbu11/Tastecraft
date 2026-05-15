import { useCallback, useRef, useState, useEffect } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import Highlight from '@tiptap/extension-highlight'
import CharacterCount from '@tiptap/extension-character-count'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { FloatingToolbar } from './FloatingToolbar'

interface TiptapEditorProps {
  content: string
  onChange: (html: string, text: string) => void
  onRewriteRequest: (text: string, action: string) => void
  isGenerating?: boolean
  className?: string
}

export function TiptapEditor({
  content,
  onChange,
  onRewriteRequest,
  isGenerating = false,
  className,
}: TiptapEditorProps) {
  const hoveredParagraph = useRef<HTMLElement | null>(null)
  const editorContainerRef = useRef<HTMLDivElement>(null)
  const [showToolbar, setShowToolbar] = useState(false)
  const [toolbarPos, setToolbarPos] = useState({ top: 0, left: 0 })

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: '开始创作...',
      }),
      Highlight.configure({
        multicolor: true,
      }),
      CharacterCount,
    ],
    content,
    editorProps: {
      attributes: {
        class: cn(
          'prose prose-stone max-w-none focus:outline-none',
          'prose-p:my-3 prose-headings:mb-3 prose-headings:mt-6',
          'min-h-[400px]',
        ),
        style: 'font-family: "Outfit", sans-serif; font-size: 18px; line-height: 1.7;',
      },
    },
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getHTML(), ed.getText())
    },
    onSelectionUpdate: ({ editor: ed }) => {
      const { from, to } = ed.state.selection
      if (from === to) {
        setShowToolbar(false)
        return
      }
      // Get selection coordinates for positioning
      const coords = ed.view.coordsAtPos(from)
      const container = editorContainerRef.current
      if (container) {
        const rect = container.getBoundingClientRect()
        setToolbarPos({
          top: coords.top - rect.top - 48,
          left: coords.left - rect.left,
        })
      }
      setShowToolbar(true)
    },
  })

  // Hide toolbar on click outside or blur
  useEffect(() => {
    const handleMouseDown = () => {
      // Small delay to allow selection changes to process first
      setTimeout(() => {
        if (editor && editor.state.selection.from === editor.state.selection.to) {
          setShowToolbar(false)
        }
      }, 100)
    }
    document.addEventListener('mousedown', handleMouseDown)
    return () => document.removeEventListener('mousedown', handleMouseDown)
  }, [editor])

  const handleParagraphHover = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement
    const paragraph = target.closest('p, h1, h2, h3, blockquote, li')
    if (paragraph instanceof HTMLElement) {
      hoveredParagraph.current = paragraph
    }
  }, [])

  const handleRegenerateParagraph = useCallback(() => {
    if (!hoveredParagraph.current) return
    const text = hoveredParagraph.current.textContent ?? ''
    if (text.trim()) {
      onRewriteRequest(text, '重写')
    }
  }, [onRewriteRequest])

  if (!editor) return null

  const charCount = editor.storage.characterCount.characters()
  const wordCount = editor.storage.characterCount.words()

  return (
    <div className={cn('relative flex flex-col', className)}>
      {/* Editor Area */}
      <div
        ref={editorContainerRef}
        className="relative flex-1 overflow-y-auto px-8 py-6"
        onMouseMove={handleParagraphHover}
      >
        {/* Floating Toolbar — positioned based on text selection */}
        <AnimatePresence>
          {showToolbar && (
            <div
              className="absolute z-50"
              style={{ top: toolbarPos.top, left: toolbarPos.left }}
            >
              <FloatingToolbar
                onAction={(action) => {
                  if (!editor) return
                  const { from, to } = editor.state.selection
                  const selectedText = editor.state.doc.textBetween(from, to, ' ')
                  if (selectedText.trim()) {
                    onRewriteRequest(selectedText, action)
                    setShowToolbar(false)
                  }
                }}
              />
            </div>
          )}
        </AnimatePresence>

        <EditorContent editor={editor} />

        {/* Paragraph regenerate button (appears on hover via CSS) */}
        <button
          onClick={handleRegenerateParagraph}
          className={cn(
            'absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-1.5',
            'bg-stone-100 text-stone-400 opacity-0 transition-all',
            'hover:bg-stone-200 hover:text-stone-600',
            'group-hover/para:opacity-100',
            'hidden',
          )}
          title="重新生成此段落"
        >
          <RotateCw size={14} />
        </button>

        {/* Generating indicator */}
        <AnimatePresence>
          {isGenerating && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="mt-4 flex items-center gap-2 text-sm text-stone-400"
            >
              <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-[#c87b5a]" />
              AI 正在生成中...
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Character Count Footer */}
      <div className="flex items-center gap-4 border-t border-stone-100 px-8 py-2 text-xs text-stone-400">
        <span>{charCount} 字符</span>
        <span>{wordCount} 词</span>
        <span className="ml-auto">自动保存</span>
      </div>
    </div>
  )
}
