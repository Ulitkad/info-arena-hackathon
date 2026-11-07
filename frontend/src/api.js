// Compatibility facade for existing pages. New code should import transport
// helpers from ./services/http.js or a domain-specific API service.
export { request as api, post, put, remove } from './services/http.js'
export const date = value => value ? new Date(/[Z+-]\d\d:?\d\d$|Z$/.test(value) ? value : `${value}Z`) : null
export const formatDate = value => date(value)?.toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) || ''
export const iso = local => new Date(local).toISOString()
export const futureLocal = (days = 1) => {
  const d = new Date(Date.now() + days * 86400000)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
export const roleName = role => ({ STUDENT: 'Ученик', TEACHER: 'Преподаватель', MANAGER: 'Управляющий', ADMIN: 'Администратор', PENDING: 'Участник' })[role] || role
export const homeFor = role => ({ TEACHER: '/teach', MANAGER: '/manage/requests', ADMIN: '/admin' })[role] || '/'
