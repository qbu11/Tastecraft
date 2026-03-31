import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

export function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return n.toString()
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    idle: 'text-gray-400',
    running: 'text-blue-500',
    waiting: 'text-yellow-500',
    error: 'text-red-500',
    completed: 'text-green-500',
    failed: 'text-red-500',
    pending: 'text-gray-400',
    success: 'text-green-500',
  }
  return colors[status] || 'text-gray-400'
}

export function getStatusBgColor(status: string): string {
  const colors: Record<string, string> = {
    idle: 'bg-gray-100 text-gray-600',
    running: 'bg-blue-100 text-blue-700',
    waiting: 'bg-yellow-100 text-yellow-700',
    error: 'bg-red-100 text-red-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    pending: 'bg-gray-100 text-gray-600',
  }
  return colors[status] || 'bg-gray-100 text-gray-600'
}
