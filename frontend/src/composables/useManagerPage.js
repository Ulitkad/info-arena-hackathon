import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, remove, post, put } from '../api';
import { useArena } from '../stores/arena';

export function useManagerPage() {
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
const editingTeacher = ref(null), inviteRole = ref('');
const renameTarget = ref(null), renameName = ref('');
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
  await store.run(async () => {
    const link = await post(
      `/organizations/${organizationId.value}/invites`,
      body,
    );
    message.value = "";
    inviteUrl.value = link.url;
    inviteRole.value = role;
    await load();
    modal.value = 'invite-result';
    await copyInvite();
  });
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
function openTeacher(person = null) {
  editingTeacher.value = person;
  assign.value = { query: '', role: 'TEACHER', group_id: '', loads: person
    ? catalog.value.loads.filter(l => l.teacher_id === person.id).map(l => `${l.subject_id}:${l.group_id}`)
    : [] };
  modal.value = 'teacher';
}
async function saveTeacherLoads() {
  const loads = assign.value.loads.map(key => {
    const [subject_id, group_id] = key.split(':').map(Number);
    return { subject_id, group_id };
  });
  await perform(() => put(`/organizations/${organizationId.value}/teachers/${editingTeacher.value.id}/loads`, { loads }), 'Нагрузка обновлена');
}
async function deleteMember(member) {
  if (!confirm(`Удалить ${member.display_name} из группы?`)) return;
  await perform(
    () => remove(`/groups/${member.group_id}/members/${member.id}`),
    "Доступ к группе закрыт",
  );
}
async function deleteTeacher(teacher) {
  if (!confirm(`Удалить ${teacher.display_name} из учреждения?`)) return;
  await perform(
    () => remove(`/organizations/${organizationId.value}/members/${teacher.id}`),
    "Преподаватель удалён",
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
function openRename(item, kind) {
  renameTarget.value = { item, kind };
  renameName.value = item.name;
  modal.value = 'rename';
}
async function saveRename() {
  const target = renameTarget.value;
  const name = renameName.value.trim();
  if (!target || !name) return;
  await perform(
    () =>
      put(
        `/${target.kind === "group" ? "groups" : "subjects"}/${target.item.id}`,
        target.kind === "group" ? { name } : { name, color: target.item.color },
      ),
    "Изменения сохранены",
  );
  renameTarget.value = null;
  renameName.value = '';
}
  return {store, route, router, tab, catalog, members, requests, invites, rewards, modal, loading, search, message, groupName, subjectName, subjectColor, inviteGroup, assign, editingTeacher, inviteRole, renameTarget, renameName, reward, editRewardId, organizations, inviteUrl, organizationId, filteredMembers, pendingByGroup, studentCount, load, chooseOrganization, perform, routeTab, createGroup, createSubject, saveLinks, toggleLink, invite, moderate, copyInvite, approveAll, openTeacher, saveTeacherLoads, deleteMember, deleteTeacher, saveReward, editReward, deleteReward, openRename, saveRename};
}
