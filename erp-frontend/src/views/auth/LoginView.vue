<template>
  <div>
    <h1>Welcome back</h1>
    <p>Sign in to access your FinOps workspace.</p>

    <form @submit.prevent="submit">
      <label>
        Email
        <input v-model="email" type="email" placeholder="you@example.com" required />
      </label>

      <label>
        Password
        <input v-model="password" type="password" placeholder="••••••••" required />
      </label>

      <button type="submit" :disabled="isLoading">Sign In</button>
    </form>

    <div class="auth-links">
      <router-link to="/auth/forgot-password">Forgot password?</router-link>
      <router-link to="/auth/signup">Create an account</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'

const email = ref('')
const password = ref('')
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const isLoading = ref(false)

const submit = async () => {
  isLoading.value = true
  try {
    await auth.login({ email: email.value, password: password.value })
    toast.show('Signed in successfully', 'success')
    router.push({ name: 'Dashboard' })
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Login failed. Please check your credentials.', 'error')
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
label {
  display: grid;
  gap: 8px;
  font-weight: 600;
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
.auth-links {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.auth-links a {
  color: #1e2a78;
  text-decoration: none;
}
</style>
