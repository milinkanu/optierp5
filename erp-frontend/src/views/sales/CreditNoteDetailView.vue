<template>
  <div class="page">
    <PageHeader :title="creditNote ? creditNote.credit_note_number : 'Credit Note'" subtitle="View credit note details, check ledger balance sheet, and apply credits to invoices.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'CreditNotes' })">Back</Button>
        <Button variant="secondary" :disabled="!creditNote" @click="openPdf">Open PDF</Button>
        
        <!-- Post (Save as Open) action for Draft credit notes -->
        <Button v-slot="icon" v-if="creditNote?.status === 'draft'" :disabled="posting" :loading="posting" @click="postCreditNote">
          Post & Open
        </Button>
        
        <!-- Apply to Invoice action for Posted/Open/Partially Applied credit notes -->
        <Button v-if="(creditNote?.status === 'open' || creditNote?.status === 'partially_applied') && creditNote?.remaining_balance > 0" @click="openApplyModal">
          Apply to Invoice
        </Button>
        
        <!-- Edit and Delete actions only for Draft credit notes -->
        <Button v-slot="icon" v-if="creditNote?.status === 'draft'" variant="secondary" @click="$router.push({ name: 'CreditNoteEdit', params: { creditNoteId: creditNote.credit_note_id } })">
          Edit
        </Button>
        <Button v-slot="icon" v-if="creditNote?.status === 'draft'" variant="danger" :disabled="deleting" :loading="deleting" @click="remove">
          Delete
        </Button>
      </template>
    </PageHeader>

    <div v-if="loading" class="muted loading-box">Loading credit note details…</div>
    <div v-else-if="!creditNote" class="muted loading-box">Credit Note not found.</div>

    <div v-else class="detail-layout-container">
      <!-- High Impact Balance Overview Cards -->
      <div class="summary-cards">
        <Card class="card summary-card blue">
          <div class="card-label">Total Credit Amount</div>
          <div class="card-val mono">₹{{ fmt(creditNote.grand_total) }}</div>
        </Card>
        <Card class="card summary-card green">
          <div class="card-label">Credits Applied</div>
          <div class="card-val mono">₹{{ fmt(creditNote.grand_total - creditNote.remaining_balance) }}</div>
        </Card>
        <Card class="card summary-card red" :class="{ outstanding: creditNote.remaining_balance > 0 }">
          <div class="card-label">Remaining Balance</div>
          <div class="card-val mono">₹{{ fmt(creditNote.remaining_balance) }}</div>
        </Card>
      </div>

      <div class="detail-layout">
        <!-- Left Sidebar: Overview Metadata -->
        <div class="detail-sidebar">
          <Card class="card metadata-card">
            <div class="section-title">Credit Note Overview</div>
            <div class="overview-list">
              <div class="kv">
                <span class="k">Status</span>
                <span class="v status-badge" :class="creditNote.status.toLowerCase()">
                  {{ formatStatus(creditNote.status) }}
                </span>
              </div>
              <div class="kv"><span class="k">Date</span><span class="v mono">{{ formatDate(creditNote.credit_note_date) }}</span></div>
              <div class="kv"><span class="k">Reference#</span><span class="v mono">{{ creditNote.reference_number || '—' }}</span></div>
              <div class="kv"><span class="k">Salesperson</span><span class="v">{{ salespersonName }}</span></div>
              <div class="kv"><span class="k">Currency</span><span class="v mono">{{ creditNote.currency }}</span></div>
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

        <!-- Right Main: Zoho Books style paper sheet -->
        <div class="detail-main">
          <Card class="card paper">
            <div class="paper-header">
              <div class="company-brand">
                <div class="brand-name">OptiReach FOS</div>
                <div class="brand-sub">Financial Operating System</div>
              </div>
              <div class="doc-type-label">
                <h1>CREDIT NOTE</h1>
                <div class="doc-num mono">{{ creditNote.credit_note_number }}</div>
              </div>
            </div>

            <div class="paper-meta">
              <div class="meta-block">
                <div class="block-title">Credit To</div>
                <div class="party-name" v-if="billingParty">{{ billingParty.name }}</div>
                <p class="address-text" v-if="billingParty">{{ billingParty.billing_address || 'No billing address specified' }}</p>
              </div>

              <div class="meta-block text-right">
                <div class="kv-row">
                  <span class="meta-k">Credit Date:</span>
                  <span class="meta-v mono">{{ formatDate(creditNote.credit_note_date) }}</span>
                </div>
                <div class="kv-row" v-if="creditNote.reference_number">
                  <span class="meta-k">Reference#:</span>
                  <span class="meta-v mono">{{ creditNote.reference_number }}</span>
                </div>
                <div class="kv-row">
                  <span class="meta-k">Payment Terms:</span>
                  <span class="meta-v">Due on Receipt</span>
                </div>
              </div>
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
                  <tr v-for="(it, idx) in creditNote.items" :key="it.credit_note_item_id || idx">
                    <td style="text-align: center;" class="muted">{{ idx + 1 }}</td>
                    <td>
                      <div class="item-desc font-bold">{{ it.description }}</div>
                      <div class="item-sub-desc text-xs muted">HSN/SAC: {{ it.hsn_sac || '0000' }}</div>
                    </td>
                    <td style="text-align: right;" class="mono">{{ it.quantity }}</td>
                    <td style="text-align: right;" class="mono">₹{{ fmt(it.rate) }}</td>
                    <td style="text-align: right;" class="mono">₹{{ fmt(it.discount_amount) }}</td>
                    <td style="text-align: right;" class="mono">{{ it.tax_percentage }}%</td>
                    <td style="text-align: right;" class="mono font-semibold">₹{{ fmt(calculateItemAmount(it)) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="paper-totals">
              <div class="totals-table">
                <div class="total-row">
                  <span class="tk">Sub Total:</span>
                  <span class="tv mono">₹{{ fmt(creditNote.subtotal) }}</span>
                </div>
                <div class="total-row">
                  <span class="tk">GST Total:</span>
                  <span class="tv mono">₹{{ fmt(creditNote.total_gst) }}</span>
                </div>
                <div class="total-row" v-if="creditNote.total_tds > 0">
                  <span class="tk">TDS Reversal:</span>
                  <span class="tv mono">- ₹{{ fmt(creditNote.total_tds) }}</span>
                </div>
                <div class="total-row" v-if="creditNote.total_tcs > 0">
                  <span class="tk">TCS Reversal:</span>
                  <span class="tv mono">+ ₹{{ fmt(creditNote.total_tcs) }}</span>
                </div>
                <div class="total-row grand-total-row">
                  <span class="tk">Total Credit:</span>
                  <span class="tv mono">₹{{ fmt(creditNote.grand_total) }}</span>
                </div>

                <div class="total-row payment-row" style="margin-top: 10px;">
                  <span class="tk font-semibold" style="color: #059669;">Credits Applied:</span>
                  <span class="tv mono font-semibold" style="color: #059669;">₹{{ fmt(creditNote.grand_total - creditNote.remaining_balance) }}</span>
                </div>
                <div class="total-row payment-row">
                  <span class="tk font-bold" style="color: #dc2626;">Remaining Balance:</span>
                  <span class="tv mono font-bold" style="color: #dc2626;">₹{{ fmt(creditNote.remaining_balance) }}</span>
                </div>
              </div>
            </div>

            <div class="paper-footer" v-if="creditNote.customer_notes || creditNote.terms_and_conditions">
              <div class="footer-section" v-if="creditNote.customer_notes">
                <div class="footer-title">Customer Notes</div>
                <p class="footer-text">{{ creditNote.customer_notes }}</p>
              </div>
              <div class="footer-section" v-if="creditNote.terms_and_conditions">
                <div class="footer-title">Terms & Conditions</div>
                <p class="footer-text">{{ creditNote.terms_and_conditions }}</p>
              </div>
            </div>
          </Card>

          <!-- Elegant Tab Bar for Applied Invoices & Activity History -->
          <div class="tabs-container">
            <div class="tabs-header">
              <button class="tab-btn" :class="{ active: activeTab === 'applied' }" @click="activeTab = 'applied'">
                Applied Invoices ({{ mappings.length }})
              </button>
              <button class="tab-btn" :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'">
                Activity History Logs ({{ activities.length }})
              </button>
            </div>

            <Card class="card tab-content-card">
              <!-- Tab 1: Applied Invoices -->
              <div v-if="activeTab === 'applied'">
                <div v-if="mappingsLoading" class="muted text-center py-4">Loading allocations…</div>
                <div v-else-if="mappings.length === 0" class="muted text-center py-4">
                  No invoices are mapped to this credit note yet.
                  <span v-if="(creditNote.status === 'open' || creditNote.status === 'partially_applied') && creditNote.remaining_balance > 0">
                    Click <strong>Apply to Invoice</strong> above to allocate credits.
                  </span>
                </div>
                <div v-else class="table-wrap">
                  <table class="table modal-table">
                    <thead>
                      <tr>
                        <th>Invoice Number</th>
                        <th>Mapping ID</th>
                        <th>Date Mapped</th>
                        <th style="text-align: right; width: 220px;">Amount Applied</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="map in mappings" :key="map.mapping_id">
                        <td class="font-semibold text-primary mono">{{ map.invoice_number || 'INV-REF' }}</td>
                        <td class="mono text-xs muted">{{ map.mapping_id }}</td>
                        <td class="muted">{{ formatDateTime(map.mapped_at) }}</td>
                        <td class="mono font-bold text-success" style="text-align: right;">
                          ₹{{ fmt(map.amount_applied) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Tab 2: Activity History -->
              <div v-if="activeTab === 'history'">
                <div v-if="activitiesLoading" class="muted text-center py-4">Loading activity history…</div>
                <div v-else-if="activities.length === 0" class="muted text-center py-4">No activity history recorded for this transaction.</div>
                <div v-else class="activity-timeline">
                  <div v-for="act in activities" :key="act.log_id" class="activity-item">
                    <div class="activity-marker"></div>
                    <div class="activity-body">
                      <div class="activity-desc font-semibold">{{ act.description }}</div>
                      <div class="activity-time mono">{{ formatDateTime(act.created_at) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>

    <!-- Apply Credit to Invoice Modal Drawer -->
    <div v-if="showApplyModal" class="modal-overlay" @click.self="showApplyModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Apply Credits to Outstanding Invoices</h3>
          <button class="modal-close" @click="showApplyModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="modal-hint">Select one of the outstanding posted invoices for <strong>{{ billingParty?.name }}</strong> to apply this credit note.</p>
          
          <div class="form-grid">
            <label class="span2">
              <div class="label">Outstanding Invoices *</div>
              <select v-model="applyForm.invoice_id" class="input" @change="onSelectInvoice">
                <option value="">Select an outstanding invoice…</option>
                <option v-for="inv in unpaidInvoices" :key="inv.invoice_id" :value="inv.invoice_id">
                  {{ inv.invoice_number }} (Due: ₹{{ fmt(inv.balance_due) }}, Total: ₹{{ fmt(inv.invoice_grand_total) }})
                </option>
              </select>
            </label>

            <!-- Invoice details card inside modal -->
            <div v-if="selectedInvoice" class="span2 invoice-sub-card">
              <div class="sub-card-row">
                <span class="k">Invoice Number</span>
                <span class="v mono font-bold">{{ selectedInvoice.invoice_number }}</span>
              </div>
              <div class="sub-card-row">
                <span class="k">Invoice Date</span>
                <span class="v mono">{{ formatDate(selectedInvoice.invoice_date) }}</span>
              </div>
              <div class="sub-card-row">
                <span class="k">Current Balance Due</span>
                <span class="v mono text-danger font-semibold">₹{{ fmt(selectedInvoice.balance_due) }}</span>
              </div>
            </div>

            <label>
              <div class="label">Amount to Apply (₹) *</div>
              <input v-model.number="applyForm.amount" type="number" step="0.01" class="input" required />
              <div class="input-hint">Maximum applicable: ₹{{ fmt(maxApplicableAmount) }}</div>
            </label>

            <label>
              <div class="label">Date Applied *</div>
              <input v-model="applyForm.apply_date" type="date" class="input" required />
            </label>
          </div>

          <div class="modal-actions">
            <Button variant="secondary" @click="showApplyModal = false">Cancel</Button>
            <Button :loading="applyingCredits" @click="applyCredits">Apply Credits</Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToastStore } from '../../stores/toast'
import { creditNotesApi } from '../../api/creditNotes'
import { contactsApi } from '../../api/contacts'
import { invoicesApi } from '../../api/invoices'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()

const loading = ref(false)
const creditNote = ref(null)
const posting = ref(false)
const deleting = ref(false)
const contacts = ref([])

// Tabs Context
const activeTab = ref('applied')
const mappings = ref([])
const mappingsLoading = ref(false)
const activities = ref([])
const activitiesLoading = ref(false)

// Apply Credits Modal Context
const showApplyModal = ref(false)
const applyingCredits = ref(false)
const unpaidInvoices = ref([])
const selectedInvoice = ref(null)

const applyForm = reactive({
  invoice_id: '',
  amount: 0,
  apply_date: new Date().toISOString().slice(0, 10),
})

const maxApplicableAmount = computed(() => {
  if (!creditNote.value) return 0
  const remainingCredit = Number(creditNote.value.remaining_balance || 0)
  if (!selectedInvoice.value) return remainingCredit
  const invoiceDue = Number(selectedInvoice.value.balance_due || 0)
  return Math.min(remainingCredit, invoiceDue)
})

const loadMappings = async () => {
  if (!creditNote.value) return
  mappingsLoading.value = true
  try {
    mappings.value = await creditNotesApi.mappings(creditNote.value.credit_note_id)
  } catch (e) {
    mappings.value = []
  } finally {
    mappingsLoading.value = false
  }
}

const loadActivities = async () => {
  if (!creditNote.value) return
  activitiesLoading.value = true
  try {
    activities.value = await creditNotesApi.activities(creditNote.value.credit_note_id)
  } catch (e) {
    activities.value = []
  } finally {
    activitiesLoading.value = false
  }
}

const load = async () => {
  loading.value = true
  try {
    creditNote.value = await creditNotesApi.get(route.params.creditNoteId)
    await Promise.all([loadMappings(), loadActivities()])
  } catch (e) {
    creditNote.value = null
    toast.error('Failed to load credit note details')
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
  if (!creditNote.value) return null
  return contacts.value.find(c => c.contact_id === creditNote.value.billing_party_id) || null
})

const salespersonName = computed(() => {
  if (!creditNote.value || !creditNote.value.salesperson_id) return '—'
  const contact = contacts.value.find(c => c.contact_id === creditNote.value.salesperson_id)
  return contact ? contact.name : '—'
})

const calculateItemAmount = (item) => {
  const base = Math.max(0, Number(item.quantity || 0) * Number(item.rate || 0) - Number(item.discount_amount || 0))
  const gst = base * (Number(item.tax_percentage || 0) / 100)
  const tcs = base * (Number(item.tcs_rate || 0) / 100)
  const tds = base * (Number(item.tds_rate || 0) / 100)
  return base + gst + tcs - tds
}

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

const formatStatus = (s) => {
  if (!s) return ''
  return s.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

const openPdf = async () => {
  try {
    const blob = await creditNotesApi.pdf(route.params.creditNoteId)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank', 'noopener,noreferrer')
    setTimeout(() => URL.revokeObjectURL(url), 30_000)
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}

const postCreditNote = async () => {
  if (!confirm('Are you sure you want to post this credit note? This will commit balanced double-entry ledger journals.')) return
  posting.value = true
  try {
    // Standard update endpoint supports changing status to open or keep current status
    const payload = {
      ...creditNote.value,
      status: 'open'
    }
    await creditNotesApi.update(creditNote.value.credit_note_id, payload)
    toast.success('Credit Note posted successfully')
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to post credit note')
  } finally {
    posting.value = false
  }
}

const remove = async () => {
  if (!confirm('Are you sure you want to delete this credit note? This will perform a soft delete.')) return
  deleting.value = true
  try {
    await creditNotesApi.remove(route.params.creditNoteId)
    toast.success('Credit Note deleted successfully')
    router.push({ name: 'CreditNotes' })
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to delete credit note')
  } finally {
    deleting.value = false
  }
}

// Apply Credit Note functions
const openApplyModal = async () => {
  if (!creditNote.value) return
  applyForm.invoice_id = ''
  applyForm.amount = 0
  applyForm.apply_date = new Date().toISOString().slice(0, 10)
  selectedInvoice.value = null
  showApplyModal.value = true
  
  // Load customer invoices and filter client-side
  try {
    const response = await invoicesApi.list({ limit: 500 })
    unpaidInvoices.value = (response || []).filter(
      inv => inv.billing_party_id === creditNote.value.billing_party_id &&
             inv.status.toLowerCase() !== 'draft' &&
             inv.status.toLowerCase() !== 'paid' &&
             inv.balance_due > 0
    )
  } catch (e) {
    toast.error('Failed to load outstanding customer invoices')
    showApplyModal.value = false
  }
}

const onSelectInvoice = () => {
  selectedInvoice.value = unpaidInvoices.value.find(inv => inv.invoice_id === applyForm.invoice_id) || null
  if (selectedInvoice.value) {
    applyForm.amount = maxApplicableAmount.value
  } else {
    applyForm.amount = 0
  }
}

const applyCredits = async () => {
  if (!applyForm.invoice_id) {
    toast.error('Please select an invoice')
    return
  }
  if (applyForm.amount <= 0) {
    toast.error('Applicable amount must be greater than zero')
    return
  }
  if (applyForm.amount > maxApplicableAmount.value) {
    toast.error(`Applicable amount cannot exceed ₹${fmt(maxApplicableAmount.value)}`)
    return
  }

  applyingCredits.value = true
  try {
    await creditNotesApi.applyToInvoice(creditNote.value.credit_note_id, {
      invoice_id: applyForm.invoice_id,
      amount: applyForm.amount
    })
    toast.success('Credits successfully allocated to invoice!')
    showApplyModal.value = false
    await load()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to allocate credits to invoice')
  } finally {
    applyingCredits.value = false
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
.summary-card.red.outstanding {
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
.status-badge {
  display: inline-flex;
  padding: 2px 6px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}
.status-badge.draft { background-color: #f1f5f9; color: #475569; }
.status-badge.open { background-color: #dbeafe; color: #2563eb; }
.status-badge.partially_applied { background-color: #fef3c7; color: #d97706; }
.status-badge.applied { background-color: #d1fae5; color: #059669; }
.status-badge.cancelled { background-color: #fee2e2; color: #dc2626; }

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
  min-height: 500px;
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

/* Elegant Tab Section */
.tabs-container {
  margin-top: 24px;
}
.tabs-header {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #cbd5e1;
  padding-bottom: 1px;
  margin-bottom: 12px;
}
.tab-btn {
  background: none;
  border: none;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  border-radius: 6px 6px 0 0;
  transition: all 0.2s ease;
  border-bottom: 2px solid transparent;
}
.tab-btn:hover {
  color: #1e88e5;
  background: #f8fafc;
}
.tab-btn.active {
  color: #1e88e5;
  border-bottom: 2px solid #1e88e5;
}
.tab-content-card {
  padding: 20px !important;
  border-radius: 0 0 12px 12px !important;
}

/* Timeline/Log styling */
.activity-timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  padding-left: 20px;
}
.activity-timeline::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 6px;
  bottom: 6px;
  width: 2px;
  background: #cbd5e1;
}
.activity-item {
  position: relative;
  display: flex;
  gap: 12px;
  font-size: 13px;
}
.activity-marker {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1e88e5;
  border: 2px solid #ffffff;
  box-shadow: 0 0 0 2px #cbd5e1;
}
.activity-time {
  font-size: 11px;
  color: #64748b;
  margin-top: 2px;
}

/* Slide-Over Drawer Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: flex-end;
  z-index: 1000;
  transition: opacity 0.3s ease;
}
.modal {
  background: #ffffff;
  width: 500px;
  max-width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-shadow: -10px 0 25px -5px rgba(0, 0, 0, 0.1), -4px 0 10px -5px rgba(0, 0, 0, 0.04);
  animation: slideIn 0.3s ease-out;
}
@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}
.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: #1e293b;
}
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #94a3b8;
  cursor: pointer;
  outline: none;
  transition: color 0.2s ease;
}
.modal-close:hover {
  color: #ef4444;
}
.modal-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.modal-hint {
  font-size: 13px;
  color: #64748b;
  margin: 0;
  line-height: 1.5;
}
.invoice-sub-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  display: grid;
  gap: 8px;
}
.sub-card-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.sub-card-row .k {
  color: #64748b;
}
.sub-card-row .v {
  color: #1e293b;
}
.input-hint {
  font-size: 11px;
  color: #64748b;
  margin-top: 4px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: auto;
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
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
  padding: 10px 12px;
  border-bottom: 2px solid #e2e8f0;
  text-align: left;
}
.table td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: middle;
}
.text-center {
  text-align: center;
}
.text-success {
  color: #10b981;
}
.text-danger {
  color: #dc2626;
}
.py-4 {
  padding-top: 16px;
  padding-bottom: 16px;
}
</style>
