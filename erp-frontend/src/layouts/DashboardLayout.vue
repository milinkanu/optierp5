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
          <span v-if="!isCollapsed">optierp</span>
        </div>
        <button class="collapse-btn" @click="isCollapsed = !isCollapsed">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" exact-active-class="active">
          <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></i>
          <span v-if="!isCollapsed">Home</span>
        </router-link>

        <!-- Items Group -->
        <div class="nav-group">
          <div class="nav-item" @click="toggleGroup('items')" :class="{ 'group-active': expandedGroups.items }">
            <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg></i>
            <span v-if="!isCollapsed">Items</span>
            <i class="chevron" :class="{ expanded: expandedGroups.items }" v-if="!isCollapsed">▼</i>
          </div>
          <div class="nav-sub-items" v-show="expandedGroups.items && !isCollapsed">
            <router-link to="/items" class="nav-sub-item" active-class="active">Items</router-link>
          </div>
        </div>

        <!-- Sales Group -->
        <div class="nav-group">
          <div class="nav-item" @click="toggleGroup('sales')" :class="{ 'group-active': expandedGroups.sales }">
            <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="21" r="1"/><circle cx="19" cy="21" r="1"/><path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12"/></svg></i>
            <span v-if="!isCollapsed">Sales</span>
            <i class="chevron" :class="{ expanded: expandedGroups.sales }" v-if="!isCollapsed">▼</i>
          </div>
          <div class="nav-sub-items" v-show="expandedGroups.sales && !isCollapsed">
            <router-link to="/contacts" class="nav-sub-item" active-class="active">Customers</router-link>
            <router-link to="/sales/quotes" class="nav-sub-item" active-class="active">Quotes</router-link>
            <router-link to="/sales/orders" class="nav-sub-item" active-class="active">Sales Orders</router-link>
            <router-link to="/sales/invoices" class="nav-sub-item" active-class="active">Invoices</router-link>
            <router-link to="/sales/recurring-invoices" class="nav-sub-item" active-class="active">Recurring Invoices</router-link>
            <router-link to="/sales/delivery-challans" class="nav-sub-item" active-class="active">Delivery Challans</router-link>
            <router-link to="/sales/payments-received" class="nav-sub-item" active-class="active">Payments Received</router-link>
            <router-link to="/sales/credit-notes" class="nav-sub-item" active-class="active">Credit Notes</router-link>
          </div>
        </div>

        <!-- Purchases Group -->
        <div class="nav-group">
          <div class="nav-item" @click="toggleGroup('purchases')" :class="{ 'group-active': expandedGroups.purchases }">
            <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg></i>
            <span v-if="!isCollapsed">Purchases</span>
            <i class="chevron" :class="{ expanded: expandedGroups.purchases }" v-if="!isCollapsed">▼</i>
          </div>
          <div class="nav-sub-items" v-show="expandedGroups.purchases && !isCollapsed">
            <router-link to="/purchases/vendors" class="nav-sub-item" active-class="active">Vendors</router-link>
            <router-link to="/purchases/expenses" class="nav-sub-item" active-class="active">Expenses</router-link>
            <router-link to="/purchases/recurring-expenses" class="nav-sub-item" active-class="active">Recurring Expenses</router-link>
            <router-link to="/purchases/orders" class="nav-sub-item" active-class="active">Purchase Orders</router-link>
            <router-link to="/purchases/bills" class="nav-sub-item" active-class="active">Bills</router-link>
            <router-link to="/purchases/recurring-bills" class="nav-sub-item" active-class="active">Recurring Bills</router-link>
            <router-link to="/purchases/payments-made" class="nav-sub-item" active-class="active">Payments Made</router-link>
            <router-link to="/purchases/vendor-credits" class="nav-sub-item" active-class="active">Vendor Credits</router-link>
          </div>
        </div>

        <!-- Time Tracking Group -->
        <div class="nav-group">
          <div class="nav-item" @click="toggleGroup('timeTracking')" :class="{ 'group-active': expandedGroups.timeTracking }">
            <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></i>
            <span v-if="!isCollapsed">Time Tracking</span>
            <i class="chevron" :class="{ expanded: expandedGroups.timeTracking }" v-if="!isCollapsed">▼</i>
          </div>
          <div class="nav-sub-items" v-show="expandedGroups.timeTracking && !isCollapsed">
            <router-link to="/time-tracking/projects" class="nav-sub-item" active-class="active">Projects</router-link>
            <router-link to="/time-tracking/timesheet" class="nav-sub-item" active-class="active">Timesheet</router-link>
          </div>
        </div>

        <router-link to="/banking" class="nav-item" active-class="active">
          <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="22" x2="21" y2="22"/><line x1="6" y1="18" x2="6" y2="11"/><line x1="10" y1="18" x2="10" y2="11"/><line x1="14" y1="18" x2="14" y2="11"/><line x1="18" y1="18" x2="18" y2="11"/><polygon points="12 2 20 7 4 7"/></svg></i>
          <span v-if="!isCollapsed">Banking</span>
        </router-link>

        <!-- Accountant Group -->
        <div class="nav-group">
          <div class="nav-item" @click="toggleGroup('accountant')" :class="{ 'group-active': expandedGroups.accountant }">
            <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></i>
            <span v-if="!isCollapsed">Accountant</span>
            <i class="chevron" :class="{ expanded: expandedGroups.accountant }" v-if="!isCollapsed">▼</i>
          </div>
          <div class="nav-sub-items" v-show="expandedGroups.accountant && !isCollapsed">
            <router-link to="/accountant/manual-journals" class="nav-sub-item" active-class="active">Manual Journals</router-link>
            <router-link to="/accountant/bulk-update" class="nav-sub-item" active-class="active">Bulk Update</router-link>
            <router-link to="/accountant/currency-adjustments" class="nav-sub-item" active-class="active">Currency Adjustments</router-link>
            <router-link to="/accountant/chart-of-accounts" class="nav-sub-item" active-class="active">Chart of Accounts</router-link>
            <router-link to="/accountant/budgets" class="nav-sub-item" active-class="active">Budgets</router-link>
            <router-link to="/accountant/transaction-locking" class="nav-sub-item" active-class="active">Transaction Locking</router-link>
          </div>
        </div>

        <router-link to="/reports" class="nav-item" active-class="active">
          <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></i>
          <span v-if="!isCollapsed">Reports</span>
        </router-link>

        <router-link to="/documents" class="nav-item" active-class="active">
          <i class="icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-1.2-1.8A2 2 0 0 0 8.55 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg></i>
          <span v-if="!isCollapsed">Documents</span>
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

const expandedGroups = ref({
  items: true,
  sales: true,
  purchases: true,
  timeTracking: false,
  accountant: false,
})

const toggleGroup = (group) => {
  expandedGroups.value[group] = !expandedGroups.value[group]
}

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
  transition: transform 0.2s ease;
}

.chevron.expanded {
  transform: rotate(180deg);
}

.nav-sub-items {
  display: flex;
  flex-direction: column;
  background: rgba(0, 0, 0, 0.15);
}

.nav-sub-item {
  padding: 8px 16px 8px 48px;
  font-size: 0.85rem;
  color: #aab2bd;
  text-decoration: none;
  transition: all 0.2s;
}

.nav-sub-item:hover {
  color: white;
  background: rgba(255, 255, 255, 0.05);
}

.nav-sub-item.active {
  color: white;
  background: #1e88e5;
  border-left: 3px solid #64b5f6;
  padding-left: 45px; /* adjust for border */
}

.nav-item.group-active {
  background: rgba(255, 255, 255, 0.05);
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
