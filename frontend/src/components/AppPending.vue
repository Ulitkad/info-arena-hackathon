<script setup>
import Icon from './Icon.vue'

defineProps({ user: { type: Object, required: true } })
const emit = defineEmits(['refresh', 'logout', 'copy-id'])
</script>

<template>
  <section class="pending-panel panel">
    <span class="pending-icon"><Icon name="clock" :size="25" /></span>
    <span class="eyebrow">ЗАЯВКА ПРИНЯТА</span>
    <h1>Пока готовится твой старт</h1>
    <p>{{ user.join_request?.status === 'PENDING' ? 'Управляющий проверит заявку и откроет доступ к группе. Мы сообщим, когда всё будет готово.' : 'Для доступа в арену нужна ссылка-приглашение от управляющего учебного заведения.' }}</p>
    <div v-if="user.join_request?.status === 'PENDING'" class="pending-meta"><span class="live-dot"></span> Заявка отправлена · {{ user.group?.name || 'группа' }}</div>
    <div class="pending-actions">
      <button class="btn secondary" @click="emit('refresh')"><Icon name="activity" :size="16" /> Обновить статус</button>
      <button class="text-btn pending-exit" @click="emit('logout')">Выйти</button>
    </div>
    <button v-if="user.max_id != null" type="button" class="pending-user-id" title="Нажмите, чтобы скопировать ID" :aria-label="`Скопировать MAX ID ${user.max_id}`" @click="emit('copy-id')">MAX ID: {{ user.max_id }}</button>
  </section>
</template>

<style scoped>
.pending-user-id { display:block; margin:18px auto 0; padding:6px 10px; border:0; border-radius:4px; background:none; color:var(--muted); font-size:11px; font-weight:400; line-height:1.5; overflow-wrap:anywhere; cursor:pointer; }
.pending-actions { display:flex; align-items:center; justify-content:center; gap:var(--space-4); margin-top:var(--space-5); }
.pending-actions .pending-exit { margin:0; }
@media (max-width:35rem) { .pending-actions { flex-direction:column; gap:var(--space-2); } .pending-actions > * { width:100%; } }
.pending-user-id:hover { text-decoration:underline; }
</style>
