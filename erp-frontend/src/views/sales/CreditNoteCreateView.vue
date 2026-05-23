<template>
  <div class="page">
    <PageHeader :title="isEdit ? 'Edit Credit Note' : 'New Credit Note'" :subtitle="isEdit ? 'Update details of your existing credit note.' : 'Create a new credit note for customer sales returns or refunds.'">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'CreditNotes' })">Cancel</Button>
        <Button v-if="!isEdit || form.status === 'draft'" variant="secondary" :loading="saving" @click="saveCreditNote('draft')">Save as Draft</Button>
        <Button :loading="saving" @click="saveCreditNote(isEdit ? form.status : 'open')">
          {{ isEdit ? 'Save Changes' : 'Save and Open' }}
        </Button>
      </template>
    </PageHeader>

    <div class="layout">
      <!-- Read-Only Banner for Posted Credit Notes -->
      <div v-if="isPosted" class="banner warning-banner">
        <i class="banner-icon">⚠️</i>
        <div class="banner-content">
          <strong>Posted Transaction:</strong> This credit note has been posted/opened. You can update references, terms, and notes, but line items cannot be modified.
        </div>
      </div>

      <Card class="card">
        <div class="form-grid">
          <label>
            <div class="label">Customer Name*</div>
            <select v-model="form.billing_party_id" class="input" :disabled="isPosted">
              <option value="">Select a customer…</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>

          <label>
            <div class="label">Shipping Party (optional)</div>
            <select v-model="form.shipping_party_id" class="input" :disabled="isPosted">
              <option value="">Same as billing</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }} ({{ c.contact_type }})
              </option>
            </select>
          </label>

          <label>
            <div class="label">Credit Note#*</div>
            <input v-model="form.credit_note_number" class="input" placeholder="CN-2026-00001 (Auto-generated)" :disabled="isEdit || isPosted" />
          </label>

          <label>
            <div class="label">Reference# (optional)</div>
            <input v-model="form.reference_number" class="input" placeholder="INV-2026-0005" />
          </label>

          <label>
            <div class="label">Credit Note Date*</div>
            <input v-model="form.credit_note_date" type="date" class="input" :disabled="isPosted" />
          </label>

          <label>
            <div class="label">Salesperson (optional)</div>
            <select v-model="form.salesperson_id" class="input" :disabled="isPosted">
              <option value="">Select salesperson…</option>
              <option v-for="c in contacts" :key="c.contact_id" :value="c.contact_id">
                {{ c.name }}
              </option>
            </select>
          </label>

          <label class="span2">
            <div class="label">Customer Notes (optional)</div>
            <textarea v-model="form.customer_notes" class="input input-textarea" placeholder="Notes for the customer..." rows="2"></textarea>
          </label>

          <label class="span2">
            <div class="label">Terms & Conditions (optional)</div>
            <textarea v-model="form.terms_and_conditions" class="input input-textarea" placeholder="Company terms and conditions..." rows="2"></textarea>
          </label>
        </div>
      </Card>

      <Card class="card">
        <div class="items-head">
          <div class="h">Line Items</div>
          <Button v-if="!isPosted" variant="secondary" @click="addItem">Add Row</Button>
        </div>

        <div class="table-wrap">
          <table class="items-table">
            <thead>
              <tr>
                <th style="width: 250px;">Item / Service Details</th>
                <th style="width: 200px;">Account Ledger*</th>
                <th style="width: 80px; text-align: right;">Qty*</th>
                <th style="width: 110px; text-align: right;">Rate*</th>
                <th style="width: 100px; text-align: right;">Discount</th>
                <th style="width: 80px; text-align: right;">GST %</th>
                <th style="width: 80px; text-align: right;">TDS %</th>
                <th style="width: 80px; text-align: right;">TCS %</th>
                <th style="width: 120px; text-align: right;">Amount</th>
                <th style="width: 50px; text-align: center;" v-if="!isPosted"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(it, idx) in form.items" :key="idx">
                <td>
                  <select v-model="it.inventory_item_id" class="input item-select" @change="onSelectItem(it)" :disabled="isPosted">
                    <option value="">Custom Item (Manual)</option>
                    <option v-for="masterItem in itemsStore.items" :key="masterItem.inventory_item_id" :value="masterItem.inventory_item_id">
                      {{ masterItem.item_name }}
                    </option>
                  </select>
                  <input v-model="it.description" class="input item-desc-input" placeholder="Description..." :disabled="isPosted" />
                </td>
                <td>
                  <select v-model="it.account_id" class="input" :disabled="isPosted">
                    <option value="">Select ledger account…</option>
                    <option v-for="a in activeAccounts" :key="a.account_id" :value="a.account_id">
                      {{ a.account_code }} - {{ a.account_name }} ({{ formatType(a.account_type) }})
                    </option>
                  </select>
                </td>
                <td>
                  <input v-model.number="it.quantity" type="number" min="0" step="0.0001" class="input text-right" :disabled="isPosted" />
                </td>
                <td>
                  <input v-model.number="it.rate" type="number" min="0" step="0.01" class="input text-right" :disabled="isPosted" />
                </td>
                <td>
                  <input v-model.number="it.discount_amount" type="number" min="0" step="0.01" class="input text-right" :disabled="isPosted" />
                </td>
                <td>
                  <input v-model.number="it.tax_percentage" type="number" min="0" max="100" step="0.01" class="input text-right" :disabled="isPosted" />
                </td>
                <td>
                  <input v-model.number="it.tds_rate" type="number" min="0" max="100" step="0.01" class="input text-right" :disabled="isPosted" />
                </td>
                <td>
                  <input v-model.number="it.tcs_rate" type="number" min="0" max="100" step="0.01" class="input text-right" :disabled="isPosted" />
                </td>
                <td class="mono font-semibold text-right text-dark">
                  ₹{{ fmt(calculateRowAmount(it)) }}
                </td>
                <td style="text-align: center;" v-if="!isPosted">
                  <button class="delete-row-btn" @click="removeItem(idx)" title="Remove Row">✕</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="totals-layout">
          <div class="notes-hint">
            <p>Double-entry postings are automatically generated on Open/Posted credit notes:</p>
            <ul class="hint-list">
              <li><strong>Debits:</strong> Sales Returns (ledger subtotal), Output GST Reversals</li>
              <li><strong>Credits:</strong> Accounts Receivable (ledger total)</li>
            </ul>
          </div>
          
          <div class="totals">
            <div class="trow"><span>Sub Total</span><span class="mono">₹{{ fmt(subtotal) }}</span></div>
            <div class="trow"><span>GST Total</span><span class="mono">₹{{ fmt(gstTotal) }}</span></div>
            <div class="trow"><span>TDS Reversal</span><span class="mono">- ₹{{ fmt(tdsTotal) }}</span></div>
            <div class="trow"><span>TCS Reversal</span><span class="mono">+ ₹{{ fmt(tcsTotal) }}</span></div>
            <div class="trow grand"><span>Total Credit ( ₹ )</span><span class="mono">₹{{ fmt(grandTotal) }}</span></div>
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
import { useChartOfAccountsStore } from '../../stores/chartOfAccounts'
import { useToastStore } from '../../stores/toast'
import { contactsApi } from '../../api/contacts'
import { creditNotesApi } from '../../api/creditNotes'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const itemsStore = useItemsStore()
const accountsStore = useChartOfAccountsStore()
const toast = useToastStore()
const router = useRouter()
const route = useRoute()

const saving = ref(false)
const contacts = ref([])

const isEdit = computed(() => !!route.params.creditNoteId)

const today = new Date()
const iso = (d) => d.toISOString().slice(0, 10)

const form = reactive({
  credit_note_number: '',
  reference_number: '',
  credit_note_date: iso(today),
  billing_party_id: '',
  shipping_party_id: '',
  currency: 'INR',
  exchange_rate: 1,
  salesperson_id: '',
  customer_notes: '',
  terms_and_conditions: '',
  status: 'draft',
  items: [
    { inventory_item_id: '', description: '', account_id: '', quantity: 1, rate: 0, discount_amount: 0, tax_percentage: 0, tds_rate: 0, tcs_rate: 0 },
  ],
})

const isPosted = computed(() => isEdit.value && form.status !== 'draft')

const activeAccounts = computed(() => {
  return (accountsStore.items || []).filter(a => a.is_active)
})

const addItem = () => {
  if (isPosted.value) return
  form.items.push({ inventory_item_id: '', description: '', account_id: '', quantity: 1, rate: 0, discount_amount: 0, tax_percentage: 0, tds_rate: 0, tcs_rate: 0 })
}

const removeItem = (idx) => {
  if (isPosted.value) return
  form.items.splice(idx, 1)
  if (form.items.length === 0) addItem()
}

const calculateRowAmount = (row) => {
  const base = Math.max(0, Number(row.quantity || 0) * Number(row.rate || 0) - Number(row.discount_amount || 0))
  const gst = base * (Number(row.tax_percentage || 0) / 100)
  const tcs = base * (Number(row.tcs_rate || 0) / 100)
  const tds = base * (Number(row.tds_rate || 0) / 100)
  return base + gst + tcs - tds
}

const subtotal = computed(() =>
  form.items.reduce((s, it) => s + Math.max(0, Number(it.quantity || 0) * Number(it.rate || 0) - Number(it.discount_amount || 0)), 0),
)

const gstTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tax_percentage || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.rate || 0) - Number(it.discount_amount || 0)), 0))
const tdsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tds_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.rate || 0) - Number(it.discount_amount || 0)), 0))
const tcsTotal = computed(() => form.items.reduce((s, it) => s + (Number(it.tcs_rate || 0) / 100) * Math.max(0, Number(it.quantity || 0) * Number(it.rate || 0) - Number(it.discount_amount || 0)), 0))
const grandTotal = computed(() => subtotal.value + gstTotal.value + tcsTotal.value - tdsTotal.value)

const fmt = (n) => Number(n || 0).toFixed(2)

const formatType = (t) => {
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1)
}

onMounted(async () => {
  try {
    contacts.value = await contactsApi.list({ page: 1, limit: 300 })
  } catch (e) {
    contacts.value = []
  }
  try {
    await itemsStore.fetchList({ page: 1, limit: 500, is_active: true })
  } catch (e) {
    // manual fallback
  }
  try {
    await accountsStore.fetchList({ page: 1, limit: 500 })
  } catch (e) {
    // accounts fallback
  }

  // Pre-fill standard income account if available
  const defaultSalesAcc = accountsStore.items.find(a => a.account_code === '4100' || a.account_code === '4110')
  if (defaultSalesAcc && form.items.length === 1 && !form.items[0].account_id) {
    form.items[0].account_id = defaultSalesAcc.account_id
  }

  if (isEdit.value) {
    try {
      const existing = await creditNotesApi.get(route.params.creditNoteId)
      if (existing) {
        form.credit_note_number = existing.credit_note_number
        form.credit_note_date = existing.credit_note_date
        form.billing_party_id = existing.billing_party_id
        form.shipping_party_id = existing.shipping_party_id || ''
        form.reference_number = existing.reference_number || ''
        form.salesperson_id = existing.salesperson_id || ''
        form.customer_notes = existing.customer_notes || ''
        form.terms_and_conditions = existing.terms_and_conditions || ''
        form.currency = existing.currency
        form.exchange_rate = existing.exchange_rate
        form.status = existing.status
        form.items = existing.items.map(it => ({
          inventory_item_id: it.inventory_item_id || '',
          description: it.description,
          account_id: it.account_id,
          quantity: it.quantity,
          rate: it.rate,
          discount_amount: it.discount_amount,
          tax_percentage: it.tax_percentage,
          tds_rate: it.tds_rate,
          tcs_rate: it.tcs_rate
        }))
      }
    } catch (e) {
      toast.error('Failed to load credit note details')
      router.push({ name: 'CreditNotes' })
    }
  }
})

const onSelectItem = (line) => {
  const selected = itemsStore.items.find((it) => it.inventory_item_id === line.inventory_item_id)
  if (!selected) return
  line.description = selected.item_name || line.description
  line.rate = Number(selected.selling_price || 0)
  line.tax_percentage = Number(selected.gst_rate || 0)
  if (selected.sales_account_id) {
    line.account_id = selected.sales_account_id
  }
}

const saveCreditNote = async (saveStatus) => {
  if (!form.billing_party_id) {
    toast.error('Billing customer is required')
    return
  }
  if (!form.items.length || !form.items.every((x) => x.description && Number(x.quantity) > 0 && x.account_id)) {
    toast.error('Add at least one valid line item with description, ledger account, and quantity')
    return
  }

  saving.value = true
  try {
    const payload = {
      credit_note_number: form.credit_note_number || null,
      reference_number: form.reference_number || null,
      credit_note_date: form.credit_note_date,
      billing_party_id: form.billing_party_id,
      shipping_party_id: form.shipping_party_id || null,
      currency: form.currency || 'INR',
      exchange_rate: form.exchange_rate || 1,
      salesperson_id: form.salesperson_id || null,
      customer_notes: form.customer_notes || null,
      terms_and_conditions: form.terms_and_conditions || null,
      status: saveStatus,
      items: form.items.map((it) => ({
        inventory_item_id: it.inventory_item_id || null,
        account_id: it.account_id,
        description: it.description,
        hsn_sac: "0000",
        quantity: it.quantity,
        unit: "pcs",
        rate: it.rate,
        discount_amount: it.discount_amount,
        tax_id: null,
        tax_percentage: it.tax_percentage,
        tds_rate: it.tds_rate,
        tcs_rate: it.tcs_rate,
      })),
    }

    if (isEdit.value) {
      // In edit, payload status will keep current or cancelled
      await creditNotesApi.update(route.params.creditNoteId, payload)
      toast.success('Credit Note updated successfully')
    } else {
      const created = await creditNotesApi.create(payload)
      toast.success(`Created Credit Note ${created.credit_note_number}`)
    }
    router.push({ name: 'CreditNotes' })
  } catch (e) {
    const msg = e?.response?.data?.detail || e?.message || 'Failed to save credit note'
    toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
}
.layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.banner {
  display: flex;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
  align-items: center;
}
.warning-banner {
  background-color: #fff9db;
  border: 1px solid #ffe066;
  color: #8c6b00;
}
.banner-icon {
  font-size: 18px;
}
.card {
  padding: 24px;
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
.input:disabled {
  background-color: #f3f4f6;
  color: #6b7280;
  cursor: not-allowed;
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
.table-wrap {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}
.items-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.items-table th {
  background: #f8fafc;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.05em;
  padding: 10px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}
.items-table td {
  padding: 12px 10px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
.item-select {
  margin-bottom: 6px;
}
.item-desc-input {
  height: 32px !important;
  font-size: 12px !important;
}
.items-table td .input {
  height: 34px;
  padding: 0 8px;
  font-size: 12px;
}
.text-right {
  text-align: right;
}
.text-dark {
  color: #1e293b;
}
.delete-row-btn {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 4px;
  transition: all 0.2s ease;
  margin-top: 4px;
}
.delete-row-btn:hover {
  color: #ef4444;
  background: #fee2e2;
}

/* Totals Section */
.totals-layout {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 30px;
  margin-top: 24px;
  align-items: start;
}
.notes-hint {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 18px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}
.hint-list {
  margin-top: 8px;
  padding-left: 20px;
}
.hint-list li {
  margin-bottom: 4px;
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

@media (max-width: 950px) {
  .totals-layout {
    grid-template-columns: 1fr;
  }
}
</style>
