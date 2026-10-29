<script setup>
import { computed, onMounted, ref } from "vue";
import { api, post, remove } from "../api";
import { useArena } from "../stores/arena";
import Icon from "../components/Icon.vue";
import Avatar from "../components/Avatar.vue";
import Modal from "../components/Modal.vue";
import DuelCard from "../components/DuelCard.vue";

const store = useArena(),
  tab = ref("friends"),
  friends = ref([]),
  results = ref([]),
  query = ref(""),
  searching = ref(false),
  modal = ref(null),
  duration = ref("3d"),
  subjectId = ref(""),
  busy = ref(false);
const incoming = computed(() =>
  friends.value.filter((f) => f.status === "PENDING" && f.incoming),
);
const accepted = computed(() =>
  friends.value.filter((f) => f.status === "ACCEPTED"),
);
const duelTarget = computed(() => modal.value?.user);
onMounted(load);
async function load() {
  busy.value = true;
  try {
    friends.value = await api("/friends");
    store.duels = await api("/duels");
  } catch (e) {
    store.toast(e.message, "error");
  } finally {
    busy.value = false;
  }
}
async function search() {
  if (query.value.trim().length < 2) {
    results.value = [];
    return;
  }
  searching.value = true;
  try {
    results.value = await api(
      `/users/search?q=${encodeURIComponent(query.value.trim())}`,
    );
  } catch (e) {
    store.toast(e.message, "error");
  } finally {
    searching.value = false;
  }
}
function relation(id) {
  return friends.value.find((f) => f.user.id === id);
}
async function add(id) {
  await store.run(async () => {
    await post(`/friends/${id}`);
    await load();
    await search();
  }, "Заявка в друзья отправлена");
}
async function respond(item, approve) {
  await store.run(
    async () => {
      await post(`/friendships/${item.id}/respond`, { approve });
      await load();
    },
    approve ? "Вы теперь друзья" : "Заявка отклонена",
  );
}
async function removeFriend(item) {
  if (!confirm(`Удалить ${item.user.display_name} из друзей?`)) return;
  await store.run(async () => {
    await remove(`/friendships/${item.id}`);
    await load();
  }, "Пользователь удалён из друзей");
}
async function challenge() {
  await store.run(async () => {
    await post("/duels", {
      opponent_id: duelTarget.value.id,
      duration: duration.value,
      subject_id: Number(subjectId.value) || null,
    });
    modal.value = null;
    await load();
  }, "Вызов отправлен!");
}
const commonSubjects = computed(() =>
  store.passes.filter(
    (p) =>
      p.subject_id &&
      duelTarget.value?.common_subject_ids?.includes(p.subject_id),
  ),
);
function relationLabel(user) {
  const r = relation(user.id);
  return !r
    ? "Добавить"
    : r.status === "ACCEPTED"
      ? "Вы друзья"
      : r.incoming
        ? "Ответить на заявку"
        : "Заявка отправлена";
}
</script>
<template>
  <section class="friends-page">
    <div class="social-banner">
      <span><Icon name="heart" :size="21" /></span>
      <div>
        <span class="eyebrow">ХОРОШИЕ РЕЗУЛЬТАТЫ РАСТУТ ВМЕСТЕ</span>
        <h2>Твоя команда сильнее</h2>
        <p>Дружи, поддерживай и устраивай дружеские состязания.</p>
      </div>
      <div class="social-counts">
        <div>
          <strong>{{ accepted.length }}</strong
          ><small>друзей</small>
        </div>
        <div>
          <strong>{{
            store.duels.filter((d) => d.status === "ACTIVE").length
          }}</strong
          ><small>дуэлей</small>
        </div>
      </div>
    </div>
    <div class="tabs social-tabs" role="tablist">
      <button
        v-for="item in [
          { id: 'friends', name: 'Мои друзья', icon: 'users' },
          { id: 'requests', name: 'Заявки', icon: 'user-plus' },
          { id: 'search', name: 'Поиск', icon: 'search' },
        ]"
        :key="item.id"
        role="tab"
        :aria-selected="tab === item.id"
        :class="{ active: tab === item.id }"
        @click="tab = item.id"
      >
        <Icon :name="item.icon" :size="16" />{{ item.name
        }}<span
          v-if="item.id === 'requests' && incoming.length"
          class="tab-count"
          >{{ incoming.length }}</span
        >
      </button>
    </div>
    <section v-if="tab === 'search'" class="social-content">
      <label class="search-box"
        ><Icon name="search" :size="19" /><input
          v-model="query"
          aria-label="Поиск участников"
          placeholder="Имя или @username"
          @input="search" /><span v-if="searching" class="mini-spinner"></span
        ><button
          v-if="query"
          class="icon-btn"
          aria-label="Очистить поиск"
          @click="
            query = '';
            results = [];
          "
        >
          <Icon name="x" :size="16" /></button
      ></label>
      <p class="field-hint">
        Участники твоего учебного учреждения, которые открыли приложение.
      </p>
      <article
        v-for="person in results"
        :key="person.id"
        class="friend-row panel"
      >
        <router-link :to="`/users/${person.id}`"
          ><Avatar :user="person" :size="44" /><span
            ><strong>{{ person.display_name }}</strong
            ><small>@{{ person.username || person.group_id }}</small></span
          ></router-link
        ><button
          v-if="!relation(person.id)"
          class="btn secondary small"
          @click="add(person.id)"
        >
          <Icon name="user-plus" :size="15" />Добавить</button
        ><button
          v-else-if="
            relation(person.id).status === 'PENDING' &&
            relation(person.id).incoming
          "
          class="btn primary small"
          @click="respond(relation(person.id), true)"
        >
          <Icon name="check" :size="15" />Принять</button
        ><span v-else class="chip neutral">{{ relationLabel(person) }}</span>
      </article>
      <div
        v-if="query.trim().length > 1 && !results.length && !searching"
        class="empty-page panel"
      >
        <Icon name="search" :size="26" />
        <h3>Пока не нашли участников</h3>
        <p>Проверь написание имени или username.</p>
      </div>
    </section>
    <section v-else-if="tab === 'requests'" class="social-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ТВОЁ ОКРУЖЕНИЕ</span>
          <h2>Новые знакомства</h2>
        </div>
        <span class="subtle-count">{{ incoming.length }} входящих</span>
      </div>
      <article v-for="item in incoming" :key="item.id" class="friend-row panel">
        <router-link :to="`/users/${item.user.id}`"
          ><Avatar :user="item.user" :size="44" /><span
            ><strong>{{ item.user.display_name }}</strong
            ><small
              >@{{ item.user.username || "участник" }} · приглашение в
              друзья</small
            ></span
          ></router-link
        >
        <div class="button-row">
          <button class="btn secondary small" @click="respond(item, false)">
            Позже</button
          ><button class="btn primary small" @click="respond(item, true)">
            <Icon name="check" :size="15" />Принять
          </button>
        </div>
      </article>
      <div v-if="!incoming.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="heart" :size="26" /></span>
        <h3>У тебя пока нет новых заявок</h3>
        <p>Тем временем можно найти друзей среди ребят из своего учреждения.</p>
        <button class="btn secondary small" @click="tab = 'search'">
          <Icon name="search" :size="15" />Найти друга
        </button>
      </div>
    </section>
    <section v-else class="social-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ТВОЁ ОКРУЖЕНИЕ</span>
          <h2>Мои друзья</h2>
        </div>
        <button class="btn secondary small" @click="tab = 'search'">
          <Icon name="user-plus" :size="15" />Найти друзей
        </button>
      </div>
      <article v-for="item in accepted" :key="item.id" class="friend-row panel">
        <router-link :to="`/users/${item.user.id}`"
          ><Avatar :user="item.user" :size="44" /><span
            ><strong>{{ item.user.display_name }}</strong
            ><small>@{{ item.user.username || "участник арены" }}</small></span
          ></router-link
        >
        <div class="button-row">
          <button
            class="icon-btn"
            aria-label="Вызвать на дуэль"
            title="Вызвать на дуэль"
            @click="
              modal = { user: item.user };
              duration = '3d';
              subjectId = '';
            "
          >
            <Icon name="swords" :size="18" /></button
          ><button
            class="icon-btn danger-icon"
            aria-label="Удалить из друзей"
            title="Удалить из друзей"
            @click="removeFriend(item)"
          >
            <Icon name="x" :size="18" />
          </button>
        </div>
      </article>
      <div v-if="!accepted.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="users" :size="26" /></span>
        <h3>Самое время расширить команду</h3>
        <p>Добавь одногруппников и вдохновляйтесь новыми результатами.</p>
        <button class="btn primary small" @click="tab = 'search'">
          <Icon name="search" :size="15" />Найти ребят
        </button>
      </div>
      <section class="friends-duels">
        <div class="section-head">
          <div>
            <span class="eyebrow">ЗНАНИЯ СИЛЬНЕЕ УДАЧИ</span>
            <h2>Дружеские дуэли</h2>
          </div>
        </div>
        <div v-if="store.duels.length" class="duel-grid">
          <DuelCard
            v-for="duel in store.duels"
            :key="duel.id"
            :duel="duel"
            @refresh="load"
          />
        </div>
        <div v-else class="empty-inline panel">
          <Icon name="swords" :size="19" /><span
            >Первая дуэль — повод начать новую историю. Вызови друга!</span
          >
        </div>
      </section>
    </section>
    <Modal
      v-if="duelTarget"
      title="Настроить дружеское состязание"
      @close="modal = null"
      ><div class="modal-form">
        <div class="challenge-with">
          <Avatar :user="duelTarget" :size="48" /><span
            ><small>ТВОЙ СОПЕРНИК</small
            ><strong>{{ duelTarget.display_name }}</strong></span
          >
        </div>
        <fieldset class="segmented-field duration-options">
          <legend>Продолжительность</legend>
          <label
            v-for="item in [
              { id: '1d', name: '1 день' },
              { id: '3d', name: '3 дня' },
              { id: '7d', name: '7 дней' },
              { id: '1m', name: '1 месяц' },
            ]"
            :key="item.id"
            ><input v-model="duration" type="radio" :value="item.id" /><span>{{
              item.name
            }}</span></label
          >
        </fieldset>
        <label class="field-label"
          >Дисциплина<select v-model="subjectId">
            <option value="">Общий зачёт · все учебные баллы</option>
            <option
              v-for="subject in commonSubjects"
              :key="subject.subject_id"
              :value="String(subject.subject_id)"
            >
              {{ subject.name }}
            </option>
          </select></label
        >
        <p class="field-hint">
          <Icon name="sparkles" :size="14" />Учитываются только новые баллы за
          зачтённые задания и завершённые события.
        </p>
        <button class="btn primary modal-submit" @click="challenge">
          <Icon name="swords" :size="16" />Бросить вызов другу
        </button>
      </div></Modal
    >
  </section>
</template>
