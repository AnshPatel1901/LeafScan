/**
 * Client-side logging utility for tracking user actions, API calls, and errors.
 * Logs are written to browser console with timestamps and severity levels.
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

interface LogEntry {
  timestamp: string
  level: LogLevel
  category: string
  message: string
  data?: unknown
}

const LOGS: LogEntry[] = []
const MAX_LOGS = 500

function formatTimestamp(date: Date): string {
  return date.toISOString()
}

function addLog(level: LogLevel, category: string, message: string, data?: unknown): void {
  const entry: LogEntry = {
    timestamp: formatTimestamp(new Date()),
    level,
    category,
    message,
    data,
  }

  LOGS.push(entry)
  if (LOGS.length > MAX_LOGS) {
    LOGS.shift()
  }

  const prefix = `[${entry.timestamp}] [${entry.category}]`
  const logFn =
    level === 'error' ? console.error :
    level === 'warn' ? console.warn :
    level === 'info' ? console.info :
    console.log

  if (data !== undefined) {
    logFn(prefix, `${level.toUpperCase()}: ${message}`, data)
  } else {
    logFn(prefix, `${level.toUpperCase()}: ${message}`)
  }
}

export const logger = {
  debug: (category: string, message: string, data?: unknown) =>
    addLog('debug', category, message, data),

  info: (category: string, message: string, data?: unknown) =>
    addLog('info', category, message, data),

  warn: (category: string, message: string, data?: unknown) =>
    addLog('warn', category, message, data),

  error: (category: string, message: string, error?: unknown) =>
    addLog('error', category, message, error),

  /**
   * Retrieve all logs (useful for debugging or sending to backend).
   */
  getLogs: (): LogEntry[] => [...LOGS],

  /**
   * Clear all stored logs.
   */
  clearLogs: (): void => {
    LOGS.splice(0, LOGS.length)
  },

  /**
   * Export logs as JSON string.
   */
  exportLogs: (): string => JSON.stringify(LOGS, null, 2),
}

// Make logger available globally for console debugging
if (typeof window !== 'undefined') {
  ;(window as any).__logger = logger
}
