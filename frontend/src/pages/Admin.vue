<script setup>
import { onMounted, ref } from 'vue'
import { api, post } from '../api'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'
import Modal from '../components/Modal.vue'
import Avatar from '../components/Avatar.vue'

const store = useArena(), organizations = ref([]), members = ref([]), modal = ref(''), name = ref(''), manager = ref(''), loading = ref(false), error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try { organizations.value = await api('/organizations'); members.value = await Promise.all(organizations.value.map(async org => ({ org, users: await api(`/organizations/${org.id}/members`).catch(() => []) }))) }
  catch (e) { error.value = e.message }
  finally { loading.value = false }
}
onMounted(load)
async function create() {
  try {
    const organization = await post('/organizations', { name: name.value })
    if (manager.value) await post(`/organizations/${organization.id}/members`, { query: manager.value, role: 'MANAGER', loads: [] })
    store.toast(manager.value ? 'Учреждение создано, управляющему открыт доступ' : 'Учреждение создано')
    name.value = ''; manager.value = ''; modal.value = ''; await load()
  } catch (e) { error.value = e.message; store.toast(e.message, 'error') }
}
</script>
<template><section class="admin-page"><div class="section-head"><div><span class="eyebrow">ОРГАНИЗАЦИОННАЯ СТРУКТУРА</span><h2>Учебные учреждения</h2></div><button class="btn primary" @click="modal = 'organization'"><Icon name="plus" :size="16" />Новое учреждение</button></div><div v-if="error" class="inline-alert"><Icon name="x-circle" :size="16" />{{ error }}</div><div class="organization-grid"><article v-for="item in members" :key="item.org.id" class="organization-card panel"><div class="organization-top"><span class="organization-mark"><Icon name="cloud" :size="21" /></span><span class="chip blue">Активно</span></div><h3>{{ item.org.name }}</h3><p>Создано {{ new Date(item.org.created_at + 'Z').toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }}</p><div class="org-stats"><span><Icon name="users" :size="15" /><b>{{ item.users.filter(u => u.role === 'STUDENT').length }}</b> учеников</span><span><Icon name="graduation" :size="15" /><b>{{ item.users.filter(u => u.role === 'TEACHER').length }}</b> преподавателей</span></div><div class="org-managers"><span class="eyebrow">УПРАВЛЕНИЕ</span><div v-for="person in item.users.filter(u => u.role === 'MANAGER')" :key="person.id" class="org-manager"><Avatar :user="person" :size="34" /><span><strong>{{ person.display_name }}</strong><small>Управляющий</small></span></div><div v-if="!item.users.some(u => u.role === 'MANAGER')" class="org-no-manager">Управляющий не назначен</div></div><router-link :to="`/manage/groups?organization=${item.org.id}`" class="org-link">Управление учреждением <Icon name="arrow-right" :size="15" /></router-link></article><div v-if="!organizations.length && !loading" class="empty-page panel"><span class="empty-icon"><Icon name="layers" :size="28" /></span><h3>Учреждений пока нет</h3><p>Создай учебное заведение и назначь управляющего.</p></div></div><div v-if="loading" class="center-state inline"><span class="spinner"></span></div><Modal v-if="modal === 'organization'" title="Новое учреждение" wide @close="modal = ''"><form class="modal-form" @submit.prevent="create"><label class="field-label">Название<input v-model.trim="name" required maxlength="160" placeholder="Например, Колледж цифровых технологий" /></label><label class="field-label">Username будущего управляющего <span class="field-hint">Можно назначить сейчас или позже.</span><input v-model.trim="manager" placeholder="@username или ID MAX" /></label><button class="btn primary modal-submit" :disabled="!name || !store.user">Создать учреждение <Icon name="arrow-right" :size="16" /></button></form></Modal></section></template>
