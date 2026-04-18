import axios, { AxiosError } from 'axios'
import type { UserProfile, TokenPair, PredictResponse, HistoryItem, HistoryResponse } from '@/types'
import Cookies from 'js-cookie'
import { logger } from './logger'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

logger.info('API', `Initialized with base URL: ${BASE}`)

export const api = axios.create({
  baseURL: BASE,
  timeout: 60_000,
})

// ── Request interceptor: attach Bearer token ──────────────────────────────────
api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token')
  logger.debug('API.Request', `${config.method?.toUpperCase()} ${config.url}`, {
    hasToken: !!token,
    tokenLength: token?.length ?? 0,
  })
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── Response interceptor: handle 401 globally ────────────────────────────────
api.interceptors.response.use(
  (res) => {
    logger.info('API.Response', `${res.config.method?.toUpperCase()} ${res.config.url}`, {
      status: res.status,
      statusText: res.statusText,
    })
    return res
  },
  async (err: AxiosError) => {
    logger.error('API.Error', `${err.config?.method?.toUpperCase()} ${err.config?.url}`, {
      status: err.response?.status,
      message: err.message,
      code: err.code,
    })

    const original = err.config as typeof err.config & { _retry?: boolean }
    if (err.response?.status === 401 && !original._retry) {
      logger.warn('API.Auth', 'Access token expired, attempting refresh')
      original._retry = true
      const refresh = Cookies.get('refresh_token')
      if (refresh) {
        try {
          logger.info('API.Auth', 'Refreshing access token')
          const { data } = await axios.post(`${BASE}/auth/refresh-token`, {
            refresh_token: refresh,
          })
          const newToken = data.data.access_token
          Cookies.set('access_token', newToken, { expires: 1 / 48 }) // 30 min
          logger.info('API.Auth', 'Access token refreshed successfully')
          if (original.headers && typeof (original.headers as any).set === 'function') {
            ;(original.headers as any).set('Authorization', `Bearer ${newToken}`)
          } else {
            original.headers = {
              ...(original.headers ?? {}),
              Authorization: `Bearer ${newToken}`,
            } as any
          }
          return api(original)
        } catch (refreshErr) {
          logger.error('API.Auth', 'Token refresh failed, redirecting to login', refreshErr)
          clearTokens()
          window.location.href = '/auth/login'
        }
      } else {
        logger.warn('API.Auth', 'No refresh token found, redirecting to login')
        clearTokens()
        window.location.href = '/auth/login'
      }
    }
    return Promise.reject(err)
  }
)

// ── Token helpers ─────────────────────────────────────────────────────────────
export function saveTokens(access: string, refresh: string) {
  Cookies.set('access_token',  access,  { expires: 1 / 48 }) // 30 min
  Cookies.set('refresh_token', refresh, { expires: 7 })
  logger.info('Auth.Tokens', 'Tokens saved to cookies')
}

export function clearTokens() {
  Cookies.remove('access_token')
  Cookies.remove('refresh_token')
  logger.info('Auth.Tokens', 'Tokens cleared from cookies')
}

export function getAccessToken() {
  return Cookies.get('access_token') ?? null
}

export function getApiErrorMessage(err: unknown, fallback: string): string {
  if (!axios.isAxiosError(err)) return fallback

  const detail = err.response?.data?.detail ?? err.response?.data?.data
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((d: any) => d?.msg ?? d?.message)
      .filter(Boolean)
    if (messages.length) return messages.join(', ')
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  const serverMessage = err.response?.data?.message
  if (typeof serverMessage === 'string' && serverMessage.trim()) {
    return serverMessage
  }

  if (err.code === 'ERR_NETWORK' || /network changed/i.test(err.message ?? '')) {
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false
    if (offline) return 'You appear to be offline. Please check your internet and try again.'
    return 'Network changed while sending request. Please try again.'
  }

  return fallback
}

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function signup(username: string, password: string) {
  logger.info('Auth.Signup', `Attempting signup for username: ${username}`)
  try {
    const { data } = await api.post('/auth/signup', { username, password })
    logger.info('Auth.Signup', `Signup successful for ${username}`, { userId: data.data.user.id })
    return data.data as { user: UserProfile; tokens: TokenPair }
  } catch (err) {
    logger.error('Auth.Signup', `Signup failed for ${username}`, err)
    throw err
  }
}

export async function login(username: string, password: string) {
  logger.info('Auth.Login', `Attempting login for username: ${username}`)
  try {
    const { data } = await api.post('/auth/login', { username, password })
    logger.info('Auth.Login', `Login successful for ${username}`, { userId: data.data.user.id })
    return data.data as { user: UserProfile; tokens: TokenPair }
  } catch (err) {
    logger.error('Auth.Login', `Login failed for ${username}`, err)
    throw err
  }
}

// ── Prediction ────────────────────────────────────────────────────────────────
export async function predict(file: File, language = 'en') {
  logger.info('Predict', `Uploading image for prediction`, {
    fileName: file.name,
    fileSize: file.size,
    language,
  })
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('language', language)
    const { data } = await api.post('/predict', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    logger.info('Predict', `Prediction successful`, {
      isPlant: data.data.is_plant,
      disease: data.data.disease_name,
      confidence: data.data.confidence_score,
    })
    return data.data as PredictResponse
  } catch (err) {
    logger.error('Predict', `Prediction failed`, err)
    throw err
  }
}

// ── History ───────────────────────────────────────────────────────────────────
export async function getHistory(page = 1, pageSize = 12) {
  logger.debug('History', `Fetching history`, { page, pageSize })
  try {
    const { data } = await api.get('/history', { params: { page, page_size: pageSize } })
    logger.info('History', `History fetched`, { itemCount: data.data.items.length, total: data.data.total })
    return data.data as HistoryResponse
  } catch (err) {
    logger.error('History', `Failed to fetch history`, err)
    throw err
  }
}

export async function getPrediction(id: string) {
  logger.debug('History', `Fetching prediction details`, { id })
  try {
    const { data } = await api.get(`/prediction/${id}`)
    logger.info('History', `Prediction details fetched`, { id })
    return data.data
  } catch (err) {
    logger.error('History', `Failed to fetch prediction`, err)
    throw err
  }
}
