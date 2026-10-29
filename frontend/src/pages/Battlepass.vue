<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'
import { api } from '../api'
const store = useArena(), route = useRoute(), router = useRouter()
onMounted(() => store.refreshStudent())
watch(() => store.revision, () => store.refreshStudent().catch(e => store.toast(e.message, 'error')))
const active = computed(() => store.passes.find(p => p.id === route.params.id) || store.passes[0])
function choose(event) { router.replace(`/battlepass/${event.target.value}`) }
function progress(reward) { return active.value.points >= reward.threshold }
</script>
<template><section v-if="active" class="battlepass-page" :style="{ '--pass-color': active.color }">
  <div class="bp-summary panel"><div class="bp-summary-copy"><span class="eyebrow">ТВОЙ ПРОГРЕСС</span><h2>{{ active.name }}</h2><p>{{ active.subtitle }}</p><label class="select-wrap"><Icon name="book" :size="16" /><select :value="active.id" aria-label="Выбрать боевой пропуск" @change="choose"><option v-for="item in store.passes" :key="item.id" :value="item.id">{{ item.name }}</option></select><Icon name="chevron-down" :size="15" /></label></div><div class="bp-stat"><div class="level-orbit"><span>{{ active.level }}</span></div><span>УРОВЕНЬ</span></div></div>
  <div class="bp-progress"><div><strong>{{ active.points }} баллов</strong><span v-if="active.rewards.find(r => r.threshold > active.points)">До {{ active.rewards.find(r => r.threshold > active.points).name }} · ещё {{ active.rewards.find(r => r.threshold > active.points).threshold - active.points }} {{ active.rewards.find(r => r.threshold > active.points).threshold - active.points === 1 ? 'балл' : 'баллов' }}</span><span v-else>Впечатляющий результат. Продолжай!</span></div><div class="progress-track large"><i :style="{ width: `${active.rewards.length ? Math.min(100, active.level / active.rewards.length * 100) : 100}%` }"></i></div></div>
  <div class="bp-timeline"><div class="bp-rail"></div><article v-for="(reward, index) in active.rewards" :key="reward.id" class="reward-row" :class="{ unlocked: reward.unlocked, reached: progress(reward) }"><span class="reward-node" :class="reward.unlocked ? 'node-unlocked' : progress(reward) ? 'node-current' : ''"> <Icon v-if="reward.unlocked" name="check" :size="16" /><span v-else>{{ String(index + 1).padStart(2, '0') }}</span></span><div class="reward-content panel"><div class="reward-art" :class="`reward-art-${reward.kind.toLowerCase()}`"><img v-if="reward.asset_url" :src="reward.asset_url" :alt="reward.name" /><Icon v-else :name="reward.icon || 'award'" :size="24" /></div><div class="reward-copy"><span class="eyebrow">{{ reward.threshold }} БАЛЛОВ</span><h3>{{ reward.name }}</h3><p>{{ reward.kind === 'TITLE' ? 'Новое звание в профиле' : reward.kind === 'FRAME' ? 'Стильная рамка аватара' : 'Достижение в коллекцию' }}</p></div><span v-if="reward.unlocked" class="chip unlocked-chip"><Icon name="check" :size="13" /> Открыто</span><span v-else class="reward-lock"><Icon name="lock" :size="15" /></span></div></article></div>
  <div class="bp-cta panel"><span class="bp-cta-icon"><Icon name="target" :size="20" /></span><div><strong>Новая цель уже рядом</strong><p>Выполняй задания и участвуй в событиях, чтобы открыть следующую награду.</p></div><router-link to="/arena" class="btn primary small">В арену <Icon name="arrow-right" :size="15" /></router-link></div>
</section><section v-else class="empty-page panel"><Icon name="layers" :size="32" /><h2>Пока нет боевых пропусков</h2><p>Твой управляющий скоро откроет первый путь к новым наградам.</p></section></template>
