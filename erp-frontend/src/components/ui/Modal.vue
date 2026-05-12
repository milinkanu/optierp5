<template>
  <div v-if="open" class="backdrop" @click.self="$emit('close')">
    <div class="modal">
      <div class="header">
        <div class="h">{{ title }}</div>
        <button class="x" @click="$emit('close')">×</button>
      </div>
      <div class="body">
        <slot />
      </div>
      <div class="footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
})
defineEmits(['close'])
</script>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 50;
}
.modal {
  width: min(720px, 100%);
  max-height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
}
.body {
  padding: 16px;
  overflow: auto;
}
.header {
  padding: 14px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e5e7eb;
}
.h {
  font-weight: 700;
  color: #111827;
}
.x {
  border: none;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
  color: #6b7280;
}
.body {
  padding: 16px;
}
.footer {
  padding: 12px 16px;
  border-top: 1px solid #e5e7eb;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

