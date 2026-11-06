<script setup>
import { computed, ref } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({ modelValue: { type: String, default: '#4f8fe8' } })
const emit = defineEmits(['update:modelValue'])
const open = ref(false)
const draft = ref(props.modelValue)
const presets = ['#357bea', '#26a687', '#33b8dc', '#e78085', '#8b6fe8', '#e3a34b', '#182337', '#8b98a8']
const validColor = computed(() => /^#[0-9a-f]{6}$/i.test(draft.value) ? draft.value : props.modelValue)
function update(value) {
  draft.value = value
  if (/^#[0-9a-f]{6}$/i.test(value)) emit('update:modelValue', value)
}
function show() { draft.value = props.modelValue; open.value = true }
function close() { draft.value = props.modelValue; open.value = false }
</script>

<template>
  <div class="color-picker">
    <button type="button" class="color-picker-trigger" @click="show">
      <span class="color-picker-swatch" :style="{ background: modelValue }"></span>
      <span><strong>Выбрать цвет</strong><small>{{ modelValue.toUpperCase() }}</small></span>
      <Icon name="chevron-down" :size="16" />
    </button>
    <div v-if="open" class="color-picker-popover" role="dialog" aria-label="Выбор цвета">
      <div class="color-picker-head"><strong>Цвет предмета</strong><button type="button" class="icon-btn" aria-label="Закрыть выбор цвета" @click="close"><Icon name="x" :size="16" /></button></div>
      <div class="color-picker-preview" :style="{ background: validColor }"><span>{{ validColor.toUpperCase() }}</span></div>
      <div class="color-presets" aria-label="Готовые цвета">
        <button v-for="color in presets" :key="color" type="button" class="color-preset" :class="{ selected: color.toLowerCase() === modelValue.toLowerCase() }" :style="{ background: color }" :aria-label="`Выбрать цвет ${color}`" @click="update(color)"></button>
      </div>
      <label class="field-label color-picker-input">HEX-код<input :value="draft" maxlength="7" inputmode="text" placeholder="#4f8fe8" @input="update($event.target.value)" /></label>
      <div class="color-picker-actions"><button type="button" class="btn secondary small" @click="close">Готово</button><label class="btn primary small color-native"><input type="color" :value="validColor" @input="update($event.target.value)" />Открыть палитру</label></div>
    </div>
  </div>
</template>
