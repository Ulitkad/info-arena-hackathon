import { ref } from 'vue'

export function createNotificationState() {
  const notifications = ref([])
  const unread = ref(0)
  const toasts = ref([])

  function reset() {
    notifications.value = []
    unread.value = 0
    toasts.value = []
  }

  return { notifications, unread, toasts, reset }
}
