<script setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import Icon from './Icon.vue'
defineProps({ title: String, wide: Boolean })
const emit = defineEmits(['close'])
const dialog = ref(null)
let previousFocus
function keydown(event) {
  if (event.key === 'Escape') emit('close')
  if (event.key === 'Tab') {
    const elements = dialog.value?.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]')
    if (!elements?.length) return
    const first = elements[0], last = elements[elements.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}
onMounted(async () => { previousFocus = document.activeElement; document.body.style.overflow = 'hidden'; document.addEventListener('keydown', keydown); await nextTick(); dialog.value?.focus() })
onBeforeUnmount(() => { document.body.style.overflow = ''; document.removeEventListener('keydown', keydown); previousFocus?.focus() })
</script>
<template>
  <Teleport to="body"><div class="modal-backdrop" @click.self="emit('close')"><section ref="dialog" role="dialog" aria-modal="true" :aria-label="title" tabindex="-1" class="modal panel" :class="{ wide }">
    <header class="modal-header"><h2>{{ title }}</h2><button class="icon-btn" aria-label="Закрыть" @click="emit('close')"><Icon name="x" /></button></header>
    <slot />
  </section></div></Teleport>
</template>
