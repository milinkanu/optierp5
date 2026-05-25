<template>
  <div v-if="open" class="backdrop" @click.self="handleClose">
    <div class="modal">
      <div class="header">
        <div class="h">Customer CSV Import Wizard</div>
        <button class="x" @click="handleClose">×</button>
      </div>

      <div class="body">
        <!-- Step Indicator -->
        <div class="stepper">
          <div class="step" :class="{ active: step === 1, done: step > 1 }">
            <span class="step-circle">1</span>
            <span class="step-text">Upload CSV</span>
          </div>
          <div class="step-line"></div>
          <div class="step" :class="{ active: step === 2, done: step > 2 }">
            <span class="step-circle">2</span>
            <span class="step-text">Map Columns</span>
          </div>
          <div class="step-line"></div>
          <div class="step" :class="{ active: step === 3 }">
            <span class="step-circle">3</span>
            <span class="step-text">Import Status</span>
          </div>
        </div>

        <!-- Step 1: Upload File -->
        <div v-if="step === 1" class="step-content fade-in">
          <div
            class="drag-drop-area"
            :class="{ active: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="handleFileDrop"
            @click="$refs.fileInput.click()"
          >
            <input
              type="file"
              ref="fileInput"
              accept=".csv"
              class="hidden"
              @change="handleFileSelect"
            />
            <span class="upload-icon">📊</span>
            <p v-if="!selectedFile" class="upload-text">
              Drag & Drop your customer CSV file here, or <span class="highlight">browse files</span>.
            </p>
            <p v-else class="upload-text selected">
              Selected File: <strong>{{ selectedFile.name }}</strong> ({{ formatBytes(selectedFile.size) }})
            </p>
            <p class="muted-text">Supported file formats: CSV (Comma Separated Values)</p>
          </div>

          <div class="sample-download">
            <span>Don't have a CSV? Download our sample customer import template:</span>
            <button type="button" class="link-btn" @click="downloadSampleCSV">Download Sample CSV</button>
          </div>
        </div>

        <!-- Step 2: Map Headers -->
        <div v-if="step === 2" class="step-content fade-in">
          <p class="step-description">
            Map columns from your uploaded CSV file to standard OptiReach customer database fields. We have auto-matched some fields based on fuzzy logic.
          </p>

          <div class="mapping-table-wrap">
            <table class="mapping-table">
              <thead>
                <tr>
                  <th>Database Field</th>
                  <th>Status</th>
                  <th>CSV Column (Source)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="field in dbFields" :key="field.key">
                  <td class="field-info">
                    <div class="field-label" :class="{ required: field.required }">
                      {{ field.label }}
                    </div>
                    <div class="field-desc">{{ field.desc }}</div>
                  </td>
                  <td>
                    <span v-if="mapping[field.key]" class="badge mapped">✓ Mapped</span>
                    <span v-else-if="field.required" class="badge missing">✗ Required</span>
                    <span v-else class="badge unmapped">Unmapped</span>
                  </td>
                  <td>
                    <select v-model="mapping[field.key]" class="input map-select">
                      <option value="">-- Choose Column --</option>
                      <option v-for="h in csvHeaders" :key="h" :value="h">{{ h }}</option>
                    </select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Step 3: Result / Complete -->
        <div v-if="step === 3" class="step-content fade-in">
          <div class="result-summary">
            <div class="result-card success">
              <span class="result-number">{{ importReport?.imported || 0 }}</span>
              <span class="result-label">Imported Successfully</span>
            </div>
            <div class="result-card warning">
              <span class="result-number">{{ importReport?.duplicates || 0 }}</span>
              <span class="result-label">Duplicates Skipped</span>
            </div>
            <div class="result-card danger">
              <span class="result-number">{{ importReport?.failed || 0 }}</span>
              <span class="result-label">Errors / Failed</span>
            </div>
          </div>

          <div class="result-status-message flex-row justify-center align-center">
            <span class="badge" :class="importReport?.failed === 0 ? 'mapped' : 'missing'">
              {{ importReport?.failed === 0 ? '✓ Complete' : '⚠ Completed with Issues' }}
            </span>
          </div>

          <div v-if="importReport?.errors && importReport.errors.length > 0" class="errors-section">
            <h4 class="errors-title">CSV Rows Validation Errors Report</h4>
            <div class="errors-table-wrap">
              <table class="errors-table">
                <thead>
                  <tr>
                    <th style="width: 80px;">CSV Row</th>
                    <th>Reason / Validation Failure Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(err, idx) in importReport.errors" :key="idx">
                    <td class="mono font-bold">{{ err.row }}</td>
                    <td class="error-desc">{{ err.error }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div class="footer">
        <Button variant="secondary" @click="handleClose">Cancel</Button>
        <Button v-if="step === 2" variant="secondary" @click="step = 1">Back</Button>
        <Button v-if="step === 1" :disabled="!selectedFile" @click="parseCsvHeaders">Next</Button>
        <Button v-if="step === 2" :loading="importing" @click="runCsvImport">Start Import</Button>
        <Button v-if="step === 3" @click="handleComplete">Done</Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { useContactsStore } from '../../stores/contacts'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'imported'])

const store = useContactsStore()
const toast = useToastStore()

const step = ref(1)
const selectedFile = ref(null)
const isDragging = ref(false)
const csvHeaders = ref([])
const importing = ref(false)
const importReport = ref(null)

const dbFields = [
  { key: 'customer_name', label: 'Customer Name', required: true, desc: 'Legal registered name of company or individual' },
  { key: 'display_name', label: 'Display Name', required: false, desc: 'Usually company trade name (default: Customer Name)' },
  { key: 'customer_type', label: 'Customer Type', required: false, desc: 'business | individual (default: business)' },
  { key: 'email', label: 'Email', required: false, desc: 'General email address for invoicing' },
  { key: 'mobile', label: 'Mobile', required: false, desc: '10-digit mobile number' },
  { key: 'phone', label: 'Landline Phone', required: false, desc: 'Alternate contact number' },
  { key: 'gst_registration_type', label: 'GST Registration Type', required: false, desc: 'regular | composition | unregistered | sez | consumer' },
  { key: 'gstin', label: 'GSTIN', required: false, desc: '15-character GSTIN number' },
  { key: 'pan', label: 'PAN', required: false, desc: '10-character PAN card number' },
  { key: 'currency', label: 'Base Currency', required: false, desc: 'INR | USD | EUR (default: INR)' },
  { key: 'payment_terms', label: 'Payment Terms', required: false, desc: 'Due on Receipt | Net 15 | Net 30' },
  { key: 'credit_limit', label: 'Credit Limit', required: false, desc: 'Maximum credit allocation allowed (number)' },
  { key: 'opening_balance', label: 'Opening Balance', required: false, desc: 'Non-zero balance (number)' },
  { key: 'opening_balance_type', label: 'Opening Balance Type', required: false, desc: 'debit | credit' },
  { key: 'billing_address_line1', label: 'Billing Address Line 1', required: false, desc: 'Street, PO Box (Required if address exists)' },
  { key: 'billing_city', label: 'Billing City', required: false, desc: 'Billing City name' },
  { key: 'billing_state', label: 'Billing State', required: false, desc: 'Billing State (e.g. Maharashtra)' },
  { key: 'billing_zip', label: 'Billing ZIP', required: false, desc: '6-digit PIN / postal code' },
  { key: 'shipping_address_line1', label: 'Shipping Address Line 1', required: false, desc: 'Street (Required if address exists)' },
  { key: 'shipping_city', label: 'Shipping City', required: false, desc: 'Shipping City' },
  { key: 'shipping_state', label: 'Shipping State', required: false, desc: 'Shipping State' },
  { key: 'shipping_zip', label: 'Shipping ZIP', required: false, desc: 'Shipping ZIP code' },
]

const mapping = reactive({})

watch(() => props.open, (val) => {
  if (val) {
    step.value = 1
    selectedFile.value = null
    csvHeaders.value = []
    importReport.value = null
    resetMapping()
  }
})

function resetMapping() {
  dbFields.forEach(f => {
    mapping[f.key] = ''
  })
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function handleFileSelect(e) {
  const file = e.target.files?.[0]
  if (file) {
    selectedFile.value = file
  }
}

function handleFileDrop(e) {
  isDragging.value = false
  const file = e.dataTransfer.files?.[0]
  if (file && file.name.endsWith('.csv')) {
    selectedFile.value = file
  } else {
    toast.error('Please drop a valid .csv file')
  }
}

function parseCsvHeaders() {
  if (!selectedFile.value) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target.result
    // Parse first line (headers)
    const lines = text.split(/\r?\n/)
    if (lines.length === 0) {
      toast.error('The selected file is empty')
      return
    }

    const firstLine = lines[0]
    // simple parser for CSV headers (handling quotes optionally)
    const headers = []
    let current = ''
    let inQuotes = false
    for (let char of firstLine) {
      if (char === '"') {
        inQuotes = !inQuotes
      } else if (char === ',' && !inQuotes) {
        headers.push(current.trim().replace(/^"|"$/g, ''))
        current = ''
      } else {
        current += char
      }
    }
    if (current) {
      headers.push(current.trim().replace(/^"|"$/g, ''))
    }

    csvHeaders.value = headers.filter(h => h.length > 0)
    autoMatchColumns()
    step.value = 2
  }
  reader.readAsText(selectedFile.value.slice(0, 4096)) // Read first few KB to get headers
}

function autoMatchColumns() {
  resetMapping()

  // Match functions
  csvHeaders.value.forEach(h => {
    const cleanH = h.toLowerCase().replace(/[^a-z0-9]/g, '')

    dbFields.forEach(f => {
      const cleanF = f.key.toLowerCase().replace(/[^a-z0-9]/g, '')
      // Check exact matches or simple aliases
      if (cleanH === cleanF) {
        mapping[f.key] = h
      } else if (f.key === 'customer_name' && ['name', 'custname', 'companyname', 'customer'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'display_name' && ['displayname', 'tradename'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'customer_type' && ['type', 'custtype'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'email' && ['emailid', 'emailaddress', 'billingemail'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'mobile' && ['mobileno', 'mobilephone', 'contactmobile'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'gst_registration_type' && ['gstregtype', 'gstregistrationtype', 'registrationtype'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'billing_address_line1' && ['billingaddress', 'billingstreet', 'billingline1', 'address1'].includes(cleanH)) {
        mapping[f.key] = h
      } else if (f.key === 'billing_zip' && ['billingpincode', 'billingzip', 'billingpostal', 'pincode', 'zip'].includes(cleanH)) {
        mapping[f.key] = h
      }
    })
  })
}

async function runCsvImport() {
  // Validate required headers
  if (!mapping.customer_name) {
    toast.error('You must map the required Legal Customer Name column.')
    return
  }

  // Filter out unmapped fields
  const activeMapping = {}
  dbFields.forEach(f => {
    if (mapping[f.key]) {
      activeMapping[f.key] = mapping[f.key]
    }
  })

  importing.value = true
  try {
    const report = await store.importCsv(selectedFile.value, activeMapping)
    importReport.value = report
    step.value = 3
    if (report.failed === 0) {
      toast.success(`Import completed! Successfully created ${report.imported} customers.`)
    } else {
      toast.warning(`Import completed with ${report.failed} errors. See report for details.`)
    }
  } catch (err) {
    toast.error(err || 'Failed to complete CSV import')
  } finally {
    importing.value = false
  }
}

function downloadSampleCSV() {
  const headers = 'Name,Code,Type,GSTIN,Email,Mobile,OpeningBal,BalType'
  const sampleRow = [
    '"OptiReach Enterprise Solutions Private Limited"',
    '"CUST-IMP-001"',
    '"business"',
    '"27AADCB8374D1Z3"',
    '"finance@optireach.com"',
    '"9876543210"',
    '"15000"',
    '"debit"'
  ].join(',')

  const csvContent = "data:text/csv;charset=utf-8," + headers + "\n" + sampleRow
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement("a")
  link.setAttribute("href", encodedUri)
  link.setAttribute("download", "optireach_customers_sample.csv")
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  toast.success('Sample customer template downloaded!')
}

function handleComplete() {
  emit('imported')
  emit('close')
}

function handleClose() {
  emit('close')
}
</script>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
  padding: 16px;
}

.modal {
  width: min(800px, 100%);
  max-height: min(750px, calc(100vh - 40px));
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.2);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
}

.h {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.x {
  border: none;
  background: transparent;
  font-size: 24px;
  cursor: pointer;
  color: #64748b;
  padding: 4px;
  line-height: 1;
}

.x:hover {
  color: #0f172a;
}

.body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Stepper progress indicator */
.stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 40px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.step-circle {
  width: 28px;
  height: 28px;
  border-radius: 99px;
  background: #e2e8f0;
  color: #64748b;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  transition: all 0.2s ease;
}

.step-text {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}

.step.active .step-circle {
  background: #1a73e8;
  color: #ffffff;
  box-shadow: 0 0 0 4px rgba(26, 115, 232, 0.15);
}

.step.active .step-text {
  color: #1a73e8;
  font-weight: 700;
}

.step.done .step-circle {
  background: #10b981;
  color: #ffffff;
}

.step.done .step-text {
  color: #10b981;
}

.step-line {
  flex: 1;
  height: 2px;
  background: #e2e8f0;
  margin: 0 12px;
  transform: translateY(-13px);
}

.step-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* Drag drop area */
.drag-drop-area {
  border: 2px dashed #cbd5e1;
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transition: all 0.2s ease;
}

.drag-drop-area:hover, .drag-drop-area.active {
  border-color: #1a73e8;
  background: #f0f7ff;
}

.upload-icon {
  font-size: 40px;
}

.upload-text {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.upload-text .highlight {
  color: #1a73e8;
  text-decoration: underline;
}

.upload-text.selected {
  color: #10b981;
}

.muted-text {
  font-size: 11px;
  color: #64748b;
}

.sample-download {
  margin-top: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  text-align: center;
}

/* Map columns step */
.step-description {
  font-size: 13px;
  color: #64748b;
  margin-top: 0;
  margin-bottom: 16px;
}

.mapping-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  overflow: auto;
  max-height: 380px;
}

.mapping-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.mapping-table th, .mapping-table td {
  padding: 10px 14px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.mapping-table th {
  background: #f8fafc;
  font-weight: 700;
  color: #334155;
  position: sticky;
  top: 0;
  z-index: 10;
}

.field-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-label {
  font-weight: 700;
  color: #0f172a;
}

.field-label.required::after {
  content: ' *';
  color: #ef4444;
}

.field-desc {
  font-size: 10px;
  color: #64748b;
}

.badge {
  display: inline-block;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.badge.mapped {
  background: #d1fae5;
  color: #065f46;
}

.badge.unmapped {
  background: #f1f5f9;
  color: #475569;
}

.badge.missing {
  background: #fee2e2;
  color: #991b1b;
}

.map-select {
  height: 32px;
  font-size: 12px;
  max-width: 220px;
}

/* Step 3: Result complete */
.result-summary {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.result-card {
  padding: 20px;
  border-radius: 12px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-card.success {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #047857;
}

.result-card.warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
}

.result-card.danger {
  background: #fdf2f2;
  border: 1px solid #fde8e8;
  color: #b91c1c;
}

.result-number {
  font-size: 32px;
  font-weight: 800;
}

.result-label {
  font-size: 12px;
  font-weight: 600;
}

.errors-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.errors-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.errors-table-wrap {
  border: 1px solid #fee2e2;
  border-radius: 8px;
  overflow: auto;
  max-height: 200px;
}

.errors-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}

.errors-table th, .errors-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #fee2e2;
  text-align: left;
}

.errors-table th {
  background: #fdf2f2;
  font-weight: 700;
  color: #991b1b;
  position: sticky;
  top: 0;
}

.errors-table tbody tr {
  background: #fff;
}

.errors-table tbody tr:hover {
  background: #fdf2f2;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
}

.font-bold {
  font-weight: 700;
}

.error-desc {
  color: #b91c1c;
}

.result-status-message {
  margin-bottom: 24px;
}

/* Footer layout */
.footer {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
}

.hidden {
  display: none;
}

.flex-row {
  display: flex;
  flex-direction: row;
}

.justify-center {
  justify-content: center;
}

.align-center {
  align-items: center;
}

.link-btn {
  background: transparent;
  border: none;
  color: #1a73e8;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.link-btn:hover {
  text-decoration: underline;
}

.fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
