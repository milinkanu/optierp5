<template>
  <div class="page">
    <PageHeader title="Recurring Invoices" subtitle="Automate invoice creation on standard schedules.">
      <template #actions>
        <Button @click="$router.push({ name: 'RecurringInvoiceNew' })">New Recurring Profile</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div class="toolbar">
        <div class="search-group">
          <label class="toolbar-label">Search Profiles</label>
          <input v-model="searchQuery" type="text" placeholder="Search by profile name or customer..." class="input search-input" />
        </div>
        <div class="filter-group">
          <label class="toolbar-label">Frequency</label>
          <select v-model="frequencyFilter" class="input filter-select">
            <option value="">All Frequencies</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="yearly">Yearly</option>
          </select>
        </div>
        <div class="filter-group">
          <label class="toolbar-label">Status</label>
          <select v-model="statusFilter" class="input filter-select">
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="stopped">Stopped</option>
          </select>
        </div>
        <Button variant="secondary" @click="refresh">Refresh</Button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Profile Name</th>
              <th>Customer</th>
              <th>Frequency</th>
              <th>Start Date</th>
              <th>Next Run Date</th>
              <th>Auto Email</th>
              <th>Status</th>
              <th style="text-align: right; width: 140px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="muted text-center">Loading…</td>
            </tr>
            <tr v-else-if="filteredProfiles.length === 0">
              <td colspan="8" class="muted text-center">No recurring profiles found.</td>
            </tr>
            <tr v-for="row in filteredProfiles" :key="row.profile_id" class="table-row">
              <td>
                <div class="profile-name font-bold">{{ row.profile_name }}</div>
              </td>
              <td>{{ getCustomerName(row.billing_party_id) }}</td>
              <td><span class="freq-badge">{{ row.frequency }}</span></td>
              <td class="muted">{{ formatDate(row.start_date) }}</td>
              <td class="mono font-semibold">{{ formatDate(row.next_run_date) }}</td>
              <td>
                <span class="email-badge" :class="{ enabled: row.auto_email }">
                  {{ row.auto_email ? 'Yes' : 'No' }}
                </span>
              </td>
              <td>
                <span class="status-badge" :class="row.status.toLowerCase()">
                  {{ row.status }}
                </span>
              </td>
              <td class="actions">
                <div class="action-dropdown">
                  <Button variant="secondary" size="small" @click="toggleStatus(row)">
                    {{ row.status === 'active' ? 'Pause' : 'Resume' }}
                  </Button>
                  <Button variant="secondary" size="small" @click="triggerManualRun(row)">
                    Run Now
                  </Button>
                  <Button variant="secondary" size="small" @click="showLogs(row)">
                    Logs
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </Card>

    <!-- Logs Modal -->
    <div v-if="logsModal.show" class="modal-overlay" @click.self="logsModal.show = false">
      <div class="modal">
        <div class="modal-header">
          <h3>Run History Logs: {{ logsModal.profile.profile_name }}</h3>
          <button class="modal-close" @click="logsModal.show = false">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="logsLoading" class="muted text-center">Loading logs…</div>
          <div v-else-if="logsModal.logs.length === 0" class="muted text-center">No logs generated yet. Logs will record success or failures of automatically scheduled runs.</div>
          <table v-else class="table modal-table">
            <thead>
              <tr>
                <th>Run Date</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logsModal.logs" :key="log.log_id">
                <td>{{ formatDateTime(log.run_date) }}</td>
                <td>
                  <span class="status-badge" :class="log.status.toLowerCase()">
                    {{ log.status }}
                  </span>
                </td>
                <td>
                  <span v-if="log.status === 'success' && log.generated_invoice_id" class="success-link">
                    Invoice Created
                  </span>
                  <span v-else class="error-msg text-danger">{{ log.error_message || 'Scheduled evaluation' }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { recurringInvoicesApi } from '../../api/recurringInvoices'
import { contactsApi } from '../../api/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const toast = useToastStore()
const loading = ref(false)
const searchQuery = ref('')
const frequencyFilter = ref('')
const statusFilter = ref('')
const profiles = ref([])
const contacts = ref([])

const logsLoading = ref(false)
const logsModal = ref({
  show: false,
  profile: null,
  logs: []
})

const refresh = async () => {
  loading.value = true
  try {
    profiles.value = await recurringInvoicesApi.list()
  } catch (e) {
    toast.error('Failed to load recurring profiles')
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

const getCustomerName = (partyId) => {
  const contact = contacts.value.find(c => c.contact_id === partyId)
  return contact ? contact.name : 'Unknown Customer'
}

onMounted(async () => {
  await loadContacts()
  await refresh()
})

const formatDate = (d) => {
  if (!d) return '—'
  const dateObj = new Date(d)
  return dateObj.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

const formatDateTime = (dt) => {
  if (!dt) return '—'
  const dateObj = new Date(dt)
  return dateObj.toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  })
}

const toggleStatus = async (profile) => {
  const nextStatus = profile.status === 'active' ? 'paused' : 'active'
  try {
    await recurringInvoicesApi.updateStatus(profile.profile_id, nextStatus)
    toast.success(`Profile ${nextStatus === 'active' ? 'resumed' : 'paused'} successfully`)
    await refresh()
  } catch (e) {
    toast.error('Failed to update profile status')
  }
}

const triggerManualRun = async (profile) => {
  if (!confirm(`Are you sure you want to run invoice generation manually for ${profile.profile_name} now?`)) return
  try {
    const res = await recurringInvoicesApi.trigger(profile.profile_id)
    toast.success(res.message || 'Invoice generated successfully')
    await refresh()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Failed to trigger generation')
  }
}

const showLogs = async (profile) => {
  logsModal.value.profile = profile
  logsModal.value.show = true
  logsLoading.value = true
  try {
    logsModal.value.logs = await recurringInvoicesApi.logs(profile.profile_id)
  } catch (e) {
    toast.error('Failed to retrieve run logs')
    logsModal.value.show = false
  } finally {
    logsLoading.value = false
  }
}

const filteredProfiles = computed(() => {
  return profiles.value.filter(row => {
    // Frequency filter
    if (frequencyFilter.value && row.frequency !== frequencyFilter.value) {
      return false
    }
    // Status filter
    if (statusFilter.value && row.status !== statusFilter.value) {
      return false
    }
    // Search query
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      const nameMatches = row.profile_name.toLowerCase().includes(q)
      const customerMatches = getCustomerName(row.billing_party_id).toLowerCase().includes(q)
      return nameMatches || customerMatches
    }
    return true
  })
})
</script>

<style scoped>
.page {
  max-width: 1250px;
  margin: 0 auto;
}
.card {
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
  border: 1px solid #f0f3f8;
  background: #ffffff;
}
.toolbar {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.filter-group, .search-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.toolbar-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #6b7280;
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
  transition: all 0.2s ease;
}
.input:focus {
  border-color: #1e88e5;
  box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.1);
}
.filter-select {
  width: 160px;
}
.search-input {
  width: 260px;
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
  padding: 14px 10px;
  border-bottom: 1px solid #f1f5f9;
  text-align: left;
  vertical-align: middle;
}
.table-row {
  transition: background 0.15s ease;
}
.table-row:hover {
  background: #f8fafc;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.font-bold {
  font-weight: 700;
  color: #1e293b;
}
.font-semibold {
  font-weight: 600;
}
.freq-badge {
  text-transform: capitalize;
  background-color: #f1f5f9;
  color: #475569;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
}
.email-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
  background-color: #fee2e2;
  color: #dc2626;
}
.email-badge.enabled {
  background-color: #d1fae5;
  color: #059669;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.status-badge.active {
  background-color: #d1fae5;
  color: #059669;
}
.status-badge.paused {
  background-color: #fef3c7;
  color: #d97706;
}
.status-badge.stopped {
  background-color: #fee2e2;
  color: #dc2626;
}
.actions {
  text-align: right;
}
.action-dropdown {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
.muted {
  color: #64748b;
}
.text-center {
  text-align: center;
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
  max-width: 650px;
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
  max-height: 400px;
  overflow-y: auto;
}
.modal-table {
  font-size: 12px;
}
.success-link {
  color: #059669;
  font-weight: 600;
}
.error-msg {
  color: #dc2626;
  font-size: 11px;
}
</style>
