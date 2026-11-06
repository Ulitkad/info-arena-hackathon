<script setup>
import { onMounted, ref } from 'vue'
import { api, post, remove } from '../api'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'
import Modal from '../components/Modal.vue'
import Avatar from '../components/Avatar.vue'

const store = useArena(), organizations = ref([]), members = ref([]), modal = ref(''), name = ref(''), loading = ref(false), error = ref('')
const inviteUrl = ref(''), inviteOrganization = ref('')
async function load() {
  loading.value = true; error.value = ''
  try {
    organizations.value = await api('/organizations')
    members.value = await Promise.all(organizations.value.map(async org => ({
      org,
      users: await api(`/organizations/${org.id}/members`),
      invites: await api(`/organizations/${org.id}/invites`),
    })))
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
onMounted(load)
async function create() {
  const ok = await store.run(async () => {
    await post('/organizations', { name: name.value })
    name.value = ''; modal.value = ''
    await load()
  }, 'Учреждение создано — пригласите управляющего по ссылке')
  return ok
}
async function inviteManager(org) {
  await store.run(async () => {
    const link = await post(`/organizations/${org.id}/invites`, { role: 'MANAGER' })
    inviteUrl.value = link.url
    inviteOrganization.value = org.name
    modal.value = 'invite-result'
    await load()
  })
}
async function revokeInvite(id) {
  await store.run(async () => { await remove(`/invites/${id}`); await load() }, 'Приглашение отозвано')
}
async function removeStaff(org, person) {
  if (!confirm(`Удалить ${person.display_name} из учреждения?`)) return
  await store.run(async () => {
    await remove(`/organizations/${org.id}/members/${person.id}`)
    await load()
  }, `${person.role === 'MANAGER' ? 'Управляющий' : 'Преподаватель'} удалён`)
}
async function copyInvite() {
  try { await navigator.clipboard.writeText(inviteUrl.value); store.toast('Приглашение скопировано') }
  catch { store.toast('Скопируйте ссылку из поля') }
}
</script>
<template>
  <section class="admin-page">
    <div class="section-head">
      <div><span class="eyebrow">ОРГАНИЗАЦИОННАЯ СТРУКТУРА</span><h2>Учебные учреждения</h2></div>
      <button class="btn primary" @click="modal = 'organization'"><Icon name="plus" :size="16" />Новое учреждение</button>
    </div>
    <div v-if="error" class="inline-alert"><Icon name="x-circle" :size="16" />{{ error }}</div>
    <div class="organization-grid">
      <article v-for="item in members" :key="item.org.id" class="organization-card panel">
        <div class="organization-top"><span class="organization-mark"><Icon name="cloud" :size="21" /></span><span class="chip blue">Активно</span></div>
        <h3>{{ item.org.name }}</h3>
        <p>Создано {{ new Date(item.org.created_at + 'Z').toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) }}</p>
        <div class="org-stats">
          <span><Icon name="users" :size="15" /><b>{{ item.users.filter(u => u.role === 'STUDENT').length }}</b> учеников</span>
          <span><Icon name="graduation" :size="15" /><b>{{ item.users.filter(u => u.role === 'TEACHER').length }}</b> преподавателей</span>
        </div>
        <div class="org-managers">
          <span class="eyebrow">УПРАВЛЕНИЕ</span>
          <div v-for="person in item.users.filter(u => u.role === 'MANAGER')" :key="person.id" class="org-manager">
            <Avatar :user="person" :size="34" /><span><strong>{{ person.display_name }}</strong><small>Управляющий</small></span><button class="icon-btn danger-icon" :aria-label="`Удалить управляющего ${person.display_name}`" :disabled="store.saving" @click="removeStaff(item.org, person)"><Icon name="trash" :size="16" /></button>
          </div>
          <div v-if="!item.users.some(u => u.role === 'MANAGER')" class="org-no-manager">Управляющий не назначен</div>
          <div v-if="item.users.some(u => u.role === 'TEACHER')" class="org-staff-list">
            <span class="eyebrow">ПРЕПОДАВАТЕЛИ</span>
            <div v-for="person in item.users.filter(u => u.role === 'TEACHER')" :key="person.id" class="org-manager">
              <Avatar :user="person" :size="34" /><span><strong>{{ person.display_name }}</strong><small>Преподаватель</small></span><button class="icon-btn danger-icon" :aria-label="`Удалить преподавателя ${person.display_name}`" :disabled="store.saving" @click="removeStaff(item.org, person)"><Icon name="trash" :size="16" /></button>
            </div>
          </div>
          <button class="btn secondary small" :disabled="store.saving" @click="inviteManager(item.org)"><Icon name="link" :size="15" />Пригласить управляющего</button>
          <div v-for="invite in item.invites.filter(i => i.role === 'MANAGER')" :key="invite.id" class="invite-row">
            <span><strong>Приглашение #{{ invite.id }}</strong><small>{{ invite.revoked ? 'ОТОЗВАНО' : invite.used_by ? 'ИСПОЛЬЗОВАНО' : 'АКТИВНО · ОДНОРАЗОВОЕ' }}</small></span>
            <button v-if="!invite.revoked && !invite.used_by" class="icon-btn danger-icon" aria-label="Отозвать приглашение управляющего" :disabled="store.saving" @click="revokeInvite(invite.id)"><Icon name="x" :size="16" /></button>
          </div>
        </div>
        <router-link :to="`/manage/groups?organization=${item.org.id}`" class="org-link">Управление учреждением <Icon name="arrow-right" :size="15" /></router-link>
      </article>
      <div v-if="!organizations.length && !loading" class="empty-page panel">
        <span class="empty-icon"><Icon name="layers" :size="28" /></span><h3>Учреждений пока нет</h3><p>Создай учебное заведение и пригласи управляющего по ссылке.</p>
      </div>
    </div>
    <div v-if="loading" class="center-state inline"><span class="spinner"></span></div>
    <Modal v-if="modal === 'organization'" title="Новое учреждение" @close="modal = ''">
      <form class="modal-form" @submit.prevent="create">
        <label class="field-label">Название<input v-model.trim="name" maxlength="100" required placeholder="Например, Колледж цифровых технологий" /></label>
        <p>После создания учреждения пригласите управляющего по одноразовой ссылке из его карточки.</p>
        <button class="btn primary modal-submit" :disabled="!name || store.saving">Создать учреждение <Icon name="arrow-right" :size="15" /></button>
      </form>
    </Modal>
    <Modal v-else-if="modal === 'invite-result'" title="Приглашение управляющего" @close="modal = ''">
      <div class="modal-form">
        <p>Учреждение: {{ inviteOrganization }}. Отправьте ссылку будущему управляющему. Она откроет доступ первому активировавшему её пользователю и больше не будет работать.</p>
        <label class="field-label">Одноразовая ссылка<input :value="inviteUrl" readonly @focus="$event.target.select()" /></label>
        <button class="btn primary" @click="copyInvite"><Icon name="link" :size="16" />Скопировать ссылку</button>
      </div>
    </Modal>
  </section>
</template>
