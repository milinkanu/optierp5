import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export function useAuthGuard() {
  const router = useRouter()
  const auth = useAuthStore()

  const requireAuth = async () => {
    if (!auth.isAuthenticated) {
      auth.initialize()
    }
    if (!auth.isAuthenticated) {
      await router.push({ name: 'Login' })
    }
  }

  return { requireAuth }
}
