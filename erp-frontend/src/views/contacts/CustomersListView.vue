<template>
  <div class="page">
    <!-- Header -->
    <PageHeader title="Customer Management Master" subtitle="Onboard compliance-ready customers, track double-entry opening balances, and run CSV mapping imports.">
      <template #actions>
        <Button variant="secondary" @click="wizardOpen = true">
          <span class="btn-icon">📊</span> Import CSV Wizard
        </Button>
        <Button @click="openCreate">
          <span class="btn-icon">+</span> New Customer
        </Button>
      </template>
    </PageHeader>

    <!-- Main List Container Card -->
    <Card class="list-card">
      <!-- Search & Filters Toolbar -->
      <div class="toolbar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input
            v-model="searchQuery"
            class="input search-input"
            placeholder="Search by legal name, display name, customer code, email, or GSTIN..."
            @keyup.enter="refresh"
          />
        </div>
        
        <div class="filter-group">
          <select v-model="statusFilter" class="input filter-select" @change="refresh">
            <option value="">All Statuses</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive Only</option>
          </select>
        </div>

        <Button variant="secondary" @click="refresh">Search</Button>
        <Button variant="secondary" @click="clearFilters" class="clear-btn">Clear</Button>
      </div>

      <!-- Main Customers Table -->
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Customer Code</th>
              <th>Customer Details</th>
              <th>Company Type</th>
              <th>GST Registration</th>
              <th>Opening Balance</th>
              <th>Status</th>
              <th style="width: 140px; text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading" class="no-hover">
              <td colspan="7" class="loading-state-row">
                <div class="loader-spinner"></div>
                <span class="muted font-semibold">Loading customer ledger database...</span>
              </td>
            </tr>
            <tr v-else-if="store.items.length === 0" class="no-hover">
              <td colspan="7" class="empty-state-row">
                <div class="empty-emoji">👥</div>
                <div class="empty-title">No customers found</div>
                <div class="empty-desc">Get started by creating your first Zoho-style progressive customer or import a CSV master record.</div>
                <div class="empty-actions">
                  <Button @click="openCreate">Onboard Customer</Button>
                </div>
              </td>
            </tr>
            <tr v-for="c in store.items" :key="c.customer_id" class="customer-row">
              <td class="mono font-bold">{{ c.customer_code }}</td>
              <td>
                <div class="customer-info-cell">
                  <div class="customer-display-name">{{ c.display_name }}</div>
                  <div class="customer-legal-name">{{ c.customer_name }}</div>
                  <div class="customer-meta" v-if="c.email || c.mobile">
                    <span v-if="c.email" class="meta-item">{{ c.email }}</span>
                    <span v-if="c.email && c.mobile" class="bullet">•</span>
                    <span v-if="c.mobile" class="meta-item">{{ c.mobile }}</span>
                  </div>
                </div>
              </td>
              <td>
                <span class="type-badge" :class="c.customer_type">
                  {{ c.customer_type === 'business' ? 'Business' : 'Individual' }}
                </span>
              </td>
              <td>
                <div class="compliance-cell">
                  <div class="gst-reg-type">{{ formatGstRegType(c.gst_registration_type) }}</div>
                  <div v-if="c.gstin" class="mono gstin-text">{{ c.gstin }}</div>
                  <div v-else class="unregistered-text">Unregistered / Consumer</div>
                </div>
              </td>
              <td>
                <div class="balance-cell" :class="{ 'has-balance': c.opening_balance > 0 }">
                  <span class="balance-amount">{{ formatCurrency(c.opening_balance) }}</span>
                  <span v-if="c.opening_balance > 0" class="balance-type-badge" :class="c.opening_balance_type">
                    {{ c.opening_balance_type === 'debit' ? 'Dr (A/R)' : 'Cr' }}
                  </span>
                </div>
              </td>
              <td>
                <button
                  type="button"
                  class="status-toggle-btn"
                  :class="{ active: c.is_active }"
                  @click="toggleCustomerStatus(c)"
                >
                  {{ c.is_active ? 'Active' : 'Inactive' }}
                </button>
              </td>
              <td>
                <div class="actions-cell">
                  <button type="button" class="action-btn edit" title="Edit Customer Details" @click="openEdit(c)">
                    ✏️ Edit
                  </button>
                  <button type="button" class="action-btn delete" title="Soft Delete Customer" @click="deleteCustomer(c)">
                    🗑️ Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <!-- Modals and Drawer Dialogs -->
    <CreateEditCustomerModal
      :open="modalOpen"
      :editing="editingCustomer"
      @close="modalOpen = false"
      @saved="refresh"
    />

    <CSVImportWizard
      :open="wizardOpen"
      @close="wizardOpen = false"
      @imported="refresh"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useCustomersStore } from '../../stores/customers'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'
import CreateEditCustomerModal from './CreateEditCustomerModal.vue'
import CSVImportWizard from './CSVImportWizard.vue'

const store = useCustomersStore()
const toast = useToastStore()

const searchQuery = ref('')
const statusFilter = ref('')

const modalOpen = ref(false)
const wizardOpen = ref(false)
const editingCustomer = ref(null)

const refresh = async () => {
  const params = {}
  if (searchQuery.value) params.q = searchQuery.value
  if (statusFilter.value === 'active') params.is_active = true
  if (statusFilter.value === 'inactive') params.is_active = false
  
  try {
    await store.fetchList(params)
  } catch (e) {
    toast.error('Failed to load customers list.')
  }
}

onMounted(refresh)

function clearFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
  refresh()
}

function openCreate() {
  editingCustomer.value = null
  modalOpen.value = true
}

function openEdit(customer) {
  editingCustomer.value = customer
  modalOpen.value = true
}

async function deleteCustomer(customer) {
  const confirmText = `Are you sure you want to delete customer '${customer.display_name}'? This will soft delete their record but maintain ledger historical records.`
  if (window.confirm(confirmText)) {
    try {
      await store.delete(customer.customer_id)
      toast.success('Customer deleted successfully')
      await refresh()
    } catch (e) {
      toast.error(e || 'Delete failed')
    }
  }
}

async function toggleCustomerStatus(customer) {
  const newStatus = !customer.is_active
  try {
    await store.update(customer.customer_id, {
      is_active: newStatus
    })
    toast.success(`Customer set to ${newStatus ? 'Active' : 'Inactive'}`)
    await refresh()
  } catch (e) {
    toast.error('Failed to update status')
  }
}

function formatCurrency(val) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2
  }).format(val || 0)
}

function formatGstRegType(type) {
  const maps = {
    regular: 'Registered Business',
    composition: 'Composition Scheme',
    unregistered: 'Unregistered Business',
    sez: 'SEZ Special Zone',
    consumer: 'Consumer / B2C'
  }
  return maps[type] || type
}
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
}

.list-card {
  padding: 20px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.btn-icon {
  margin-right: 4px;
}

/* Toolbar & Filters */
.toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 300px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: #94a3b8;
  font-size: 14px;
}

.search-input {
  padding-left: 36px !important;
  width: 100%;
}

.filter-select {
  width: 160px;
}

.clear-btn {
  color: #64748b;
}

/* Table Design */
.table-wrap {
  overflow: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #ffffff;
}

.table th {
  background: #f8fafc;
  font-weight: 700;
  color: #334155;
  padding: 14px 16px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.customer-row:hover {
  background: #f8fafc;
}

.no-hover:hover {
  background: transparent !important;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.font-bold {
  font-weight: 700;
}

/* Loading & Empty States */
.loading-state-row, .empty-state-row {
  text-align: center;
  padding: 64px 32px !important;
}

.loader-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #e2e8f0;
  border-top-color: #1a73e8;
  border-radius: 50%;
  margin: 0 auto 12px auto;
  animation: spin 0.8s linear infinite;
}

.empty-emoji {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.empty-desc {
  font-size: 13px;
  color: #64748b;
  max-width: 400px;
  margin: 0 auto 20px auto;
  line-height: 1.5;
}

.empty-actions {
  display: flex;
  justify-content: center;
}

/* Cells formatting */
.customer-info-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.customer-display-name {
  font-weight: 700;
  color: #0f172a;
  font-size: 14px;
}

.customer-legal-name {
  font-size: 12px;
  color: #64748b;
}

.customer-meta {
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}

.bullet {
  color: #cbd5e1;
}

.type-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 99px;
  text-transform: capitalize;
}

.type-badge.business {
  background: #eff6ff;
  color: #1e40af;
}

.type-badge.individual {
  background: #fdf2f8;
  color: #9d174d;
}

.compliance-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gst-reg-type {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
}

.gstin-text {
  color: #1e293b;
  font-size: 12px;
  font-weight: 500;
}

.unregistered-text {
  font-size: 11px;
  color: #94a3b8;
}

.balance-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.balance-cell.has-balance {
  font-weight: 700;
  color: #0f172a;
}

.balance-amount {
  font-size: 13px;
}

.balance-type-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 4px;
  border-radius: 4px;
  text-transform: uppercase;
}

.balance-type-badge.debit {
  background: #fee2e2;
  color: #991b1b;
}

.balance-type-badge.credit {
  background: #d1fae5;
  color: #065f46;
}

/* Status Active/Inactive Toggle Button */
.status-toggle-btn {
  border: none;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #f1f5f9;
  color: #475569;
}

.status-toggle-btn.active {
  background: #d1fae5;
  color: #065f46;
}

.status-toggle-btn:hover {
  opacity: 0.85;
}

/* Actions list */
.actions-cell {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.action-btn {
  border: 1px solid transparent;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
}

.action-btn.edit {
  color: #1a73e8;
  background: #f0f7ff;
}

.action-btn.edit:hover {
  background: #dbeafe;
}

.action-btn.delete {
  color: #ef4444;
  background: #fdf2f2;
}

.action-btn.delete:hover {
  background: #fee2e2;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Mobile Layout */
@media (max-width: 1024px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }
  .search-box {
    width: 100%;
  }
  .filter-select {
    width: 100%;
  }
}
</style>
