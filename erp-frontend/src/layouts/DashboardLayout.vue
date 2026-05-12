<template>
  <div class="zoho-shell">
    <!-- Sidebar -->
    <aside class="zoho-sidebar" :class="{ 'collapsed': isCollapsed }">
      <div class="sidebar-header">
        <div class="logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="2" y="2" width="20" height="20" rx="4" fill="#1e88e5"/>
            <path d="M7 12H17M7 8H17M7 16H13" stroke="white" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <span v-if="!isCollapsed">Books</span>
        </div>
        <button class="collapse-btn" @click="isCollapsed = !isCollapsed">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item active">
          <i class="icon">🏠</i>
          <span v-if="!isCollapsed">Home</span>
        </router-link>

        <router-link to="/contacts" class="nav-item">
          <i class="icon">C</i>
          <span v-if="!isCollapsed">Contacts</span>
        </router-link>

        <router-link to="/items" class="nav-item">
          <i class="icon">M</i>
          <span v-if="!isCollapsed">Items Master</span>
        </router-link>
        
        <div class="nav-group">
          <div class="nav-item">
            <i class="icon">📦</i>
            <span v-if="!isCollapsed">Items</span>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-item">
            <i class="icon">🛒</i>
            <span v-if="!isCollapsed">Sales</span>
            <i class="chevron" v-if="!isCollapsed">▼</i>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-item">
            <i class="icon">🛍️</i>
            <span v-if="!isCollapsed">Purchases</span>
            <i class="chevron" v-if="!isCollapsed">▼</i>
          </div>
        </div>

        <div class="nav-item">
          <i class="icon">⏳</i>
          <span v-if="!isCollapsed">Time Tracking</span>
        </div>

        <div class="nav-item">
          <i class="icon">🏦</i>
          <span v-if="!isCollapsed">Banking</span>
        </div>

        <div class="nav-item">
          <i class="icon">👨‍💼</i>
          <span v-if="!isCollapsed">Accountant</span>
        </div>

        <div class="nav-item">
          <i class="icon">📊</i>
          <span v-if="!isCollapsed">Reports</span>
        </div>

        <div class="nav-item">
          <i class="icon">📁</i>
          <span v-if="!isCollapsed">Documents</span>
        </div>

        <router-link to="/sales/invoices" class="nav-item">
          <i class="icon">I</i>
          <span v-if="!isCollapsed">Invoices</span>
        </router-link>

        <router-link to="/accountant/chart-of-accounts" class="nav-item">
          <i class="icon">A</i>
          <span v-if="!isCollapsed">Chart of Accounts</span>
        </router-link>
      </nav>

      <div class="sidebar-footer" v-if="!isCollapsed">
        <div class="apps-label">APPS</div>
        <div class="nav-item small">Zoho Payroll</div>
        <div class="nav-item small">Zoho Payments</div>
      </div>
    </aside>

    <!-- Main Area -->
    <div class="zoho-main">
      <header class="zoho-header">
        <div class="header-left">
          <div class="search-bar">
            <i class="search-icon">🔍</i>
            <input type="text" placeholder="Search in Customers (/)" />
          </div>
        </div>
        
        <div class="header-right">
          <div class="trial-badge">Your premium trial expires in 12 days</div>
          <button class="subscribe-btn">Subscribe</button>
          <div class="header-icons">
            <button class="icon-btn">➕</button>
            <button class="icon-btn">🔔</button>
            <button class="icon-btn">⚙️</button>
            <div class="user-profile" @click="logout">
              <div class="avatar">SK</div>
            </div>
          </div>
        </div>
      </header>

      <main class="zoho-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const isCollapsed = ref(false)

const logout = async () => {
  await auth.logout()
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.zoho-shell {
  display: flex;
  height: 100vh;
  background: #f5f7fa;
  color: #333;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* Sidebar */
.zoho-sidebar {
  width: 240px;
  background: #2b334a;
  color: #aab2bd;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  flex-shrink: 0;
}

.zoho-sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  color: white;
  font-weight: 700;
  font-size: 1.1rem;
}

.collapse-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 0;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  color: inherit;
  font-size: 0.9rem;
}

.nav-item:hover {
  background: #3b455d;
  color: white;
}

.nav-item.active {
  background: #1e88e5;
  color: white;
}

.icon {
  font-style: normal;
  width: 20px;
  text-align: center;
}

.chevron {
  margin-left: auto;
  font-size: 0.7rem;
  opacity: 0.5;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.apps-label {
  font-size: 0.7rem;
  font-weight: 700;
  margin-bottom: 8px;
  opacity: 0.5;
}

.nav-item.small {
  padding: 6px 0;
  font-size: 0.8rem;
}

/* Main Area */
.zoho-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.zoho-header {
  height: 56px;
  background: #2b334a;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  color: white;
  z-index: 10;
}

.header-left {
  flex: 1;
}

.search-bar {
  position: relative;
  max-width: 400px;
}

.search-bar input {
  width: 100%;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 4px;
  padding: 8px 12px 8px 36px;
  color: white;
  font-size: 0.9rem;
}

.search-icon {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  opacity: 0.5;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.trial-badge {
  font-size: 0.8rem;
  opacity: 0.7;
}

.subscribe-btn {
  background: #1e88e5;
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}

.header-icons {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-btn {
  background: none;
  border: none;
  color: white;
  font-size: 1.1rem;
  cursor: pointer;
  opacity: 0.8;
}

.user-profile {
  margin-left: 8px;
  cursor: pointer;
}

.avatar {
  width: 32px;
  height: 32px;
  background: #ff7043;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8rem;
  font-weight: 700;
}

.zoho-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

@media (max-width: 768px) {
  .zoho-sidebar {
    position: fixed;
    height: 100%;
    z-index: 100;
    transform: translateX(-100%);
  }
  .zoho-sidebar.open {
    transform: translateX(0);
  }
}
</style>
