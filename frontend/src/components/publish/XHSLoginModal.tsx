import { useState, useCallback } from 'react'
import { X, QrCode, Loader2, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'

interface XHSLoginModalProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

type LoginStep = 'idle' | 'loading' | 'qr_ready' | 'waiting' | 'success' | 'error'

/**
 * Modal for XHS (Xiaohongshu) login flow.
 *
 * MVP: Shows a QR code that the user scans with the XHS mobile app.
 * Phase 2: Will embed a noVNC iframe for remote browser streaming.
 */
export function XHSLoginModal({ open, onClose, onSuccess }: XHSLoginModalProps) {
  const [step, setStep] = useState<LoginStep>('idle')
  const [qrUrl, setQrUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const initLogin = useCallback(async () => {
    setStep('loading')
    setError(null)

    try {
      const { data } = await api.post<{
        qr_url: string | null
        ws_url: string | null
        message: string
      }>('/v1/publish/xhs/init-login')

      if (data.qr_url) {
        setQrUrl(data.qr_url)
        setStep('qr_ready')
      } else {
        setError(data.message || 'Could not generate QR code')
        setStep('error')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login initialization failed')
      setStep('error')
    }
  }, [])

  const checkLoginStatus = useCallback(async () => {
    setStep('waiting')

    try {
      const { data } = await api.get<{
        logged_in: boolean
        platform: string
        message: string
      }>('/v1/publish/xhs/session-status')

      if (data.logged_in) {
        setStep('success')
        setTimeout(() => {
          onSuccess?.()
          onClose()
        }, 1500)
      } else {
        setError('Not logged in yet. Please scan the QR code and try again.')
        setStep('qr_ready')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Status check failed')
      setStep('error')
    }
  }, [onClose, onSuccess])

  const handleClose = () => {
    setStep('idle')
    setQrUrl(null)
    setError(null)
    onClose()
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div className="relative w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        {/* Close button */}
        <button
          onClick={handleClose}
          className="absolute right-4 top-4 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close"
        >
          <X size={20} />
        </button>

        {/* Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
            <QrCode className="text-red-500" size={24} />
          </div>
          <h2 className="text-lg font-semibold text-gray-900">
            {'\u8FDE\u63A5\u5C0F\u7EA2\u4E66'}
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            {'\u626B\u7801\u767B\u5F55\u540E\u53EF\u81EA\u52A8\u53D1\u5E03\u5185\u5BB9'}
          </p>
        </div>

        {/* Body */}
        <div className="flex flex-col items-center gap-4">
          {/* Idle state */}
          {step === 'idle' && (
            <button
              onClick={initLogin}
              className={cn(
                'w-full rounded-lg px-4 py-3 text-sm font-medium text-white transition-colors',
                'bg-red-500 hover:bg-red-600 active:bg-red-700',
              )}
            >
              {'\u5F00\u59CB\u8FDE\u63A5'}
            </button>
          )}

          {/* Loading */}
          {step === 'loading' && (
            <div className="flex items-center gap-2 py-8 text-gray-500">
              <Loader2 className="animate-spin" size={20} />
              <span className="text-sm">{'\u6B63\u5728\u521D\u59CB\u5316...'}</span>
            </div>
          )}

          {/* QR code ready */}
          {step === 'qr_ready' && qrUrl && (
            <>
              <div className="rounded-lg border border-gray-200 bg-white p-3">
                {qrUrl.startsWith('data:') ? (
                  <img src={qrUrl} alt="XHS Login QR" className="h-48 w-48" />
                ) : (
                  <img src={qrUrl} alt="XHS Login QR" className="h-48 w-48 object-contain" />
                )}
              </div>
              <p className="text-center text-xs text-gray-400">
                {'\u6253\u5F00\u5C0F\u7EA2\u4E66 App \u2192 \u626B\u4E00\u626B'}
              </p>
              <button
                onClick={checkLoginStatus}
                className={cn(
                  'w-full rounded-lg px-4 py-2.5 text-sm font-medium transition-colors',
                  'bg-gray-100 text-gray-700 hover:bg-gray-200',
                )}
              >
                {'\u5DF2\u626B\u7801\uFF0C\u68C0\u67E5\u767B\u5F55\u72B6\u6001'}
              </button>
            </>
          )}

          {/* Waiting for scan verification */}
          {step === 'waiting' && (
            <div className="flex items-center gap-2 py-8 text-gray-500">
              <Loader2 className="animate-spin" size={20} />
              <span className="text-sm">{'\u6B63\u5728\u68C0\u67E5\u767B\u5F55\u72B6\u6001...'}</span>
            </div>
          )}

          {/* Success */}
          {step === 'success' && (
            <div className="flex flex-col items-center gap-2 py-8">
              <CheckCircle2 className="text-green-500" size={40} />
              <p className="text-sm font-medium text-green-700">
                {'\u5C0F\u7EA2\u4E66\u8D26\u53F7\u5DF2\u8FDE\u63A5'}
              </p>
            </div>
          )}

          {/* Error */}
          {error && step === 'error' && (
            <div className="w-full rounded-lg bg-red-50 p-3 text-center">
              <p className="text-sm text-red-600">{error}</p>
              <button
                onClick={initLogin}
                className="mt-2 text-sm font-medium text-red-500 hover:text-red-700"
              >
                {'\u91CD\u8BD5'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
