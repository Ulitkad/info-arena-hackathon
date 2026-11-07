import { defineStore } from 'pinia'
import { api, post, homeFor } from '../api.js'
import { createSessionState } from './arena/session.js'
import { createLearningState } from './arena/learning.js'
import { createSocialState } from './arena/social.js'
import { createNotificationState } from './arena/notifications.js'

export const useArena = defineStore('arena', () => {
  const session = createSessionState()
  const learning = createLearningState()
  const social = createSocialState()
  const notificationState = createNotificationState()
  const { user, config, loading, error, revision, saving, connected } = session
  const { passes, inventory, homework, events } = learning
  const { duels } = social
  const { notifications, unread, toasts } = notificationState
  let socket, reconnect, heartbeat, toastTimer, toastSequence = 0, stopped = false
  let notificationQueue = [], seen = new Set()

  function toast(message, kind = 'success', link = null, notificationId = null) {
    const id = ++toastSequence
    toasts.value.push({ id, message, kind, link, notificationId })
    setTimeout(() => dismiss(id), 6500)
  }
  function dismiss(id) { toasts.value = toasts.value.filter(t => t.id !== id) }
  async function run(work, message = '') {
    if (saving.value) return false
    saving.value = true
    try {
      await work()
      revision.value++
      if (message) toast(message)
      return true
    } catch (e) { toast(e.message, 'error'); return false }
    finally { saving.value = false }
  }
  async function refreshUser() {
    const version = session.currentVersion()
    const profile = await api('/me')
    if (version === session.currentVersion()) user.value = profile
  }
  async function refreshStudent() {
    if (user.value?.role !== 'STUDENT') return
    const version = session.currentVersion()
    const result = await Promise.all([api('/battlepasses'), api('/inventory'), api('/duels'), api('/homework'), api('/events')])
    if (version !== session.currentVersion()) return
    ;[passes.value, inventory.value, duels.value, homework.value, events.value] = result
    await refreshUser()
  }
  async function refreshNotifications() {
    const version = session.currentVersion()
    const data = await api('/notifications')
    if (version !== session.currentVersion()) return data
    notifications.value = data.items
    unread.value = data.unread
    return data
  }
  function nextToast() {
    if (!notificationQueue.length || stopped) return
    const n = notificationQueue.shift()
    toast(n.title + (n.body ? ` · ${n.body}` : ''), 'notification', n.link, n.id)
    post('/notifications/toasted', { ids: [n.id] }).catch(() => {})
    toastTimer = setTimeout(nextToast, 1800)
  }
  async function connect() {
    if (stopped || !user.value) return
    const version = session.currentVersion()
    try {
      const { ticket } = await post('/ws-ticket')
      if (stopped || version !== session.currentVersion()) return
      const client = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`)
      socket = client
      const current = () => !stopped && version === session.currentVersion() && socket === client
      client.onopen = () => {
        if (!current()) return
        connected.value = true
        client.send(JSON.stringify({ ticket }))
        heartbeat = setInterval(() => { if (current() && client.readyState === WebSocket.OPEN) client.send('ping') }, 25000)
      }
      client.onmessage = event => {
        if (!current()) return
        const data = JSON.parse(event.data)
        unread.value = data.unread
        const items = (data.items || []).filter(n => !seen.has(n.id))
        for (const n of items) seen.add(n.id)
        const wasEmpty = notificationQueue.length === 0
        notificationQueue.push(...items)
        if (wasEmpty && items.length) { clearTimeout(toastTimer); nextToast() }
        if (items.length) {
          refreshNotifications().catch(() => {})
          refreshUser().catch(() => {})
          revision.value++
        }
      }
      client.onclose = () => {
        if (!current()) return
        socket = null
        connected.value = false
        clearInterval(heartbeat)
        if (!stopped) reconnect = setTimeout(connect, 5000)
      }
      client.onerror = () => { if (current()) client.close() }
    } catch { if (!stopped && version === session.currentVersion()) reconnect = setTimeout(connect, 10000) }
  }
  function disconnect() {
    session.nextVersion()
    stopped = true
    clearTimeout(reconnect); clearInterval(heartbeat); clearTimeout(toastTimer)
    if (socket) {
      socket.onopen = socket.onmessage = socket.onclose = socket.onerror = null
      socket.close(); socket = null
    }
    notificationQueue = []; seen = new Set(); connected.value = false
  }
  async function initialize() {
    disconnect()
    const version = session.currentVersion()
    loading.value = true; error.value = ''; stopped = false
    try {
      const settings = await api('/config')
      if (version !== session.currentVersion()) return
      config.value = settings
      const params = new URLSearchParams(location.search)
      const invite = params.get('group_token') || params.get('invite_token')
      const initData = window.WebApp?.initData || new URLSearchParams(location.hash.slice(1)).get('WebAppData')
      if (initData) {
        const result = await post('/auth/max', { init_data: initData, invite_token: invite || null })
        if (version !== session.currentVersion()) return
        sessionStorage.setItem('arena-token', result.access_token)
      }
      if (!sessionStorage.getItem('arena-token')) return
      await refreshUser()
      if (version !== session.currentVersion()) return
      if (invite && !initData) await post('/invites/accept', { token: invite })
      if (version !== session.currentVersion()) return
      if (invite) {
        params.delete('group_token'); params.delete('invite_token'); params.delete('role')
        history.replaceState(null, '', `${location.pathname}${params.size ? '?' + params : ''}${location.hash}`)
        await refreshUser()
        if (version !== session.currentVersion()) return
      }
      await refreshNotifications()
      if (version !== session.currentVersion()) return
      connect()
    } catch (e) {
      if (version !== session.currentVersion()) return
      error.value = e.message
      if (e.status === 401) { sessionStorage.removeItem('arena-token'); user.value = null }
    } finally { if (version === session.currentVersion()) loading.value = false }
  }
  async function demo(persona) {
    disconnect()
    const version = session.currentVersion()
    const result = await post('/auth/dev', { persona })
    if (version !== session.currentVersion()) return homeFor(user.value?.role)
    sessionStorage.setItem('arena-token', result.access_token)
    learning.reset(); social.reset(); notificationState.reset()
    await initialize()
    return homeFor(user.value?.role)
  }
  function logout() {
    disconnect(); sessionStorage.removeItem('arena-token'); user.value = null
    learning.reset(); social.reset(); notificationState.reset(); error.value = ''
    loading.value = false
  }
  return { user, config, loading, error, passes, inventory, duels, homework, events, notifications, unread,
    toasts, revision, saving, connected, initialize, demo, logout, toast, dismiss, run, refreshUser,
    refreshStudent, refreshNotifications, disconnect }
})
