export async function api(path, options = {}) {
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

export const post = (path, body = {}) => api(path, { method: 'POST', body })
export const put = (path, body = {}) => api(path, { method: 'PUT', body })
export const remove = path => api(path, { method: 'DELETE' })
export const date = value => value ? new Date(/[Z+-]\d\d:?\d\d$|Z$/.test(value) ? value : `${value}Z`) : null
export const formatDate = value => date(value)?.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) || ''
export const iso = local => new Date(local).toISOString()
export const futureLocal = (days = 1) => {
  const d = new Date(Date.now() + days * 86400000)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
export const roleName = role => ({ STUDENT: 'Ученик', TEACHER: 'Преподаватель', MANAGER: 'Управляющий', ADMIN: 'Администратор', PENDING: 'Участник' })[role] || role
export const homeFor = role => ({ TEACHER: '/teach', MANAGER: '/manage/requests', ADMIN: '/admin' })[role] || '/'
