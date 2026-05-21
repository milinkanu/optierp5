<template>
  <div class="page">
    <PageHeader title="Invoices" subtitle="Create invoices, view PDF, and manage status.">
      <template #actions>
        <Button @click="$router.push({ name: 'InvoiceNew' })">New Invoice</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <div class="filter-group">
          <label class="toolbar-label">Type</label>
          <select v-model="typeFilter" class="input filter-select" @change="refresh">
            <option value="">All Types</option>
            <option value="sales_invoice">Sales</option>
            <option value="purchase_invoice">Purchase</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="toolbar-label">Status</label>
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="posted">Posted</option>
            <option value="paid">Paid</option>
            <option value="partial">Partially Paid</option>
            <option value="overdue">Overdue</option>
          </select>
        </div>
        
        <div class="search-group">
          <label class="toolbar-label">Search</label>
          <input v-model="searchQuery" type="text" placeholder="Search by Invoice# or Customer..." class="input search-input" />
        </div>

        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 160px;">Invoice#</th>
              <th style="width: 140px;">Type</th>
              <th style="width: 120px;">Date</th>
              <th style="width: 120px;">Due Date</th>
              <th>Customer</th>
              <th style="width: 120px;">Status</th>
              <th style="width: 150px; text-align: right;">Total</th>
              <th style="width: 260px; text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="muted text-center">Loading…</td>
            </tr>
            <tr v-else-if="filteredInvoices.length === 0">
              <td colspan="8" class="muted text-center">No invoices found.</td>
            </tr>
            <tr v-for="row in filteredInvoices" :key="row.invoice_id">
              <td class="mono font-bold">{{ row.invoice_number }}</td>
              <td class="pill font-semibold">
                {{ row.invoice_type === 'sales_invoice' ? 'Sales' : 'Purchase' }}
              </td>
              <td class="muted">{{ formatDate(row.invoice_date) }}</td>
              <td class="muted">{{ formatDate(row.due_date) }}</td>
              <td>
                <div class="customer-info">
                  <span class="customer-name">{{ getCustomerName(row.billing_party_id) }}</span>
                </div>
              </td>
              <td>
                <span class="status-badge" :class="row.status.toLowerCase()">
                  {{ row.status === 'partial' ? 'Partial' : row.status }}
                </span>
              </td>
              <td class="mono font-semibold" style="text-align: right; color: #10b981;">
                ₹{{ fmt(row.invoice_grand_total) }}
              </td>
              <td class="actions">
                <Button variant="secondary" size="small" @click="$router.push({ name: 'InvoiceDetail', params: { invoiceId: row.invoice_id } })">
                  View
                </Button>
                <Button variant="secondary" size="small" @click="openPdf(row.invoice_id)">
                  PDF
                </Button>
                <Button v-if="row.status === 'draft'" size="small" @click="postInvoice(row.invoice_id)">
                  Post
                </Button>
                <Button v-if="row.status === 'draft'" variant="danger" size="small" @click="remove(row.invoice_id)">
                  Delete
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
import { useInvoicesStore } from '../../stores/invoices'
import { useToastStore } from '../../stores/toast'
import { invoicesApi } from '../../api/invoices'
import { contactsApi } from '../../api/contacts'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const store = useInvoicesStore()
const toast = useToastStore()

const loading = ref(false)
const typeFilter = ref('')
const statusFilter = ref('')
const searchQuery = ref('')
const contacts = ref([])

const refresh = async () => {
  loading.value = true
  try {
    await store.fetchList({ page: 1, limit: 100, invoice_type: typeFilter.value })
  } catch (e) {
    toast.error('Failed to load invoices')
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

// Client-side filtering for status and search query
const filteredInvoices = computed(() => {
  return store.items.filter(row => {
    // Filter by status
    if (statusFilter.value && row.status.toLowerCase() !== statusFilter.value.toLowerCase()) {
      return false
    }
    // Filter by search query (invoice number or customer name)
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const numberMatches = row.invoice_number.toLowerCase().includes(q)
      const customerName = getCustomerName(row.billing_party_id).toLowerCase()
      const customerMatches = customerName.includes(q)
      return numberMatches || customerMatches
    }
    return true
  })
})

const openPdf = async (invoiceId) => {
  try {
    const blob = await invoicesApi.pdf(invoiceId)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}

const postInvoice = async (invoiceId) => {
  if (!confirm('Are you sure you want to post this invoice? This will lock the invoice details.')) return
  try {
    const key = crypto.randomUUID()
    await store.post(invoiceId, { idempotencyKey: key })
    toast.success('Invoice posted successfully')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to post invoice')
  }
}

const remove = async (invoiceId) => {
  if (!confirm('Are you sure you want to delete this invoice?')) return
  try {
    await store.remove(invoiceId)
    toast.success('Invoice deleted successfully')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to delete invoice')
  }
}
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
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
.table tbody tr:hover {
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
.pill {
  text-transform: capitalize;
  color: #475569;
}
.customer-name {
  font-weight: 600;
  color: #334155;
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
.status-badge.draft {
  background-color: #f1f5f9;
  color: #475569;
}
.status-badge.posted {
  background-color: #dbeafe;
  color: #2563eb;
}
.status-badge.paid {
  background-color: #d1fae5;
  color: #059669;
}
.status-badge.partial {
  background-color: #ede9fe;
  color: #7c3aed;
}
.status-badge.overdue {
  background-color: #fee2e2;
  color: #dc2626;
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


