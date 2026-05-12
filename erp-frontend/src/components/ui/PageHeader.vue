<template>
  <div class="page-header">
    <div>
      <h1 class="title">{{ title }}</h1>
      <p v-if="subtitle" class="subtitle">{{ subtitle }}</p>
    </div>
    <div class="actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.title {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #1f2a37;
}
.subtitle {
  margin: 6px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>

