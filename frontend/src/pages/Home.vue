<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../api'
import { useArena } from '../stores/arena'
import Avatar from '../components/Avatar.vue'
import DuelCard from '../components/DuelCard.vue'
import Icon from '../components/Icon.vue'

const store = useArena(), busy = ref(false), rewards = ref([]), tick = ref(Date.now())
let interval
async function load() {
  busy.value = true
  try { await store.refreshStudent(); rewards.value = await api('/inventory') }
  catch (e) { store.toast(e.message, 'error') }
  finally { busy.value = false }
}
onMounted(() => { load(); interval = setInterval(() => { tick.value = Date.now() }, 60000) })
watch(() => store.revision, load)
import { onBeforeUnmount } from 'vue'
onBeforeUnmount(() => clearInterval(interval))
const active = computed(() => store.duels.filter(d => ['ACTIVE', 'PENDING'].includes(d.status)).slice(0, 3))
const wins = computed(() => store.user?.duel_wins || 0)
const displayRewards = computed(() => store.user?.showcase?.map(id => rewards.value.find(r => r.id === id)).filter(Boolean).slice(0, 3) || [])
const nextDeadline = computed(() => store.homework.filter(h => !h.submission && !h.optional).sort((a, b) => new Date(a.deadline) - new Date(b.deadline))[0])
function until(value) {
  const seconds = Math.max(0, Math.floor((new Date(value + (value.endsWith('Z') ? '' : 'Z')).getTime() - tick.value) / 1000))
  const days = Math.floor(seconds / 86400), hours = Math.floor(seconds % 86400 / 3600), minutes = Math.floor(seconds % 3600 / 60)
  return days ? `${days} д ${hours} ч` : hours ? `${hours} ч ${minutes} мин` : `${minutes} мин`
}
</script>
<template><section class="dashboard" :aria-busy="busy">
  <div class="dashboard-topline"><span class="greeting"><Icon name="cloud" :size="17" /> {{ new Date().getHours() < 12 ? 'Доброе утро' : new Date().getHours() < 18 ? 'Хороший день' : 'Добрый вечер' }}, {{ store.user.display_name.split(' ')[0] }}</span><span class="status-caption"><span class="live-dot"></span> Арена открыта</span></div>
  <div class="home-grid">
    <section class="player-panel panel">
      <div class="player-banner"><span class="cloud-shape cloud-one"></span><span class="cloud-shape cloud-two"></span><span class="banner-caption"><Icon name="sparkles" :size="15" /> ТВОЙ ПУТЬ В АРЕНЕ</span><div class="banner-sun"></div></div>
      <div class="player-body"><div class="player-identity"><Avatar :user="store.user" :size="74" :framed="Boolean(store.user.active_frame_id)" /><div><div class="player-label">УЧАСТНИК АРЕНЫ</div><h2>{{ store.user.display_name }}</h2><span class="muted username">{{ store.user.username ? `@${store.user.username}` : store.user.group?.name }}</span></div><router-link to="/settings" class="icon-btn player-edit" aria-label="Настроить профиль"><Icon name="settings" /></router-link></div>
        <div v-if="store.user.active_title_id && displayRewards.length" class="active-title"><Icon name="crown" :size="15" />{{ rewards.find(r => r.id === store.user.active_title_id)?.name }}</div>
        <div class="profile-divider"></div><div class="profile-stats"><div><span class="stat-icon wins"><Icon name="trophy" :size="17" /></span><strong>{{ wins }}</strong><small>побед в дуэлях</small></div><div><span class="stat-icon awards"><Icon name="award" :size="17" /></span><strong>{{ rewards.length }}</strong><small>открытых наград</small></div><div><span class="stat-icon subjects"><Icon name="book" :size="17" /></span><strong>{{ store.passes.length || 1 }}</strong><small>боевых пропусков</small></div></div>
      </div>
      <div class="showcase"><div class="section-label"><span>Витрина достижений</span><router-link to="/settings">Изменить</router-link></div><div class="showcase-row"><div v-for="(item, i) in displayRewards" :key="item.id" class="achievement"><span class="achievement-icon" :class="`achievement-${item.kind.toLowerCase()}`"><Icon :name="item.icon || 'award'" :size="18" /></span><span><strong>{{ item.name }}</strong><small>{{ item.kind === 'BADGE' ? 'Знак отличия' : item.kind === 'FRAME' ? 'Рамка профиля' : 'Звание' }}</small></span></div><div v-for="n in Math.max(0, 3 - displayRewards.length)" :key="`empty-${n}`" class="achievement empty-achievement"><span class="achievement-icon"><Icon name="plus" :size="17" /></span><span><strong>Новая цель</strong><small>Продолжай учиться</small></span></div></div></div>
    </section>
    <section class="home-side">
      <div class="section-head"><div><span class="eyebrow">ТВОЙ ПРОГРЕСС</span><h2>Боевые пропуски</h2></div><router-link class="text-arrow" to="/battlepass">Все пропуски <Icon name="arrow-right" :size="15" /></router-link></div>
      <div class="mini-pass-list"><router-link v-for="item in store.passes.slice(0, 3)" :key="item.id" :to="`/battlepass/${item.id}`" class="mini-pass panel"><span class="pass-color" :style="{ background: item.color }"></span><span class="mini-pass-info"><strong>{{ item.name }}</strong><small>{{ item.points }} {{ item.points === 1 ? 'балл' : 'баллов' }} · уровень {{ item.level }}</small><span class="progress-track"><i :style="{ width: `${item.rewards.length ? Math.min(100, item.level / item.rewards.length * 100) : 0}%`, background: item.color }"></i></span></span><Icon name="chevron-right" :size="17" /></router-link><div v-if="!store.passes.length" class="empty-inline panel"><Icon name="layers" :size="22" /><span>Твой прогресс появится здесь.</span></div></div>
      <router-link v-if="nextDeadline" :to="`/arena?homework=${nextDeadline.id}`" class="deadline-card"><span class="deadline-icon"><Icon name="clock" :size="19" /></span><span><small>БЛИЖАЙШИЙ ДЕДЛАЙН</small><strong>{{ nextDeadline.title }}</strong><span>Осталось {{ until(nextDeadline.deadline) }}</span></span><Icon name="arrow-up-right" class="deadline-arrow" :size="18" /></router-link>
      <router-link v-else to="/arena" class="deadline-card"><span class="deadline-icon"><Icon name="target" :size="19" /></span><span><small>СЛЕДУЮЩИЙ ШАГ</small><strong>Выбери свою новую цель</strong><span>Задания и события ждут тебя</span></span><Icon name="arrow-up-right" class="deadline-arrow" :size="18" /></router-link>
      <router-link to="/arena?tab=events" class="event-shortcut"><span class="event-shortcut-icon"><Icon name="calendar" :size="19" /></span><span><strong>Ближайшие события</strong><small>Присоединяйся к новым возможностям</small></span><Icon name="arrow-right" :size="16" /></router-link>
    </section>
  </div>
  <section class="duels-section"><div class="section-head"><div><span class="eyebrow">ДВИГАЙСЯ ВМЕСТЕ</span><h2>Дружеское состязание <span class="inline-count">{{ active.length }}</span></h2></div><router-link class="text-arrow" to="/friends">Все друзья <Icon name="arrow-right" :size="15" /></router-link></div><div v-if="active.length" class="duel-grid"><DuelCard v-for="duel in active" :key="duel.id" :duel="duel" @refresh="load" /></div><div v-else class="empty-duels panel"><span class="empty-duels-icon"><Icon name="swords" :size="21" /></span><div><strong>Время объединиться в цель</strong><p>Найди друга и начни первую дуэль. Вместе можно больше.</p></div><router-link to="/friends" class="btn secondary small">Найти друга <Icon name="arrow-right" :size="15" /></router-link></div></section>
</section></template>
