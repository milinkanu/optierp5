<template>
  <div class="auth-shell">
    <div class="auth-card">
      <slot />
    </div>
  </div>
</template>

<script setup>
</script>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(180deg, #eef2ff 0%, #f7f8fc 100%);
}

.auth-card {
  width: min(520px, 100%);
  padding: 32px;
  border-radius: 24px;
  background: #ffffff;
  box-shadow: 0 18px 60px rgba(32, 41, 72, 0.08);
}
</style>
