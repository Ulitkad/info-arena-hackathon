<script setup>
import { computed, ref, watch } from 'vue'
const props = defineProps({ user: Object, size: { type: Number, default: 44 }, framed: Boolean })
const broken = ref(false)
watch(() => props.user?.avatar_url, () => { broken.value = false })
const initials = computed(() => (props.user?.display_name || '?').split(' ').slice(0, 2).map(p => p[0]).join(''))
const colors = ['#e0edff', '#e8e7ff', '#def5ee', '#ffeadf', '#e0f3ff']
</script>
<template>
  <span class="avatar" :class="{ framed: framed || user?.active_frame_id }" :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * .3}px`, background: colors[(user?.id || 0) % colors.length] }">
    <img v-if="user?.avatar_url && !broken" :src="user.avatar_url" :alt="user.display_name" referrerpolicy="no-referrer" @error="broken = true" />
    <span v-else>{{ initials }}</span>
  </span>
</template>
