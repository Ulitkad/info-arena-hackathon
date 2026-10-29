import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'
import { createPinia, setActivePinia } from 'pinia'
import { useArena } from '../src/stores/arena.js'

const originalGlobals = new Map()
let store, requests, sockets, timers, storage, respond

function replaceGlobal(name, value) {
  originalGlobals.set(name, Object.getOwnPropertyDescriptor(globalThis, name))
  Object.defineProperty(globalThis, name, { configurable: true, writable: true, value })
}

function deferred() {
  let resolve
  const promise = new Promise(done => { resolve = done })
  return { promise, resolve }
}

const response = data => ({ ok: true, json: async () => data })
const flush = () => new Promise(resolve => setImmediate(resolve))

beforeEach(() => {
  requests = []; sockets = []; timers = new Map(); storage = new Map([['arena-token', 'first-token']])
  respond = url => {
    if (url === '/api/config') return { dev_auth: true, demo: true }
    if (url === '/api/me') return { id: 1, role: 'STUDENT' }
    if (url === '/api/notifications') return { items: [], unread: 0 }
    if (url === '/api/ws-ticket') return { ticket: 'current-ticket' }
    return []
  }
  replaceGlobal('sessionStorage', {
    getItem: key => storage.get(key) ?? null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: key => storage.delete(key),
  })
  replaceGlobal('window', {})
  replaceGlobal('location', { protocol: 'http:', host: 'localhost:5173', search: '', hash: '' })
  replaceGlobal('fetch', async (url, options) => {
    requests.push({ url, options })
    return response(await respond(url, options))
  })
  let timerId = 0
  for (const name of ['setTimeout', 'setInterval']) {
    replaceGlobal(name, (callback, delay) => {
      const id = ++timerId
      timers.set(id, { callback, delay })
      return id
    })
  }
  for (const name of ['clearTimeout', 'clearInterval']) replaceGlobal(name, id => timers.delete(id))
  replaceGlobal('WebSocket', class {
    static OPEN = 1
    readyState = 0
    sent = []
    constructor() { sockets.push(this) }
    send(data) { this.sent.push(data) }
    close() { this.readyState = 3 }
    open() { this.readyState = 1; this.onopen?.() }
  })
  setActivePinia(createPinia())
  store = useArena()
})

afterEach(() => {
  store.disconnect()
  for (const [name, descriptor] of originalGlobals) {
    if (descriptor) Object.defineProperty(globalThis, name, descriptor)
    else delete globalThis[name]
  }
  originalGlobals.clear()
})

test('logout stays logged out when an earlier profile request completes', async () => {
  const pending = deferred()
  const fallback = respond
  respond = url => url === '/api/me' ? pending.promise : fallback(url)
  const opening = store.initialize()
  await flush()
  store.logout()
  pending.resolve({ id: 1, role: 'STUDENT' })
  await opening
  assert.equal(store.user, null)
  assert.equal(store.loading, false)
  assert.equal(storage.has('arena-token'), false)
  assert.equal(sockets.length, 0)
})

test('a late socket ticket cannot open a previous user session', async () => {
  const pending = deferred()
  const fallback = respond
  let ticketRequests = 0
  respond = url => url === '/api/ws-ticket' && ++ticketRequests === 1 ? pending.promise : fallback(url)
  await store.initialize()
  await store.initialize()
  await flush()
  assert.equal(sockets.length, 1)
  pending.resolve({ ticket: 'old-ticket' })
  await flush()
  assert.equal(sockets.length, 1)
  sockets[0].open()
  assert.deepEqual(sockets[0].sent, [JSON.stringify({ ticket: 'current-ticket' })])
})

test('events from a closed socket cannot affect the new connection', async () => {
  await store.initialize()
  await flush()
  const first = sockets[0]
  first.open()
  const lateClose = first.onclose
  const lateMessage = first.onmessage
  await store.initialize()
  await flush()
  sockets[1].open()
  lateClose()
  lateMessage({ data: JSON.stringify({ unread: 99, items: [{ id: 99, title: 'Old user' }] }) })
  assert.equal(store.connected, true)
  assert.equal(store.unread, 0)
  assert.equal(store.toasts.length, 0)
  assert.equal([...timers.values()].filter(t => t.delay === 5000).length, 0)
})

test('late learning and notification responses cannot restore data after logout', async () => {
  const learning = deferred(), notices = deferred()
  store.user = { id: 1, role: 'STUDENT' }
  respond = url => url === '/api/notifications' ? notices.promise : learning.promise
  const refreshingLearning = store.refreshStudent()
  const refreshingNotifications = store.refreshNotifications()
  store.logout()
  learning.resolve([{ id: 1 }])
  notices.resolve({ items: [{ id: 1 }], unread: 7 })
  await Promise.all([refreshingLearning, refreshingNotifications])
  for (const field of ['passes', 'inventory', 'duels', 'homework', 'events', 'notifications']) {
    assert.deepEqual(store[field], [])
  }
  assert.equal(store.unread, 0)
  assert.equal(store.user, null)
})
