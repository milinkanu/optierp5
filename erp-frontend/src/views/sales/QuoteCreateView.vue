<template>
  <div class="page">
    <PageHeader :title="isEdit ? 'Edit Quote' : 'New Quote'" :subtitle="isEdit ? 'Update details of your price proposal.' : 'Create a new price quote for your customer.'">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'Quotes' })">Cancel</Button>
        <Button :loading="saving" @click="saveQuote">{{ isEdit ? 'Save Changes' : 'Create Quote' }}</Button>
      </template>
    </PageHeader>

    <div class="layout">
      <Card class="card">
        <div class="form-grid">
          <label>
            <div class="label">Customer Name*</div>
            <select v-model="form.billing_party_id" class="input">
              <option value="">Select a customer…</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>

          <label>
            <div class="label">Shipping Party (optional)</div>
            <select v-model="form.shipping_party_id" class="input">
              <option value="">Same as billing</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>

          <label>
            <div class="label">Quote#*</div>
            <input v-model="form.quote_number" class="input" placeholder="QT-2026-00001" :disabled="isEdit" />
          </label>

          <label>
            <div class="label">Reference# (optional)</div>
            <input v-model="form.reference_number" class="input" placeholder="Ref-001" />
          </label>

          <label>
            <div class="label">Quote Date*</div>
            <input v-model="form.quote_date" type="date" class="input" />
          </label>

          <label>
            <div class="label">Expiry Date (optional)</div>
            <input v-model="form.expiry_date" type="date" class="input" />
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

          <label>
            <div class="label">Project Name (optional)</div>
            <input v-model="form.project_name" class="input" placeholder="Select or Add Project" />
          </label>

          <label class="span2">
            <div class="label">Subject (optional)</div>
            <input v-model="form.subject" class="input" placeholder="Proposal Title / Subject" />
          </label>

          <label class="span2">
            <div class="label">Customer Notes (optional)</div>
            <textarea v-model="form.customer_notes" class="input input-textarea" placeholder="Looking forward for your business..." rows="3"></textarea>
          </label>

          <label class="span2">
            <div class="label">Terms & Conditions (optional)</div>
            <textarea v-model="form.terms_and_conditions" class="input input-textarea" placeholder="Payment terms, delivery details..." rows="3"></textarea>
          </label>
        </div>
      </Card>

      <Card class="card">
        <div class="items-head">
          <div class="h">Line Items</div>
          <Button variant="secondary" @click="addItem">Add Row</Button>
        </div>

        <div class="items-table-header">
          <div class="header-col description-col">Item Details</div>
          <div class="header-col num-col">Quantity</div>
          <div class="header-col num-col">Rate</div>
          <div class="header-col num-col">Discount</div>
          <div class="header-col tax-col">GST %</div>
          <div class="header-col tax-col">TDS %</div>
          <div class="header-col tax-col">TCS %</div>
          <div class="header-col amount-col">Amount</div>
          <div class="header-col action-col"></div>
        </div>

        <div class="items-list">
          <div v-for="(it, idx) in form.items" :key="idx" class="item-row">
            <div class="item-row-fields">
              <div class="description-col">
                <select v-model="it.inventory_item_id" class="input select-item" @change="onSelectItem(it)">
                  <option value="">Custom line (manual)</option>
                  <option v-for="masterItem in itemsStore.items" :key="masterItem.inventory_item_id" :value="masterItem.inventory_item_id">
                    {{ masterItem.item_name }} ({{ masterItem.item_type }})
                  </option>
                </select>
                <input v-model="it.description" class="input manual-desc" placeholder="Add description..." />
              </div>
              <div class="num-col">
                <input v-model.number="it.quantity" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="num-col">
                <input v-model.number="it.unit_price" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="num-col">
                <input v-model.number="it.discount_amount" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="tax-col">
                <input v-model.number="it.gst_rate" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="tax-col">
                <input v-model.number="it.tds_rate" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="tax-col">
                <input v-model.number="it.tcs_rate" type="number" min="0" step="0.01" class="input" />
              </div>
              <div class="amount-col font-semibold mono">
                ₹{{ fmt(calculateRowAmount(it)) }}
              </div>
              <div class="action-col">
                <button class="delete-row-btn" @click="removeItem(idx)" title="Remove Row">✕</button>
              </div>
            </div>
          </div>
        </div>

        <div class="totals-layout">
          <div class="notes-hint">
            <p>Taxes and subtotals are calculated in real-time based on selected item configurations.</p>
          </div>
          
          <div class="totals">
            <div class="trow"><span>Sub Total</span><span class="mono">₹{{ fmt(subtotal) }}</span></div>
            <div class="trow discount-row">
              <span>Discount</span>
              <div class="discount-inputs">
                <input v-model.number="form.discount_percentage" type="number" min="0" max="100" class="input num-input small-input" placeholder="%" />
                <span>%</span>
                <input v-model.number="form.discount_amount" type="number" min="0" class="input num-input" placeholder="Amount" />
              </div>
            </div>
            <div class="trow"><span>GST Total</span><span class="mono">₹{{ fmt(gstTotal) }}</span></div>
            <div class="trow"><span>TDS Total</span><span class="mono">- ₹{{ fmt(tdsTotal) }}</span></div>
            <div class="trow"><span>TCS Total</span><span class="mono">+ ₹{{ fmt(tcsTotal) }}</span></div>
            <div class="trow adjustment-row">
              <span>Adjustment</span>
              <input v-model.number="form.adjustment" type="number" class="input num-input" placeholder="0.00" />
            </div>
            <div class="trow grand"><span>Total ( ₹ )</span><span class="mono">₹{{ fmt(grandTotal) }}</span></div>
          </div>
        </div>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useItemsStore } from '../../stores/items'
import { useToastStore } from '../../stores/toast'
import { contactsApi } from '../../api/contacts'
import { quotesApi } from '../../api/quotes'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const itemsStore = useItemsStore()
const toast = useToastStore()
const router = useRouter()
const route = useRoute()
const saving = ref(false)
const contacts = ref([])

const isEdit = computed(() => !!route.params.quoteId)

const today = new Date()
const iso = (d) => d.toISOString().slice(0, 10)

const form = reactive({
  quote_number: `QT-${today.getFullYear()}-${Math.floor(10000 + Math.random() * 90000)}`,
  quote_date: iso(today),
  expiry_date: '',
  billing_party_id: '',
  shipping_party_id: '',
  reference_number: '',
  salesperson_id: '',
  project_name: '',
  subject: '',
  customer_notes: '',
  terms_and_conditions: '',
  currency: 'INR',
  exchange_rate: 1,
  discount_percentage: 0,
  discount_amount: 0,
  adjustment: 0,
  items: [
    { inventory_item_id: '', description: '', quantity: 1, unit_price: 0, discount_amount: 0, gst_rate: 0, tds_rate: 0, tcs_rate: 0 },
  ],
})

const addItem = () => {
  form.items.push({ inventory_item_id: '', description: '', quantity: 1, unit_price: 0, discount_amount: 0, gst_rate: 0, tds_rate: 0, tcs_rate: 0 })
}
const removeItem = (idx) => {
  form.items.splice(idx, 1)
  if (form.items.length === 0) addItem()
}

const calculateRowAmount = (row) => {
  const base = Math.max(0, Number(row.quantity || 0) * Number(row.unit_price || 0) - Number(row.discount_amount || 0))
  const gst = base * (Number(row.gst_rate || 0) / 100)
  const tcs = base * (Number(row.tcs_rate || 0) / 100)
  const tds = base * (Number(row.tds_rate || 0) / 100)
  return base + gst + tcs - tds
}

const subtotal = computed(() =>
  form.items.reduce((s, it) => s + Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0),
)

// In Zoho Books, the main discount can be applied on the subtotal.
const computedDiscountAmount = computed(() => {
  if (form.discount_percentage > 0) {
    return subtotal.value * (Number(form.discount_percentage) / 100)
  }
  return Number(form.discount_amount || 0)
})

const gstTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.gst_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const tdsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tds_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const tcsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tcs_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.unit_price || 0) - Number(it.discount_amount || 0)), 0))
const grandTotal = computed(() => subtotal.value + gstTotal.value + tcsTotal.value - tdsTotal.value - computedDiscountAmount.value + Number(form.adjustment || 0))

const fmt = (n) => Number(n || 0).toFixed(2)

onMounted(async () => {
  try {
    contacts.value = await contactsApi.list({ page: 1, limit: 300 })
  } catch (e) {
    contacts.value = []
  }
  try {
    await itemsStore.fetchList({ page: 1, limit: 500, is_active: true })
  } catch (e) {
    // Master items fetch fails but form can still work manually.
  }

  if (isEdit.value) {
    try {
      const existing = await quotesApi.get(route.params.quoteId)
      if (existing) {
        form.quote_number = existing.quote_number
        form.quote_date = existing.quote_date
        form.expiry_date = existing.expiry_date || ''
        form.billing_party_id = existing.billing_party_id
        form.shipping_party_id = existing.shipping_party_id || ''
        form.reference_number = existing.reference_number || ''
        form.salesperson_id = existing.salesperson_id || ''
        form.project_name = existing.project_name || ''
        form.subject = existing.subject || ''
        form.customer_notes = existing.customer_notes || ''
        form.terms_and_conditions = existing.terms_and_conditions || ''
        form.currency = existing.currency
        form.exchange_rate = existing.exchange_rate
        form.discount_percentage = existing.discount_percentage
        form.discount_amount = existing.discount_amount
        form.adjustment = existing.adjustment
        form.items = existing.items.map(it => ({
          inventory_item_id: it.inventory_item_id || '',
          description: it.description,
          quantity: it.quantity,
          unit_price: it.unit_price,
          discount_amount: it.discount_amount,
          gst_rate: it.gst_rate,
          tds_rate: it.tds_rate,
          tcs_rate: it.tcs_rate
        }))
      }
    } catch (e) {
      toast.error('Failed to load quote details')
      router.push({ name: 'Quotes' })
    }
  }
})

const onSelectItem = (line) => {
  const selected = itemsStore.items.find((it) => it.inventory_item_id === line.inventory_item_id)
  if (!selected) return
  line.description = selected.item_name || line.description
  line.unit_price = Number(selected.selling_price || 0)
  line.gst_rate = Number(selected.gst_rate || 0)
}

const saveQuote = async () => {
  if (!form.billing_party_id) {
    toast.error('Billing party is required')
    return
  }
  if (!form.quote_number) {
    toast.error('Quote number is required')
    return
  }
  if (!form.items.length || !form.items.every((x) => x.description && Number(x.quantity) > 0)) {
    toast.error('Add at least one valid line item with description and quantity')
    return
  }

  saving.value = true
  try {
    const payload = {
      quote_number: form.quote_number,
      quote_date: form.quote_date,
      expiry_date: form.expiry_date || null,
      billing_party_id: form.billing_party_id,
      shipping_party_id: form.shipping_party_id || null,
      reference_number: form.reference_number || null,
      salesperson_id: form.salesperson_id || null,
      project_name: form.project_name || null,
      subject: form.subject || null,
      customer_notes: form.customer_notes || null,
      terms_and_conditions: form.terms_and_conditions || null,
      currency: form.currency || 'INR',
      exchange_rate: form.exchange_rate || 1,
      discount_percentage: form.discount_percentage || 0,
      discount_amount: form.discount_amount || 0,
      adjustment: form.adjustment || 0,
      items: form.items.map((it) => ({
        inventory_item_id: it.inventory_item_id || null,
        description: it.description,
        quantity: it.quantity,
        unit_price: it.unit_price,
        discount_amount: it.discount_amount,
        gst_rate: it.gst_rate,
        tds_rate: it.tds_rate,
        tcs_rate: it.tcs_rate,
      })),
    }

    if (isEdit.value) {
      await quotesApi.update(route.params.quoteId, payload)
      toast.success('Quote updated successfully')
    } else {
      const created = await quotesApi.create(payload)
      toast.success(`Created Quote ${created.quote_number}`)
    }
    router.push({ name: 'Quotes' })
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || 'Failed to save quote'
    toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
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
  gap: 16px;
}
.card {
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.span2 {
  grid-column: span 2;
}
.label {
  font-size: 12px;
  color: #4b5563;
  margin-bottom: 6px;
  font-weight: 700;
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
.input-textarea {
  height: auto;
  padding: 10px 12px;
  font-family: inherit;
  resize: vertical;
}
.items-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.h {
  font-weight: 800;
  color: #1f2937;
  font-size: 15px;
}

/* Horizontal Line Items Grid */
.items-table-header {
  display: grid;
  grid-template-columns: 2.5fr 1fr 1fr 1fr 0.8fr 0.8fr 0.8fr 1.2fr 0.4fr;
  gap: 8px;
  padding: 10px 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-bottom: none;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
}
.header-col {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.num-col, .tax-col, .amount-col {
  text-align: right;
}
.items-list {
  border: 1px solid #e2e8f0;
  border-bottom-left-radius: 8px;
  border-bottom-right-radius: 8px;
  background: #ffffff;
  overflow: hidden;
}
.item-row {
  border-bottom: 1px solid #f1f5f9;
  padding: 10px 12px;
}
.item-row:last-child {
  border-bottom: none;
}
.item-row-fields {
  display: grid;
  grid-template-columns: 2.5fr 1fr 1fr 1fr 0.8fr 0.8fr 0.8fr 1.2fr 0.4fr;
  gap: 8px;
  align-items: center;
}
.select-item {
  margin-bottom: 4px;
}
.manual-desc {
  height: 32px !important;
  font-size: 12px !important;
}
.item-row-fields .input {
  height: 34px;
  padding: 0 8px;
  font-size: 12px;
}
.amount-col {
  font-size: 13px;
  color: #334155;
  padding-right: 4px;
}
.delete-row-btn {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 4px;
  transition: all 0.2s ease;
}
.delete-row-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

/* Totals Layout */
.totals-layout {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 24px;
  margin-top: 20px;
  align-items: start;
}
.notes-hint {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}
.totals {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  background: #fafbfc;
  display: grid;
  gap: 12px;
}
.trow {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #475569;
  align-items: center;
}
.grand {
  font-weight: 800;
  color: #1e293b;
  font-size: 15px;
  border-top: 2px double #cbd5e1;
  padding-top: 12px;
  margin-top: 4px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.discount-row, .adjustment-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.discount-inputs {
  display: flex;
  align-items: center;
  gap: 6px;
}
.num-input {
  width: 100px !important;
  height: 30px !important;
  text-align: right;
  font-size: 12px !important;
}
.small-input {
  width: 50px !important;
}

@media (max-width: 950px) {
  .items-table-header {
    display: none;
  }
  .item-row-fields {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .num-col, .tax-col, .amount-col {
    text-align: left;
  }
  .totals-layout {
    grid-template-columns: 1fr;
  }
}
</style>
