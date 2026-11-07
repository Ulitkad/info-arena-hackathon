<script setup>
import { computed, onMounted } from 'vue'
import { useArena } from '../stores/arena'
import Icon from '../components/Icon.vue'

const store = useArena()
onMounted(() => store.refreshStudent().catch(error => store.toast(error.message, 'error')))
const unlocked = computed(() => store.achievements.filter(item => item.unlocked))
const locked = computed(() => store.achievements.filter(item => !item.unlocked && !item.hidden))
</script>

<template>
  <section class="achievements-page">
    <div class="section-head">
      <div><span class="eyebrow">КОЛЛЕКЦИЯ</span><h2>Достижения</h2><p class="muted">Они открываются сами, когда ты выполняешь условия.</p></div>
      <span class="subtle-count">{{ unlocked.length }} / {{ store.achievements.length }} открыто</span>
    </div>
    <div class="achievement-grid">
      <article v-for="item in unlocked" :key="item.id" class="achievement-card panel unlocked">
        <span class="achievement-icon achievement-badge"><Icon :name="item.icon || 'award'" :size="22" /></span>
        <div><strong>{{ item.name }}</strong><p>{{ item.description }}</p><small>Открыто</small></div>
      </article>
      <article v-for="item in locked" :key="item.id" class="achievement-card panel locked">
        <span class="achievement-icon"><Icon name="lock" :size="20" /></span>
        <div><strong>{{ item.name }}</strong><p>{{ item.description }}</p><small>{{ item.progress }} / {{ item.threshold }}</small></div>
      </article>
    </div>
    <p v-if="!store.achievements.length" class="empty-page panel">Достижения появятся после вступления в учебную группу.</p>
  </section>
</template>
