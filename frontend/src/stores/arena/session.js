import { ref } from 'vue'

export function createSessionState() {
  const user = ref(null)
  const config = ref({})
  const loading = ref(true)
  const error = ref('')
  const revision = ref(0)
  const saving = ref(false)
  const connected = ref(false)
  let version = 0

  return {
    user, config, loading, error, revision, saving, connected,
    nextVersion() { version += 1; return version },
    currentVersion() { return version },
  }
}
