/**
 * Transport boundary for the frontend. Pages and stores should use this
 * module (or a domain service built on it), not call fetch directly.
 */
export async function request(path, options = {}) {
  const token = sessionStorage.getItem('arena-token')
  const headers = { ...options.headers }
  if (token) headers.Authorization = `Bearer ${token}`
  let body = options.body
  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(body)
  }
  const response = await fetch(`/api${path}`, { ...options, headers, body })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = data.detail
    const message = Array.isArray(detail)
      ? detail.map(e => `${e.loc?.slice(1).join('.')}: ${e.msg}`).join('\n')
      : detail || 'Не удалось выполнить запрос. Попробуйте ещё раз.'
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return data
}

export const post = (path, body = {}) => request(path, { method: 'POST', body })
export const put = (path, body = {}) => request(path, { method: 'PUT', body })
export const remove = path => request(path, { method: 'DELETE' })
