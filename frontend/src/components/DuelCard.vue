<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api, date, post, formatDate } from '../api'
import { useArena } from '../stores/arena'
import Avatar from './Avatar.vue'
import Icon from './Icon.vue'
const props = defineProps({ duel: Object })
const emit = defineEmits(['refresh'])
const store = useArena(), moment = ref(Date.now()), expanded = ref(false), ledger = ref([])
let timer
onMounted(() => { timer = setInterval(() => { moment.value = Date.now() }, 1000) })
onUnmounted(() => clearInterval(timer))
const mine = computed(() => props.duel.challenger_id === store.user.id)
const other = computed(() => mine.value ? props.duel.opponent : props.duel.challenger)
const myScore = computed(() => mine.value ? props.duel.challenger_score : props.duel.opponent_score)
const theirScore = computed(() => mine.value ? props.duel.opponent_score : props.duel.challenger_score)
const percent = computed(() => myScore.value + theirScore.value ? myScore.value / (myScore.value + theirScore.value) * 100 : 50)
const remaining = computed(() => {
  const ms = date(props.duel.ends_at)?.getTime() - moment.value
  if (!ms || ms <= 0) return 'Подводим итоги'
  const hours = Math.floor(ms / 3600000), minutes = Math.floor(ms / 60000) % 60
  return hours >= 24 ? `${Math.floor(hours / 24)} д ${hours % 24} ч` : `${hours} ч ${minutes} мин`
})
async function action(kind) { if (await store.run(() => post(`/duels/${props.duel.id}/${kind}`), kind === 'accept' ? 'Дуэль началась!' : 'Вызов отменён')) emit('refresh') }
async function toggle() {
  expanded.value = !expanded.value
  if (expanded.value) { try { ledger.value = await api(`/duels/${props.duel.id}/ledger`) } catch (e) { store.toast(e.message, 'error') } }
}
</script>
<template><article class="duel-card panel">
  <div class="flex-between"><span class="eyebrow"><Icon name="swords" :size="16" />{{ duel.subject_id ? store.passes.find(p => p.subject_id === duel.subject_id)?.name || 'Предметная дуэль' : 'Общий зачёт' }}</span><span class="chip" :class="duel.status === 'ACTIVE' ? 'blue' : 'neutral'"><span v-if="duel.status === 'ACTIVE'" class="live-dot"></span>{{ duel.status === 'ACTIVE' ? remaining : duel.status === 'PENDING' ? 'Ожидает ответа' : duel.status === 'COMPLETED' ? 'Завершена' : { CANCELLED: 'Отменена', EXPIRED: 'Истекла', DECLINED: 'Отклонена' }[duel.status] }}</span></div>
  <div class="duel-players"><div><Avatar :user="store.user" :size="40" /><strong>Ты</strong></div><div class="duel-score">{{ myScore }} <span>:</span> {{ theirScore }}<small>VS</small></div><router-link :to="`/users/${other.id}`"><Avatar :user="other" :size="40" /><strong>{{ other.display_name.split(' ')[0] }}</strong></router-link></div>
  <div class="vs-track"><span :style="{ width: `${percent}%` }"></span></div>
  <div v-if="duel.status === 'PENDING'" class="button-row mt-4"><button v-if="!mine" class="btn primary small" :disabled="store.saving" @click="action('accept')">Принять вызов</button><button class="btn ghost small" :disabled="store.saving" @click="action('cancel')">{{ mine ? 'Отменить' : 'Отклонить' }}</button></div>
  <div v-else-if="duel.status === 'COMPLETED'" class="duel-result"><Icon name="trophy" :size="15" />{{ !duel.winner_id ? 'Ничья · +3 балла каждому' : duel.winner_id === store.user.id ? 'Твоя победа! +10 баллов' : 'Новый опыт. До следующей дуэли!' }}</div>
  <button v-if="['ACTIVE', 'COMPLETED'].includes(duel.status)" class="text-btn duel-log" @click="toggle">{{ expanded ? 'Скрыть' : 'История начислений' }}<Icon name="chevron-down" :size="14" /></button>
  <div v-if="expanded" class="ledger"><p v-if="!ledger.length" class="muted">Пока без начислений. Самое время начать!</p><div v-for="entry in ledger" :key="entry.id"><span>{{ entry.user_id === store.user.id ? 'Ты' : other.display_name.split(' ')[0] }} · {{ entry.label }}<small>{{ formatDate(entry.created_at) }}</small></span><b>+{{ entry.points }}</b></div></div>
</article></template>
