<template>
  <div class="page">
    <PageHeader title="Chart of Accounts" subtitle="Seed the default Indian CoA and manage accounts.">
      <template #actions>
        <Button variant="secondary" :loading="seeding" @click="seedDefault">Seed Default</Button>
        <Button @click="openCreate">New Account</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <input v-model="q" class="input" placeholder="Search by name or code" @keyup.enter="refresh" />
        <select v-model="activeFilter" class="input" @change="refresh">
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
        <Button variant="secondary" @click="refresh">Search</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 140px;">Code</th>
              <th>Name</th>
              <th style="width: 140px;">Type</th>
              <th style="width: 110px;">Status</th>
              <th style="width: 160px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="5" class="muted">Loading…</td>
            </tr>
            <tr v-else-if="store.items.length === 0">
              <td colspan="5" class="muted">No accounts found.</td>
            </tr>
            <tr v-for="row in store.items" :key="row.account_id">
              <td class="mono">{{ row.account_code }}</td>
              <td>{{ row.account_name }}</td>
              <td class="pill">{{ row.account_type }}</td>
              <td>
                <span class="status" :class="row.is_active ? 'on' : 'off'">{{ row.is_active ? 'Active' : 'Inactive' }}</span>
              </td>
              <td class="actions">
                <Button variant="secondary" @click="openEdit(row)">Edit</Button>
                <Button v-if="row.is_active" variant="danger" @click="deactivate(row)">Deactivate</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Modal :open="modalOpen" :title="editing ? 'Edit Account' : 'Create Account'" @close="closeModal">
      <div class="modal-layout">
        <div class="category-picker">
          <input v-model="categorySearch" type="text" class="search-input" placeholder="Search" />
          
          <div class="categories">
            <div v-for="(group, idx) in accountCategories" :key="idx" class="category-group">
              <button 
                class="category-header" 
                @click="toggleGroup(idx)"
                :class="{ expanded: expandedGroups[idx] }"
              >
                {{ group.label }}
              </button>
              
              <div v-if="expandedGroups[idx]" class="category-items">
                <button 
                  v-for="item in group.items" 
                  :key="item.value"
                  class="category-item"
                  :class="{ selected: form.account_type === item.value }"
                  @click="selectCategory(item)"
                >
                  {{ item.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="form-content">
            <label>
              <div class="label">Account Type*</div>
              <div class="selected-type">{{ selectedCategoryLabel }}</div>
            </label>
            <label>
              <div class="label">Account Name*</div>
              <input v-model="form.account_name" class="input" placeholder="Enter account name" />
            </label>
            <label>
              <div class="label">Account Code</div>
              <input v-model="form.account_code" class="input" placeholder="e.g. 4100" />
            </label>
            <label>
              <div class="label">Description</div>
              <textarea v-model="form.description" class="input textarea" placeholder="Max. 500 characters"></textarea>
            </label>
            <label class="checkbox-label">
              <input v-model="form.add_to_watchlist" type="checkbox" />
              <span>Add to the watchlist on my dashboard</span>
            </label>
          </div>

          <div class="description-panel">
            <div class="panel-title">{{ selectedCategoryLabel || 'Asset' }}</div>
            <div class="panel-text">{{ selectedCategoryDesc }}</div>
          </div>
        </div>
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
import { useChartOfAccountsStore } from '../../stores/chartOfAccounts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import Modal from '../../components/ui/Modal.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const store = useChartOfAccountsStore()
const toast = useToastStore()

const q = ref('')
const activeFilter = ref('')
const categorySearch = ref('')
const expandedGroups = ref({
  0: true, // Asset expanded by default
  1: false,
  2: false,
  3: false,
  4: false,
})

const accountCategories = [
  {
    label: 'Asset',
    type: 'asset',
    items: [
      { label: 'Other Asset', value: 'asset:other-asset', desc: 'Track special assets like goodwill and other intangible assets' },
      { label: 'Other Current Asset', value: 'asset:other-current', desc: 'Current assets that don\'t fit other categories' },
      { label: 'Cash', value: 'asset:cash', desc: 'Physical cash and cash equivalents' },
      { label: 'Bank', value: 'asset:bank', desc: 'Bank account balances' },
      { label: 'Fixed Asset', value: 'asset:fixed', desc: 'Long-term assets like property and equipment' },
      { label: 'Accounts Receivable', value: 'asset:ar', desc: 'Money owed by customers' },
      { label: 'Stock', value: 'asset:stock', desc: 'Inventory and stock items' },
      { label: 'Payment Clearing Account', value: 'asset:clearing', desc: 'Temporary account for payment processing' },
      { label: 'Intangible Asset', value: 'asset:intangible', desc: 'Non-physical assets like patents and trademarks' },
      { label: 'Non Current Asset', value: 'asset:non-current', desc: 'Long-term assets held for more than one year' },
      { label: 'Deferred Tax Asset', value: 'asset:deferred-tax', desc: 'Tax benefits to be realized in future periods' },
    ],
  },
  {
    label: 'Liability',
    type: 'liability',
    items: [
      { label: 'Other Current Liability', value: 'liability:other-current', desc: 'Short-term obligations not elsewhere classified' },
      { label: 'Credit Card', value: 'liability:credit-card', desc: 'Credit card payables' },
      { label: 'Non Current Liability', value: 'liability:non-current', desc: 'Long-term obligations' },
      { label: 'Other Liability', value: 'liability:other', desc: 'Other liabilities' },
      { label: 'Accounts Payable', value: 'liability:ap', desc: 'Money owed to suppliers' },
      { label: 'Overseas Tax Payable', value: 'liability:overseas-tax', desc: 'Tax obligations to foreign authorities' },
      { label: 'Deferred Tax Liability', value: 'liability:deferred-tax', desc: 'Tax obligations deferred to future periods' },
    ],
  },
  {
    label: 'Equity',
    type: 'equity',
    items: [
      { label: 'Equity', value: 'equity:capital', desc: 'Owner\'s equity and capital investment' },
    ],
  },
  {
    label: 'Income',
    type: 'income',
    items: [
      { label: 'Income', value: 'income:income', desc: 'Primary revenue and sales income' },
      { label: 'Other Income', value: 'income:other', desc: 'Income from non-operating activities' },
    ],
  },
  {
    label: 'Expense',
    type: 'expense',
    items: [
      { label: 'Expense', value: 'expense:expense', desc: 'Operating expenses' },
      { label: 'Cost Of Goods Sold', value: 'expense:cogs', desc: 'Direct costs of producing goods sold' },
      { label: 'Other Expense', value: 'expense:other', desc: 'Non-operating expenses' },
      { label: 'Meals and Entertainment', value: 'expense:meals', desc: 'Meals and entertainment expenses' },
    ],
  },
]

const modalOpen = ref(false)
const saving = ref(false)
const seeding = ref(false)
const editing = ref(null)

const form = reactive({
  account_code: '',
  account_name: '',
  account_type: 'asset:other-asset',
  description: '',
  add_to_watchlist: false,
  parent_account_id: null,
  is_active: true,
})

const selectedCategoryLabel = computed(() => {
  for (const group of accountCategories) {
    const item = group.items.find((i) => i.value === form.account_type)
    if (item) return item.label
  }
  return 'Select Category'
})

const selectedCategoryDesc = computed(() => {
  for (const group of accountCategories) {
    const item = group.items.find((i) => i.value === form.account_type)
    if (item) return item.desc
  }
  return ''
})

const toggleGroup = (idx) => {
  expandedGroups.value[idx] = !expandedGroups.value[idx]
}

const selectCategory = (item) => {
  form.account_type = item.value
}

const refresh = async () => {
  const is_active = activeFilter.value === '' ? undefined : activeFilter.value === 'true'
  await store.fetchList({ page: 1, limit: 200, q: q.value, is_active })
}

onMounted(refresh)

const seedDefault = async () => {
  seeding.value = true
  try {
    const res = await store.seed()
    toast.success(`Seeded ${res.seeded || 0} accounts`)
    await refresh()
  } catch (e) {
    toast.error('Failed to seed chart of accounts')
  } finally {
    seeding.value = false
  }
}

const openCreate = () => {
  editing.value = null
  Object.assign(form, { 
    account_code: '', 
    account_name: '', 
    account_type: 'asset:other-asset', 
    description: '',
    add_to_watchlist: false,
    parent_account_id: null, 
    is_active: true 
  })
  modalOpen.value = true
}

const openEdit = (row) => {
  editing.value = row
  Object.assign(form, {
    account_code: row.account_code,
    account_name: row.account_name,
    account_type: row.account_type,
    description: row.description || '',
    add_to_watchlist: false,
    parent_account_id: row.parent_account_id || null,
    is_active: !!row.is_active,
  })
  modalOpen.value = true
}

const closeModal = () => {
  modalOpen.value = false
}

const save = async () => {
  if (!form.account_code || !form.account_name) {
    toast.error('Code and name are required')
    return
  }
  saving.value = true
  try {
    // Extract account type (e.g., 'asset' from 'asset:other-asset')
    const accountType = form.account_type.split(':')[0]
    const payload = {
      account_code: form.account_code,
      account_name: form.account_name,
      account_type: accountType,
      description: form.description || null,
      parent_account_id: form.parent_account_id,
      is_active: form.is_active,
    }
    if (editing.value) {
      await store.update(editing.value.account_id, payload)
      toast.success('Account updated')
    } else {
      await store.create(payload)
      toast.success('Account created')
    }
    modalOpen.value = false
  } catch (e) {
    const message = e?.response?.data?.detail || 'Save failed'
    toast.error(message)
  } finally {
    saving.value = false
  }
}

const deactivate = async (row) => {
  if (!confirm(`Deactivate account ${row.account_code} — ${row.account_name}?`)) return
  try {
    await store.deactivate(row.account_id)
    toast.success('Account deactivated')
  } catch (e) {
    toast.error('Deactivate failed')
  }
}
</script>

<style scoped>
.page {
  max-width: 1100px;
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
.input:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.15);
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
}
.status.on {
  color: #059669;
}
.status.off {
  color: #9ca3af;
}
.actions {
  display: flex;
  gap: 8px;
}
.muted {
  color: #6b7280;
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
.modal-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
}
.category-picker {
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 500px;
}
.search-input {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: 13px;
  outline: none;
}
.search-input:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.15);
}
.categories {
  overflow: auto;
  flex: 1;
}
.category-group {
  margin-bottom: 4px;
}
.category-header {
  width: 100%;
  padding: 10px 12px;
  border: none;
  background: transparent;
  text-align: left;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}
.category-header:hover {
  background: #f3f4f6;
}
.category-items {
  padding-left: 8px;
}
.category-item {
  width: calc(100% - 8px);
  padding: 8px 12px;
  border: none;
  background: transparent;
  text-align: left;
  color: #6b7280;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
  border-radius: 6px;
}
.category-item:hover {
  background: #f3f4f6;
  color: #374151;
}
.category-item.selected {
  background: #1a73e8;
  color: #fff;
  font-weight: 600;
}
.form-section {
  display: grid;
  grid-template-columns: 1fr 200px;
  gap: 12px;
}
.form-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: auto;
}
.selected-type {
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #f9fafb;
  color: #374151;
  font-size: 13px;
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
.input:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.15);
}
.textarea {
  height: 80px !important;
  padding: 10px !important;
  resize: none;
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}
.checkbox-label input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
.description-panel {
  background: #1f2937;
  color: #fff;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: fit-content;
}
.panel-title {
  font-weight: 600;
  font-size: 13px;
  color: #fff;
}
.panel-text {
  font-size: 12px;
  color: #e5e7eb;
  line-height: 1.4;
}
</style>

