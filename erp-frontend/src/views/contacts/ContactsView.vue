<template>
  <div class="page">
    <PageHeader title="Contacts" subtitle="Customers, vendors, and both — with CSV import.">
      <template #actions>
        <label class="file-btn">
          <input type="file" accept=".csv,text/csv" class="hidden" @change="onPickCsv" />
          <Button variant="secondary" :loading="importing">Import CSV</Button>
        </label>
        <Button @click="openCreate">New Contact</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <input v-model="q" class="input" placeholder="Search by name" @keyup.enter="refresh" />
        <select v-model="typeFilter" class="input" @change="refresh">
          <option value="">All</option>
          <option value="customer">Customer</option>
          <option value="vendor">Vendor</option>
          <option value="both">Both</option>
        </select>
        <Button variant="secondary" @click="refresh">Search</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Name</th>
              <th style="width: 120px;">Type</th>
              <th>Email</th>
              <th style="width: 140px;">Phone</th>
              <th style="width: 140px;">GSTIN</th>
              <th style="width: 160px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="6" class="muted">Loading…</td>
            </tr>
            <tr v-else-if="store.items.length === 0">
              <td colspan="6" class="muted">No contacts found.</td>
            </tr>
            <tr v-for="row in store.items" :key="row.contact_id">
              <td>{{ row.name }}</td>
              <td class="pill">{{ row.contact_type }}</td>
              <td class="muted">{{ row.email || '—' }}</td>
              <td class="muted">{{ row.phone || '—' }}</td>
              <td class="mono">{{ row.gstin || '—' }}</td>
              <td class="actions">
                <Button variant="secondary" @click="openEdit(row)">Edit</Button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <Modal :open="modalOpen" :title="editing ? 'Edit Contact' : 'New Contact'" @close="closeModal">
      <div class="form-grid">
        <label class="span2">
          <div class="label">Name</div>
          <input v-model="form.name" class="input" placeholder="Contact name" />
        </label>
        <label>
          <div class="label">Type</div>
          <select v-model="form.contact_type" class="input">
            <option value="customer">customer</option>
            <option value="vendor">vendor</option>
            <option value="both">both</option>
          </select>
        </label>
        <label>
          <div class="label">Currency</div>
          <input v-model="form.currency" class="input" placeholder="INR" />
        </label>
        <label>
          <div class="label">Email</div>
          <input v-model="form.email" class="input" placeholder="name@company.com" />
        </label>
        <label>
          <div class="label">Phone</div>
          <input v-model="form.phone" class="input" placeholder="+91…" />
        </label>
        <label>
          <div class="label">GSTIN</div>
          <input v-model="form.gstin" class="input" placeholder="Optional" />
        </label>
        <label>
          <div class="label">PAN</div>
          <input v-model="form.pan" class="input" placeholder="Optional" />
        </label>
        <label class="span2">
          <div class="label">Payment Terms</div>
          <input v-model="form.payment_terms" class="input" placeholder="e.g. Net 15" />
        </label>
      </div>

      <template #footer>
        <Button variant="secondary" @click="closeModal">Cancel</Button>
        <Button :loading="saving" @click="save">{{ editing ? 'Save' : 'Create' }}</Button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useContactsStore } from '../../stores/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import Modal from '../../components/ui/Modal.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const store = useContactsStore()
const toast = useToastStore()

const q = ref('')
const typeFilter = ref('')
const importing = ref(false)

const modalOpen = ref(false)
const saving = ref(false)
const editing = ref(null)

const form = reactive({
  contact_type: 'customer',
  name: '',
  email: '',
  phone: '',
  gstin: '',
  pan: '',
  payment_terms: '',
  currency: 'INR',
})

const refresh = async () => {
  await store.fetchList({ page: 1, limit: 200, q: q.value, contact_type: typeFilter.value })
}

onMounted(refresh)

const onPickCsv = async (e) => {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  importing.value = true
  try {
    const res = await store.importCsv(file)
    toast.success(`Imported ${res.created || 0} contacts`)
    await refresh()
  } catch (err) {
    toast.error('CSV import failed (need headers: contact_type,name)')
  } finally {
    importing.value = false
  }
}

const openCreate = () => {
  editing.value = null
  Object.assign(form, { contact_type: 'customer', name: '', email: '', phone: '', gstin: '', pan: '', payment_terms: '', currency: 'INR' })
  modalOpen.value = true
}

const openEdit = (row) => {
  editing.value = row
  Object.assign(form, {
    contact_type: row.contact_type,
    name: row.name,
    email: row.email || '',
    phone: row.phone || '',
    gstin: row.gstin || '',
    pan: row.pan || '',
    payment_terms: row.payment_terms || '',
    currency: row.currency || 'INR',
  })
  modalOpen.value = true
}

const closeModal = () => {
  modalOpen.value = false
}

const save = async () => {
  if (!form.name) {
    toast.error('Name is required')
    return
  }
  saving.value = true
  try {
    const payload = {
      contact_type: form.contact_type,
      name: form.name,
      email: form.email || null,
      phone: form.phone || null,
      gstin: form.gstin || null,
      pan: form.pan || null,
      payment_terms: form.payment_terms || null,
      currency: form.currency || 'INR',
    }
    if (editing.value) {
      await store.update(editing.value.contact_id, payload)
      toast.success('Contact updated')
    } else {
      await store.create(payload)
      toast.success('Contact created')
    }
    modalOpen.value = false
  } catch (e) {
    toast.error('Save failed')
  } finally {
    saving.value = false
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
.hidden {
  display: none;
}
.file-btn {
  display: inline-flex;
}
</style>

