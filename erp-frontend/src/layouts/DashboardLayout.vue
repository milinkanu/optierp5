<template>
  <div class="dashboard-shell">
    <aside class="dashboard-sidebar">
      <div class="brand">FinOps</div>
      <nav>
        <router-link to="/">Dashboard</router-link>
      </nav>
    </aside>

    <main class="dashboard-main">
      <header class="dashboard-header">
        <button class="logout-button" @click="logout">Sign out</button>
      </header>
      <section class="dashboard-content">
        <slot />
      </section>
    </main>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const logout = async () => {
  await auth.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.dashboard-shell {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}

.dashboard-sidebar {
  background: #1e2a78;
  color: white;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.brand {
  font-size: 1.75rem;
  font-weight: 700;
}

.dashboard-sidebar a {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  display: block;
  margin-top: 12px;
}

.dashboard-main {
  background: #f4f7fb;
  padding: 24px;
}

.dashboard-header {
  display: flex;
  justify-content: flex-end;
}

.logout-button {
  color: #1e2a78;
  font-weight: 600;
  text-decoration: none;
}

.dashboard-content {
  margin-top: 24px;
}

@media (max-width: 900px) {
  .dashboard-shell {
    grid-template-columns: 1fr;
  }
  .dashboard-sidebar {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
