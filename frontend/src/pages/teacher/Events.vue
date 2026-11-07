<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
import Modal from '../../components/Modal.vue';
import Avatar from '../../components/Avatar.vue';
const teacher = inject('teacher-page');
const { store, route, tab, catalog, modal, loading, reviews, participants, toast, hw, ev, canCreate, load, teachingGroups, forGroup, createHomework, createEvent, openReview, mark, openRoster, closeEvent, completeEvent, kick, fileLink } = teacher;
</script>

<template>
    <section class="teacher-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">СОВМЕСТНЫЕ ЦЕЛИ</span>
          <h2>Учебные мероприятия</h2>
        </div>
        <button
          class="btn primary"
          :disabled="!canCreate"
          @click="modal = 'event'"
        >
          <Icon name="plus" :size="17" />Создать событие
        </button>
      </div>
      <div v-if="!store.events.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="calendar" :size="28" /></span>
        <h3>События начинаются здесь</h3>
        <p>Создай встречу и пригласи учебные группы.</p>
      </div>
      <article
        v-for="event in store.events"
        :key="event.id"
        class="teacher-item panel"
      >
        <div class="teacher-item-copy">
          <div class="flex-between">
            <span class="eyebrow"
              >{{ event.subject?.name }} ·
              {{ event.group_ids.map(forGroup).join(", ") }}</span
            ><span
              class="chip"
              :class="event.status === 'OPEN' ? 'blue' : 'neutral'"
              >{{
                event.status === "OPEN" &&
                new Date(event.closes_at + "Z") > new Date()
                  ? "Открыт набор"
                  : event.status === "COMPLETED"
                    ? "Завершено"
                    : "Набор закрыт"
              }}</span
            >
          </div>
          <h3>{{ event.title }}</h3>
          <p>{{ event.description || "Учебное мероприятие" }}</p>
          <span class="meta-caption"
            ><Icon name="users" :size="14" />{{ event.count }}/{{
              event.max_participants
            }}
            участников · минимум {{ event.min_participants }}
            <Icon name="award" :size="14" />+{{ event.points }} баллов</span
          >
        </div>
        <div class="button-row wrap">
          <button class="btn secondary small" @click="openRoster(event)">
            <Icon name="users" :size="15" />Участники</button
          ><button
            v-if="event.status === 'OPEN'"
            class="btn secondary small"
            @click="closeEvent(event)"
          >
            Закрыть набор</button
          ><button
            v-if="event.status !== 'COMPLETED'"
            class="btn primary small"
            :disabled="event.count < event.min_participants"
            @click="completeEvent(event)"
          >
            <Icon name="check" :size="14" />Завершить
          </button>
        </div>
      </article>
    </section>

</template>
