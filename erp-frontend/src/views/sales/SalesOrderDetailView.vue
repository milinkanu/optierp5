<template>
  <div class="page">
    <PageHeader :title="order ? order.sales_order_number : 'Sales Order'" subtitle="View sales order details, track logs, and convert to invoices.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'SalesOrders' })">Back</Button>
        
        <!-- Confirm Action for Draft -->
        <Button v-if="order && order.status === 'draft'" variant="secondary" :loading="confirming" @click="confirmOrder">
          Confirm Order
        </Button>
        
        <Button v-if="order && (order.status === 'draft' || order.status === 'confirmed')" variant="secondary" @click="$router.push({ name: 'SalesOrderEdit', params: { salesOrderId: order.sales_order_id } })">
          Edit
        </Button>
        <Button v-if="order && order.status === 'draft'" variant="danger" @click="removeOrder">
          Delete
        </Button>
        
        <!-- Conversion Actions -->
        <span v-if="order && order.status !== 'invoiced' && order.status !== 'cancelled'" class="convert-actions">
          <Button :loading="convertingInvoice" @click="convertToInvoice">Convert to Invoice</Button>
        </span>
      </template>
    </PageHeader>

    <div v-if="loading" class="muted loading-box">Loading sales order details…</div>
    <div v-else-if="!order" class="muted loading-box">Sales order not found.</div>
    <div v-else class="detail-layout">
      <!-- Left sidebar: summary metadata -->
      <div class="detail-sidebar">
        <Card class="card metadata-card">
          <div class="section-title">Sales Order Overview</div>
          <div class="overview-list">
            <div class="kv">
              <span class="k">Status</span>
              <span class="v status-badge" :class="order.status.toLowerCase()">
                {{ order.status.replace('_', ' ') }}
              </span>
            </div>
            <div class="kv"><span class="k">Date</span><span class="v mono">{{ formatDate(order.sales_order_date) }}</span></div>
            <div class="kv"><span class="k">Expected Shipment</span><span class="v mono">{{ formatDate(order.expected_shipment_date) }}</span></div>
            <div class="kv"><span class="k">Payment Terms</span><span class="v">{{ order.payment_terms || 'Due on Receipt' }}</span></div>
            <div class="kv"><span class="k">Reference#</span><span class="v">{{ order.reference_number || '—' }}</span></div>
            <div class="kv"><span class="k">Salesperson</span><span class="v">{{ salespersonName }}</span></div>
            <div class="kv" v-if="order.quote_id"><span class="k">Linked Quote</span><span class="v font-bold mono"><router-link :to="{ name: 'QuoteDetail', params: { quoteId: order.quote_id } }" class="link">View Quote</router-link></span></div>
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
              <h1>SALES ORDER</h1>
              <div class="doc-num mono">{{ order.sales_order_number }}</div>
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
                <span class="meta-k">Order Date:</span>
                <span class="meta-v mono">{{ formatDate(order.sales_order_date) }}</span>
              </div>
              <div class="kv-row" v-if="order.expected_shipment_date">
                <span class="meta-k">Expected Shipment Date:</span>
                <span class="meta-v mono">{{ formatDate(order.expected_shipment_date) }}</span>
              </div>
              <div class="kv-row" v-if="order.payment_terms">
                <span class="meta-k">Payment Terms:</span>
                <span class="meta-v">{{ order.payment_terms }}</span>
              </div>
              <div class="kv-row" v-if="order.reference_number">
                <span class="meta-k">Reference#:</span>
                <span class="meta-v">{{ order.reference_number }}</span>
              </div>
            </div>
          </div>

          <div class="paper-subject" v-if="order.subject">
            <strong>Subject:</strong> {{ order.subject }}
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
                <tr v-for="(it, idx) in order.items" :key="it.sales_order_item_id || idx">
                  <td style="text-align: center;" class="muted">{{ idx + 1 }}</td>
                  <td>
                    <div class="item-desc font-bold">{{ getItemName(it.inventory_item_id) || it.description }}</div>
                    <div class="item-sub-desc text-xs muted" v-if="getItemName(it.inventory_item_id)">{{ it.description }}</div>
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
              <div class="total-row"><span class="tk">Sub Total:</span><span class="tv mono">₹{{ fmt(order.subtotal) }}</span></div>
              <div class="total-row" v-if="order.discount_amount > 0">
                <span class="tk">Discount ({{ order.discount_percentage }}%):</span>
                <span class="tv mono">- ₹{{ fmt(order.discount_amount) }}</span>
              </div>
              <div class="total-row"><span class="tk">GST Total:</span><span class="tv mono">₹{{ fmt(order.total_gst) }}</span></div>
              <div class="total-row" v-if="order.total_tds > 0"><span class="tk">TDS Total:</span><span class="tv mono">- ₹{{ fmt(order.total_tds) }}</span></div>
              <div class="total-row" v-if="order.total_tcs > 0"><span class="tk">TCS Total:</span><span class="tv mono">+ ₹{{ fmt(order.total_tcs) }}</span></div>
              <div class="total-row" v-if="order.adjustment !== 0"><span class="tk">Adjustment:</span><span class="tv mono">₹{{ fmt(order.adjustment) }}</span></div>
              <div class="total-row grand-total-row">
                <span class="tk">Total:</span>
                <span class="tv mono">₹{{ fmt(order.grand_total) }}</span>
              </div>
            </div>
          </div>

          <div class="paper-footer" v-if="order.customer_notes || order.terms_and_conditions">
            <div class="footer-section" v-if="order.customer_notes">
              <div class="footer-title">Customer Notes</div>
              <p class="footer-text">{{ order.customer_notes }}</p>
            </div>
            <div class="footer-section" v-if="order.terms_and_conditions">
              <div class="footer-title">Terms & Conditions</div>
              <p class="footer-text">{{ order.terms_and_conditions }}</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useItemsStore } from '../../stores/items'
import { useToastStore } from '../../stores/toast'
import { salesOrdersApi } from '../../api/salesOrders'
import { contactsApi } from '../../api/contacts'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToastStore()
const itemsStore = useItemsStore()

const order = ref(null)
const contacts = ref([])
const loading = ref(false)
const confirming = ref(false)
const convertingInvoice = ref(false)

const load = async () => {
  loading.value = true
  try {
    order.value = await salesOrdersApi.get(route.params.salesOrderId)
  } catch (e) {
    order.value = null
    toast.error('Failed to load sales order details')
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
  await itemsStore.fetchList({ page: 1, limit: 500, is_active: true })
  await loadContacts()
  await load()
})

const billingParty = computed(() => {
  if (!order.value) return null
  return contacts.value.find(c => c.contact_id === order.value.billing_party_id) || null
})

const salespersonName = computed(() => {
  if (!order.value || !order.value.salesperson_id) return '—'
  const contact = contacts.value.find(c => c.contact_id === order.value.salesperson_id)
  return contact ? contact.name : '—'
})

const getItemName = (itemId) => {
  if (!itemId) return null
  const item = itemsStore.items.find(i => i.inventory_item_id === itemId)
  return item ? item.item_name : null
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

const confirmOrder = async () => {
  confirming.value = true
  try {
    order.value = await salesOrdersApi.update(order.value.sales_order_id, { status: 'confirmed' })
    toast.success('Sales Order confirmed successfully')
  } catch (e) {
    toast.error('Failed to confirm sales order')
  } finally {
    confirming.value = false
  }
}

const removeOrder = async () => {
  if (!confirm('Are you sure you want to delete this draft sales order?')) return
  try {
    await salesOrdersApi.remove(order.value.sales_order_id)
    toast.success('Sales order deleted successfully')
    router.push({ name: 'SalesOrders' })
  } catch (e) {
    toast.error('Failed to delete sales order')
  }
}

const convertToInvoice = async () => {
  if (!confirm('Convert this Sales Order into a standard Tax Invoice?')) return
  convertingInvoice.value = true
  try {
    const res = await salesOrdersApi.convertToInvoice(order.value.sales_order_id)
    toast.success('Successfully converted to standard Tax Invoice')
    router.push({ name: 'InvoiceDetail', params: { invoiceId: res.invoice_id } })
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to convert to standard Tax Invoice')
  } finally {
    convertingInvoice.value = false
  }
}
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
}
.convert-actions {
  display: inline-flex;
  gap: 8px;
  margin-left: 8px;
}
.loading-box {
  padding: 40px;
  text-align: center;
  font-size: 15px;
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
.status-badge.confirmed { background-color: #dbeafe; color: #2563eb; }
.status-badge.partially_invoiced { background-color: #fef3c7; color: #d97706; }
.status-badge.invoiced { background-color: #d1fae5; color: #059669; }
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
.link {
  color: #1e88e5;
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}

/* Zoho Books Paper Document styling */
.paper {
  padding: 40px;
  min-height: 800px;
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

@media (max-width: 900px) {
  .detail-layout {
    grid-template-columns: 1fr;
  }
}
</style>
