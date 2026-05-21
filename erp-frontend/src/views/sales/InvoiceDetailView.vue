<template>
  <div class="page">
    <PageHeader :title="invoice ? invoice.invoice_number : 'Invoice'" subtitle="View invoice details, view PDF preview, and post/delete invoices.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'Invoices' })">Back</Button>
        <Button variant="secondary" :disabled="!invoice" @click="openPdf">Open PDF</Button>
        <Button v-if="invoice?.status === 'draft'" :disabled="posting" :loading="posting" @click="postInvoice">
          Post
        </Button>
        <Button v-if="invoice?.status !== 'draft' && invoice?.balance_due > 0" @click="openPaymentModal">
          Record Payment
        </Button>
        <Button v-if="invoice?.status === 'draft'" variant="danger" :disabled="deleting" :loading="deleting" @click="remove">
          Delete
        </Button>
      </template>
    </PageHeader>

    <div v-if="loading" class="muted loading-box">Loading invoice details…</div>
    <div v-else-if="!invoice" class="muted loading-box">Invoice not found.</div>
    
    <div v-else class="detail-layout-container">
      <!-- High Impact Balance Overview Cards -->
      <div class="summary-cards">
        <Card class="card summary-card blue">
          <div class="card-label">Invoice Amount</div>
          <div class="card-val mono">₹{{ fmt(invoice.invoice_grand_total) }}</div>
        </Card>
        <Card class="card summary-card green">
          <div class="card-label">Total Paid</div>
          <div class="card-val mono">₹{{ fmt(invoice.paid_amount) }}</div>
        </Card>
        <Card class="card summary-card red" :class="{ unpaid: invoice.balance_due > 0 }">
          <div class="card-label">Balance Due</div>
          <div class="card-val mono">₹{{ fmt(invoice.balance_due) }}</div>
        </Card>
      </div>

      <div class="detail-layout">
        <!-- Left sidebar: summary metadata -->
        <div class="detail-sidebar">
          <Card class="card metadata-card">
            <div class="section-title">Invoice Overview</div>
            <div class="overview-list">
              <div class="kv">
                <span class="k">Status</span>
                <span class="v status-badge" :class="invoice.status.toLowerCase()">
                  {{ invoice.status === 'partial' ? 'Partial' : invoice.status }}
                </span>
              </div>
              <div class="kv">
                <span class="k">Type</span>
                <span class="v pill font-semibold">{{ invoice.invoice_type === 'sales_invoice' ? 'Sales' : 'Purchase' }}</span>
              </div>
              <div class="kv"><span class="k">Date</span><span class="v mono">{{ formatDate(invoice.invoice_date) }}</span></div>
              <div class="kv"><span class="k">Due Date</span><span class="v mono">{{ formatDate(invoice.due_date) }}</span></div>
              <div class="kv"><span class="k">Order Number</span><span class="v mono">{{ invoice.order_number || '—' }}</span></div>
              <div class="kv"><span class="k">Salesperson</span><span class="v">{{ salespersonName }}</span></div>
            </div>
          </Card>

          <Card class="card customer-card">
            <div class="section-title">Customer Details</div>
            <div class="customer-info" v-if="billingParty">
              <div class="party-name">{{ billingParty.name }}</div>
              <div class="party-meta">{{ billingParty.email }}</div>
              <div class="party-meta">{{ billingParty.phone }}</div>
              <div class="address-box" v-if="billingParty.billing_address">
                <div class="address-title">Billing Address</div>
                <p class="address-text">{{ billingParty.billing_address }}</p>
              </div>
            </div>
          </Card>
        </div>

        <!-- Right core details: standard Zoho Books document paper sheet -->
        <div class="detail-main">
          <Card class="card paper">
            <div class="paper-header">
              <div class="company-brand">
                <div class="brand-name">OptiReach FOS</div>
                <div class="brand-sub">Financial Operating System</div>
              </div>
              <div class="doc-type-label">
                <h1>TAX INVOICE</h1>
                <div class="doc-num mono">{{ invoice.invoice_number }}</div>
              </div>
            </div>

            <div class="paper-meta">
              <div class="meta-block">
                <div class="block-title">Bill To</div>
                <div class="party-name" v-if="billingParty">{{ billingParty.name }}</div>
                <p class="address-text" v-if="billingParty">{{ billingParty.billing_address || 'No billing address specified' }}</p>
              </div>

              <div class="meta-block text-right">
                <div class="kv-row">
                  <span class="meta-k">Invoice Date:</span>
                  <span class="meta-v mono">{{ formatDate(invoice.invoice_date) }}</span>
                </div>
                <div class="kv-row" v-if="invoice.due_date">
                  <span class="meta-k">Due Date:</span>
                  <span class="meta-v mono">{{ formatDate(invoice.due_date) }}</span>
                </div>
                <div class="kv-row" v-if="invoice.order_number">
                  <span class="meta-k">Order Number:</span>
                  <span class="meta-v mono">{{ invoice.order_number }}</span>
                </div>
              </div>
            </div>

            <div class="paper-subject" v-if="invoice.subject">
              <strong>Subject:</strong> {{ invoice.subject }}
            </div>

            <div class="paper-items">
              <table class="items-table">
                <thead>
                  <tr>
                    <th style="width: 40px; text-align: center;">#</th>
                    <th>Item & Description</th>
                    <th style="width: 80px; text-align: right;">Qty</th>
                    <th style="width: 100px; text-align: right;">Rate</th>
                    <th style="width: 90px; text-align: right;">Discount</th>
                    <th style="width: 80px; text-align: right;">GST %</th>
                    <th style="width: 110px; text-align: right;">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(it, idx) in invoice.items" :key="it.invoice_item_id || idx">
                    <td style="text-align: center;" class="muted">{{ idx + 1 }}</td>
                    <td>
                      <div class="item-desc font-bold">{{ it.description }}</div>
                      <div class="item-sub-desc text-xs muted" v-if="it.hsn_sac">HSN/SAC: {{ it.hsn_sac }}</div>
                    </td>
                    <td style="text-align: right;" class="mono">{{ it.quantity }}</td>
                    <td style="text-align: right;" class="mono">₹{{ fmt(it.unit_price) }}</td>
                    <td style="text-align: right;" class="mono">₹{{ fmt(it.discount_amount) }}</td>
                    <td style="text-align: right;" class="mono">{{ it.gst_rate }}%</td>
                    <td style="text-align: right;" class="mono font-semibold">₹{{ fmt(it.total_amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="paper-totals">
              <div class="totals-table">
                <div class="total-row">
                  <span class="tk">Sub Total:</span>
                  <span class="tv mono">₹{{ fmt(invoice.invoice_subtotal) }}</span>
                </div>
                <div class="total-row" v-if="totalItemDiscount > 0">
                  <span class="tk">Discount Amount:</span>
                  <span class="tv mono">- ₹{{ fmt(totalItemDiscount) }}</span>
                </div>
                <div class="total-row">
                  <span class="tk">GST Total:</span>
                  <span class="tv mono">₹{{ fmt(invoice.invoice_total_gst) }}</span>
                </div>
                <div class="total-row" v-if="invoice.invoice_total_tds > 0">
                  <span class="tk">TDS Total:</span>
                  <span class="tv mono">- ₹{{ fmt(invoice.invoice_total_tds) }}</span>
                </div>
                <div class="total-row" v-if="invoice.invoice_total_tcs > 0">
                  <span class="tk">TCS Total:</span>
                  <span class="tv mono">+ ₹{{ fmt(invoice.invoice_total_tcs) }}</span>
                </div>
                <div class="total-row grand-total-row">
                  <span class="tk">Grand Total:</span>
                  <span class="tv mono">₹{{ fmt(invoice.invoice_grand_total) }}</span>
                </div>
                
                <!-- Payment Allocation details -->
                <div class="total-row payment-row" style="margin-top: 10px;">
                  <span class="tk font-semibold" style="color: #059669;">Paid Amount:</span>
                  <span class="tv mono font-semibold" style="color: #059669;">₹{{ fmt(invoice.paid_amount) }}</span>
                </div>
                <div class="total-row payment-row">
                  <span class="tk font-bold" style="color: #dc2626;">Balance Due:</span>
                  <span class="tv mono font-bold" style="color: #dc2626;">₹{{ fmt(invoice.balance_due) }}</span>
                </div>
              </div>
            </div>

            <div class="paper-footer" v-if="invoice.customer_notes || invoice.terms_and_conditions">
              <div class="footer-section" v-if="invoice.customer_notes">
                <div class="footer-title">Customer Notes</div>
                <p class="footer-text">{{ invoice.customer_notes }}</p>
              </div>
              <div class="footer-section" v-if="invoice.terms_and_conditions">
                <div class="footer-title">Terms & Conditions</div>
                <p class="footer-text">{{ invoice.terms_and_conditions }}</p>
              </div>
            </div>
          </Card>

          <!-- Payment History Card (Zoho style allocations grid at the bottom) -->
          <Card v-if="invoice.status !== 'draft'" class="card allocations-card">
            <h3 class="section-title">Payment History Logs</h3>
            <div v-if="allocationsLoading" class="muted text-center py-4">Loading allocations…</div>
            <div v-else-if="allocations.length === 0" class="muted text-center py-4">No payments recorded for this invoice yet. Click <strong>Record Payment</strong> to apply a receipt.</div>
            <div v-else class="table-wrap">
              <table class="table modal-table">
                <thead>
                  <tr>
                    <th>Allocation ID</th>
                    <th>Receipt Date</th>
                    <th style="text-align: right; width: 220px;">Amount Allocated</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="alloc in allocations" :key="alloc.allocation_id">
                    <td class="mono text-xs text-muted">{{ alloc.allocation_id }}</td>
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
    </div>

    <!-- Record Payment Modal (Slide-Over Drawer style) -->
    <div v-if="showPaymentModal" class="modal-overlay" @click.self="showPaymentModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Record Payment: {{ invoice.invoice_number }}</h3>
          <button class="modal-close" @click="showPaymentModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-grid">
            <label class="span2">
              <div class="label">Customer Name</div>
              <input type="text" class="input disabled-input" :value="billingParty?.name" disabled />
            </label>
            <label>
              <div class="label">Payment Date *</div>
              <input v-model="paymentForm.payment_date" type="date" class="input" required />
            </label>
            <label>
              <div class="label">Payment Mode *</div>
              <select v-model="paymentForm.payment_mode" class="input">
                <option value="Cash">Cash</option>
                <option value="Bank Transfer">Bank Transfer</option>
                <option value="Check">Check</option>
                <option value="UPI">UPI</option>
                <option value="Credit Card">Credit Card</option>
              </select>
            </label>
            <label>
              <div class="label">Amount Received (INR) *</div>
              <input v-model.number="paymentForm.amount" type="number" step="0.01" class="input" required />
            </label>
            <label>
              <div class="label">Reference / PO# (optional)</div>
              <input v-model="paymentForm.reference_number" type="text" class="input" placeholder="e.g. UPI txn ID, Check#" />
            </label>
            <label class="span2">
              <div class="label">Notes / Remarks (optional)</div>
              <textarea v-model="paymentForm.notes" class="input input-textarea" placeholder="Payment recorded successfully..." rows="2"></textarea>
            </label>
          </div>
          <div class="modal-actions">
            <Button variant="secondary" @click="showPaymentModal = false">Cancel</Button>
            <Button :loading="recordingPayment" @click="recordPayment">Save as Paid</Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToastStore } from '../../stores/toast'
import { invoicesApi } from '../../api/invoices'
import { contactsApi } from '../../api/contacts'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const loading = ref(false)
const invoice = ref(null)
const posting = ref(false)
const deleting = ref(false)
const contacts = ref([])

// Payment Recording Refs
const showPaymentModal = ref(false)
const recordingPayment = ref(false)
const allocations = ref([])
const allocationsLoading = ref(false)

const paymentForm = reactive({
  payment_date: '',
  payment_mode: 'Cash',
  amount: 0,
  reference_number: '',
  notes: ''
})

const loadAllocations = async () => {
  if (!invoice.value || invoice.value.status === 'draft') return
  allocationsLoading.value = true
  try {
    allocations.value = await invoicesApi.getPayments(invoice.value.invoice_id)
  } catch (e) {
    allocations.value = []
  } finally {
    allocationsLoading.value = false
  }
}

const load = async () => {
  loading.value = true
  try {
    invoice.value = await invoicesApi.get(route.params.invoiceId)
    await loadAllocations()
  } catch (e) {
    invoice.value = null
    toast.error('Failed to load invoice details')
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

onMounted(async () => {
  await loadContacts()
  await load()
})

const billingParty = computed(() => {
  if (!invoice.value) return null
  return contacts.value.find(c => c.contact_id === invoice.value.billing_party_id) || null
})

const salespersonName = computed(() => {
  if (!invoice.value || !invoice.value.salesperson_id) return '—'
  const contact = contacts.value.find(c => c.contact_id === invoice.value.salesperson_id)
  return contact ? contact.name : '—'
})

const totalItemDiscount = computed(() => {
  if (!invoice.value || !invoice.value.items) return 0
  return invoice.value.items.reduce((sum, item) => sum + (item.discount_amount || 0), 0)
})

const fmt = (n) => Number(n || 0).toFixed(2)

const formatDate = (d) => {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const formatDateTime = (dt) => {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

const openPdf = async () => {
  try {
    const blob = await invoicesApi.pdf(route.params.invoiceId)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}

const postInvoice = async () => {
  if (!confirm('Are you sure you want to post this invoice? This will finalize all details.')) return
  posting.value = true
  try {
    const key = crypto.randomUUID()
    invoice.value = await invoicesApi.post(route.params.invoiceId, { idempotencyKey: key })
    toast.success('Invoice posted successfully')
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to post invoice')
  } finally {
    posting.value = false
  }
}

const remove = async () => {
  if (!confirm('Are you sure you want to delete this invoice?')) return
  deleting.value = true
  try {
    await invoicesApi.remove(route.params.invoiceId)
    toast.success('Invoice deleted successfully')
    router.push({ name: 'Invoices' })
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to delete invoice')
  } finally {
    deleting.value = false
  }
}

const openPaymentModal = () => {
  paymentForm.amount = invoice.value.balance_due
  paymentForm.payment_date = new Date().toISOString().slice(0, 10)
  paymentForm.payment_mode = 'Cash'
  paymentForm.reference_number = ''
  paymentForm.notes = ''
  showPaymentModal.value = true
}

const recordPayment = async () => {
  if (paymentForm.amount <= 0) {
    toast.error('Payment amount must be greater than 0')
    return
  }
  recordingPayment.value = true
  try {
    invoice.value = await invoicesApi.recordPayment(invoice.value.invoice_id, {
      payment_date: paymentForm.payment_date,
      payment_mode: paymentForm.payment_mode,
      amount: paymentForm.amount,
      reference_number: paymentForm.reference_number || null,
      notes: paymentForm.notes || null
    })
    toast.success('Payment recorded successfully!')
    showPaymentModal.value = false
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to record payment')
  } finally {
    recordingPayment.value = false
  }
}
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
}
.loading-box {
  padding: 40px;
  text-align: center;
  font-size: 15px;
}
.detail-layout-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* High Impact Overview Cards */
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
.summary-card.blue {
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.05), rgba(37, 99, 235, 0.01));
  border-left: 4px solid #2563eb;
}
.summary-card.blue .card-val {
  color: #2563eb;
}
.summary-card.green {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), rgba(16, 185, 129, 0.01));
  border-left: 4px solid #10b981;
}
.summary-card.green .card-val {
  color: #059669;
}
.summary-card.red {
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.05), rgba(220, 38, 38, 0.01));
  border-left: 4px solid #dc2626;
  opacity: 0.5;
}
.summary-card.red.unpaid {
  opacity: 1;
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.08), rgba(220, 38, 38, 0.02));
}
.summary-card.red .card-val {
  color: #dc2626;
}
.card-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}
.card-val {
  font-size: 20px;
  font-weight: 800;
}

.detail-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 20px;
  align-items: start;
}
.detail-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.card {
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.section-title {
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  color: #475569;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}
.overview-list {
  display: grid;
  gap: 10px;
}
.kv {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.k {
  color: #64748b;
}
.v {
  font-weight: 600;
  color: #1e293b;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.pill {
  text-transform: capitalize;
}
.status-badge {
  display: inline-flex;
  padding: 2px 6px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.status-badge.draft { background-color: #f1f5f9; color: #475569; }
.status-badge.posted { background-color: #dbeafe; color: #2563eb; }
.status-badge.paid { background-color: #d1fae5; color: #059669; }
.status-badge.partial { background-color: #ede9fe; color: #7c3aed; }
.status-badge.overdue { background-color: #fee2e2; color: #dc2626; }

.customer-info {
  display: grid;
  gap: 6px;
}
.party-name {
  font-weight: 700;
  color: #1e293b;
  font-size: 14px;
}
.party-meta {
  font-size: 12px;
  color: #64748b;
}
.address-box {
  margin-top: 10px;
  background: #f8fafc;
  padding: 8px 10px;
  border-radius: 6px;
}
.address-title {
  font-size: 10px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
}
.address-text {
  font-size: 12px;
  color: #334155;
  margin: 4px 0 0 0;
  white-space: pre-line;
}

/* Zoho Books Paper Document styling */
.paper {
  padding: 40px;
  min-height: 700px;
  display: flex;
  flex-direction: column;
}
.paper-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 20px;
}
.brand-name {
  font-weight: 900;
  font-size: 20px;
  color: #1e88e5;
  letter-spacing: -0.02em;
}
.brand-sub {
  font-size: 11px;
  color: #64748b;
}
.doc-type-label h1 {
  font-size: 24px;
  font-weight: 900;
  color: #334155;
  margin: 0;
  letter-spacing: 0.05em;
  text-align: right;
}
.doc-num {
  text-align: right;
  font-size: 14px;
  color: #64748b;
  font-weight: 600;
  margin-top: 4px;
}
.paper-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 30px;
  gap: 20px;
}
.meta-block {
  flex: 1;
}
.block-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 6px;
  letter-spacing: 0.05em;
}
.kv-row {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 4px;
}
.meta-k {
  color: #64748b;
}
.meta-v {
  font-weight: 600;
  color: #1e293b;
}
.text-right {
  text-align: right;
}
.paper-subject {
  margin-top: 24px;
  background: #f8fafc;
  border-left: 3px solid #1e88e5;
  padding: 10px 14px;
  font-size: 13px;
  color: #334155;
  border-radius: 0 6px 6px 0;
}
.paper-items {
  margin-top: 30px;
}
.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.items-table th {
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  padding: 10px 8px;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}
.items-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.item-desc {
  color: #1e293b;
  font-weight: 600;
}
.font-bold {
  font-weight: 700;
}
.paper-totals {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.totals-table {
  width: 320px;
  display: grid;
  gap: 10px;
}
.total-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #475569;
}
.grand-total-row {
  font-weight: 900;
  color: #1e293b;
  font-size: 16px;
  border-top: 2px double #cbd5e1;
  padding-top: 10px;
  margin-top: 4px;
}
.payment-row {
  border-top: 1px solid #f1f5f9;
  padding-top: 8px;
}
.paper-footer {
  margin-top: 40px;
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
  display: grid;
  gap: 20px;
}
.footer-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 6px;
}
.footer-text {
  font-size: 12px;
  color: #475569;
  margin: 0;
  line-height: 1.5;
  white-space: pre-line;
}
.muted {
  color: #64748b;
}

.allocations-card {
  margin-top: 20px;
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
  padding: 12px 10px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: middle;
}
.text-success {
  color: #059669;
}
.py-4 {
  padding-top: 16px;
  padding-bottom: 16px;
}
.text-xs {
  font-size: 11px;
}

/* Modal CSS */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: #ffffff;
  border-radius: 16px;
  width: 100%;
  max-width: 580px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.8);
}
.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
}
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
}
.modal-body {
  padding: 20px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}
.span2 {
  grid-column: span 2;
}
.label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #6b7280;
  margin-bottom: 6px;
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
  width: 100%;
  transition: all 0.2s ease;
}
.input:focus {
  border-color: #1e88e5;
  box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.1);
}
.disabled-input {
  background: #f1f5f9;
  color: #64748b;
  cursor: not-allowed;
}
.input-textarea {
  height: auto;
  padding: 10px;
  font-family: inherit;
  resize: vertical;
}
.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  border-top: 1px solid #f1f5f9;
  padding-top: 16px;
}

@media (max-width: 900px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
  .summary-cards {
    grid-template-columns: 1fr;
  }
}
</style>
