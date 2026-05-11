<template>
  <div>
    <h1>Create your company</h1>
    <p>Start your FinOps trial with secure team access.</p>

    <form @submit.prevent="submit">
      <label>
        Company name
        <input v-model="companyName" required />
      </label>

      <label>
        Owner name
        <input v-model="name" required />
      </label>

      <label>
        Email
        <input v-model="email" type="email" required />
      </label>

      <label>
        Password
        <input v-model="password" type="password" required />
      </label>

      <button type="submit" :disabled="isLoading">Create account</button>
    </form>

    <p class="footer-text">
      Already have an account? <router-link to="/auth/login">Sign in</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useToastStore } from '../../stores/toast'

const companyName = ref('')
const name = ref('')
const email = ref('')
const password = ref('')
const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()
const isLoading = ref(false)

const submit = async () => {
  isLoading.value = true
  try {
    await auth.signup({
      company: {
        company_name: companyName.value,
        company_type: 'pvt_ltd',
        pan: 'AAAAA1111A',
        gst_type: 'regular',
        primary_state: 'Karnataka',
      },
      user: {
        name: name.value,
        email: email.value,
        password: password.value,
      },
    })
    toast.show('Signup complete. Welcome to FinOps!', 'success')
    router.push({ name: 'Dashboard' })
  } catch (error) {
    toast.show(error.response?.data?.detail || 'Signup failed. Please retry.', 'error')
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
