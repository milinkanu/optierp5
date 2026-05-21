<template>
  <div class="page">
    <PageHeader :title="payment ? payment.payment_number : 'Payment Receipt'" subtitle="Deep-dive receipt allocations and journal balances.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'PaymentsReceived' })">Back to List</Button>
        <Button v-if="payment" variant="secondary" @click="downloadReceipt">PDF Receipt</Button>
      </template>
    </PageHeader>

    <div v-if="loading" class="muted text-center py-8">Loading payment details…</div>
    
    <div v-else-if="!payment" class="muted text-center py-8">
      <p>Failed to find payment transaction or unauthorized access.</p>
    </div>

    <div v-else class="layout">
      <!-- Top Overview Row -->
      <div class="summary-cards">
        <Card class="card summary-card green">
          <div class="card-label">Amount Received</div>
          <div class="card-val mono">₹{{ fmt(payment.amount) }}</div>
        </Card>
        <Card class="card summary-card warning" :class="{ inactive: payment.unused_balance === 0 }">
          <div class="card-label">Unused Balance (Excess)</div>
          <div class="card-val mono">₹{{ fmt(payment.unused_balance) }}</div>
        </Card>
        <Card class="card summary-card blue">
          <div class="card-label">Payment Mode</div>
          <div class="card-val">{{ payment.payment_mode }}</div>
        </Card>
      </div>

      <!-- Payment & Customer Sheet -->
      <div class="grid-details">
        <Card class="card">
          <h3 class="section-title">Payment Information</h3>
          <table class="detail-table">
            <tr>
              <th>Payment Number</th>
              <td class="mono font-bold">{{ payment.payment_number }}</td>
            </tr>
            <tr>
              <th>Payment Date</th>
              <td>{{ formatDate(payment.payment_date) }}</td>
            </tr>
            <tr>
              <th>Reference Number</th>
              <td class="mono">{{ payment.reference_number || '—' }}</td>
            </tr>
            <tr>
              <th>Bank Charges</th>
              <td class="mono">₹{{ fmt(payment.bank_charges) }}</td>
            </tr>
            <tr>
              <th>Status</th>
              <td>
                <span class="status-badge" :class="payment.status.toLowerCase()">
                  {{ formatStatus(payment.status) }}
                </span>
              </td>
            </tr>
            <tr>
              <th>Notes / Remarks</th>
              <td class="notes-cell">{{ payment.notes || '—' }}</td>
            </tr>
          </table>
        </Card>

        <Card class="card">
          <h3 class="section-title">Customer Information</h3>
          <table class="detail-table">
            <tr>
              <th>Customer Name</th>
              <td class="font-bold text-lg text-primary">{{ customer ? customer.name : 'Unknown Customer' }}</td>
            </tr>
            <tr>
              <th>Contact Email</th>
              <td>{{ customer ? customer.email : '—' }}</td>
            </tr>
            <tr>
              <th>Contact Phone</th>
              <td>{{ customer ? customer.phone : '—' }}</td>
            </tr>
            <tr>
              <th>Contact Type</th>
              <td class="capitalize">{{ customer ? customer.contact_type : '—' }}</td>
            </tr>
            <tr>
              <th>Billing Address</th>
              <td class="notes-cell">{{ customer ? customer.billing_address : '—' }}</td>
            </tr>
          </table>
        </Card>
      </div>

      <!-- Invoice Allocations Table -->
      <Card class="card">
        <h3 class="section-title">Invoice Allocations</h3>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>Allocated Invoice#</th>
                <th>Allocation Date</th>
                <th style="text-align: right; width: 220px;">Amount Allocated</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!payment.allocations || payment.allocations.length === 0">
                <td colspan="3" class="muted text-center">No allocations recorded. This entire amount represents excess/unused customer balance.</td>
              </tr>
              <tr v-for="alloc in payment.allocations" :key="alloc.allocation_id" class="table-row">
                <td class="mono font-bold">{{ alloc.invoice_number }}</td>
                <td class="muted">{{ formatDateTime(alloc.allocated_at) }}</td>
                <td class="mono font-bold text-success" style="text-align: right;">
                  ₹{{ fmt(alloc.allocated_amount) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { paymentsApi } from '../../api/payments'
import { contactsApi } from '../../api/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const route = useRoute()
const toast = useToastStore()
const loading = ref(true)
const payment = ref(null)
const customer = ref(null)

const loadPaymentDetails = async () => {
  const paymentId = route.params.paymentId
  loading.value = true
  try {
    payment.value = await paymentsApi.get(paymentId)
    if (payment.value?.party_id) {
      await loadCustomer(payment.value.party_id)
    }
  } catch (e) {
    toast.error('Failed to load payment details')
  } finally {
    loading.value = false
  }
}

const loadCustomer = async (partyId) => {
  try {
    customer.value = await contactsApi.get(partyId)
  } catch (e) {
    customer.value = null
  }
}

onMounted(async () => {
  await loadPaymentDetails()
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

const formatDateTime = (dt) => {
  if (!dt) return '—'
  const dateObj = new Date(dt)
  return dateObj.toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

const formatStatus = (s) => {
  if (s === 'fully_allocated') return 'Fully Allocated'
  if (s === 'partially_allocated') return 'Partially Allocated'
  if (s === 'excess') return 'Excess Balance'
  return s
}

const downloadReceipt = async () => {
  try {
    const blob = await paymentsApi.pdf(payment.value.payment_id)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load receipt PDF')
  }
}
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.py-8 {
  padding-top: 32px;
  padding-bottom: 32px;
}
.layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.summary-cards {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}
.summary-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #f0f3f8;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.summary-card.green {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(16, 185, 129, 0.01));
  border-left: 4px solid #10b981;
}
.summary-card.green .card-val {
  color: #059669;
}
.summary-card.warning {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), rgba(245, 158, 11, 0.01));
  border-left: 4px solid #f59e0b;
}
.summary-card.warning.inactive {
  opacity: 0.5;
  background: #ffffff;
  border-left: 4px solid #94a3b8;
}
.summary-card.warning.inactive .card-val {
  color: #64748b;
}
.summary-card.warning:not(.inactive) .card-val {
  color: #d97706;
}
.summary-card.blue {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.05), rgba(59, 130, 246, 0.01));
  border-left: 4px solid #3b82f6;
}
.summary-card.blue .card-val {
  color: #2563eb;
}
.card-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #6b7280;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.card-val {
  font-size: 20px;
  font-weight: 800;
}

.grid-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.card {
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.section-title {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  margin-top: 0;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 6px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.detail-table th {
  text-align: left;
  font-weight: 700;
  color: #64748b;
  padding: 10px 0;
  width: 150px;
  border-bottom: 1px solid #f8fafc;
}
.detail-table td {
  padding: 10px 0 10px 10px;
  color: #1e293b;
  border-bottom: 1px solid #f8fafc;
}
.notes-cell {
  white-space: pre-wrap;
  line-height: 1.5;
}
.text-lg {
  font-size: 16px;
}
.text-primary {
  color: #1e88e5;
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

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.font-bold {
  font-weight: 700;
}
.text-success {
  color: #059669;
}
.muted {
  color: #64748b;
}
.text-center {
  text-align: center;
}
@media (max-width: 900px) {
  .grid-details, .summary-cards {
    grid-template-columns: 1fr;
  }
}
</style>
