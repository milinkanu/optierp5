<template>
  <div class="page">
    <PageHeader title="Sales Orders" subtitle="Track confirmed sales orders, shipments, and invoicing status.">
      <template #actions>
        <Button @click="$router.push({ name: 'SalesOrderNew' })">New Sales Order</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <div class="filter-group">
          <label class="toolbar-label">Status</label>
          <select v-model="statusFilter" class="input filter-select" @change="refresh">
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="confirmed">Confirmed</option>
            <option value="partially_invoiced">Partially Invoiced</option>
            <option value="invoiced">Invoiced</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
        
        <div class="search-group">
          <input v-model="searchQuery" type="text" placeholder="Search by SO#..." class="input search-input" @input="refresh" />
        </div>

        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 160px;">Sales Order#</th>
              <th style="width: 140px;">Date</th>
              <th style="width: 150px;">Expected Shipment</th>
              <th>Customer</th>
              <th style="width: 140px;">Status</th>
              <th style="width: 150px; text-align: right;">Amount</th>
              <th style="width: 240px; text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="muted text-center">Loading…</td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="7" class="muted text-center">No sales orders found.</td>
            </tr>
            <tr v-for="row in items" :key="row.sales_order_id">
              <td class="mono font-bold">{{ row.sales_order_number }}</td>
              <td class="muted">{{ formatDate(row.sales_order_date) }}</td>
              <td class="muted">{{ formatDate(row.expected_shipment_date) }}</td>
              <td>
                <div class="customer-info">
                  <span class="customer-name">{{ getCustomerName(row.billing_party_id) }}</span>
                </div>
              </td>
              <td>
                <span class="status-badge" :class="row.status.toLowerCase()">
                  {{ row.status.replace('_', ' ') }}
                </span>
              </td>
              <td class="mono font-semibold" style="text-align: right; color: #10b981;">
                ₹{{ fmt(row.grand_total) }}
              </td>
              <td class="actions">
                <Button variant="secondary" size="small" @click="$router.push({ name: 'SalesOrderDetail', params: { salesOrderId: row.sales_order_id } })">
                  View
                </Button>
                <Button v-if="row.status === 'draft' || row.status === 'confirmed'" variant="secondary" size="small" @click="$router.push({ name: 'SalesOrderEdit', params: { salesOrderId: row.sales_order_id } })">
                  Edit
                </Button>
                <Button v-if="row.status === 'draft'" variant="danger" size="small" @click="removeOrder(row.sales_order_id)">
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
import { onMounted, ref } from 'vue'
import { salesOrdersApi } from '../../api/salesOrders'
import { contactsApi } from '../../api/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const toast = useToastStore()
const items = ref([])
const contacts = ref([])
const loading = ref(false)
const statusFilter = ref('')
const searchQuery = ref('')

const refresh = async () => {
  loading.value = true
  try {
    const data = await salesOrdersApi.list({
      page: 1,
      limit: 100,
      q: searchQuery.value,
      status: statusFilter.value
    })
    items.value = data
  } catch (e) {
    toast.error('Failed to load sales orders')
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

const removeOrder = async (salesOrderId) => {
  if (!confirm('Are you sure you want to delete this sales order?')) return
  try {
    await salesOrdersApi.remove(salesOrderId)
    toast.success('Sales order deleted successfully')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to delete sales order')
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
  width: 240px;
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
.status-badge.confirmed {
  background-color: #dbeafe;
  color: #2563eb;
}
.status-badge.partially_invoiced {
  background-color: #fef3c7;
  color: #d97706;
}
.status-badge.invoiced {
  background-color: #d1fae5;
  color: #059669;
}
.status-badge.cancelled {
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
