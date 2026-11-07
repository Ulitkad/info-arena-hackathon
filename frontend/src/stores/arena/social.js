import { ref } from 'vue'

export function createSocialState() {
  const duels = ref([])

  function reset() { duels.value = [] }

  return { duels, reset }
}
