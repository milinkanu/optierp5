<template>
  <div>
    <h1>Verify your email</h1>
    <p v-if="message">{{ message }}</p>
    <p v-else>Verifying your email address now...</p>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../../api/auth'
import { useToastStore } from '../../stores/toast'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const message = ref('')

onMounted(async () => {
  const token = route.query.token
  if (!token) {
    message.value = 'Verification token missing.'
    return
  }

  try {
    await authApi.verifyEmail(token)
    message.value = 'Email verified. Please sign in to continue.'
    toast.show('Email verified successfully', 'success')
    setTimeout(() => router.push({ name: 'Login' }), 1800)
  } catch {
    message.value = 'Verification failed. Please request a new link.'
    toast.show('Verification failed. Please request a new link.', 'error')
  }
})
</script>

<style scoped>
h1 {
  margin-bottom: 16px;
}
</style>
