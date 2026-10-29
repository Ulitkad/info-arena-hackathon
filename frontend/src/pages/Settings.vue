<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api, put } from '../api'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'
import Avatar from '../components/Avatar.vue'
const store = useArena(), inventory = ref([]), titleId = ref(null), frameId = ref(null), showcase = ref([])
async function load() {
  try { inventory.value = await api('/inventory'); titleId.value = store.user.active_title_id || null; frameId.value = store.user.active_frame_id || null; showcase.value = [...(store.user.showcase || [])] }
  catch (e) { store.toast(e.message, 'error') }
}
onMounted(load)
watch(() => store.revision, () => load())
const titles = computed(() => inventory.value.filter(r => r.kind === 'TITLE'))
const frames = computed(() => inventory.value.filter(r => r.kind === 'FRAME'))
const badges = computed(() => inventory.value.filter(r => r.kind === 'BADGE'))
const previewUser = computed(() => ({ ...store.user, active_frame_id: frameId.value }))
function toggleBadge(id) {
  if (showcase.value.includes(id)) showcase.value = showcase.value.filter(x => x !== id)
  else if (showcase.value.length < 3) showcase.value.push(id)
  else store.toast('В витрине может быть до трёх достижений', 'error')
}
async function save() {
  await store.run(async () => { await put('/me/profile', { active_title_id: titleId.value, active_frame_id: frameId.value, showcase: showcase.value }); await store.refreshUser() }, 'Стиль профиля обновлён')
}
async function logout() { store.logout(); await store.initialize() }
</script>
<template><section class="settings-page"><div class="settings-preview panel"><span class="eyebrow">ТВОЙ ПРОФИЛЬ</span><Avatar :user="previewUser" :size="76" :framed="Boolean(frameId)" /><strong>{{ store.user.display_name }}</strong><span class="muted">{{ store.user.username ? `@${store.user.username}` : store.user.group?.name }}</span><span v-if="titles.find(t => t.id === titleId)" class="public-title"><Icon name="crown" :size="14" />{{ titles.find(t => t.id === titleId)?.name }}</span><button class="text-btn" @click="logout"><Icon name="logout" :size="15" />Выйти</button></div><div class="settings-content"><section class="settings-section"><div class="section-head"><div><span class="eyebrow">ТВОЙ ОБРАЗ</span><h2>Звания</h2></div><span class="subtle-count">{{ titles.length }} открыто</span></div><div class="select-cards"><label class="select-card" :class="{ selected: !titleId }"><input v-model="titleId" type="radio" :value="null" /><span class="reward-art"><Icon name="user-plus" :size="20" /></span><span><strong>Без звания</strong><small>Покажи свой стиль</small></span><Icon v-if="!titleId" name="check" :size="17" class="selected-check" /></label><label v-for="item in titles" :key="item.id" class="select-card" :class="{ selected: titleId === item.id }"><input v-model="titleId" type="radio" :value="item.id" /><span class="reward-art reward-art-title"><Icon :name="item.icon || 'crown'" :size="20" /></span><span><strong>{{ item.name }}</strong><small>Открыто {{ new Date(item.unlocked_at + 'Z').toLocaleDateString('ru-RU') }}</small></span><Icon v-if="titleId === item.id" name="check" :size="17" class="selected-check" /></label></div></section><section class="settings-section"><div class="section-head"><div><span class="eyebrow">ВЫРАЖАЙ СЕБЯ</span><h2>Рамка аватара</h2></div><span class="subtle-count">{{ frames.length }} открыто</span></div><div class="frame-selector"><label class="frame-choice" :class="{ selected: !frameId }"><input v-model="frameId" type="radio" :value="null" /><Avatar :user="store.user" :size="58" /><span>Оригинал</span><Icon v-if="!frameId" name="check" :size="15" /></label><label v-for="item in frames" :key="item.id" class="frame-choice" :class="{ selected: frameId === item.id }"><input v-model="frameId" type="radio" :value="item.id" /><span class="avatar frame-preview"><Icon :name="item.icon || 'shield'" :size="20" /></span><span>{{ item.name }}</span><Icon v-if="frameId === item.id" name="check" :size="15" /></label></div></section><section class="settings-section"><div class="section-head"><div><span class="eyebrow">ПОКАЖИ СВОИ ПОБЕДЫ</span><h2>Достижения на витрине</h2></div><span class="subtle-count">{{ showcase.length }}/3</span></div><div v-if="!badges.length" class="empty-inline panel"><Icon name="award" :size="19" /><span>Выполняй задания и открывай новые достижения.</span><router-link to="/battlepass">Пропуски</router-link></div><div v-else class="badge-options"><button v-for="item in badges" :key="item.id" class="badge-option panel" :class="{ selected: showcase.includes(item.id) }" :aria-pressed="showcase.includes(item.id)" @click="toggleBadge(item.id)"><span class="achievement-icon achievement-badge"><Icon :name="item.icon || 'award'" :size="20" /></span><span><strong>{{ item.name }}</strong><small>{{ item.subject_id ? 'Предметный пропуск' : 'Общий пропуск' }}</small></span><span class="fake-check"><Icon name="check" :size="13" /></span></button></div></section><div class="settings-save"><span class="field-hint">{{ inventory.length }} наград доступно для оформления</span><button class="btn primary" :disabled="store.saving" @click="save"><Icon name="check" :size="16" />Сохранить образ</button></div></div></section></template>
