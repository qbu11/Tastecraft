import { create } from 'zustand'

interface EditSnapshot {
  timestamp: number
  content: string
  source: 'user' | 'ai'
}

interface ContentState {
  currentContent: string
  currentTitle: string
  editHistory: EditSnapshot[]
  setContent: (content: string, source?: 'user' | 'ai') => void
  setTitle: (title: string) => void
  captureEdit: () => void
  resetContent: () => void
}

export const useContentStore = create<ContentState>()((set, get) => ({
  currentContent: '',
  currentTitle: '',
  editHistory: [],

  setContent: (content, source = 'user') =>
    set((state) => ({
      currentContent: content,
      editHistory: [
        ...state.editHistory,
        { timestamp: Date.now(), content, source },
      ],
    })),

  setTitle: (title) => set({ currentTitle: title }),

  captureEdit: () => {
    const { currentContent, editHistory } = get()
    set({
      editHistory: [
        ...editHistory,
        { timestamp: Date.now(), content: currentContent, source: 'user' },
      ],
    })
  },

  resetContent: () =>
    set({ currentContent: '', currentTitle: '', editHistory: [] }),
}))
