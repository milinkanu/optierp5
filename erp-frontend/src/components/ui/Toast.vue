<template>
  <div v-if="toast.visible" :class="['toast', toast.type]">
    {{ toast.message }}
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useToastStore } from '../../stores/toast'

const toastStore = useToastStore()
const toast = computed(() => toastStore)
</script>

<style scoped>
.toast {
  position: fixed;
  right: 20px;
  bottom: 20px;
  background: white;
  border-radius: 14px;
  padding: 14px 20px;
  box-shadow: 0 18px 50px rgba(51, 64, 106, 0.12);
  min-width: 240px;
  z-index: 999;
}
.toast.info {
  border-left: 4px solid #3b82f6;
}
.toast.success {
  border-left: 4px solid #10b981;
}
.toast.error {
  border-left: 4px solid #ef4444;
}
</style>
