<script setup>
import Icon from './Icon.vue'

defineProps({
  config: { type: Object, default: () => ({}) },
  error: { type: String, default: '' },
  persona: { type: String, required: true },
})

const emit = defineEmits(['update:persona', 'demo'])
</script>

<template>
  <section class="login-wrap">
    <div class="login-brand">
      <span class="brand-mark large"><Icon name="cloud" :size="30" /></span>
      <div>
        <span class="eyebrow">ТВОЙ МАРШРУТ К НОВЫМ ЦЕЛЯМ</span>
        <h1>Здесь начинается<br /><span class="accent">следующий уровень.</span></h1>
        <p>Выполняй задания, открывай награды и соревнуйся с друзьями. Каждый шаг приближает к цели.</p>
      </div>
    </div>
    <div class="login-art">
      <img src="https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1100&q=85" alt="Солнечный свет над горами, открывающий путь к новым вершинам" fetchpriority="high" />
    </div>
    <div class="login-footer">
      <span>Учись в своём ритме. Расти вместе.</span>
      <div class="role-chip-row">
        <span><Icon name="book" :size="14" /> Задания</span><span><Icon name="award" :size="14" /> Награды</span><span><Icon name="swords" :size="14" /> Дуэли</span>
      </div>
      <p v-if="error" class="login-error">{{ error }}</p>
      <div v-if="config.dev_auth" class="dev-login">
        <label>Демонстрационный вход
          <select id="dev-persona" :value="persona" @change="emit('update:persona', $event.target.value)">
            <option value="student">Ученик</option><option value="friend">Друг ученика</option><option value="teacher">Преподаватель</option><option value="manager">Управляющий</option><option value="admin">Администратор</option>
          </select>
        </label>
        <button class="btn primary" @click="emit('demo')">Открыть арену <Icon name="arrow-right" :size="16" /></button>
      </div>
      <span v-else class="login-hint"><Icon name="lock" :size="15" /> Откройте приложение через MAX, чтобы продолжить</span>
    </div>
  </section>
</template>
