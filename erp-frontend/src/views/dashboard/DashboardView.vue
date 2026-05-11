<template>
  <div class="dashboard-grid">
    <section class="dashboard-hero">
      <h1>Welcome to FinOps</h1>
      <p>Your secure ERP dashboard is ready.</p>
    </section>

    <section class="dashboard-cards">
      <article class="feature-card">
        <h2>Secure auth</h2>
        <p>JWT, refresh tokens, password reset, and email verification built for production.</p>
      </article>
      <article class="feature-card">
        <h2>Tenant aware</h2>
        <p>Company tenancy ensures data isolation and RBAC-ready access control.</p>
      </article>
    </section>
  </div>
</template>

<script setup>
</script>

<style scoped>
.dashboard-grid {
  display: grid;
  gap: 24px;
}
.dashboard-hero {
  background: white;
  padding: 32px;
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(51, 64, 106, 0.08);
}
.feature-card {
  background: white;
  padding: 24px;
  border-radius: 20px;
  box-shadow: 0 12px 32px rgba(51, 64, 106, 0.08);
}
</style>
