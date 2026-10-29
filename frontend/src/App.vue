<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useArena } from "./stores/arena";
import Icon from "./components/Icon.vue";
import Avatar from "./components/Avatar.vue";
import { homeFor, post } from "./api";

const store = useArena(),
  route = useRoute(),
  router = useRouter();
const nav = computed(() =>
  store.user?.role === "STUDENT"
    ? [
        { to: "/", title: "Главная", icon: "home" },
        { to: "/battlepass", title: "Пропуск", icon: "layers" },
        { to: "/arena", title: "Арена", icon: "target" },
        { to: "/friends", title: "Друзья", icon: "users" },
      ]
    : store.user?.role === "TEACHER"
      ? [{ to: "/teach", title: "Преподавание", icon: "graduation" }]
      : store.user?.role === "MANAGER"
        ? [
            { to: "/manage/requests", title: "Заявки", icon: "users" },
            { to: "/manage/groups", title: "Ученики", icon: "book" },
            {
              to: "/manage/teachers",
              title: "Преподаватели",
              icon: "graduation",
            },
            { to: "/manage/rewards", title: "Награды", icon: "award" },
          ]
        : store.user?.role === "ADMIN"
          ? [
              { to: "/admin", title: "Учреждения", icon: "layers" },
              { to: "/manage/groups", title: "Управление", icon: "settings" },
            ]
          : [],
);
const pending = computed(() => store.user?.role === "PENDING");
const title = computed(() => route.meta.title || "Инфо Арена");
const persona = ref("student");
watch(
  () => [store.loading, store.user?.role, route.fullPath],
  () => {
    if (!store.loading && store.user && !pending.value && route.meta.roles && !route.meta.roles.includes(store.user.role)) {
      router.replace(homeFor(store.user.role));
    }
  },
);
function openToast(toast) {
  store.dismiss(toast.id);
  if (toast.notificationId)
    post(`/notifications/${toast.notificationId}/read`).catch(() => {});
  if (toast.link && toast.link.startsWith("/") && route.fullPath !== toast.link)
    router.push(toast.link);
}
watch(
  () => [route.fullPath, store.user?.role],
  () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    const bridge = window.WebApp;
    if (bridge?.initData && bridge?.BackButton) {
      if (route.path !== homeFor(store.user?.role) && route.path !== "/") {
        bridge.BackButton.show();
      } else bridge.BackButton.hide();
    }
  },
);
function back() {
  router.back();
}
function windowIsMax() {
  return Boolean(window.WebApp?.initData);
}
onMounted(() => {
  if (windowIsMax()) window.WebApp?.BackButton?.onClick(back);
  store.initialize();
});
onBeforeUnmount(() => {
  window.WebApp?.BackButton?.offClick(back);
  store.disconnect();
});
</script>

<template>
  <div class="app-shell">
    <header v-if="store.user && !pending" class="topbar">
      <router-link :to="homeFor(store.user.role)" class="brand"
        ><span class="brand-mark"><Icon name="cloud" :size="20" /></span
        ><span>инфо<span class="brand-light">арена</span></span></router-link
      >
      <div class="topbar-right">
        <router-link
          to="/notifications"
          class="icon-btn notification-button"
          aria-label="Уведомления"
          ><Icon name="bell" /><span
            v-if="store.unread"
            class="notification-dot"
            aria-label="Непрочитанные уведомления"
          ></span
        ></router-link>
        <button v-if="store.config.dev_auth && !windowIsMax()" class="icon-btn" aria-label="Сменить демопользователя" title="Сменить демопользователя" @click="store.logout()"><Icon name="logout" :size="18" /></button>
        <router-link :to="store.user.role === 'STUDENT' ? '/settings' : homeFor(store.user.role)" class="user-mini"
          ><Avatar :user="store.user" :size="34" /><span>{{
            store.user.display_name.split(" ")[0]
          }}</span></router-link
        >
      </div>
    </header>
    <main v-if="store.loading" class="app-main center-state">
      <span class="spinner"></span>
      <p>Открываем арену…</p>
    </main>
    <main v-else-if="!store.user" class="app-main">
      <section class="login-wrap">
        <div class="login-brand">
          <span class="brand-mark large"><Icon name="cloud" :size="30" /></span>
          <div>
            <span class="eyebrow">ТВОЙ МАРШРУТ К НОВЫМ ЦЕЛЯМ</span>
            <h1>
              Здесь начинается<br /><span class="accent"
                >следующий уровень.</span
              >
            </h1>
            <p>
              Выполняй задания, открывай награды и соревнуйся с друзьями. Каждый
              шаг приближает к цели.
            </p>
          </div>
        </div>
        <div class="login-art">
          <img
            src="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1100&q=85"
            alt="Солнечный свет над горами, открывающий путь к новым вершинам"
            fetchpriority="high"
          />
        </div>
        <div class="login-footer">
          <span>Учись в своём ритме. Расти вместе.</span>
          <div class="role-chip-row">
            <span><Icon name="book" :size="14" /> Задания</span
            ><span><Icon name="award" :size="14" /> Награды</span
            ><span><Icon name="swords" :size="14" /> Дуэли</span>
          </div>
          <p v-if="store.error" class="login-error">{{ store.error }}</p>
          <div v-if="store.config.dev_auth" class="dev-login">
            <label
              >Демонстрационный вход
              <select id="dev-persona" v-model="persona">
                <option value="student">Ученик</option>
                <option value="friend">Друг ученика</option>
                <option value="teacher">Преподаватель</option>
                <option value="manager">Управляющий</option>
                <option value="admin">Администратор</option>
              </select></label
            ><button
              class="btn primary"
              @click="
                store
                  .demo(persona)
                  .then((to) => router.replace(to))
                  .catch((e) => store.toast(e.message, 'error'))
              "
            >
              Открыть арену <Icon name="arrow-right" :size="16" />
            </button>
          </div>
          <span v-else class="login-hint"
            ><Icon name="lock" :size="15" /> Откройте приложение через MAX,
            чтобы продолжить</span
          >
        </div>
      </section>
    </main>
    <main v-else-if="pending" class="app-main pending-state">
      <section class="pending-panel panel">
        <span class="pending-icon"><Icon name="clock" :size="25" /></span
        ><span class="eyebrow">ЗАЯВКА ПРИНЯТА</span>
        <h1>Пока готовится твой старт</h1>
        <p>
          {{
            store.user.join_request?.status === "PENDING"
              ? "Управляющий проверит заявку и откроет доступ к группе. Мы сообщим, когда всё будет готово."
              : "Для доступа в арену нужна ссылка-приглашение от управляющего учебного заведения."
          }}
        </p>
        <div
          v-if="store.user.join_request?.status === 'PENDING'"
          class="pending-meta"
        >
          <span class="live-dot"></span> Заявка отправлена ·
          {{ store.user.group?.name || "группа" }}
        </div>
        <button class="btn secondary" @click="store.initialize()">
          <Icon name="activity" :size="16" /> Обновить статус</button
        ><button
          class="text-btn pending-exit"
          @click="
            store.logout();
            store.initialize();
          "
        >
          Выйти
        </button>
      </section>
    </main>
    <main v-else class="app-main">
      <div class="page-heading">
        <div>
          <span class="page-kicker">{{
            store.user.organization?.name || "ИНФО АРЕНА"
          }}</span>
          <h1>{{ title }}</h1>
          <p v-if="store.user.role === 'STUDENT' && store.user.group">
            {{ store.user.group.name }} · {{ store.user.display_name }}
          </p>
        </div>
        <span class="role-chip"
          ><Icon
            :name="
              store.user.role === 'STUDENT'
                ? 'star'
                : store.user.role === 'TEACHER'
                  ? 'graduation'
                  : 'shield'
            "
            :size="15"
          />{{
            {
              STUDENT: "Участник",
              TEACHER: "Преподаватель",
              MANAGER: "Управляющий",
              ADMIN: "Администратор",
            }[store.user.role]
          }}</span
        >
      </div>
      <router-view v-slot="{ Component }"
        ><component :is="Component" :key="route.fullPath"
      /></router-view>
    </main>
    <nav
      v-if="store.user && !pending && nav.length"
      class="bottom-nav"
      aria-label="Основная навигация"
    >
      <router-link
        v-for="item in nav"
        :key="item.to"
        :to="item.to"
        :aria-label="item.title"
        :aria-current="
          route.path === item.to || route.path.startsWith(item.to + '/')
            ? 'page'
            : undefined
        "
        :class="{
          active:
            route.path === item.to || route.path.startsWith(item.to + '/'),
        }"
        ><Icon :name="item.icon" :size="20" /><span>{{ item.title }}</span
        ><i
          v-if="item.to.includes('requests') && store.user.role === 'MANAGER'"
          class="nav-dot"
        ></i
      ></router-link>
    </nav>
    <div class="toast-stack" aria-live="polite" aria-relevant="additions">
      <div
        v-for="toast in store.toasts"
        :key="toast.id"
        class="toast"
        :class="[`toast-${toast.kind}`, { clickable: toast.link }]"
      >
        <span class="toast-icon"
          ><Icon
            :name="
              toast.kind === 'error'
                ? 'x-circle'
                : toast.kind === 'notification'
                  ? 'bell'
                  : 'check'
            "
            :size="17" /></span
        ><button type="button" class="toast-message" @click="openToast(toast)">{{ toast.message }}</button
        ><button
          class="toast-close"
          aria-label="Скрыть уведомление"
          @click.stop="store.dismiss(toast.id)"
        >
          <Icon name="x" :size="15" />
        </button>
      </div>
    </div>
  </div>
</template>
