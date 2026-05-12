<template>
  <div class="page">
    <PageHeader title="Items" subtitle="Item master used across invoices, sales orders, delivery challans, and credit notes.">
      <template #actions>
        <Button @click="openCreate">New Item</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <input v-model="q" class="input" placeholder="Search by name or SKU" @keyup.enter="refresh" />
        <select v-model="typeFilter" class="input" @change="refresh">
          <option value="">All Types</option>
          <option value="goods">Goods</option>
          <option value="service">Service</option>
        </select>
        <select v-model="statusFilter" class="input" @change="refresh">
          <option value="">All Statuses</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
        <Button variant="secondary" @click="refresh">Search</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th style="width: 130px;">Type</th>
              <th style="width: 120px;">Unit</th>
              <th style="width: 150px;">SKU</th>
              <th style="width: 180px;">Sales Account</th>
              <th style="width: 180px;">Purchase Account</th>
              <th style="width: 180px;">Preferred Vendor</th>
              <th style="width: 140px; text-align:right;">Sell Price</th>
              <th style="width: 120px;">Status</th>
              <th style="width: 180px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading"><td colspan="10" class="muted">Loading…</td></tr>
            <tr v-else-if="store.items.length === 0"><td colspan="10" class="muted">No items found.</td></tr>
            <tr v-for="item in store.items" :key="item.inventory_item_id">
              <td>{{ item.item_name }}</td>
              <td class="pill">{{ item.item_type }}</td>
              <td>{{ item.unit }}</td>
              <td class="mono">{{ item.sku || '—' }}</td>
              <td>{{ getAccountLabel(item.sales_account_id) || '—' }}</td>
              <td>{{ getAccountLabel(item.purchase_account_id) || '—' }}</td>
              <td>{{ getVendorLabel(item.preferred_vendor_id) || '—' }}</td>
              <td class="mono" style="text-align:right;">₹{{ fmt(item.selling_price) }}</td>
              <td><span :class="item.is_active ? 'active' : 'inactive'">{{ item.is_active ? 'Active' : 'Inactive' }}</span></td>
              <td class="actions">
                <Button variant="secondary" @click="openEdit(item)">Edit</Button>
                <Button v-if="item.is_active" variant="danger" @click="deactivate(item)">Deactivate</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Modal :open="modalOpen" :title="editing ? 'Edit Item' : 'New Item'" @close="closeModal">
      <div class="form-grid">
        <label class="span2"><div class="label">Name*</div><input v-model="form.item_name" class="input" /></label>
        <label><div class="label">Type*</div><select v-model="form.item_type" class="input"><option value="goods">Goods</option><option value="service">Service</option></select></label>
        <label><div class="label">Unit*</div>
          <select v-model="form.unit" class="input">
            <option value="">Select unit</option>
            <option v-for="unit in unitOptions" :key="unit.value" :value="unit.value">
              {{ unit.label }}
            </option>
          </select>
        </label>
        <label class="span2 section-title">Sales Information</label>
        <label><div class="label">Sales Account</div>
          <select v-model="form.sales_account_id" class="input">
            <option :value="null">None</option>
            <optgroup v-for="group in groupedAccounts" :key="group.type" :label="group.label">
              <option v-for="a in group.items" :key="a.account_id" :value="a.account_id">
                {{ a.account_code }} — {{ a.account_name }}
              </option>
            </optgroup>
          </select>
        </label>
        <label><div class="label">Selling Price</div><input v-model.number="form.selling_price" type="number" step="0.01" min="0" class="input" /></label>

        <label class="span2 section-title">Purchase Information</label>
        <label><div class="label">Purchase Account</div>
          <select v-model="form.purchase_account_id" class="input">
            <option :value="null">None</option>
            <optgroup v-for="group in groupedAccounts" :key="group.type" :label="group.label">
              <option v-for="a in group.items" :key="a.account_id" :value="a.account_id">
                {{ a.account_code }} — {{ a.account_name }}
              </option>
            </optgroup>
          </select>
        </label>
        <label><div class="label">Preferred Vendor</div>
          <select v-model="form.preferred_vendor_id" class="input">
            <option :value="null">None</option>
            <option v-for="vendor in vendors.items" :key="vendor.contact_id" :value="vendor.contact_id">
              {{ vendor.name }}
            </option>
          </select>
        </label>
        <label><div class="label">Purchase Price</div><input v-model.number="form.purchase_price" type="number" step="0.01" min="0" class="input" /></label>
        <label><div class="label">SKU</div><input v-model="form.sku" class="input" /></label>
        <label><div class="label">HSN/SAC</div><input v-model="form.hsn_sac" class="input" /></label>
        <label><div class="label">GST %</div><input v-model.number="form.gst_rate" type="number" step="0.01" min="0" class="input" /></label>
        <label class="span2"><div class="label">Description</div><textarea v-model="form.description" class="input area" /></label>
      </div>
      <template #footer>
        <Button variant="secondary" @click="closeModal">Cancel</Button>
        <Button :loading="saving" @click="save">{{ editing ? 'Save' : 'Create' }}</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useItemsStore } from '../../stores/items'
import { useChartOfAccountsStore } from '../../stores/chartOfAccounts'
import { useContactsStore } from '../../stores/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import Modal from '../../components/ui/Modal.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const store = useItemsStore()
const accounts = useChartOfAccountsStore()
const vendors = useContactsStore()
const toast = useToastStore()
const q = ref('')
const typeFilter = ref('')
const statusFilter = ref('')
const modalOpen = ref(false)
const saving = ref(false)
const editing = ref(null)

const unitOptions = [
  { label: 'BOX - box', value: 'box' },
  { label: 'CMS - cm', value: 'cm' },
  { label: 'DOZ - dz', value: 'dz' },
  { label: 'FTS - ft', value: 'ft' },
  { label: 'GMS - g', value: 'g' },
  { label: 'INC - in', value: 'in' },
  { label: 'KGS - kg', value: 'kg' },
  { label: 'KME - km', value: 'km' },
  { label: 'LBS - lb', value: 'lb' },
  { label: 'MGS - mg', value: 'mg' },
  { label: 'MLT - ml', value: 'ml' },
  { label: 'MTR - m', value: 'm' },
  { label: 'PCS - pcs', value: 'pcs' },
]

const form = reactive({
  item_name: '',
  item_type: 'goods',
  unit: 'pcs',
  sku: '',
  hsn_sac: '',
  gst_rate: 0,
  selling_price: 0,
  purchase_price: 0,
  sales_account_id: null,
  purchase_account_id: null,
  preferred_vendor_id: null,
  description: '',
})

const refresh = async () => {
  const is_active = statusFilter.value === '' ? undefined : statusFilter.value === 'true'
  await store.fetchList({ page: 1, limit: 200, q: q.value, item_type: typeFilter.value, is_active })
}

onMounted(async () => {
  await Promise.all([
    refresh(),
    accounts.fetchList({ page: 1, limit: 200, is_active: true }),
  ])

  try {
    await vendors.fetchList({ page: 1, limit: 200, contact_type: 'vendor' })
  } catch {
    // Vendor load is optional for item list rendering.
  }
})

const fmt = (n) => Number(n || 0).toFixed(2)
const accountTypeLabels = {
  asset: 'Asset',
  liability: 'Liability',
  equity: 'Equity',
  income: 'Income',
  expense: 'Expense',
  other: 'Other',
}
const groupedAccounts = computed(() => {
  const groups = accounts.items.reduce((acc, account) => {
    const type = account.account_type || 'other'
    if (!acc[type]) acc[type] = []
    acc[type].push(account)
    return acc
  }, {})

  return Object.entries(groups)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([type, items]) => ({
      type,
      label: accountTypeLabels[type] || type,
      items: items.sort((a, b) => a.account_code.localeCompare(b.account_code)),
    }))
})

const getAccountLabel = (accountId) => {
  if (!accountId) return ''
  const account = accounts.items.find((a) => a.account_id === accountId)
  return account ? `${account.account_code} — ${account.account_name}` : accountId
}
const getVendorLabel = (contactId) => {
  if (!contactId) return ''
  const contact = vendors.items.find((c) => c.contact_id === contactId)
  return contact ? contact.name : contactId
}

const openCreate = () => {
  editing.value = null
  Object.assign(form, {
    item_name: '',
    item_type: 'goods',
    unit: 'pcs',
    sku: '',
    hsn_sac: '',
    gst_rate: 0,
    selling_price: 0,
    purchase_price: 0,
    sales_account_id: null,
    purchase_account_id: null,
    preferred_vendor_id: null,
    description: '',
  })
  modalOpen.value = true
}

const openEdit = (item) => {
  editing.value = item
  Object.assign(form, { ...item })
  modalOpen.value = true
}

const closeModal = () => {
  modalOpen.value = false
}

const save = async () => {
  if (!form.item_name || !form.unit) return toast.error('Name and unit are required')
  saving.value = true
  try {
    if (editing.value) {
      await store.update(editing.value.inventory_item_id, { ...form })
      toast.success('Item updated')
    } else {
      await store.create({ ...form })
      toast.success('Item created')
    }
    modalOpen.value = false
  } catch (error) {
    const message = error?.response?.data?.detail || error?.message || 'Save failed'
    toast.error(message)
  } finally {
    saving.value = false
  }
}

const deactivate = async (item) => {
  if (!confirm(`Deactivate ${item.item_name}?`)) return
  await store.deactivate(item.inventory_item_id)
  toast.success('Item deactivated')
}
</script>

<style scoped>
.page{max-width:1200px;margin:0 auto}.card{padding:14px}.toolbar{display:flex;gap:10px;margin-bottom:12px}.input{height:38px;border:1px solid #d1d5db;border-radius:10px;padding:0 10px}.area{height:90px;padding:10px}.table{width:100%;border-collapse:collapse;font-size:13px}.table th,.table td{padding:10px 8px;border-bottom:1px solid #eef2f7}.table-wrap{overflow:auto}.pill{text-transform:lowercase}.mono{font-family:ui-monospace,Consolas,monospace}.actions{display:flex;gap:8px}.active{color:#059669;font-weight:700}.inactive{color:#9ca3af;font-weight:700}.muted{color:#6b7280}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.span2{grid-column:span 2}.label{font-size:12px;color:#6b7280;margin-bottom:6px;font-weight:600}.section-title{font-size:13px;font-weight:700;color:#111827;margin-bottom:6px}
</style>

