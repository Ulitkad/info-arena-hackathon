<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, formatDate, futureLocal, iso, post } from "../api";
import { useArena } from "../stores/arena";
import Icon from "../components/Icon.vue";
import Modal from "../components/Modal.vue";
import Attachments from "../components/Attachments.vue";
import Avatar from "../components/Avatar.vue";

const store = useArena(),
  route = useRoute(),
  tab = ref("homework"),
  catalog = ref({ groups: [], subjects: [], loads: [] });
const modal = ref(""),
  loading = ref(false),
  reviews = ref([]),
  participants = ref([]),
  toast = (m) => store.toast(m, "error");
const hw = ref({
  title: "",
  text: "",
  subject_id: "",
  group_ids: [],
  deadline: futureLocal(2),
  optional: false,
  files: [],
});
const ev = ref({
  title: "",
  description: "",
  subject_id: "",
  group_ids: [],
  kind: "OTHER",
  points: 3,
  min_participants: 2,
  max_participants: 8,
  closes_at: futureLocal(2),
});
const canCreate = computed(() => catalog.value.loads?.length > 0);
onMounted(load);
watch(
  () => route.fullPath,
  () => {
    tab.value = route.query.tab === "events" ? "events" : "homework";
    load();
  },
);
watch(() => store.revision, load);
async function load() {
  loading.value = true;
  try {
    const [catalogData, homeworkData, eventsData] = await Promise.all([
      api(`/organizations/${store.user.organization_id}/catalog`),
      api("/homework"),
      api("/events"),
    ]);
    catalog.value = catalogData;
    store.homework = homeworkData;
    store.events = eventsData;
    const first = catalogData.loads?.[0];
    if (first && !hw.value.subject_id)
      hw.value.subject_id = String(first.subject_id);
    if (first && !ev.value.subject_id)
      ev.value.subject_id = String(first.subject_id);
    if (first && !hw.value.group_ids.length)
      hw.value.group_ids = [first.group_id];
    if (first && !ev.value.group_ids.length)
      ev.value.group_ids = [first.group_id];
  } catch (e) {
    toast(e.message);
  } finally {
    loading.value = false;
  }
}
const teachingGroups = computed(() =>
  [
    ...new Set(
      (catalog.value.loads || [])
        .filter(
          (l) =>
            String(l.subject_id) ===
            String(
              tab.value === "events"
                ? ev.value.subject_id
                : hw.value.subject_id,
            ),
        )
        .map((l) => l.group_id),
    ),
  ]
    .map((id) => catalog.value.groups.find((g) => g.id === id))
    .filter(Boolean),
);
function forGroup(id) {
  return catalog.value.groups.find((g) => g.id === id)?.name || "Группа";
}
async function createHomework() {
  await store.run(async () => {
    await post("/homework", {
      ...hw.value,
      subject_id: Number(hw.value.subject_id),
      deadline: iso(hw.value.deadline),
    });
    modal.value = "";
    hw.value.title = "";
    hw.value.text = "";
    hw.value.files = [];
    await load();
  }, "Задание опубликовано");
}
async function createEvent() {
  await store.run(async () => {
    await post("/events", {
      ...ev.value,
      subject_id: Number(ev.value.subject_id),
      group_ids: ev.value.group_ids.map(Number),
      closes_at: iso(ev.value.closes_at),
    });
    modal.value = "";
    ev.value.title = "";
    ev.value.description = "";
    await load();
  }, "Мероприятие опубликовано");
}
async function openReview(item) {
  try {
    reviews.value = await api(`/homework/${item.id}/submissions`);
    modal.value = `review:${item.id}`;
  } catch (e) {
    toast(e.message);
  }
}
async function mark(item, approve) {
  await store.run(
    async () => {
      await post(`/submissions/${item.id}/review`, {
        approve,
        feedback: item.editable_feedback || "",
      });
      await openReview({ id: item.homework_id });
      await load();
    },
    approve ? "Работа зачтена · +1 балл" : "Работа отправлена на доработку",
  );
}
async function openRoster(event) {
  try {
    participants.value = await api(`/events/${event.id}/participants`);
    modal.value = `participants:${event.id}`;
  } catch (e) {
    toast(e.message);
  }
}
async function closeEvent(event) {
  await store.run(async () => {
    await post(`/events/${event.id}/close`);
    await load();
  }, "Набор закрыт");
}
async function completeEvent(event) {
  await store.run(async () => {
    await post(`/events/${event.id}/complete`);
    await load();
  }, "Мероприятие завершено, баллы начислены");
}
async function kick(item) {
  await store.run(async () => {
    await api(
      `/events/${modal.value.split(":")[1]}/participants/${item.user.id}`,
      { method: "DELETE" },
    );
    await openRoster({ id: Number(modal.value.split(":")[1]) });
    await load();
  }, "Участник исключён");
}
function fileLink(url) {
  return `${location.origin}${url}`;
}
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
      </button>
    </div>
    <section v-if="tab === 'homework'" class="teacher-content">
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
    <section v-else class="teacher-content">
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
    <div v-if="!canCreate" class="empty-inline panel">
      <Icon name="settings" :size="20" /><span
        >Попроси управляющего настроить предметы и группы для твоей
        нагрузки.</span
      >
    </div>
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
  </section>
</template>
