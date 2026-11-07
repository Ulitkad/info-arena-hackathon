import { ref } from 'vue'

export function createLearningState() {
  const passes = ref([])
  const inventory = ref([])
  const homework = ref([])
  const events = ref([])
  const achievements = ref([])

  function reset() {
    passes.value = []
    inventory.value = []
    homework.value = []
    events.value = []
    achievements.value = []
  }

  return { passes, inventory, homework, events, achievements, reset }
}
