<template>
  <div>
    <h1>Reset password</h1>
    <p>Enter a secure new password for your account.</p>

    <form @submit.prevent="submit">
      <label>
        New password
        <input v-model="password" type="password" required />
      </label>
      <button type="submit" :disabled="isLoading">Reset password</button>
    </form>

    <p class="footer-text">
      Back to <router-link to="/auth/login">Sign in</router-link>
    </p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi } from '../../api/auth'
import { useToastStore } from '../../stores/toast'

const router = useRouter()
const route = useRoute()
const toast = useToastStore()
const password = ref('')
const token = ref('')
const isLoading = ref(false)

onMounted(() => {
  token.value = route.query.token || ''
})

const submit = async () => {
  if (!token.value) {
    alert('Reset token is missing.')
    return
  }
  isLoading.value = true
  try {
    await authApi.resetPassword({ reset_token: token.value, password: password.value })
    toast.show('Password has been reset successfully.', 'success')
    router.push({ name: 'Login' })
  } catch {
    toast.show('Reset failed. Please try again with a valid link.', 'error')
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
form {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}
label,
.footer-text {
  display: grid;
  gap: 8px;
}
input {
  border: 1px solid #cad3e8;
  border-radius: 12px;
  padding: 14px 16px;
  width: 100%;
}
button {
  width: 100%;
  padding: 14px 16px;
  border: none;
  background: #1e2a78;
  color: white;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.footer-text {
  color: #4b5563;
}
.footer-text a {
  color: #1e2a78;
  text-decoration: none;
}
</style>
