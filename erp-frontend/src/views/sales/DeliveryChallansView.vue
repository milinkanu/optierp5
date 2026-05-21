<template>
  <div class="page">
    <PageHeader title="Delivery Challans" subtitle="Track physical shipments, approvals, and job works prior to invoicing.">
      <template #actions>
        <Button @click="$router.push({ name: 'DeliveryChallanNew' })">New Delivery Challan</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <div class="filter-group">
          <label class="toolbar-label">Challan Type</label>
          <select v-model="typeFilter" class="input filter-select">
            <option value="">All Types</option>
            <option value="supply_on_approval">Approval</option>
            <option value="job_work">Job Work</option>
            <option value="transport">Transport</option>
            <option value="others">Others</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="toolbar-label">Status</label>
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="invoiced">Invoiced</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        <div class="search-group">
          <label class="toolbar-label">Search</label>
          <input v-model="searchQuery" type="text" placeholder="Search by Challan# or Customer..." class="input search-input" />
        </div>

        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 140px;">Challan#</th>
              <th style="width: 150px;">Type</th>
              <th style="width: 110px;">Date</th>
              <th>Customer</th>
              <th style="width: 130px;">Ref#</th>
              <th style="width: 110px;">Status</th>
              <th style="width: 130px; text-align: right;">Total</th>
              <th style="width: 280px; text-align: center;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="muted text-center">Loading…</td>
            </tr>
            <tr v-else-if="filteredChallans.length === 0">
              <td colspan="8" class="muted text-center">No delivery challans found.</td>
            </tr>
            <tr v-for="row in filteredChallans" :key="row.delivery_challan_id" class="table-row">
              <td class="mono font-bold">{{ row.challan_number }}</td>
              <td>
                <span class="type-badge" :class="row.challan_type">
                  {{ formatType(row.challan_type) }}
                </span>
              </td>
              <td class="muted">{{ formatDate(row.challan_date) }}</td>
              <td>
                <span class="customer-name">{{ getCustomerName(row.billing_party_id) }}</span>
              </td>
              <td class="mono muted">{{ row.reference_number || '—' }}</td>
              <td>
                <span class="status-badge" :class="row.status.toLowerCase()">
                  {{ row.status }}
                </span>
              </td>
              <td class="mono font-semibold" style="text-align: right;">
                ₹{{ fmt(row.grand_total) }}
              </td>
              <td class="actions">
                <Button variant="secondary" size="small" @click="openPdf(row.delivery_challan_id)">
                  PDF
                </Button>
                <Button v-if="row.status === 'draft'" size="small" @click="convertToInvoice(row)">
                  Convert to Invoice
                </Button>
                <span v-else-if="row.status === 'invoiced'" class="success-text font-bold">
                  Invoiced
                </span>
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
import { deliveryChallansApi } from '../../api/deliveryChallans'
import { contactsApi } from '../../api/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const toast = useToastStore()
const loading = ref(false)
const typeFilter = ref('')
const statusFilter = ref('')
const searchQuery = ref('')
const challans = ref([])
const contacts = ref([])

const refresh = async () => {
  loading.value = true
  try {
    challans.value = await deliveryChallansApi.list()
  } catch (e) {
    toast.error('Failed to load delivery challans')
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

const formatType = (t) => {
  if (t === 'supply_on_approval') return 'Approval'
  if (t === 'job_work') return 'Job Work'
  if (t === 'transport') return 'Transport'
  return 'Others'
}

const filteredChallans = computed(() => {
  return challans.value.filter(row => {
    if (typeFilter.value && row.challan_type !== typeFilter.value) {
      return false
    }
    if (statusFilter.value && row.status.toLowerCase() !== statusFilter.value.toLowerCase()) {
      return false
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const numberMatches = row.challan_number.toLowerCase().includes(q)
      const customerMatches = getCustomerName(row.billing_party_id).toLowerCase().includes(q)
      return numberMatches || customerMatches
    }
    return true
  })
})

const openPdf = async (challanId) => {
  try {
    const blob = await deliveryChallansApi.pdf(challanId)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}

const convertToInvoice = async (challan) => {
  if (!confirm(`Are you sure you want to convert Delivery Challan ${challan.challan_number} to a posted Invoice?`)) return
  try {
    const res = await deliveryChallansApi.convert(challan.delivery_challan_id)
    toast.success(`Converted successfully! Created Invoice ${res.invoice_number}`)
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to convert to invoice')
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

.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
}
.type-badge.supply_on_approval {
  background-color: #ede9fe;
  color: #7c3aed;
}
.type-badge.job_work {
  background-color: #e0f2fe;
  color: #0369a1;
}
.type-badge.transport {
  background-color: #fef3c7;
  color: #d97706;
}
.type-badge.others {
  background-color: #f1f5f9;
  color: #475569;
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
  align-items: center;
}
.success-text {
  color: #059669;
  font-size: 13px;
}
.muted {
  color: #64748b;
}
.text-center {
  text-align: center;
}
</style>
