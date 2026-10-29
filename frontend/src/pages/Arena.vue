<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useArena } from "../stores/arena";
import { date, formatDate, post } from "../api";
import Modal from "../components/Modal.vue";
import Attachments from "../components/Attachments.vue";
import Icon from "../components/Icon.vue";
const store = useArena(),
  route = useRoute(),
  router = useRouter();
const tab = ref("homework"),
  submission = ref(null),
  answer = ref(""),
  files = ref([]),
  busy = ref(false),
  focusId = ref(null);
function initialTab() {
  return route.query.tab === "events" ? "events" : "homework";
}
watch(
  () => route.fullPath,
  () => {
    tab.value = initialTab();
    focusId.value = Number(route.query.homework) || null;
  },
  { immediate: true },
);
onMounted(load);
watch(() => store.revision, load);
async function load() {
  busy.value = true;
  try {
    await store.refreshStudent();
  } catch (e) {
    store.toast(e.message, "error");
  } finally {
    busy.value = false;
  }
}
const subjects = computed(() => store.passes.filter((p) => p.subject_id));
const now = Date.now();
const tasks = computed(() =>
  store.homework.filter((h) => !focusId.value || h.id === focusId.value),
);
function state(item) {
  if (item.submission?.status === "APPROVED") return ["Зачтено", "done"];
  if (item.submission?.status === "SUBMITTED") return ["На проверке", "wait"];
  if (item.submission?.status === "REVISION") return ["На доработку", "revise"];
  if (date(item.deadline)?.getTime() <= now)
    return ["Срок сдачи истёк", "closed"];
  return ["Можно выполнить", "open"];
}
function openSubmission(item) {
  submission.value = item;
  answer.value = item.submission?.text || "";
  files.value = [...(item.submission?.files || [])];
}
async function submit() {
  if (!answer.value.trim() && !files.value.length) {
    store.toast("Добавьте текст или файл", "error");
    return;
  }
  await store.run(async () => {
    await post(`/homework/${submission.value.id}/submit`, {
      text: answer.value,
      files: files.value,
    });
    submission.value = null;
    await load();
  }, "Работа отправлена преподавателю");
}
async function join(item) {
  await store.run(
    () =>
      post(
        `/events/${item.id}/${item.participant?.status === "JOINED" ? "leave" : "join"}`,
      ),
    item.participant?.status === "JOINED"
      ? "Ты покинул список участников"
      : "Ты записан на мероприятие",
  );
  await load();
}
</script>
<template>
  <section class="arena-page" :aria-busy="busy">
    <div class="arena-banner">
      <div class="arena-banner-content">
        <span class="eyebrow"
          ><Icon name="target" :size="15" /> ПРОСТРАНСТВО ВОЗМОЖНОСТЕЙ</span
        >
        <h2>Каждый шаг<br />ведёт дальше.</h2>
        <p>Задания и события складываются в твой опыт.</p>
        <div class="arena-subjects">
          <span v-for="subject in subjects" :key="subject.id"
            ><i :style="{ background: subject.color }"></i
            >{{ subject.name }}</span
          >
        </div>
      </div>
      <img
        src="https://images.unsplash.com/photo-1481627834876-b7833e8f5570?auto=format&fit=crop&w=1000&q=80"
        alt="Стол с открытой книгой, воплощающий пространство для новых знаний"
        fetchpriority="high"
      />
    </div>
    <div class="tabs arena-tabs" role="tablist" aria-label="Содержание арены">
      <button
        role="tab"
        :aria-selected="tab === 'homework'"
        :class="{ active: tab === 'homework' }"
        @click="
          tab = 'homework';
          router.replace({ query: {} });
        "
      >
        <Icon name="book" :size="16" />Домашние задания
        <span>{{
          store.homework.filter(
            (h) => !h.submission || h.submission.status === "REVISION",
          ).length
        }}</span></button
      ><button
        role="tab"
        :aria-selected="tab === 'events'"
        :class="{ active: tab === 'events' }"
        @click="
          tab = 'events';
          router.replace({ query: { tab: 'events' } });
        "
      >
        <Icon name="calendar" :size="16" />Мероприятия
        <span>{{
          store.events.filter((e) => e.status === "OPEN").length
        }}</span>
      </button>
    </div>
    <section v-if="tab === 'homework'" class="arena-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ТВОИ ЗАДАНИЯ</span>
          <h2>Учись и открывай больше</h2>
        </div>
        <span class="subtle-count">+1 балл за зачёт</span>
      </div>
      <div v-if="!tasks.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="book" :size="28" /></span>
        <h3>
          {{
            focusId ? "Задание больше недоступно" : "Новые задания уже в пути"
          }}
        </h3>
        <p>
          {{
            focusId
              ? "Возможно, срок сдачи уже завершился."
              : "Загляни сюда позже, чтобы продолжить свой путь."
          }}
        </p>
        <button
          v-if="focusId"
          class="btn secondary small"
          @click="router.replace('/arena')"
        >
          Все задания
        </button>
      </div>
      <article
        v-for="item in tasks"
        :key="item.id"
        class="homework-card panel"
        :class="{ 'task-focused': focusId === item.id }"
      >
        <div class="homework-top">
          <div class="subject-dot" :style="{ background: item.subject?.color }">
            <Icon name="book" :size="16" />
          </div>
          <span class="subject-name">{{ item.subject?.name }}</span
          ><span class="chip" :class="`state-${state(item)[1]}`">{{
            state(item)[0]
          }}</span>
        </div>
        <div class="homework-main">
          <h3>{{ item.title }}</h3>
          <p class="homework-description">{{ item.text }}</p>
          <div v-if="item.files?.length" class="homework-attachments">
            <a
              v-for="file in item.files"
              :key="file"
              :href="file"
              target="_blank"
              rel="noreferrer"
              ><Icon name="file" :size="15" /> Материалы задания
              <Icon name="external" :size="13"
            /></a>
          </div>
          <div class="homework-meta">
            <span
              ><Icon name="clock" :size="15" />Сдать до
              {{ formatDate(item.deadline) }}</span
            ><span v-if="item.optional" class="optional"
              ><Icon name="sparkles" :size="14" />Можно пропустить</span
            ><span><Icon name="award" :size="15" />+1 балл</span>
          </div>
          <div v-if="item.submission?.feedback" class="feedback">
            <strong>Комментарий преподавателя</strong>
            <p>{{ item.submission.feedback }}</p>
          </div>
        </div>
        <button
          v-if="
            !item.optional &&
            !item.submission?.status?.match?.(/APPROVED|SUBMITTED/) &&
            date(item.deadline)?.getTime() > Date.now()
          "
          class="btn primary task-action"
          @click="openSubmission(item)"
        >
          {{
            item.submission?.status === "REVISION"
              ? "Отправить исправления"
              : "Выполнить задание"
          }}<Icon name="arrow-right" :size="16" /></button
        ><button
          v-else-if="item.submission"
          class="btn secondary task-action"
          disabled
        >
          <Icon name="check" :size="15" />{{
            item.submission.status === "APPROVED"
              ? "Работа зачтена"
              : item.submission.status === "SUBMITTED"
                ? "Ожидает проверки"
                : "Дедлайн закрыт"
          }}
        </button>
      </article>
    </section>
    <section v-else class="arena-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ВМЕСТЕ ЯРЧЕ</span>
          <h2>Будь частью событий</h2>
        </div>
        <span class="subtle-count"
          >{{ store.events.filter((e) => e.status === "OPEN").length }} набора
          открыто</span
        >
      </div>
      <div v-if="!store.events.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="calendar" :size="28" /></span>
        <h3>Впереди много интересного</h3>
        <p>Преподаватели сообщат, когда появится новое событие.</p>
      </div>
      <article
        v-for="event in store.events"
        :key="event.id"
        class="event-card panel"
      >
        <div class="event-card-main">
          <div
            class="event-icon"
            :class="event.kind === 'DUTY' ? 'event-duty' : ''"
          >
            <Icon
              :name="event.kind === 'DUTY' ? 'layers' : 'calendar'"
              :size="22"
            />
          </div>
          <div>
            <span class="eyebrow"
              >{{ event.subject?.name }} ·
              {{ event.kind === "DUTY" ? "ОБЩЕЕ ДЕЛО" : "МЕРОПРИЯТИЕ" }}</span
            >
            <h3>{{ event.title }}</h3>
            <p v-if="event.description">{{ event.description }}</p>
          </div>
        </div>
        <div class="event-metrics">
          <span
            ><Icon name="award" :size="15" /><strong
              >+{{ event.points }}</strong
            >
            баллов</span
          ><span
            ><Icon name="users" :size="15" />{{ event.count }}<i>/</i
            >{{ event.max_participants }} мест</span
          ><span
            ><Icon name="clock" :size="15" />До
            {{ formatDate(event.closes_at) }}</span
          >
        </div>
        <div class="event-bottom">
          <span class="event-min"
            >Набор от {{ event.min_participants }} участников</span
          ><button
            v-if="
              event.status === 'OPEN' &&
              date(event.closes_at)?.getTime() > Date.now()
            "
            class="btn"
            :class="
              event.participant?.status === 'JOINED' ? 'secondary' : 'primary'
            "
            :disabled="
              store.saving ||
              (event.count >= event.max_participants &&
                event.participant?.status !== 'JOINED')
            "
            @click="join(event)"
          >
            {{
              event.participant?.status === "JOINED"
                ? "Покинуть список"
                : event.count >= event.max_participants
                  ? "Мест больше нет"
                  : "Записаться"
            }}<Icon
              :name="
                event.participant?.status === 'JOINED' ? 'check' : 'arrow-right'
              "
              :size="15"
            /></button
          ><span v-else class="chip neutral">{{
            event.status === "COMPLETED"
              ? "Завершено"
              : event.status === "OPEN"
                ? "Набор закрыт"
                : "Набор закрыт"
          }}</span>
        </div>
      </article>
    </section>
    <Modal v-if="submission" title="Моя работа" wide @close="submission = null"
      ><div class="modal-form">
        <label class="field-label"
          >{{ submission.title
          }}<span class="field-hint">Можно добавить текст и файлы</span
          ><textarea
            v-model="answer"
            rows="5"
            maxlength="10000"
            placeholder="Опиши решение, приложи результат работы…"
          ></textarea></label
        ><Attachments v-model="files" /><button
          class="btn primary modal-submit"
          :disabled="store.saving"
          @click="submit"
        >
          <Icon name="send" :size="16" />Отправить на проверку
        </button>
      </div></Modal
    >
  </section>
</template>
