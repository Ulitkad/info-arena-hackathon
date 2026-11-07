<script setup>
import { inject } from 'vue'
import Icon from '../../components/Icon.vue'

const teacher = inject('teacher-page')
const { catalog, rewards, selectedRewardSubject, modal, editRewardId, resetReward, editReward, deleteReward } = teacher
const currentRewards = () => rewards.value.filter(item => item.subject_id === selectedRewardSubject.value)
</script>

<template>
  <section class="teacher-content management-content">
    <div class="section-head">
      <div><span class="eyebrow">ПУТЬ УЧЕНИКОВ</span><h2>Боевой пропуск предмета</h2></div>
      <button class="btn primary" :disabled="!selectedRewardSubject" @click="resetReward"><Icon name="plus" :size="16" />Добавить уровень</button>
    </div>
    <label class="field-label reward-subject-picker">Предмет<select v-model="selectedRewardSubject">
      <option v-for="subject in catalog.subjects" :key="subject.id" :value="subject.id">{{ subject.name }}</option>
    </select></label>
    <div v-if="selectedRewardSubject" class="reward-scope">
      <div class="catalog-heading"><span class="eyebrow">{{ catalog.subjects.find(s => s.id === selectedRewardSubject)?.name?.toUpperCase() }}</span><span class="subtle-count">{{ currentRewards().length }} уровней</span></div>
      <article v-for="item in currentRewards()" :key="item.id" class="manager-reward-row panel">
        <span class="reward-art" :class="`reward-art-${item.kind.toLowerCase()}`"><Icon :name="item.icon || 'sparkles'" :size="20" /></span>
        <span class="manager-reward-name"><strong>{{ item.name }}</strong><small>{{ { TITLE: 'Звание', FRAME: 'Рамка', BADGE: 'Достижение', CUSTOM: 'Кастомная награда' }[item.kind] }} · {{ item.threshold }} баллов</small></span>
        <span class="button-row"><button class="icon-btn" :aria-label="`Изменить награду ${item.name}`" @click="editReward(item)"><Icon name="pencil" :size="16" /></button><button class="icon-btn danger-icon" :aria-label="`Удалить награду ${item.name}`" @click="deleteReward(item)"><Icon name="trash" :size="16" /></button></span>
      </article>
      <p v-if="!currentRewards().length" class="empty-inline">В этом предметном пропуске пока нет уровней.</p>
    </div>
  </section>
</template>
