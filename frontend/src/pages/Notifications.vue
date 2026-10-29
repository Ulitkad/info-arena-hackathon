<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { post, formatDate } from '../api'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'
const store = useArena(), router = useRouter(), loading = ref(false)
onMounted(refresh)
async function refresh() { loading.value = true; try { await store.refreshNotifications() } catch (e) { store.toast(e.message, 'error') } finally { loading.value = false } }
async function open(item) { if (!item.read) { await post(`/notifications/${item.id}/read`).catch(() => {}); await refresh() }; if (item.link?.startsWith('/')) router.push(item.link) }
async function allRead() { await store.run(async () => { await post('/notifications/read-all'); await refresh() }, 'Все уведомления прочитаны') }
function icon(n) { const text = `${n.title} ${n.body}`.toLowerCase(); return text.includes('дуэл') ? 'swords' : text.includes('заяв') || text.includes('групп') ? 'users' : text.includes('задан') || text.includes('работ') ? 'book' : text.includes('меропр') ? 'calendar' : 'award' }
</script>
<template><section class="notifications-page"><div class="section-head"><div><span class="eyebrow">ТВОИ ВАЖНЫЕ СОБЫТИЯ</span><h2>Всё, что движет вперёд</h2></div><button v-if="store.unread" class="btn secondary small" @click="allRead"><Icon name="check-check" :size="15" />Прочитать всё</button></div><div v-if="loading" class="center-state inline"><span class="spinner" /></div><div v-else-if="!store.notifications.length" class="empty-page panel"><span class="empty-icon"><Icon name="bell" :size="28" /></span><h3>Здесь появятся хорошие новости</h3><p>Новые задания, открытые уровни и приглашения друзей — всё в одном месте.</p></div><section v-else class="notification-list"> <button v-for="item in store.notifications" :key="item.id" class="notification-row panel" :class="{ unread: !item.read }" @click="open(item)"><span class="notification-kind"><Icon :name="icon(item)" :size="20" /></span><span class="notification-copy"><strong>{{ item.title }}</strong><small>{{ item.body }}</small><time>{{ formatDate(item.created_at) }}</time></span><span v-if="!item.read" class="unread-indicator"></span><Icon name="chevron-right" :size="17" /></button></section></section></template>
