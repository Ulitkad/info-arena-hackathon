<script setup>
import Icon from './Icon.vue'

defineProps({
  items: { type: Array, default: () => [] },
  routePath: { type: String, default: '' },
  userRole: { type: String, default: '' },
})
</script>

<template>
  <nav v-if="items.length" class="bottom-nav" aria-label="Основная навигация">
    <router-link v-for="item in items" :key="item.to" :to="item.to" :aria-label="item.title" :aria-current="routePath === item.to || routePath.startsWith(item.to + '/') ? 'page' : undefined" :class="{ active: routePath === item.to || routePath.startsWith(item.to + '/') }">
      <Icon :name="item.icon" :size="20" /><span>{{ item.title }}</span><i v-if="item.to.includes('requests') && userRole === 'MANAGER'" class="nav-dot"></i>
    </router-link>
  </nav>
</template>
