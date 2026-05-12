<template>
  <div class="page">
    <PageHeader title="Invoices" subtitle="Create invoices, view PDF, and manage status.">
      <template #actions>
        <Button @click="$router.push({ name: 'InvoiceNew' })">New Invoice</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <select v-model="typeFilter" class="input" @change="refresh">
          <option value="">All</option>
          <option value="sales_invoice">Sales</option>
          <option value="purchase_invoice">Purchase</option>
        </select>
        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 220px;">Number</th>
              <th style="width: 140px;">Type</th>
              <th style="width: 120px;">Status</th>
              <th style="width: 160px; text-align: right;">Total</th>
              <th style="width: 160px;">Created</th>
              <th style="width: 260px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="6" class="muted">Loading…</td>
            </tr>
            <tr v-else-if="store.items.length === 0">
              <td colspan="6" class="muted">No invoices found.</td>
            </tr>
            <tr v-for="row in store.items" :key="row.invoice_id">
              <td class="mono">{{ row.invoice_number }}</td>
              <td class="pill">{{ row.invoice_type }}</td>
              <td><span class="status">{{ row.status }}</span></td>
              <td class="mono" style="text-align: right;">₹{{ fmt(row.invoice_grand_total) }}</td>
              <td class="muted">{{ fmtDate(row.created_at) }}</td>
              <td class="actions">
                <Button variant="secondary" @click="$router.push({ name: 'InvoiceDetail', params: { invoiceId: row.invoice_id } })">View</Button>
                <Button variant="secondary" @click="openPdf(row.invoice_id)">PDF</Button>
                <Button v-if="row.status === 'draft'" @click="postInvoice(row.invoice_id)">Post</Button>
                <Button v-if="row.status === 'draft'" variant="danger" @click="remove(row.invoice_id)">Delete</Button>
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
import { useInvoicesStore } from '../../stores/invoices'
import { useToastStore } from '../../stores/toast'
import { invoicesApi } from '../../api/invoices'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const store = useInvoicesStore()
const toast = useToastStore()
const typeFilter = ref('')

const refresh = async () => {
  await store.fetchList({ page: 1, limit: 100, invoice_type: typeFilter.value })
}

onMounted(refresh)

const fmt = (n) => Number(n || 0).toFixed(2)
const fmtDate = (d) => (d ? new Date(d).toLocaleString() : '—')

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
  try {
    const key = crypto.randomUUID()
    await store.post(invoiceId, { idempotencyKey: key })
    toast.success('Invoice posted')
  } catch (e) {
    toast.error('Post failed')
  }
}

const remove = async (invoiceId) => {
  if (!confirm('Delete (soft-delete) this invoice?')) return
  try {
    await store.remove(invoiceId)
    toast.success('Invoice deleted')
  } catch (e) {
    toast.error('Delete failed')
  }
}
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.card {
  padding: 14px;
}
.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}
.input {
  height: 38px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  background: #fff;
}
.table-wrap {
  overflow: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.table th,
.table td {
  padding: 10px 8px;
  border-bottom: 1px solid #eef2f7;
  text-align: left;
}
.table tbody tr:hover {
  background: #f9fafb;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
.pill {
  text-transform: lowercase;
  color: #374151;
}
.status {
  font-weight: 700;
  font-size: 12px;
  color: #1f2937;
  text-transform: uppercase;
}
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.muted {
  color: #6b7280;
}
</style>

