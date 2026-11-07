<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  user: { type: Object, required: true },
  title: { type: String, required: true },
})
const roleIcon = computed(() => ({ STUDENT: 'star', TEACHER: 'graduation' }[props.user.role] || 'shield'))
const roleTitle = computed(() => ({ STUDENT: 'Участник', TEACHER: 'Преподаватель', MANAGER: 'Управляющий', ADMIN: 'Администратор' }[props.user.role]))
</script>

<template>
  <div class="page-heading">
    <div>
      <span class="page-kicker">{{ user.organization?.name || 'ИНФО АРЕНА' }}</span>
      <h1>{{ title }}</h1>
      <p v-if="user.role === 'STUDENT' && user.group">{{ user.group.name }} · {{ user.display_name }}</p>
    </div>
    <span class="role-chip"><Icon :name="roleIcon" :size="15" />{{ roleTitle }}</span>
  </div>
  <slot />
</template>
