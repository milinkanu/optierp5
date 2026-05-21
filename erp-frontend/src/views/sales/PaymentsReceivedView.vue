<template>
  <div class="page">
    <PageHeader title="Payments Received" subtitle="View all customer inbound payments, unused balances, and invoice allocations.">
      <template #actions>
        <!-- No direct 'New Payment' button from here since payments are typically recorded in reference to invoices, but could be added if desired. Let's keep it clean or redirect to invoices list. -->
        <span class="muted text-sm mr-4">To record a payment, open an invoice and click <strong>Record Payment</strong>.</span>
        <Button variant="secondary" @click="$router.push({ name: 'Invoices' })">Go to Invoices</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <div class="filter-group">
          <label class="toolbar-label">Payment Mode</label>
          <select v-model="modeFilter" class="input filter-select">
            <option value="">All Modes</option>
            <option value="Cash">Cash</option>
            <option value="Bank Transfer">Bank Transfer</option>
            <option value="Check">Check</option>
            <option value="UPI">UPI</option>
            <option value="Credit Card">Credit Card</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="toolbar-label">Status</label>
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Statuses</option>
            <option value="fully_allocated">Fully Allocated</option>
            <option value="partially_allocated">Partially Allocated</option>
            <option value="excess">Excess Balance</option>
          </select>
        </div>

        <div class="search-group">
          <label class="toolbar-label">Search</label>
          <input v-model="searchQuery" type="text" placeholder="Search by Payment# or Customer..." class="input search-input" />
        </div>

        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 140px;">Payment#</th>
              <th style="width: 110px;">Date</th>
              <th>Customer</th>
              <th style="width: 150px;">Payment Mode</th>
              <th style="width: 130px; text-align: right;">Amount</th>
              <th style="width: 140px; text-align: right;">Unused Balance</th>
              <th style="width: 150px; text-align: center;">Status</th>
              <th style="width: 180px; text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="muted text-center">Loading…</td>
            </tr>
            <tr v-else-if="filteredPayments.length === 0">
              <td colspan="8" class="muted text-center">No received payments found.</td>
            </tr>
            <tr v-for="row in filteredPayments" :key="row.payment_id" class="table-row">
              <td class="mono font-bold">{{ row.payment_number }}</td>
              <td class="muted">{{ formatDate(row.payment_date) }}</td>
              <td>
                <span class="customer-name">{{ getCustomerName(row.party_id) }}</span>
              </td>
              <td><span class="mode-badge">{{ row.payment_mode }}</span></td>
              <td class="mono font-semibold" style="text-align: right; color: #0f172a;">
                ₹{{ fmt(row.amount) }}
              </td>
              <td class="mono font-semibold" style="text-align: right;" :class="row.unused_balance > 0 ? 'excess-amount' : 'muted'">
                ₹{{ fmt(row.unused_balance) }}
              </td>
              <td style="text-align: center;">
                <span class="status-badge" :class="row.status.toLowerCase()">
                  {{ formatStatus(row.status) }}
                </span>
              </td>
              <td class="actions">
                <Button variant="secondary" size="small" @click="$router.push({ name: 'PaymentReceivedDetail', params: { paymentId: row.payment_id } })">
                  Details
                </Button>
                <Button variant="secondary" size="small" @click="openPdf(row.payment_id)">
                  Receipt
                </Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { paymentsApi } from '../../api/payments'
import { contactsApi } from '../../api/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const toast = useToastStore()
const loading = ref(false)
const modeFilter = ref('')
const statusFilter = ref('')
const searchQuery = ref('')
const payments = ref([])
const contacts = ref([])

const refresh = async () => {
  loading.value = true
  try {
    payments.value = await paymentsApi.list()
  } catch (e) {
    toast.error('Failed to load received payments')
  } finally {
    loading.value = false
  }
}

const loadContacts = async () => {
  try {
    contacts.value = await contactsApi.list({ page: 1, limit: 300 })
  } catch (e) {
    contacts.value = []
  }
}

const getCustomerName = (partyId) => {
  const contact = contacts.value.find(c => c.contact_id === partyId)
  return contact ? contact.name : 'Unknown Customer'
}

onMounted(async () => {
  await loadContacts()
  await refresh()
})

const fmt = (n) => Number(n || 0).toFixed(2)

const formatDate = (d) => {
  if (!d) return '—'
  const dateObj = new Date(d)
  return dateObj.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const formatStatus = (s) => {
  if (s === 'fully_allocated') return 'Fully Allocated'
  if (s === 'partially_allocated') return 'Partially Allocated'
  if (s === 'excess') return 'Excess Balance'
  return s
}

const filteredPayments = computed(() => {
  return payments.value.filter(row => {
    if (modeFilter.value && row.payment_mode !== modeFilter.value) {
      return false
    }
    if (statusFilter.value && row.status.toLowerCase() !== statusFilter.value.toLowerCase()) {
      return false
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const numberMatches = row.payment_number.toLowerCase().includes(q)
      const customerMatches = getCustomerName(row.party_id).toLowerCase().includes(q)
      return numberMatches || customerMatches
    }
    return true
  })
})

const openPdf = async (paymentId) => {
  try {
    const blob = await paymentsApi.pdf(paymentId)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
}
.mr-4 {
  margin-right: 16px;
}
.text-sm {
  font-size: 13px;
}
.card {
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.toolbar {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.filter-group, .search-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.toolbar-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #6b7280;
  letter-spacing: 0.05em;
}
.input {
  height: 38px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  padding: 0 12px;
  font-size: 13px;
  outline: none;
  background: #fff;
  transition: all 0.2s ease;
}
.input:focus {
  border-color: #1e88e5;
  box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.1);
}
.filter-select {
  width: 160px;
}
.search-input {
  width: 260px;
}
.table-wrap {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #eef2f7;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th {
  background: #f8fafc;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.05em;
  padding: 12px 10px;
  border-bottom: 2px solid #e2e8f0;
  text-align: left;
}
.table td {
  padding: 14px 10px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: middle;
}
.table-row {
  transition: background 0.15s ease;
}
.table-row:hover {
  background: #f8fafc;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.font-bold {
  font-weight: 700;
  color: #1e293b;
}
.font-semibold {
  font-weight: 600;
}
.customer-name {
  font-weight: 600;
  color: #334155;
}

.mode-badge {
  background-color: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.excess-amount {
  color: #d97706;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.status-badge.fully_allocated {
  background-color: #d1fae5;
  color: #059669;
}
.status-badge.partially_allocated {
  background-color: #ede9fe;
  color: #7c3aed;
}
.status-badge.excess {
  background-color: #fef3c7;
  color: #d97706;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}
.muted {
  color: #64748b;
}
.text-center {
  text-align: center;
}
</style>
