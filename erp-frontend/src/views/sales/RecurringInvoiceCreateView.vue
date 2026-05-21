<template>
  <div class="page">
    <PageHeader title="New Recurring Invoice Profile" subtitle="Set up auto-generated invoices on a recurring schedule.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'RecurringInvoices' })">Cancel</Button>
        <Button :loading="saving" @click="createProfile">Create Profile</Button>
      </template>
    </PageHeader>

    <div class="layout">
      <!-- Profile & Billing Details -->
      <Card class="card">
        <h3 class="section-title">Recurring Configuration</h3>
        <div class="form-grid">
          <label class="span2">
            <div class="label">Profile Name *</div>
            <input v-model="form.profile_name" type="text" class="input" placeholder="e.g. Monthly Retainer for Acme Corp" required />
          </label>
          <label>
            <div class="label">Frequency *</div>
            <select v-model="form.frequency" class="input">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="yearly">Yearly</option>
            </select>
          </label>
          <label>
            <div class="label">Auto-Email Generated Invoices</div>
            <div class="toggle-wrapper">
              <input v-model="form.auto_email" type="checkbox" id="auto-email-toggle" class="toggle-checkbox" />
              <label for="auto-email-toggle" class="toggle-label-switch">
                <span class="toggle-inner"></span>
                <span class="toggle-switch"></span>
              </label>
              <span class="toggle-status-text">{{ form.auto_email ? 'Enabled' : 'Disabled' }}</span>
            </div>
          </label>
          <label>
            <div class="label">Start Date *</div>
            <input v-model="form.start_date" type="date" class="input" required />
          </label>
          <label>
            <div class="label">End Date (optional)</div>
            <input v-model="form.end_date" type="date" class="input" />
          </label>
        </div>
      </Card>

      <Card class="card">
        <h3 class="section-title">Billing & Shipping</h3>
        <div class="form-grid">
          <label class="span2">
            <div class="label">Billing Party *</div>
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
            <div class="label">Currency</div>
            <input v-model="form.currency" class="input" placeholder="INR" />
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
            <div class="label">Reference / PO Number (optional)</div>
            <input v-model="form.order_number" class="input" placeholder="PO-001" />
          </label>
          <label>
            <div class="label">Subject (optional)</div>
            <input v-model="form.subject" class="input" placeholder="Invoice subject/title" />
          </label>
          <label class="span2">
            <div class="label">Customer Notes (optional)</div>
            <textarea v-model="form.customer_notes" class="input input-textarea" placeholder="Thank you for your business..." rows="2"></textarea>
          </label>
          <label class="span2">
            <div class="label">Terms & Conditions (optional)</div>
            <textarea v-model="form.terms_and_conditions" class="input input-textarea" placeholder="Payment terms, delivery terms, etc." rows="2"></textarea>
          </label>
        </div>
      </Card>

      <!-- Line Items Section -->
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
          <div class="trow grand"><span>Estimated Total (per invoice)</span><span class="mono">₹{{ fmt(grandTotal) }}</span></div>
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
import { recurringInvoicesApi } from '../../api/recurringInvoices'
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
  profile_name: '',
  frequency: 'monthly',
  start_date: iso(today),
  end_date: '',
  auto_email: false,
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
    contacts.value = await contactsApi.list({ page: 1, limit: 300 })
  } catch (e) {
    contacts.value = []
  }
  try {
    await itemsStore.fetchList({ page: 1, limit: 500, is_active: true })
  } catch (e) {
    // master items list fail isn't fatal
  }
})

const onSelectItem = (line) => {
  const selected = itemsStore.items.find((it) => it.inventory_item_id === line.inventory_item_id)
  if (!selected) return
  line.description = selected.item_name || line.description
  line.hsn_sac = selected.hsn_sac || null
  line.account_id = selected.sales_account_id || null
  line.unit_price = Number(selected.selling_price || 0)
  line.gst_rate = Number(selected.gst_rate || 0)
}

const createProfile = async () => {
  if (!form.profile_name) {
    toast.error('Profile Name is required')
    return
  }
  if (!form.billing_party_id) {
    toast.error('Billing Party is required')
    return
  }
  if (!form.start_date) {
    toast.error('Start Date is required')
    return
  }
  if (!form.items.length || !form.items.every((x) => x.description && Number(x.quantity) > 0)) {
    toast.error('Add at least one valid line item')
    return
  }

  saving.value = true
  try {
    const payload = {
      profile_name: form.profile_name,
      billing_party_id: form.billing_party_id,
      shipping_party_id: form.shipping_party_id || null,
      frequency: form.frequency,
      start_date: form.start_date,
      end_date: form.end_date || null,
      auto_email: form.auto_email,
      currency: form.currency || 'INR',
      exchange_rate: form.exchange_rate || 1,
      order_number: form.order_number || null,
      salesperson_id: form.salesperson_id || null,
      subject: form.subject || null,
      customer_notes: form.customer_notes || null,
      terms_and_conditions: form.terms_and_conditions || null,
      items: form.items.map((it) => ({
        inventory_item_id: it.inventory_item_id || null,
        description: it.description,
        hsn_sac: it.hsn_sac,
        account_id: it.account_id || null,
        quantity: it.quantity,
        unit_price: it.unit_price,
        discount_amount: it.discount_amount || 0,
        gst_rate: it.gst_rate,
        tds_rate: it.tds_rate || 0,
        tcs_rate: it.tcs_rate || 0,
      })),
    }

    await recurringInvoicesApi.create(payload)
    toast.success('Recurring Invoice Profile created successfully')
    router.push({ name: 'RecurringInvoices' })
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
  gap: 16px;
}
.card {
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
  margin-top: 0;
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 6px;
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
.input-textarea {
  height: auto;
  padding: 10px;
  font-family: inherit;
  resize: vertical;
}

/* Switch Toggle Styling */
.toggle-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 38px;
}
.toggle-checkbox {
  display: none;
}
.toggle-label-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 24px;
  cursor: pointer;
}
.toggle-inner {
  display: block;
  width: 100%;
  height: 100%;
  background-color: #e2e8f0;
  border-radius: 12px;
  transition: background-color 0.2s ease;
}
.toggle-checkbox:checked + .toggle-label-switch .toggle-inner {
  background-color: #10b981;
}
.toggle-switch {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 20px;
  height: 20px;
  background-color: #ffffff;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
  transition: transform 0.2s ease;
}
.toggle-checkbox:checked + .toggle-label-switch .toggle-switch {
  transform: translateX(24px);
}
.toggle-status-text {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}

.items-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}
.h {
  font-weight: 800;
  font-size: 14px;
  color: #1e293b;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.row {
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 16px;
  background: #fafbfc;
  margin-bottom: 12px;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.01);
}
.row-grid {
  display: grid;
  grid-template-columns: 2fr 1.5fr 0.8fr 1fr 1fr 0.8fr 0.8fr 0.8fr auto;
  gap: 12px;
  align-items: end;
}
.row-actions {
  display: flex;
}
.totals {
  margin-top: 12px;
  border-top: 1px solid #eef2f7;
  padding-top: 16px;
  display: grid;
  gap: 8px;
  max-width: 400px;
  margin-left: auto;
}
.trow {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #475569;
}
.grand {
  font-weight: 800;
  color: #1e293b;
  font-size: 14px;
  border-top: 1px dashed #e2e8f0;
  padding-top: 8px;
  margin-top: 4px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
}
@media (max-width: 1100px) {
  .row-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
