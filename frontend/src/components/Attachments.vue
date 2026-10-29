<script setup>
import { ref } from 'vue'
import { post } from '../api'
import { useArena } from '../stores/arena'
import Icon from './Icon.vue'
const props = defineProps({ modelValue: { type: Array, default: () => [] }, readonly: Boolean })
const emit = defineEmits(['update:modelValue'])
const store = useArena(), uploading = ref(false)
async function upload(event) {
  const files = Array.from(event.target.files || [])
  if (props.modelValue.length + files.length > 10) { store.toast('Можно прикрепить до 10 файлов', 'error'); return }
  uploading.value = true
  try {
    let result = [...props.modelValue]
    for (const file of files) {
      if (file.size > 20 * 1024 * 1024) throw new Error('Файл должен быть не больше 20 МБ')
      const form = new FormData(); form.append('file', file)
      const data = await post('/uploads', form)
      result = [...result, data.url]; emit('update:modelValue', result)
    }
  } catch (e) { store.toast(e.message, 'error') }
  finally { uploading.value = false; event.target.value = '' }
}
function open(url) {
  const absolute = new URL(url, location.origin).href
  if (window.WebApp?.initData && window.WebApp?.downloadFile && location.protocol === 'https:') window.WebApp.downloadFile(absolute, url.split('/').pop()).catch(() => store.toast('Не удалось скачать файл', 'error'))
  else window.open(absolute, '_blank', 'noopener,noreferrer')
}
</script>
<template><div class="attachments">
  <div v-for="(url, index) in modelValue" :key="url" class="file-chip"><button type="button" @click="open(url)"><Icon name="file" :size="16" /> Файл {{ index + 1 }}<Icon name="external" :size="12" /></button><button v-if="!readonly" type="button" aria-label="Удалить вложение" @click="emit('update:modelValue', modelValue.filter(v => v !== url))"><Icon name="x" :size="15" /></button></div>
  <label v-if="!readonly" class="attach-btn"><Icon name="upload" :size="17" />{{ uploading ? 'Загрузка…' : 'Прикрепить файлы' }}<input type="file" multiple :disabled="uploading" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.txt,.docx,.xlsx,.pptx,.zip" @change="upload" /></label>
</div></template>
