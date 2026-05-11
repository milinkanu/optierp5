<template>
  <div>
    <h1>Forgot password</h1>
    <p>Enter the email associated with your account.</p>

    <form @submit.prevent="submit">
      <label>
        Email
        <input v-model="email" type="email" required />
      </label>
      <button type="submit" :disabled="isLoading">Send reset link</button>
    </form>

    <p class="footer-text">
      Remembered? <router-link to="/auth/login">Sign in</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../../api/auth'
import { useToastStore } from '../../stores/toast'

const email = ref('')
const isLoading = ref(false)
const router = useRouter()
const toast = useToastStore()

const submit = async () => {
  isLoading.value = true
  try {
    await authApi.forgotPassword({ email: email.value })
    toast.show('If that email exists, we sent instructions.', 'success')
    router.push({ name: 'Login' })
  } catch (error) {
    toast.show('Unable to send reset link. Please try again later.', 'error')
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
