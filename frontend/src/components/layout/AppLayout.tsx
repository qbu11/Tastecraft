import { Outlet } from 'react-router-dom'
import { motion, AnimatePresence, type Variants } from 'framer-motion'
import { Sidebar } from './Sidebar'
import { MobileNav } from './MobileNav'
import { NotificationBell } from '../notifications/NotificationBell'

const pageVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.25, ease: [0.25, 0.1, 0.25, 1] } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
}

export function AppLayout() {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[260px_1fr]">
      {/* Sidebar — hidden on mobile */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      <div className="flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-stone-100 bg-white px-4 md:justify-end md:px-6">
          <span className="text-base font-semibold text-stone-800 md:hidden">TasteCraft</span>
          <NotificationBell />
        </header>

        <main className="flex-1 overflow-y-auto bg-stone-50 px-4 py-6 pb-20 md:px-10 md:py-8 md:pb-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="mx-auto max-w-5xl"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Bottom tab nav — mobile only */}
      <MobileNav />
    </div>
  )
}
