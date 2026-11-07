<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useArena } from './stores/arena'
import { homeFor, post } from './api'
import AppAuth from './components/AppAuth.vue'
import AppHeader from './components/AppHeader.vue'
import AppNavigation from './components/AppNavigation.vue'
import AppPageFrame from './components/AppPageFrame.vue'
import AppPending from './components/AppPending.vue'
import AppToasts from './components/AppToasts.vue'

const store = useArena()
const route = useRoute()
const router = useRouter()
const persona = ref('student')
const lastPage = ref('/')
const pending = computed(() => store.user?.role === 'PENDING')
const title = computed(() => route.meta.title || 'Инфо Арена')
const nav = computed(() => {
  if (store.user?.role === 'STUDENT') return [
    { to: '/', title: 'Главная', icon: 'home' }, { to: '/battlepass', title: 'Пропуск', icon: 'layers' }, { to: '/achievements', title: 'Достижения', icon: 'award' },
    { to: '/arena', title: 'Арена', icon: 'target' }, { to: '/friends', title: 'Друзья', icon: 'users' },
  ]
  if (store.user?.role === 'TEACHER') return [{ to: '/teach', title: 'Преподавание', icon: 'graduation' }]
  if (store.user?.role === 'MANAGER') return [
    { to: '/manage/requests', title: 'Заявки', icon: 'users' }, { to: '/manage/groups', title: 'Ученики', icon: 'book' },
    { to: '/manage/teachers', title: 'Преподаватели', icon: 'graduation' }, { to: '/manage/rewards', title: 'Награды', icon: 'award' },
  ]
  if (store.user?.role === 'ADMIN') return [{ to: '/admin', title: 'Учреждения', icon: 'layers' }, { to: '/manage/groups', title: 'Управление', icon: 'settings' }]
  return []
})

watch(() => [store.loading, store.user?.role, route.fullPath], () => {
  if (!store.loading && store.user && !pending.value && route.meta.roles && !route.meta.roles.includes(store.user.role)) router.replace(homeFor(store.user.role))
})
watch(() => [route.fullPath, store.user?.role], () => {
  if (route.path !== '/notifications') lastPage.value = route.fullPath
  window.scrollTo({ top: 0, behavior: 'smooth' })
  const bridge = window.WebApp
  if (bridge?.initData && bridge?.BackButton) route.path !== homeFor(store.user?.role) && route.path !== '/' ? bridge.BackButton.show() : bridge.BackButton.hide()
})
function windowIsMax() { return Boolean(window.WebApp?.initData) }
function back() { router.back() }
function toggleNotifications() { route.path === '/notifications' ? router.push(lastPage.value || homeFor(store.user?.role)) : router.push('/notifications') }
function openToast(item) {
  store.dismiss(item.id)
  if (item.notificationId) post(`/notifications/${item.notificationId}/read`).catch(() => {})
  if (item.link?.startsWith('/') && route.fullPath !== item.link) router.push(item.link)
}
function copyMaxId() {
  const id = store.user?.max_id
  if (id == null) return
  navigator.clipboard.writeText(String(id)).then(() => store.toast('ID скопирован')).catch(() => store.toast('Не удалось скопировать ID. Попробуйте ещё раз', 'error'))
}
function logoutAndInitialize() { store.logout(); store.initialize() }
async function demo() { try { await store.demo(persona.value).then(to => router.replace(to)) } catch (error) { store.toast(error.message, 'error') } }
onMounted(() => { if (windowIsMax()) window.WebApp?.BackButton?.onClick(back); store.initialize() })
onBeforeUnmount(() => { window.WebApp?.BackButton?.offClick(back); store.disconnect() })
</script>

<template>
  <div class="app-shell">
    <AppHeader v-if="store.user && !pending" :user="store.user" :config="store.config" :unread="store.unread" :is-max="windowIsMax()" :route-path="route.path" @toggle-notifications="toggleNotifications" @logout="store.logout" />
    <main v-if="store.loading" class="app-main center-state"><span class="spinner"></span><p>Открываем арену…</p></main>
    <main v-else-if="!store.user" class="app-main"><AppAuth :config="store.config" :error="store.error" :persona="persona" @update:persona="persona = $event" @demo="demo" /></main>
    <main v-else-if="pending" class="app-main pending-state"><AppPending :user="store.user" @refresh="store.initialize" @logout="logoutAndInitialize" @copy-id="copyMaxId" /></main>
    <main v-else class="app-main"><AppPageFrame :user="store.user" :title="title"><router-view v-slot="{ Component }"><component :is="Component" :key="route.fullPath" /></router-view></AppPageFrame></main>
    <AppNavigation v-if="store.user && !pending" :items="nav" :route-path="route.path" :user-role="store.user.role" />
    <AppToasts :toasts="store.toasts" @open="openToast" @dismiss="store.dismiss" />
  </div>
</template>
