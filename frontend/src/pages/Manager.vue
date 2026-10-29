<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, remove, post, put, roleName } from "../api";
import { useArena } from "../stores/arena";
import Modal from "../components/Modal.vue";
import Icon from "../components/Icon.vue";
import Avatar from "../components/Avatar.vue";

const store = useArena(),
  route = useRoute(),
  router = useRouter();
const tab = computed(
  () =>
    route.params.tab || (store.user.role === "ADMIN" ? "groups" : "requests"),
);
const catalog = ref({ groups: [], subjects: [], links: [], loads: [] }),
  members = ref([]),
  requests = ref([]),
  invites = ref([]),
  rewards = ref([]);
const modal = ref(""),
  loading = ref(false),
  search = ref(""),
  message = ref("");
const groupName = ref(""),
  subjectName = ref(""),
  subjectColor = ref("#4f8fe8"),
  inviteGroup = ref(null);
const assign = ref({ query: "", role: "STUDENT", group_id: "", loads: [] });
const reward = ref({
  name: "",
  kind: "BADGE",
  threshold: 10,
  subject_id: "",
  asset_url: null,
  icon: "award",
});
const editRewardId = ref(null);
const organizations = ref([]), inviteUrl = ref("");
const organizationId = computed(() => store.user.role === "ADMIN"
  ? Number(route.query.organization) || organizations.value[0]?.id || null
  : store.user.organization_id);
const filteredMembers = computed(() =>
  members.value.filter(
    (m) =>
      !search.value ||
      `${m.display_name} @${m.username || ""} ${m.role} ${catalog.value.groups.find(g => g.id === m.group_id)?.name || ""}`
        .toLocaleLowerCase("ru")
        .includes(search.value.toLocaleLowerCase("ru")),
  ),
);
const pendingByGroup = computed(() =>
  catalog.value.groups
    .map((group) => ({
      group,
      items: requests.value.filter((item) => item.group.id === group.id),
    }))
    .filter((item) => item.items.length),
);
const studentCount = computed(
  () => members.value.filter((m) => m.role === "STUDENT").length,
);
async function load() {
  loading.value = true;
  message.value = "";
  try {
    if (!organizationId.value) {
      catalog.value = { groups: [], subjects: [], links: [], loads: [] };
      return;
    }
    const oid = organizationId.value;
    const results = await Promise.all([
      api(`/organizations/${oid}/catalog`),
      api(`/organizations/${oid}/members`),
      api(`/organizations/${oid}/requests`),
      api(`/organizations/${oid}/invites`),
      api(`/organizations/${oid}/rewards`),
    ]);
    [
      catalog.value,
      members.value,
      requests.value,
      invites.value,
      rewards.value,
    ] = results;
  } catch (e) {
    message.value = e.message;
  } finally {
    loading.value = false;
  }
}
onMounted(async () => {
  if (store.user.role === "ADMIN") organizations.value = await api('/organizations');
  await load();
});
watch(() => route.query.organization, load);
function chooseOrganization(event) {
  router.replace({ path: route.path, query: { organization: event.target.value } });
}
async function perform(work, success) {
  const ok = await store.run(async () => {
    await work();
    await load();
  }, success);
  if (ok) modal.value = "";
  return ok;
}
function routeTab(value) {
  router.push({ path: `/manage/${value}`, query: route.query });
}
async function createGroup() {
  await perform(
    () =>
      post(`/organizations/${organizationId.value}/groups`, {
        name: groupName.value,
      }),
    "Группа создана",
  );
  groupName.value = "";
}
async function createSubject() {
  await perform(
    () =>
      post(`/organizations/${organizationId.value}/subjects`, {
        name: subjectName.value,
        color: subjectColor.value,
      }),
    "Предмет создан",
  );
  subjectName.value = "";
}
async function saveLinks(group) {
  const ids = catalog.value.links
    .filter((item) => item.group_id === group.id)
    .map((item) => item.subject_id);
  await store.run(() => put(`/groups/${group.id}/subjects`, { subject_ids: ids }), "Предметы группы обновлены");
  await load();
}
async function toggleLink(groupId, subjectId) {
  const i = catalog.value.links.findIndex(
    (item) => item.group_id === groupId && item.subject_id === subjectId,
  );
  if (i >= 0) catalog.value.links.splice(i, 1);
  else catalog.value.links.push({ group_id: groupId, subject_id: subjectId });
  await saveLinks({ id: groupId });
}
async function invite(role, groupId = null) {
  const body = { role, group_id: groupId, loads: [] };
  if (role === "TEACHER")
    body.loads = assign.value.loads.map((key) => {
      const [subject_id, group_id] = key.split(":").map(Number);
      return { subject_id, group_id };
    });
  try {
    const link = await post(
      `/organizations/${organizationId.value}/invites`,
      body,
    );
    message.value = "";
    inviteUrl.value = link.url;
    await load();
    modal.value = 'invite-result';
    await copyInvite();
  } catch (e) {
    message.value = e.message;
    store.toast(e.message, "error");
  }
}
async function moderate(item, approve) {
  await perform(
    () => post(`/requests/${item.id}/moderate`, { approve }),
    approve
      ? `${item.student.display_name} принят в группу`
      : "Заявка отклонена",
  );
}
async function copyInvite() {
  try {
    await navigator.clipboard.writeText(inviteUrl.value);
    store.toast("Приглашение скопировано");
  } catch { store.toast("Ссылка готова — скопируйте её из поля"); }
}
async function approveAll(group) {
  await perform(
    () => post(`/groups/${group.id}/approve-all`),
    "Заявки группы рассмотрены",
  );
}
async function assignUser() {
  const body = {
    query: assign.value.query,
    role: assign.value.role,
    group_id: Number(assign.value.group_id) || null,
    loads:
      assign.value.role === "TEACHER"
        ? assign.value.loads.map((key) => {
            const [subject_id, group_id] = key.split(":").map(Number);
            return { subject_id, group_id };
          })
        : [],
  };
  await perform(
    () => post(`/organizations/${organizationId.value}/members`, body),
    "Участнику предоставлен доступ",
  );
  assign.value.query = "";
  assign.value.group_id = "";
}
async function deleteMember(member) {
  if (!confirm(`Удалить ${member.display_name} из группы?`)) return;
  await perform(
    () => remove(`/groups/${member.group_id}/members/${member.id}`),
    "Доступ к группе закрыт",
  );
}
async function saveReward() {
  const body = {
    ...reward.value,
    threshold: Number(reward.value.threshold),
    subject_id: Number(reward.value.subject_id) || null,
  };
  await perform(
    () =>
      editRewardId.value
        ? put(`/rewards/${editRewardId.value}`, body)
        : post(`/organizations/${organizationId.value}/rewards`, body),
    editRewardId.value ? "Награда обновлена" : "Награда добавлена",
  );
  reward.value = {
    name: "",
    kind: "BADGE",
    threshold: 10,
    subject_id: "",
    asset_url: null,
    icon: "award",
  };
  editRewardId.value = null;
}
function editReward(item) {
  editRewardId.value = item.id;
  reward.value = {
    name: item.name,
    kind: item.kind,
    threshold: item.threshold,
    subject_id: item.subject_id || "",
    asset_url: item.asset_url,
    icon: item.icon || "award",
  };
  modal.value = "reward";
}
async function deleteReward(item) {
  if (item.special) return;
  await perform(() => remove(`/rewards/${item.id}`), "Награда удалена");
}
async function rename(item, kind) {
  const name = prompt(
    `Новое название для ${kind === "group" ? "группы" : "предмета"}:`,
    item.name,
  );
  if (!name?.trim()) return;
  await perform(
    () =>
      put(
        `/${kind === "group" ? "groups" : "subjects"}/${item.id}`,
        kind === "group" ? { name } : { name, color: item.color },
      ),
    "Изменения сохранены",
  );
}
</script>
<template>
  <section class="manager-page">
    <label v-if="store.user.role === 'ADMIN'" class="field-label organization-picker">Учреждение
      <select :value="organizationId" @change="chooseOrganization"><option v-for="org in organizations" :key="org.id" :value="org.id">{{ org.name }}</option></select>
    </label>
    <div v-if="message" class="inline-alert">
      <Icon name="x-circle" :size="16" />{{ message }}
    </div>
    <div class="manager-stats">
      <div class="stat-card panel">
        <span class="stat-icon subjects"><Icon name="users" /></span
        ><span
          ><strong>{{ studentCount }}</strong
          ><small>учеников</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon wins"><Icon name="book" /></span
        ><span
          ><strong>{{ catalog.groups.length }}</strong
          ><small>учебных групп</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon awards"><Icon name="bell" /></span
        ><span
          ><strong>{{ requests.length }}</strong
          ><small>новых заявок</small></span
        >
      </div>
      <div class="stat-card panel">
        <span class="stat-icon events-stat"><Icon name="award" /></span
        ><span
          ><strong>{{ rewards.filter((r) => !r.special).length }}</strong
          ><small>наград</small></span
        >
      </div>
    </div>
    <div class="manager-tabs" role="tablist">
      <button
        v-for="item in [
          { id: 'requests', title: 'Заявки', icon: 'bell' },
          { id: 'groups', title: 'Группы и предметы', icon: 'book' },
          { id: 'teachers', title: 'Преподаватели', icon: 'graduation' },
          { id: 'rewards', title: 'Награды', icon: 'award' },
        ]"
        :key="item.id"
        role="tab"
        :aria-selected="tab === item.id"
        :class="{ active: tab === item.id }"
        @click="routeTab(item.id)"
      >
        <Icon :name="item.icon" :size="16" />{{ item.title
        }}<span
          v-if="item.id === 'requests' && requests.length"
          class="tab-count"
          >{{ requests.length }}</span
        >
      </button>
    </div>
    <section v-if="tab === 'requests'" class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">НОВЫЕ УЧАСТНИКИ</span>
          <h2>Заявки на вступление</h2>
        </div>
        <button
          v-if="requests.length"
          class="btn secondary small"
          @click="load()"
        >
          <Icon name="activity" :size="15" />Обновить
        </button>
      </div>
      <div v-if="!requests.length" class="empty-page panel">
        <span class="empty-icon"><Icon name="users" :size="28" /></span>
        <h3>Все спокойно, все заявки рассмотрены</h3>
        <p>
          Новые участники появятся здесь, когда перейдут по ссылке-приглашению.
        </p>
      </div>
      <section
        v-for="row in pendingByGroup"
        :key="row.group.id"
        class="request-group panel"
      >
        <div class="request-group-head">
          <span class="group-icon"><Icon name="users" :size="18" /></span
          ><span
            ><strong>{{ row.group.name }}</strong
            ><small
              >{{ row.items.length }}
              {{
                row.items.length === 1 ? "новая заявка" : "новые заявки"
              }}</small
            ></span
          ><button
            v-if="row.items.length > 1"
            class="btn secondary small"
            @click="approveAll(row.group)"
          >
            <Icon name="check-check" :size="15" />Принять всех
          </button>
        </div>
        <article v-for="item in row.items" :key="item.id" class="request-row">
          <Avatar :user="item.student" :size="43" />
          <div class="request-user">
            <strong>{{ item.student.display_name }}</strong
            ><span>@{{ item.student.username || "без username" }}</span
            ><small>В группе {{ row.group.name }}</small>
          </div>
          <button
            class="icon-btn approve-btn"
            :aria-label="`Принять ${item.student.display_name}`"
            @click="moderate(item, true)"
          >
            <Icon name="check" :size="18" /></button
          ><button
            class="icon-btn danger-icon"
            :aria-label="`Отклонить ${item.student.display_name}`"
            @click="moderate(item, false)"
          >
            <Icon name="x" :size="18" />
          </button>
        </article>
      </section>
      <button class="btn primary" @click="modal = 'invite-student'">
        <Icon name="link" :size="16" />Приглашение для ученика
      </button>
    </section>
    <section v-else-if="tab === 'groups'" class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">СТРУКТУРА УЧРЕЖДЕНИЯ</span>
          <h2>Учебные группы и предметы</h2>
        </div>
        <div class="button-row">
          <button class="btn secondary small" @click="modal = 'subject'">
            <Icon name="plus" :size="15" />Предмет</button
          ><button class="btn primary small" @click="modal = 'group'">
            <Icon name="plus" :size="15" />Группа
          </button>
        </div>
      </div>
      <div class="catalog-grid">
        <section class="catalog-column">
          <div class="catalog-heading">
            <span class="eyebrow">ГРУППЫ</span
            ><span class="subtle-count">{{ catalog.groups.length }}</span>
          </div>
          <article
            v-for="group in catalog.groups"
            :key="group.id"
            class="catalog-row"
          >
            <span class="catalog-symbol"><Icon name="users" :size="17" /></span
            ><span class="catalog-row-main"
              ><strong>{{ group.name }}</strong
              ><small
                >{{
                  members.filter((m) => m.group_id === group.id).length
                }}
                участников</small
              ><span class="linked-subjects">{{
                catalog.links
                  .filter((l) => l.group_id === group.id)
                  .map(
                    (l) =>
                      catalog.subjects.find((s) => s.id === l.subject_id)?.name,
                  )
                  .filter(Boolean)
                  .join(" · ") || "Предметы пока не выбраны"
              }}</span></span
            ><button
              class="icon-btn"
              :aria-label="`Пригласить ученика в ${group.name}`"
              @click="assign.group_id = String(group.id); modal = 'invite-student'"
            ><Icon name="link" :size="16" /></button><button
              class="icon-btn"
              :aria-label="`Переименовать ${group.name}`"
              @click="rename(group, 'group')"
            >
              <Icon name="pencil" :size="16" /></button
            ><button
              class="icon-btn"
              :aria-label="`Настроить предметы ${group.name}`"
              @click="
                inviteGroup = group;
                modal = `links:${group.id}`;
              "
            >
              <Icon name="settings" :size="17" />
            </button>
          </article>
          <p v-if="!catalog.groups.length" class="empty-inline">
            Создай первую учебную группу.
          </p>
        </section>
        <section class="catalog-column">
          <div class="catalog-heading">
            <span class="eyebrow">ПРЕДМЕТЫ</span
            ><span class="subtle-count">{{ catalog.subjects.length }}</span>
          </div>
          <article
            v-for="subject in catalog.subjects"
            :key="subject.id"
            class="catalog-row"
          >
            <span class="subject-dot" :style="{ background: subject.color }"
              ><Icon name="book" :size="15" /></span
            ><span class="catalog-row-main"
              ><strong>{{ subject.name }}</strong
              ><small
                >{{
                  catalog.links.filter((l) => l.subject_id === subject.id)
                    .length
                }}
                учебных групп</small
              ></span
            ><button
              class="icon-btn"
              :aria-label="`Переименовать ${subject.name}`"
              @click="rename(subject, 'subject')"
            >
              <Icon name="pencil" :size="16" />
            </button>
          </article>
          <p v-if="!catalog.subjects.length" class="empty-inline">
            Добавь предметы, чтобы назначить нагрузку.
          </p>
        </section>
      </div>
      <div class="student-list-head">
        <div>
          <span class="eyebrow">УЧАСТНИКИ</span>
          <h3>
            Ученики и преподаватели
            <span class="inline-count">{{ filteredMembers.length }}</span>
          </h3>
        </div>
        <div class="member-actions">
          <label class="search-field"
            ><Icon name="search" :size="16" /><input
              v-model="search"
              placeholder="Поиск по имени или группе" /></label
          ><button class="btn primary small" @click="modal = 'assign-student'">
            <Icon name="user-plus" :size="15" />Добавить
          </button>
        </div>
      </div>
      <article
        v-for="member in filteredMembers"
        :key="member.id"
        class="member-row panel"
      >
        <Avatar :user="member" :size="40" />
        <div class="request-user">
          <strong>{{ member.display_name }}</strong
          ><span>@{{ member.username || member.max_id }}</span>
        </div>
        <span class="role-chip small-role">{{ roleName(member.role) }}</span
        ><span v-if="member.group_id" class="member-group">{{
          catalog.groups.find((g) => g.id === member.group_id)?.name || "Группа"
        }}</span
        ><button
          v-if="member.role === 'STUDENT' && member.group_id"
          class="icon-btn danger-icon"
          aria-label="Удалить ученика из группы"
          @click="deleteMember(member)"
        >
          <Icon name="trash" :size="17" />
        </button>
      </article>
      <p v-if="!filteredMembers.length" class="empty-inline">
        Участников не найдено.
      </p>
    </section>
    <section v-else-if="tab === 'teachers'" class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">ПРЕПОДАВАТЕЛЬСКИЙ СОСТАВ</span>
          <h2>Преподаватели и нагрузка</h2>
        </div>
        <button
          class="btn primary"
          @click="
            assign = { query: '', role: 'TEACHER', loads: [] };
            modal = 'teacher';
          "
        >
          <Icon name="plus" :size="16" />Добавить преподавателя
        </button>
      </div>
      <div class="teacher-load-grid">
        <article
          v-for="person in members.filter((m) => m.role === 'TEACHER')"
          :key="person.id"
          class="teacher-load-card panel"
        >
          <div class="teacher-load-profile">
            <Avatar :user="person" :size="46" />
            <div>
              <strong>{{ person.display_name }}</strong
              ><span>@{{ person.username || person.max_id }}</span>
            </div>
            <button
              class="icon-btn"
              :aria-label="`Изменить нагрузку ${person.display_name}`"
              @click="
                assign.query = person.username
                  ? '@' + person.username
                  : String(person.max_id);
                assign.role = 'TEACHER';
                assign.loads = catalog.loads
                  .filter((l) => l.teacher_id === person.id)
                  .map((l) => `${l.subject_id}:${l.group_id}`);
                modal = 'teacher';
              "
            >
              <Icon name="pencil" :size="16" />
            </button>
          </div>
          <div
            v-for="subject in [
              ...new Set(
                catalog.loads
                  .filter((l) => l.teacher_id === person.id)
                  .map((l) => l.subject_id),
              ),
            ]
              .map((id) => catalog.subjects.find((s) => s.id === id))
              .filter(Boolean)"
            :key="subject.id"
            class="load-subject"
          >
            <span :style="{ background: subject.color }"></span
            ><strong>{{ subject.name }}</strong
            ><small>{{
              catalog.loads
                .filter(
                  (l) =>
                    l.teacher_id === person.id && l.subject_id === subject.id,
                )
                .map(
                  (l) => catalog.groups.find((g) => g.id === l.group_id)?.name,
                )
                .filter(Boolean)
                .join(", ")
            }}</small>
          </div>
        </article>
        <div
          v-if="!members.some((m) => m.role === 'TEACHER')"
          class="empty-page panel"
        >
          <span class="empty-icon"><Icon name="graduation" :size="27" /></span>
          <h3>Учителей пока нет</h3>
          <p>Назначь преподавателя по username и собери учебную нагрузку.</p>
          <button
            class="btn primary small"
            @click="
              assign = { query: '', role: 'TEACHER', loads: [] };
              modal = 'teacher';
            "
          >
            <Icon name="plus" :size="15" />Добавить
          </button>
        </div>
      </div>
      <div class="invites-list">
        <div class="catalog-heading">
          <span class="eyebrow">ПРИГЛАШЕНИЯ ПРЕПОДАВАТЕЛЯМ</span>
        </div>
        <article
          v-for="invite in invites.filter((i) => i.role === 'TEACHER')"
          :key="invite.id"
          class="invite-row"
        >
          <span class="catalog-symbol"><Icon name="link" :size="16" /></span
          ><span
            ><strong>{{
              invite.group_id
                ? catalog.groups.find((g) => g.id === invite.group_id)?.name
                : "Все учебные группы"
            }}</strong
            ><small>{{
              invite.revoked
                ? "ОТЗЫВАНО"
                : invite.used_by
                  ? "ИСПОЛЬЗОВАНО"
                  : "АКТИВНО"
            }}</small></span
          ><button
            v-if="!invite.revoked && !invite.used_by"
            class="icon-btn danger-icon"
            aria-label="Отозвать приглашение"
            @click="
              perform(
                () => remove(`/invites/${invite.id}`),
                'Приглашение отозвано',
              )
            "
          >
            <Icon name="x" :size="16" />
          </button>
        </article>
      </div>
    </section>
    <section v-else-if="tab === 'rewards'" class="management-content">
      <div class="section-head">
        <div>
          <span class="eyebrow">РАЗВИТИЕ УЧАСТНИКОВ</span>
          <h2>Уровни и награды</h2>
        </div>
        <button
          class="btn primary"
          @click="
            editRewardId = null;
            reward = {
              name: '',
              kind: 'BADGE',
              threshold: 10,
              subject_id: '',
              asset_url: null,
              icon: 'award',
            };
            modal = 'reward';
          "
        >
          <Icon name="plus" :size="16" />Добавить уровень
        </button>
      </div>
      <div
        v-for="scope in [
          { subject_id: null, name: 'Общий боевой пропуск' },
          ...catalog.subjects.map((s) => ({ subject_id: s.id, name: s.name })),
        ]"
        :key="scope.subject_id || 'general'"
        class="reward-scope"
      >
        <div class="catalog-heading">
          <span class="eyebrow">{{ scope.name.toUpperCase() }}</span
          ><span class="subtle-count"
            >{{
              rewards.filter((r) => r.subject_id === scope.subject_id).length
            }}
            уровней</span
          >
        </div>
        <article
          v-for="item in rewards.filter(
            (r) => r.subject_id === scope.subject_id,
          )"
          :key="item.id"
          class="manager-reward-row panel"
        >
          <span
            class="reward-art"
            :class="`reward-art-${item.kind.toLowerCase()}`"
            ><img
              v-if="item.asset_url"
              :src="item.asset_url"
              :alt="item.name" /><Icon
              v-else
              :name="item.icon || 'award'"
              :size="20" /></span
          ><span class="manager-reward-name"
            ><strong>{{ item.name }}</strong
            ><small
              >{{
                { TITLE: "Звание", FRAME: "Рамка", BADGE: "Достижение" }[
                  item.kind
                ]
              }}
              ·
              {{
                item.threshold ? `${item.threshold} баллов` : "Особая награда"
              }}</small
            ></span
          ><span v-if="item.special" class="chip neutral">Системная</span
          ><span v-else class="button-row"
            ><button
              class="icon-btn"
              :aria-label="`Изменить награду ${item.name}`"
              @click="editReward(item)"
            >
              <Icon name="pencil" :size="16" /></button
            ><button
              class="icon-btn danger-icon"
              :aria-label="`Удалить награду ${item.name}`"
              @click="deleteReward(item)"
            >
              <Icon name="trash" :size="16" /></button
          ></span>
        </article>
        <p
          v-if="!rewards.some((r) => r.subject_id === scope.subject_id)"
          class="empty-inline"
        >
          Здесь будут появляться новые уровни.
        </p>
      </div>
    </section>
    <Modal v-if="modal === 'group'" title="Новая группа" @close="modal = ''"
      ><form
        class="modal-form"
        @submit.prevent="createGroup"
      >
        <label class="field-label"
          >Название группы<input
            v-model.trim="groupName"
            required
            maxlength="100"
            placeholder="Например, ИС-21" /></label
        ><button class="btn primary modal-submit">Создать группу</button>
      </form></Modal
    >
    <Modal
      v-else-if="modal === 'subject'"
      title="Новый предмет"
      @close="modal = ''"
      ><form
        class="modal-form"
        @submit.prevent="createSubject"
      >
        <label class="field-label"
          >Название предмета<input
            v-model.trim="subjectName"
            required
            maxlength="100"
            placeholder="Например, Программирование" /></label
        ><label class="field-label"
          >Цвет предмета<input v-model="subjectColor" type="color" /></label
        ><button class="btn primary modal-submit">Добавить предмет</button>
      </form></Modal
    >
    <Modal
      v-else-if="modal.startsWith('links:')"
      :title="`Предметы · ${inviteGroup?.name || ''}`"
      @close="modal = ''"
      ><fieldset class="modal-form choice-field">
        <legend>Выбери предметы, которые изучает группа</legend>
        <label
          v-for="subject in catalog.subjects"
          :key="subject.id"
          class="check-option"
          ><input
            type="checkbox"
            :checked="
              catalog.links.some(
                (l) =>
                  l.group_id === inviteGroup.id && l.subject_id === subject.id,
              )
            "
            @change="toggleLink(inviteGroup.id, subject.id)"
          /><span class="fake-check"><Icon name="check" :size="13" /></span
          ><i class="subject-tiny" :style="{ background: subject.color }"></i
          >{{ subject.name }}</label
        >
        <p v-if="!catalog.subjects.length" class="muted">
          Сначала добавь предметы учреждения.
        </p>
      </fieldset></Modal
    >
    <Modal
      v-else-if="modal === 'invite-student'"
      title="Приглашение для ученика"
      @close="modal = ''"
      ><div class="modal-form">
        <p>
          Ссылка группы создаст заявку на вступление. Группа будет
          активирована после модерации.
        </p>
        <label class="field-label"
          >Группа<select v-model="assign.group_id" required>
            <option disabled value="">Выбери группу</option>
            <option
              v-for="group in catalog.groups"
              :key="group.id"
              :value="String(group.id)"
            >
              {{ group.name }}
            </option>
          </select></label
        ><button
          class="btn primary modal-submit"
          :disabled="!assign.group_id"
          @click="invite('STUDENT', Number(assign.group_id))"
        >
          <Icon name="link" :size="16" />Создать и скопировать ссылку
        </button>
      </div></Modal
    >
    <Modal
      v-else-if="modal === 'invite-result'"
      title="Приглашение готово"
      @close="modal = ''"
    ><div class="modal-form"><p>Отправьте ссылку будущему участнику.</p><label class="field-label">Ссылка приглашения<input :value="inviteUrl" readonly @focus="$event.target.select()" /></label><button class="btn primary" @click="copyInvite">Скопировать ссылку</button></div></Modal>
    <Modal
      v-else-if="modal === 'assign-student'"
      title="Добавить участника"
      wide
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="assignUser">
        <label class="field-label"
          >Учётная запись
          <span class="field-hint"
            >По username, ID MAX или подтвержденному номеру телефона</span
          ><input
            v-model.trim="assign.query"
            required
            placeholder="@username или ID MAX"
        /></label>
        <div class="segmented-field">
          <legend>Роль</legend>
          <label
            v-for="role in [
              { value: 'STUDENT', label: 'Ученик' },
              { value: 'TEACHER', label: 'Преподаватель' },
            ]"
            :key="role.value"
            ><input
              v-model="assign.role"
              type="radio"
              :value="role.value"
            /><span>{{ role.label }}</span></label
          >
        </div>
        <label v-if="assign.role === 'STUDENT'" class="field-label"
          >Группа<select v-model="assign.group_id" required>
            <option disabled value="">Выбери группу</option>
            <option
              v-for="group in catalog.groups"
              :key="group.id"
              :value="String(group.id)"
            >
              {{ group.name }}
            </option>
          </select></label
        >
        <fieldset v-else class="choice-field">
          <legend>Предметы и группы нагрузки</legend>
          <div
            v-for="subject in catalog.subjects"
            :key="subject.id"
            class="matrix-subject"
          >
            <span
              class="matrix-dot"
              :style="{ background: subject.color }"
            ></span
            ><strong>{{ subject.name }}</strong>
            <div class="matrix-groups">
              <label
                v-for="group in catalog.groups.filter((g) =>
                  catalog.links.some(
                    (l) => l.group_id === g.id && l.subject_id === subject.id,
                  ),
                )"
                :key="group.id"
                ><input
                  v-model="assign.loads"
                  type="checkbox"
                  :value="`${subject.id}:${group.id}`"
                /><span>{{ group.name }}</span></label
              >
            </div>
          </div>
        </fieldset>
        <button class="btn primary modal-submit" :disabled="store.saving">
          <Icon name="user-plus" :size="16" />Открыть доступ
        </button>
      </form></Modal
    >
    <Modal
      v-else-if="modal === 'teacher'"
      title="Преподаватель и нагрузка"
      wide
      @close="modal = ''"
      ><div class="modal-form">
        <label class="field-label"
          >Username или ID MAX<input
            v-model.trim="assign.query"
            placeholder="@username"
            required
        /></label>
        <div
          v-for="subject in catalog.subjects"
          :key="subject.id"
          class="matrix-subject"
        >
          <span class="matrix-dot" :style="{ background: subject.color }"></span
          ><strong>{{ subject.name }}</strong>
          <div class="matrix-groups">
            <label
              v-for="group in catalog.groups.filter((g) =>
                catalog.links.some(
                  (l) => l.group_id === g.id && l.subject_id === subject.id,
                ),
              )"
              :key="group.id"
              ><input
                v-model="assign.loads"
                type="checkbox"
                :value="`${subject.id}:${group.id}`"
              /><span>{{ group.name }}</span></label
            >
          </div>
        </div>
        <button
          class="btn primary modal-submit"
          :disabled="!assign.query || !assign.loads.length || store.saving"
          @click="assignUser()"
        >
          <Icon name="link" :size="16" />{{
            "Сохранить преподавателя"
          }}
        </button>
        <button class="btn secondary" :disabled="!assign.loads.length || store.saving" @click="invite('TEACHER')"><Icon name="link" :size="16" />Создать приглашение с выбранной нагрузкой</button>
      </div></Modal
    >
    <Modal
      v-else-if="modal === 'reward'"
      :title="editRewardId ? 'Изменить награду' : 'Новая награда'"
      @close="modal = ''"
      ><form class="modal-form" @submit.prevent="saveReward">
        <label class="field-label"
          >Название<input
            v-model.trim="reward.name"
            maxlength="100"
            required
            placeholder="Например, Исследователь"
        /></label>
        <div class="form-grid">
          <label class="field-label"
            >Тип награды<select v-model="reward.kind">
              <option value="BADGE">Достижение</option>
              <option value="TITLE">Звание</option>
              <option value="FRAME">Рамка профиля</option>
            </select></label
          ><label class="field-label"
            >Нужно баллов<input
              v-model.number="reward.threshold"
              type="number"
              min="1"
              max="100000"
              required
          /></label>
        </div>
        <label class="field-label"
          >Боевой пропуск<select v-model="reward.subject_id">
            <option value="">Общий пропуск</option>
            <option
              v-for="subject in catalog.subjects"
              :key="subject.id"
              :value="String(subject.id)"
            >
              {{ subject.name }}
            </option>
          </select></label
        ><label class="field-label"
          >Символ<select v-model="reward.icon">
            <option
              v-for="name in [
                'award',
                'sparkles',
                'crown',
                'flame',
                'swords',
                'star',
                'shield',
              ]"
              :key="name"
              :value="name"
            >
              {{ name }}
            </option>
          </select></label
        ><button class="btn primary modal-submit" :disabled="store.saving">
          {{ editRewardId ? "Сохранить" : "Создать награду" }}
          <Icon name="check" :size="15" />
        </button></form
    ></Modal>
  </section>
</template>
