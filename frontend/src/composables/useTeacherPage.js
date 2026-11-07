import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { api, formatDate, futureLocal, iso, post, put, remove } from '../api';
import { useArena } from '../stores/arena';

export function useTeacherPage() {
  const store = useArena(),
  route = useRoute(),
  tab = ref("homework"),
  catalog = ref({ groups: [], subjects: [], loads: [] }),
  rewards = ref([]),
  selectedRewardSubject = ref(null);
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
const reward = ref({ name: "", kind: "CUSTOM", threshold: 10, subject_id: "", asset_url: null, icon: "sparkles" });
const editRewardId = ref(null);
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
    const [catalogData, homeworkData, eventsData, rewardsData] = await Promise.all([
      api(`/organizations/${store.user.organization_id}/catalog`),
      api("/homework"),
      api("/events"),
      api(`/organizations/${store.user.organization_id}/rewards`),
    ]);
    catalog.value = catalogData;
    store.homework = homeworkData;
    store.events = eventsData;
    rewards.value = rewardsData;
    if (!selectedRewardSubject.value || !catalogData.subjects.some(s => s.id === selectedRewardSubject.value))
      selectedRewardSubject.value = catalogData.subjects[0]?.id || null;
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
function resetReward() {
  editRewardId.value = null;
  reward.value = { name: "", kind: "CUSTOM", threshold: 10, subject_id: selectedRewardSubject.value || "", asset_url: null, icon: "sparkles" };
  modal.value = "reward";
}
function editReward(item) {
  editRewardId.value = item.id;
  reward.value = { name: item.name, kind: item.kind, threshold: item.threshold, subject_id: item.subject_id, asset_url: item.asset_url, icon: item.icon || "sparkles" };
  selectedRewardSubject.value = item.subject_id;
  modal.value = "reward";
}
async function saveReward() {
  await store.run(async () => {
    const body = { ...reward.value, threshold: Number(reward.value.threshold), subject_id: Number(selectedRewardSubject.value) };
    if (editRewardId.value) await put(`/rewards/${editRewardId.value}`, body);
    else await post(`/organizations/${store.user.organization_id}/rewards`, body);
    modal.value = "";
    await load();
  }, editRewardId.value ? "Награда обновлена" : "Награда добавлена");
}
async function deleteReward(item) {
  if (!confirm(`Удалить награду «${item.name}»?`)) return;
  await store.run(async () => { await remove(`/rewards/${item.id}`); await load(); }, "Награда удалена");
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
  return {store, route, tab, catalog, rewards, selectedRewardSubject, reward, editRewardId, modal, loading, reviews, participants, toast, hw, ev, canCreate, load, teachingGroups, forGroup, createHomework, createEvent, openReview, mark, openRoster, closeEvent, completeEvent, kick, fileLink, formatDate, resetReward, editReward, saveReward, deleteReward};
}
