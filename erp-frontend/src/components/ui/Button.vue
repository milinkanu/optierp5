<template>
  <button class="btn" :class="variant" :type="type" :disabled="disabled || loading" @click="$emit('click', $event)">
    <span v-if="loading" class="spinner" />
    <slot />
  </button>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // primary|secondary|danger
  type: { type: String, default: 'button' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})
defineEmits(['click'])
</script>

<style scoped>
.btn {
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: 0.15s ease;
}
.primary {
  background: #1a73e8;
  color: #fff;
}
.primary:hover {
  background: #1565d8;
}
.secondary {
  background: #fff;
  border-color: #d1d5db;
  color: #111827;
}
.secondary:hover {
  background: #f9fafb;
}
.danger {
  background: #ef4444;
  color: #fff;
}
.danger:hover {
  background: #dc2626;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.spinner {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: rgba(255, 255, 255, 1);
  animation: spin 0.8s linear infinite;
}
.secondary .spinner {
  border-color: rgba(17, 24, 39, 0.2);
  border-top-color: rgba(17, 24, 39, 0.8);
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>

