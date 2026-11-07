<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import QRCode from 'qrcode'
import Modal from './Modal.vue'

const props = defineProps({
  title: { type: String, default: 'QR-код приглашения' },
  url: { type: String, required: true },
})
const emit = defineEmits(['close'])
const canvas = ref(null)

async function renderQr() {
  await nextTick()
  if (!canvas.value || !props.url) return
  await QRCode.toCanvas(canvas.value, props.url, {
    width: 260,
    margin: 2,
    errorCorrectionLevel: 'M',
    color: { dark: '#151a2d', light: '#ffffff' },
  })
}

watch(() => props.url, renderQr)
onMounted(renderQr)
</script>

<template>
  <Modal :title="title" @close="emit('close')">
    <div class="qr-modal-content">
      <p>Наведите камеру телефона, чтобы открыть ссылку-приглашение.</p>
      <canvas ref="canvas" class="invite-qr" aria-label="QR-код ссылки приглашения"></canvas>
      <code class="qr-url">{{ url }}</code>
    </div>
  </Modal>
</template>
