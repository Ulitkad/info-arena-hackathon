<script setup>
import { inject } from 'vue';
import Icon from '../../components/Icon.vue';
import Modal from '../../components/Modal.vue';
import Attachments from '../../components/Attachments.vue';
import Avatar from '../../components/Avatar.vue';
const teacher = inject('teacher-page');
const { store, route, tab, catalog, modal, loading, reviews, participants, toast, hw, ev, canCreate, load, teachingGroups, forGroup, createHomework, createEvent, openReview, mark, openRoster, closeEvent, completeEvent, kick, fileLink } = teacher;
</script>

<template>
    <section class="teacher-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">УЧЕБНЫЙ ПРОЦЕСС</span>
          <h2>Домашние задания</h2>
        </div>
        <button
          class="btn primary"
          :disabled="!canCreate"
          @click="modal = 'homework'"
        >
          <Icon name="plus" :size="17" />Создать задание
        </button>
      </div>
      <div v-if="!store.homework.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="book" :size="28" /></span>
        <h3>Заданий пока нет</h3>
        <p>Создай первое задание для своей учебной группы.</p>
        <button
          class="btn primary small"
          :disabled="!canCreate"
          @click="modal = 'homework'"
        >
          Создать задание
        </button>
      </div>
      <article
        v-for="item in store.homework"
        :key="item.id"
        class="teacher-item panel"
      >
        <div class="teacher-item-copy">
          <span class="eyebrow"
            >{{ item.subject?.name }} ·
            {{ item.group_ids.map(forGroup).join(", ") }}</span
          >
          <h3>{{ item.title }}</h3>
          <p>{{ item.text }}</p>
          <span class="meta-caption"
            ><Icon name="clock" :size="14" />До
            {{ formatDate(item.deadline) }} · +1 балл
            <span v-if="item.optional" class="optional"
              >· необязательно</span
            ></span
          >
        </div>
        <button
          class="btn"
          :class="item.pending_count ? 'primary' : 'secondary'"
          @click="openReview(item)"
        >
          <Icon name="check-check" :size="16" />{{
            item.pending_count
              ? `${item.pending_count} на проверке`
              : "Работы учеников"
          }}
        </button>
      </article>
    </section>

</template>
