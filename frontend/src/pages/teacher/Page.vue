<script setup>
import { provide } from 'vue';
import { useTeacherPage } from '../../composables/useTeacherPage';
import Icon from '../../components/Icon.vue';
import TeacherHomework from './Homework.vue';
import TeacherEvents from './Events.vue';
import TeacherRewards from './Rewards.vue';
import TeacherModals from './Modals.vue';
const teacher = useTeacherPage();
provide('teacher-page', teacher);
const { store, route, tab, catalog, modal, loading, reviews, participants, toast, hw, ev, canCreate, load, teachingGroups, forGroup, createHomework, createEvent, openReview, mark, openRoster, closeEvent, completeEvent, kick, fileLink, formatDate } = teacher;
</script>

<template>
  <section class="teacher-page">
    <div class="teacher-stats">
      <div class="stat-card panel">
        <span class="stat-icon subjects"><Icon name="book" /></span
        ><span
          ><strong>{{ catalog.subjects.length }}</strong
          ><small>предмета</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon wins"><Icon name="users" /></span
        ><span
          ><strong>{{ catalog.groups.length }}</strong
          ><small>учебных групп</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon awards"><Icon name="file" /></span
        ><span
          ><strong>{{
            store.homework.reduce((n, h) => n + h.pending_count, 0)
          }}</strong
          ><small>работ на проверке</small></span
        >
      </div>
    </div>
    <div class="tabs teacher-tabs" role="tablist">
      <button
        role="tab"
        :aria-selected="tab === 'homework'"
        :class="{ active: tab === 'homework' }"
        @click="tab = 'homework'"
      >
        <Icon name="book" :size="16" />Задания</button
      ><button
        role="tab"
        :aria-selected="tab === 'events'"
        :class="{ active: tab === 'events' }"
        @click="tab = 'events'"
      >
        <Icon name="calendar" :size="16" />Мероприятия
      </button><button
        role="tab"
        :aria-selected="tab === 'rewards'"
        :class="{ active: tab === 'rewards' }"
        @click="tab = 'rewards'"
      ><Icon name="award" :size="16" />Боевые пропуски</button>
    </div>
    <TeacherHomework v-if="tab === 'homework'" />
    <TeacherEvents v-else-if="tab === 'events'" />
    <TeacherRewards v-else-if="tab === 'rewards'" />
    <div v-if="tab !== 'rewards' && !canCreate" class="empty-inline panel">
      <Icon name="settings" :size="20" /><span>Попроси управляющего настроить предметы и группы для твоей нагрузки.</span>
    </div>
    <TeacherModals />
  </section>
</template>
