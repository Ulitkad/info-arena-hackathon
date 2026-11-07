<script setup>
import Icon from './Icon.vue'

defineProps({ toasts: { type: Array, default: () => [] } })
const emit = defineEmits(['open', 'dismiss'])
</script>

<template>
  <div class="toast-stack" aria-live="polite" aria-relevant="additions">
    <div v-for="toast in toasts" :key="toast.id" class="toast" :class="[`toast-${toast.kind}`, { clickable: toast.link }]">
      <span class="toast-icon"><Icon :name="toast.kind === 'error' ? 'x-circle' : toast.kind === 'notification' ? 'bell' : 'check'" :size="17" /></span>
      <button type="button" class="toast-message" @click="emit('open', toast)">{{ toast.message }}</button>
      <button class="toast-close" aria-label="Скрыть уведомление" @click.stop="emit('dismiss', toast.id)"><Icon name="x" :size="15" /></button>
    </div>
  </div>
</template>
