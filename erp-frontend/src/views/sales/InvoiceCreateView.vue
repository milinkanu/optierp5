<template>
  <div class="page">
    <PageHeader title="New Invoice" subtitle="Draft invoice with line items.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'Invoices' })">Cancel</Button>
        <Button :loading="saving" @click="createInvoice">Create</Button>
      </template>
    </PageHeader>

    <div class="layout">
      <Card class="card">
        <div class="form-grid">
          <label>
            <div class="label">Invoice Type</div>
            <select v-model="form.invoice_type" class="input">
              <option value="sales_invoice">sales_invoice</option>
              <option value="purchase_invoice">purchase_invoice</option>
            </select>
          </label>
          <label>
            <div class="label">Invoice Date</div>
            <input v-model="form.invoice_date" type="date" class="input" />
          </label>
          <label>
            <div class="label">Due Date (optional)</div>
            <input v-model="form.due_date" type="date" class="input" />
          </label>
          <label>
            <div class="label">Currency</div>
            <input v-model="form.currency" class="input" placeholder="INR" />
          </label>
          <label class="span2">
            <div class="label">Billing Party</div>
            <select v-model="form.billing_party_id" class="input">
              <option value="">Select contact…</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>
          <label class="span2">
            <div class="label">Shipping Party (optional)</div>
            <select v-model="form.shipping_party_id" class="input">
              <option value="">Same as billing</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>
          <label>
            <div class="label">Order Number (optional)</div>
            <input v-model="form.order_number" class="input" placeholder="PO-001" />
          </label>
          <label>
            <div class="label">Salesperson (optional)</div>
            <select v-model="form.salesperson_id" class="input">
              <option value="">Select salesperson…</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }}
              </option>
            </select>
          </label>
          <label class="span2">
            <div class="label">Subject (optional)</div>
            <input v-model="form.subject" class="input" placeholder="Invoice subject/title" />
          </label>
          <label class="span2">
            <div class="label">Customer Notes (optional)</div>
            <textarea v-model="form.customer_notes" class="input input-textarea" placeholder="Thank you for your business..." rows="3"></textarea>
          </label>
          <label class="span2">
            <div class="label">Terms & Conditions (optional)</div>
            <textarea v-model="form.terms_and_conditions" class="input input-textarea" placeholder="Payment terms, delivery terms, etc." rows="3"></textarea>
          </label>
        </div>
      </Card>

      <Card class="card">
        <div class="items-head">
          <div class="h">Line Items</div>
          <Button variant="secondary" @click="addItem">Add Item</Button>
        </div>

        <div class="items">
          <div v-for="(it, idx) in form.items" :key="idx" class="row">
            <div class="row-grid">
              <label class="span2">
                <div class="label">Select Item</div>
                <select v-model="it.inventory_item_id" class="input" @change="onSelectItem(it)">
                  <option value="">Custom line (manual)</option>
                  <option v-for="masterItem in itemsStore.items" :key="masterItem.inventory_item_id" :value="masterItem.inventory_item_id">
                    {{ masterItem.item_name }} ({{ masterItem.item_type }})
                  </option>
                </select>
              </label>
              <label class="span2">
                <div class="label">Description</div>
                <input v-model="it.description" class="input" placeholder="Item / service description" />
              </label>
              <label>
                <div class="label">Qty</div>
                <input v-model.number="it.quantity" type="number" min="0" step="0.01" class="input" />
              </label>
              <label>
                <div class="label">Rate</div>
                <input v-model.number="it.unit_price" type="number" min="0" step="0.01" class="input" />
              </label>
              <label>
                <div class="label">Discount</div>
                <input v-model.number="it.discount_amount" type="number" min="0" step="0.01" class="input" />
              </label>
              <label>
                <div class="label">GST %</div>
                <input v-model.number="it.gst_rate" type="number" min="0" step="0.01" class="input" />
              </label>
              <label>
                <div class="label">TDS %</div>
                <input v-model.number="it.tds_rate" type="number" min="0" step="0.01" class="input" />
              </label>
              <label>
                <div class="label">TCS %</div>
                <input v-model.number="it.tcs_rate" type="number" min="0" step="0.01" class="input" />
              </label>
              <div class="row-actions">
                <Button variant="danger" @click="removeItem(idx)">Remove</Button>
              </div>
            </div>
          </div>
        </div>

        <div class="totals">
          <div class="trow"><span>Subtotal</span><span class="mono">₹{{ fmt(subtotal) }}</span></div>
          <div class="trow"><span>GST</span><span class="mono">₹{{ fmt(gstTotal) }}</span></div>
          <div class="trow"><span>TDS</span><span class="mono">₹{{ fmt(tdsTotal) }}</span></div>
          <div class="trow"><span>TCS</span><span class="mono">₹{{ fmt(tcsTotal) }}</span></div>
          <div class="trow grand"><span>Total</span><span class="mono">₹{{ fmt(grandTotal) }}</span></div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useItemsStore } from '../../stores/items'
import { useToastStore } from '../../stores/toast'
import { contactsApi } from '../../api/contacts'
import { invoicesApi } from '../../api/invoices'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const itemsStore = useItemsStore()
const toast = useToastStore()
const router = useRouter()
const saving = ref(false)
const contacts = ref([])

const today = new Date()
const iso = (d) => d.toISOString().slice(0, 10)

const form = reactive({
  invoice_type: 'sales_invoice',
  invoice_date: iso(today),
  due_date: '',
  billing_party_id: '',
  shipping_party_id: '',
  order_number: '',
  salesperson_id: '',
  subject: '',
  customer_notes: '',
  terms_and_conditions: '',
  currency: 'INR',
  exchange_rate: 1,
  items: [
    { inventory_item_id: '', description: '', hsn_sac: null, account_id: null, quantity: 1, unit_price: 0, discount_amount: 0, gst_rate: 0, tds_rate: 0, tcs_rate: 0 },
  ],
  meta: null,
})

const addItem = () => {
  form.items.push({ inventory_item_id: '', description: '', hsn_sac: null, account_id: null, quantity: 1, unit_price: 0, discount_amount: 0, gst_rate: 0, tds_rate: 0, tcs_rate: 0 })
}
const removeItem = (idx) => {
  form.items.splice(idx, 1)
  if (form.items.length === 0) addItem()
}

const subtotal = computed(() =>
  form.items.reduce((s, it) => s + Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0),
)
const gstTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.gst_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const tdsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tds_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const tcsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tcs_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const grandTotal = computed(() => subtotal.value + gstTotal.value + tcsTotal.value - tdsTotal.value)

const fmt = (n) => Number(n || 0).toFixed(2)

onMounted(async () => {
  try {
    contacts.value = await contactsApi.list({ page: 1, limit: 200 })
  } catch (e) {
    contacts.value = []
  }
  try {
    await itemsStore.fetchList({ page: 1, limit: 500, is_active: true })
  } catch (e) {
    // Items load failed, but allow form to continue
  }
})

// Pull defaults from item master into invoice line while still allowing manual override.
const onSelectItem = (line) => {
  const selected = itemsStore.items.find((it) => it.inventory_item_id === line.inventory_item_id)
  if (!selected) return
  line.description = selected.item_name || line.description
  line.hsn_sac = selected.hsn_sac || null
  line.account_id = selected.sales_account_id || null
  line.unit_price = Number(selected.selling_price || 0)
  line.gst_rate = Number(selected.gst_rate || 0)
}

const createInvoice = async () => {
  if (!form.billing_party_id) {
    toast.error('Billing party is required')
    return
  }
  if (!form.items.length || !form.items.every((x) => x.description && Number(x.quantity) > 0)) {
    toast.error('Add at least one valid line item')
    return
  }
  saving.value = true
  try {
    const payload = {
      invoice_type: form.invoice_type,
      invoice_date: form.invoice_date,
      due_date: form.due_date || null,
      billing_party_id: form.billing_party_id,
      shipping_party_id: form.shipping_party_id || null,
      order_number: form.order_number || null,
      salesperson_id: form.salesperson_id || null,
      subject: form.subject || null,
      customer_notes: form.customer_notes || null,
      terms_and_conditions: form.terms_and_conditions || null,
      currency: form.currency || 'INR',
      exchange_rate: form.exchange_rate || 1,
      items: form.items.map((it) => ({
        inventory_item_id: it.inventory_item_id || null,
        description: it.description,
        hsn_sac: it.hsn_sac,
        account_id: it.account_id,
        quantity: it.quantity,
        unit_price: it.unit_price,
        discount_amount: it.discount_amount,
        gst_rate: it.gst_rate,
        tds_rate: it.tds_rate,
        tcs_rate: it.tcs_rate,
      })),
      meta: form.meta,
    }
    const key = crypto.randomUUID()
    const created = await invoicesApi.create(payload, { idempotencyKey: key })
    toast.success(`Created ${created.invoice_number}`)
    router.push({ name: 'InvoiceDetail', params: { invoiceId: created.invoice_id } })
  } catch (e) {
    const message = Array.isArray(e?.response?.data?.detail)
      ? e.response.data.detail.map((item) => item.msg || item).join(', ')
      : e?.response?.data?.detail || e?.message || 'Create failed'
    toast.error(message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}
.card {
  padding: 14px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.span2 {
  grid-column: span 2;
}
.label {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
  font-weight: 600;
}
.input {
  height: 38px;
  border-radius: 10px;
  border: 1px solid #d1d5db;
  padding: 0 10px;
  font-size: 13px;
  outline: none;
  background: #fff;
  width: 100%;
}
.input-textarea {
  height: auto;
  padding: 10px;
  font-family: inherit;
  resize: vertical;
}
.items-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.h {
  font-weight: 800;
  color: #111827;
}
.row {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 12px;
  background: #fafafa;
  margin-bottom: 10px;
}
.row-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1fr 1fr 1fr auto;
  gap: 10px;
  align-items: end;
}
.row-actions {
  display: flex;
}
.totals {
  margin-top: 8px;
  border-top: 1px solid #eef2f7;
  padding-top: 10px;
  display: grid;
  gap: 6px;
  max-width: 360px;
  margin-left: auto;
}
.trow {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #374151;
}
.grand {
  font-weight: 800;
  color: #111827;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
@media (max-width: 1050px) {
  .row-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
