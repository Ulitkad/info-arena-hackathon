import { ref } from 'vue'

export function createLearningState() {
  const passes = ref([])
  const inventory = ref([])
  const homework = ref([])
  const events = ref([])

  function reset() {
    passes.value = []
    inventory.value = []
    homework.value = []
    events.value = []
  }

  return { passes, inventory, homework, events, reset }
}
