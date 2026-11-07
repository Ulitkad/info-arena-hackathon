<script setup>
import { inject } from 'vue';
import Modal from '../../components/Modal.vue';
import Icon from '../../components/Icon.vue';
import Attachments from '../../components/Attachments.vue';
import Avatar from '../../components/Avatar.vue';
import { frameStyles } from '../../constants/frameStyles';
const teacher = inject('teacher-page');
const { store, route, tab, catalog, rewards, selectedRewardSubject, reward, editRewardId, modal, loading, reviews, participants, toast, hw, ev, canCreate, load, teachingGroups, forGroup, createHomework, createEvent, openReview, mark, openRoster, closeEvent, completeEvent, kick, fileLink, formatDate, saveReward } = teacher;
</script>

<template>
    <Modal
      v-if="modal === 'homework'"
      title="Новое задание"
      wide
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="createHomework">
        <label class="field-label"
          >Предмет<select v-model="hw.subject_id" required>
            <option disabled value="">Выбери предмет</option>
            <option
              v-for="subject in catalog.subjects"
              :key="subject.id"
              :value="String(subject.id)"
            >
              {{ subject.name }}
            </option>
          </select></label
        >
        <fieldset class="choice-field">
          <legend>Для каких групп</legend>
          <label
            v-for="group in teachingGroups"
            :key="group.id"
            class="check-option"
            ><input
              v-model="hw.group_ids"
              type="checkbox"
              :value="group.id"
            /><span class="fake-check"><Icon name="check" :size="13" /></span
            >{{ group.name }}</label
          >
        </fieldset>
        <label class="field-label"
          >Название<input
            v-model.trim="hw.title"
            maxlength="160"
            required
            placeholder="Например, алгоритмы и рекурсия" /></label
        ><label class="field-label"
          >Описание<textarea
            v-model.trim="hw.text"
            rows="5"
            maxlength="10000"
            placeholder="Добавь условия задания или приложи файл"
          ></textarea></label
        ><Attachments v-model="hw.files" />
        <div class="form-grid">
          <label class="field-label"
            >Дедлайн<input
              v-model="hw.deadline"
              type="datetime-local"
              required /></label
          ><label class="check-line"
            ><input v-model="hw.optional" type="checkbox" />Задание
            необязательное</label
          >
        </div>
        <div class="modal-submit-row">
          <span
            ><Icon name="award" :size="16" /> Награда за проверенную работу:
            +1</span
          ><button
            class="btn primary"
            :disabled="
              store.saving ||
              !hw.group_ids.length ||
              (!hw.text && !hw.files.length)
            "
          >
            <Icon name="send" :size="16" />Опубликовать
          </button>
        </div>
      </form></Modal
    >
    <Modal
      v-else-if="modal === 'event'"
      title="Новое мероприятие"
      wide
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="createEvent">
        <label class="field-label"
          >Предмет<select v-model="ev.subject_id" required>
            <option disabled value="">Выбери предмет</option>
            <option
              v-for="subject in catalog.subjects"
              :key="subject.id"
              :value="String(subject.id)"
            >
              {{ subject.name }}
            </option>
          </select></label
        >
        <fieldset class="choice-field">
          <legend>Для каких групп</legend>
          <label
            v-for="group in teachingGroups"
            :key="group.id"
            class="check-option"
            ><input
              v-model="ev.group_ids"
              type="checkbox"
              :value="group.id"
            /><span class="fake-check"><Icon name="check" :size="13" /></span
            >{{ group.name }}</label
          >
        </fieldset>
        <fieldset class="segmented-field">
          <legend>Формат</legend>
          <label
            ><input v-model="ev.kind" value="OTHER" type="radio" /><span
              >Событие</span
            ></label
          ><label
            ><input v-model="ev.kind" value="DUTY" type="radio" /><span
              >Дежурство · +2 балла</span
            ></label
          >
        </fieldset>
        <label v-if="ev.kind === 'OTHER'" class="field-label"
          >Название<input
            v-model.trim="ev.title"
            maxlength="160"
            required
            placeholder="Имя события" /></label
        ><label class="field-label"
          >Описание<textarea
            v-model.trim="ev.description"
            rows="3"
            maxlength="10000"
            placeholder="Что будем делать вместе?"
          />
        </label>
        <div v-if="ev.kind === 'OTHER'" class="field-label">
          <span class="input-heading">Баллы за участие</span>
          <div class="points-control">
            <button
              type="button"
              aria-label="Минус один балл"
              @click="ev.points = Math.max(1, ev.points - 1)"
            >
              −</button
            ><input
              v-model.number="ev.points"
              type="number"
              min="1"
              max="30"
            /><button
              type="button"
              aria-label="Плюс один балл"
              @click="ev.points = Math.min(30, ev.points + 1)"
            >
              +</button
            ><input v-model.number="ev.points" type="range" min="1" max="30" />
          </div>
        </div>
        <div class="form-grid">
          <label class="field-label"
            >Минимум для проведения<input
              v-model.number="ev.min_participants"
              type="number"
              min="1"
              required /></label
          ><label class="field-label"
            >Мест всего<input
              v-model.number="ev.max_participants"
              type="number"
              min="1"
              required /></label
          ><label class="field-label"
            >Закрыть набор<input
              v-model="ev.closes_at"
              type="datetime-local"
              required
          /></label>
        </div>
        <button
          class="btn primary modal-submit"
          :disabled="store.saving || !ev.group_ids.length"
        >
          Опубликовать событие <Icon name="arrow-right" :size="16" />
        </button></form
    ></Modal>
    <Modal
      v-else-if="modal.startsWith('review:')"
      title="Работы учеников"
      wide
      @close="modal = ''"
      ><div class="review-list">
        <div v-if="!reviews.length" class="empty-inline">
          <Icon name="check-check" :size="20" /><span
            >Работ на проверке нет. Скоро здесь появятся новые.</span
          >
        </div>
        <article v-for="item in reviews" :key="item.id" class="review-item">
          <div class="review-student">
            <Avatar :user="item.student" :size="40" />
            <div>
              <strong>{{ item.student.display_name }}</strong
              ><span class="eyebrow"
                >{{ formatDate(item.submitted_at) }} ·
                {{
                  item.status === "SUBMITTED"
                    ? "НА ПРОВЕРКЕ"
                    : item.status === "APPROVED"
                      ? "ЗАЧТЕНО"
                      : "НА ДОРАБОТКЕ"
                }}</span
              >
            </div>
          </div>
          <p v-if="item.text" class="review-text">{{ item.text }}</p>
          <div v-if="item.files.length" class="homework-attachments">
            <a
              v-for="file in item.files"
              :key="file"
              :href="fileLink(file)"
              target="_blank"
              rel="noopener noreferrer"
              ><Icon name="file" :size="15" />Открыть файл<Icon
                name="external"
                :size="13"
            /></a>
          </div>
          <p v-if="item.feedback" class="muted">
            Комментарий: {{ item.feedback }}
          </p>
          <div v-if="item.status === 'SUBMITTED'" class="review-actions">
            <input
              v-model="item.editable_feedback"
              class="review-feedback"
              maxlength="2000"
              placeholder="Комментарий, если нужно вернуть на доработку"
            /><button class="btn primary small" @click="mark(item, true)">
              <Icon name="check" :size="14" />Засчитать · +1</button
            ><button class="btn secondary small" @click="mark(item, false)">
              На доработку
            </button>
          </div>
        </article>
      </div></Modal
    >
    <Modal
      v-else-if="modal.startsWith('participants:')"
      title="Участники мероприятия"
      @close="modal = ''"
      ><div class="review-list">
        <article
          v-for="item in participants"
          :key="item.user.id"
          class="participant-row"
        >
          <Avatar :user="item.user" :size="38" />
          <div class="participant-copy">
            <strong>{{ item.user.display_name }}</strong
            ><span class="eyebrow"
              >{{
                { JOINED: "УЧАСТВУЕТ", LEFT: "ПОКИНУЛ", KICKED: "ИСКЛЮЧЁН" }[
                  item.status
                ]
              }}<span v-if="item.blacklisted">
                · НЕ МОЖЕТ ЗАПИСАТЬСЯ СНОВА</span
              ></span
            >
          </div>
          <button
            v-if="item.status === 'JOINED'"
            class="icon-btn danger-icon"
            aria-label="Исключить участника"
            @click="kick(item)"
          >
            <Icon name="x" :size="17" />
          </button>
        </article>
        <div v-if="!participants.length" class="empty-inline">
          Участники пока не записались.
        </div>
      </div></Modal
    >
    <Modal
      v-else-if="modal === 'reward'"
      :title="editRewardId ? 'Изменить награду' : 'Новый уровень'"
      @close="modal = ''"
    ><form class="modal-form" @submit.prevent="saveReward">
      <p class="muted">Награда будет добавлена в предметный пропуск «{{ catalog.subjects.find(s => s.id === selectedRewardSubject)?.name }}».</p>
       <label v-if="reward.kind !== 'FRAME'" class="field-label">Текст награды<input v-model.trim="reward.name" maxlength="100" required placeholder="Например, +1 балл к худшей контрольной в семестре" /></label>
       <div v-else class="field-label frame-style-field"><span>Стиль рамки</span><div class="frame-style-grid"><label v-for="style in frameStyles" :key="style.id" class="frame-style-option" :class="{ selected: reward.frame_style === style.id }"><input v-model="reward.frame_style" type="radio" :value="style.id" required @change="reward.name = style.name" /><span class="avatar frame-style-swatch" :class="`frame-${style.id}`"><Icon :name="style.icon" :size="18" /></span><span><strong>{{ style.name }}</strong><small>{{ style.description }}</small></span><Icon v-if="reward.frame_style === style.id" name="check" :size="14" class="selected-check" /></label></div></div>
      <div class="form-grid">
         <label class="field-label">Тип награды<select v-model="reward.kind" @change="reward.frame_style = reward.kind === 'FRAME' ? (reward.frame_style || frameStyles[0].id) : null; reward.name = reward.kind === 'FRAME' ? (frameStyles.find(item => item.id === reward.frame_style)?.name || '') : reward.name"><option value="CUSTOM">Своя награда</option><option value="BADGE">Достижение</option><option value="TITLE">Звание</option><option value="FRAME">Рамка профиля</option></select></label>
        <label class="field-label">Нужно баллов<input v-model.number="reward.threshold" type="number" min="1" max="100000" required /></label>
      </div>
      <label class="field-label">Символ<select v-model="reward.icon"><option v-for="name in ['sparkles', 'award', 'crown', 'flame', 'star', 'shield']" :key="name" :value="name">{{ name }}</option></select></label>
      <button class="btn primary modal-submit" :disabled="store.saving || !selectedRewardSubject">{{ editRewardId ? 'Сохранить' : 'Создать уровень' }} <Icon name="check" :size="15" /></button>
    </form></Modal>
</template>
