/**
 * API 调用层 - 统一 fetch 封装
 *
 * 使用方式：
 *   import { get, post, put, del } from '@/api/client'
 *   const items = await get<Item[]>('/items')
 *   const item  = await post<Item>('/items', { name: 'xxx' })
 *
 * 环境变量 VITE_API_URL 设置后端地址，默认 http://localhost:3000/api
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:3002/api'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.error || `HTTP ${res.status}`, res.status)
  }
  // 204 No Content
  if (res.status === 204) return undefined as T
  return res.json()
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

export function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function del(path: string): Promise<void> {
  return request<void>(path, { method: 'DELETE' })
}
