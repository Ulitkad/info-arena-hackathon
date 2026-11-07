<script setup>
import { homeFor } from '../api'
import Icon from './Icon.vue'
import Avatar from './Avatar.vue'

defineProps({
  user: { type: Object, required: true },
  config: { type: Object, default: () => ({}) },
  unread: { type: Number, default: 0 },
  isMax: { type: Boolean, default: false },
  routePath: { type: String, default: '' },
})

const emit = defineEmits(['toggle-notifications', 'logout'])
</script>

<template>
  <header class="topbar">
    <router-link :to="homeFor(user.role)" class="brand">
      <span class="brand-mark"><Icon name="cloud" :size="20" /></span>
      <span>инфо<span class="brand-light">арена</span></span>
    </router-link>
    <div class="topbar-right">
      <button class="icon-btn notification-button" aria-label="Уведомления" :aria-pressed="routePath === '/notifications'" @click="emit('toggle-notifications')">
        <Icon name="bell" /><span v-if="unread" class="notification-dot" aria-label="Непрочитанные уведомления"></span>
      </button>
      <button v-if="config.dev_auth && !isMax" class="icon-btn" aria-label="Сменить демопользователя" title="Сменить демопользователя" @click="emit('logout')">
        <Icon name="logout" :size="18" />
      </button>
      <router-link :to="user.role === 'STUDENT' ? '/settings' : homeFor(user.role)" class="user-mini">
        <Avatar :user="user" :size="34" /><span>{{ user.display_name.split(' ')[0] }}</span>
      </router-link>
    </div>
  </header>
</template>
