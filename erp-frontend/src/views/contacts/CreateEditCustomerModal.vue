<template>
  <div v-if="open" class="backdrop" @click.self="handleClose">
    <div class="drawer">
      <!-- Header -->
      <div class="header">
        <div class="header-left">
          <div class="h">{{ editing ? 'Edit Customer' : 'New Customer' }}</div>
          <div v-if="draftFound && !editing" class="draft-alert">
            <span>Unsaved draft found.</span>
            <button class="draft-action-btn restore" @click="restoreDraft">Restore</button>
            <button class="draft-action-btn discard" @click="discardDraft">Discard</button>
          </div>
          <span v-else-if="savingDraft && !editing" class="draft-status-badge">Auto-saving...</span>
          <span v-else-if="draftSaved && !editing" class="draft-status-badge saved">Draft saved</span>
        </div>
        <button class="x" @click="handleClose">×</button>
      </div>

      <!-- Main Layout: Sidebar tabs + Content Panel -->
      <div class="main-layout">
        <!-- Sidebar Navigation -->
        <div class="sidebar">
          <button
            v-for="(step, index) in steps"
            :key="index"
            class="tab-btn"
            :class="{ active: currentStep === index, error: stepErrors[index] }"
            @click="currentStep = index"
          >
            <span class="step-num">{{ index + 1 }}</span>
            <span class="step-label">{{ step }}</span>
            <span v-if="stepErrors[index]" class="err-dot">!</span>
          </button>
        </div>

        <!-- Form Fields Content Area -->
        <div class="content">
          <!-- Step 1: Basic Information -->
          <div v-show="currentStep === 0" class="form-section">
            <h3 class="section-title">Basic Information</h3>
            <div class="form-grid">
              <div class="span2 flex-row gap-12">
                <label class="flex-1">
                  <div class="label required-label">Customer Type</div>
                  <div class="radio-group">
                    <label class="radio-label">
                      <input type="radio" v-model="form.customer_type" value="business" />
                      <span>Business</span>
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="form.customer_type" value="individual" />
                      <span>Individual</span>
                    </label>
                  </div>
                </label>
                <label class="flex-1">
                  <div class="label">Customer Code</div>
                  <input
                    v-model="form.customer_code"
                    class="input code-input"
                    placeholder="e.g. CUST-2026-00001 (Auto-generated if empty)"
                  />
                </label>
              </div>

              <label class="span2">
                <div class="label required-label">Legal Name</div>
                <input
                  v-model="form.customer_name"
                  class="input"
                  placeholder="Official legal name"
                  @input="handleNameInput"
                />
              </label>

              <label class="span2">
                <div class="label required-label">Display Name</div>
                <input
                  v-model="form.display_name"
                  class="input"
                  placeholder="Zoho-style display name"
                />
              </label>

              <label>
                <div class="label">Email Address</div>
                <input
                  v-model="form.email"
                  type="email"
                  class="input"
                  placeholder="billing@customer.com"
                />
              </label>

              <label>
                <div class="label">Mobile Number</div>
                <input
                  v-model="form.mobile"
                  class="input"
                  placeholder="10-digit mobile"
                />
              </label>

              <label>
                <div class="label">Landline Phone</div>
                <input
                  v-model="form.phone"
                  class="input"
                  placeholder="Phone number"
                />
              </label>

              <label>
                <div class="label">Base Currency</div>
                <select v-model="form.currency" class="input">
                  <option value="INR">INR - Indian Rupee</option>
                  <option value="USD">USD - United States Dollar</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="GBP">GBP - British Pound</option>
                </select>
              </label>

              <label>
                <div class="label">Invoice Delivery Preference</div>
                <select v-model="form.invoice_delivery_preference" class="input">
                  <option value="email">Email only</option>
                  <option value="portal">Customer Portal</option>
                  <option value="both">Both (Email & Portal)</option>
                </select>
              </label>

              <label>
                <div class="label">Tags (comma-separated)</div>
                <input
                  v-model="tagsInput"
                  class="input"
                  placeholder="e.g. VIP, Wholesale, Technology"
                  @change="syncTags"
                />
              </label>
            </div>
          </div>

          <!-- Step 2: Tax & Compliance -->
          <div v-show="currentStep === 1" class="form-section">
            <h3 class="section-title">Tax & Compliance</h3>
            <div class="form-grid">
              <label class="span2">
                <div class="label required-label">GST Registration Type</div>
                <select v-model="form.gst_registration_type" class="input" @change="handleGstTypeChange">
                  <option value="regular">Regular Registered Business</option>
                  <option value="composition">Composition Scheme</option>
                  <option value="unregistered">Unregistered Business</option>
                  <option value="sez">SEZ (Special Economic Zone)</option>
                  <option value="consumer">Consumer / B2C</option>
                </select>
              </label>

              <div class="span2 flex-row gap-12 align-end" v-if="isGstRequired">
                <label class="flex-1">
                  <div class="label required-label">GSTIN</div>
                  <div class="gstin-container">
                    <input
                      v-model="form.gstin"
                      class="input gstin-input"
                      placeholder="15-digit GSTIN (e.g. 36AAFCD5862R1ZO)"
                      @input="handleGstinInput"
                    />
                    <span v-if="gstinValidationResult?.valid === true" class="gstin-badge valid">✓ Valid</span>
                    <span v-else-if="gstinValidationResult?.valid === false" class="gstin-badge invalid">✗ Invalid</span>
                  </div>
                </label>
                <Button
                  variant="secondary"
                  :loading="validatingGstin"
                  :disabled="!form.gstin || form.gstin.length !== 15"
                  @click="runGstinValidation"
                >
                  Verify
                </Button>
                <Button
                  :loading="prefillingGstin"
                  :disabled="!form.gstin || form.gstin.length !== 15"
                  @click="runGstinPrefill"
                >
                  Auto-Prefill
                </Button>
              </div>

              <label v-if="isGstRequired">
                <div class="label required-label">PAN (Symmetrically Encrypted at Rest)</div>
                <input
                  v-model="form.pan"
                  class="input"
                  placeholder="10-digit PAN (Auto-extracted from GSTIN)"
                  :disabled="!!form.gstin"
                />
              </label>

              <label v-else>
                <div class="label">PAN (Symmetrically Encrypted at Rest)</div>
                <input
                  v-model="form.pan"
                  class="input"
                  placeholder="10-digit PAN (Optional)"
                />
              </label>

              <label>
                <div class="label">CIN (Corporate Identity Number)</div>
                <input
                  v-model="form.cin"
                  class="input"
                  placeholder="21-character CIN (Optional)"
                />
              </label>

              <div class="span2 divider"></div>

              <div class="span2 msme-section">
                <div class="msme-header">
                  <div class="msme-title-group">
                    <div class="msme-label">MSME Registered</div>
                    <div class="msme-desc">Is this customer registered under MSME?</div>
                  </div>
                  <label class="switch">
                    <input type="checkbox" v-model="form.msme_status" />
                    <span class="slider"></span>
                  </label>
                </div>

                <div v-if="form.msme_status" class="msme-body fade-in">
                  <label>
                    <div class="label required-label">MSME Registration Number</div>
                    <input
                      v-model="form.msme_registration_no"
                      class="input"
                      placeholder="e.g. UDYAM-XX-00-1234567"
                    />
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 3: Billing & Shipping Address -->
          <div v-show="currentStep === 2" class="form-section">
            <h3 class="section-title">Addresses</h3>
            <div class="address-layout">
              <!-- Billing Address -->
              <div class="address-col">
                <div class="address-title">Billing Address</div>
                <div class="form-grid">
                  <label class="span2">
                    <div class="label">Attention / Contact Person</div>
                    <input v-model="billingAddr.attention" class="input" placeholder="e.g. Accounts Department" />
                  </label>
                  <label class="span2">
                    <div class="label required-label">Address Line 1</div>
                    <input v-model="billingAddr.address_line1" class="input" placeholder="Street Address, PO Box" />
                  </label>
                  <label class="span2">
                    <div class="label">Address Line 2</div>
                    <input v-model="billingAddr.address_line2" class="input" placeholder="Building, Apartment, Unit" />
                  </label>
                  <label>
                    <div class="label required-label">City</div>
                    <input v-model="billingAddr.city" class="input" placeholder="City" />
                  </label>
                  <label>
                    <div class="label required-label">State / Region</div>
                    <input v-model="billingAddr.state" class="input" placeholder="State (e.g. Telangana)" />
                  </label>
                  <label>
                    <div class="label required-label">ZIP / Postal Code</div>
                    <input v-model="billingAddr.zip_code" class="input" placeholder="ZIP code" />
                  </label>
                  <label>
                    <div class="label required-label">Country</div>
                    <input v-model="billingAddr.country" class="input" placeholder="Country" />
                  </label>
                  <label class="span2">
                    <div class="label">Phone Number</div>
                    <input v-model="billingAddr.phone" class="input" placeholder="Phone" />
                  </label>
                </div>
              </div>

              <!-- Shipping Address -->
              <div class="address-col">
                <div class="address-title flex-row justify-between align-center">
                  <span>Shipping Address</span>
                  <button type="button" class="link-btn" @click="copyBillingToShipping">
                    Copy Billing Address
                  </button>
                </div>
                <div class="form-grid">
                  <label class="span2">
                    <div class="label">Attention / Contact Person</div>
                    <input v-model="shippingAddr.attention" class="input" placeholder="e.g. Receptionist Desk" />
                  </label>
                  <label class="span2">
                    <div class="label required-label">Address Line 1</div>
                    <input v-model="shippingAddr.address_line1" class="input" placeholder="Street Address, PO Box" />
                  </label>
                  <label class="span2">
                    <div class="label">Address Line 2</div>
                    <input v-model="shippingAddr.address_line2" class="input" placeholder="Building, Apartment, Unit" />
                  </label>
                  <label>
                    <div class="label required-label">City</div>
                    <input v-model="shippingAddr.city" class="input" placeholder="City" />
                  </label>
                  <label>
                    <div class="label required-label">State / Region</div>
                    <input v-model="shippingAddr.state" class="input" placeholder="State" />
                  </label>
                  <label>
                    <div class="label required-label">ZIP / Postal Code</div>
                    <input v-model="shippingAddr.zip_code" class="input" placeholder="ZIP code" />
                  </label>
                  <label>
                    <div class="label required-label">Country</div>
                    <input v-model="shippingAddr.country" class="input" placeholder="Country" />
                  </label>
                  <label class="span2">
                    <div class="label">Phone Number</div>
                    <input v-model="shippingAddr.phone" class="input" placeholder="Phone" />
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 4: Contact Persons -->
          <div v-show="currentStep === 3" class="form-section">
            <div class="flex-row justify-between align-center margin-b-16">
              <h3 class="section-title margin-0">Secondary Contacts</h3>
              <button type="button" class="add-btn" @click="addContactPerson">+ Add New Contact</button>
            </div>

            <div v-if="form.contacts.length === 0" class="empty-state">
              <p>No secondary contact persons added yet.</p>
              <button type="button" class="link-btn" @click="addContactPerson">Add one now</button>
            </div>

            <div v-else class="contacts-grid">
              <div
                v-for="(ct, idx) in form.contacts"
                :key="idx"
                class="contact-card"
              >
                <div class="contact-card-header">
                  <span class="contact-index">Contact #{{ idx + 1 }}</span>
                  <button type="button" class="remove-btn" @click="removeContactPerson(idx)">×</button>
                </div>
                <div class="form-grid">
                  <label>
                    <div class="label required-label">First Name</div>
                    <input v-model="ct.first_name" class="input" placeholder="First Name" />
                  </label>
                  <label>
                    <div class="label">Last Name</div>
                    <input v-model="ct.last_name" class="input" placeholder="Last Name" />
                  </label>
                  <label class="span2">
                    <div class="label required-label">Email Address</div>
                    <input v-model="ct.email" type="email" class="input" placeholder="name@company.com" />
                  </label>
                  <label>
                    <div class="label">Phone</div>
                    <input v-model="ct.phone" class="input" placeholder="Landline" />
                  </label>
                  <label>
                    <div class="label">Mobile</div>
                    <input v-model="ct.mobile" class="input" placeholder="Mobile" />
                  </label>
                  <label>
                    <div class="label">Designation</div>
                    <input v-model="ct.designation" class="input" placeholder="e.g. Purchase Manager" />
                  </label>
                  <label class="checkbox-container justify-start align-center flex-row">
                    <input type="checkbox" v-model="ct.is_primary" @change="setPrimaryContact(idx)" />
                    <span class="checkbox-label">Primary Contact for Communication</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          <!-- Step 5: Banking & Credit -->
          <div v-show="currentStep === 4" class="form-section">
            <h3 class="section-title">Banking & Credit</h3>
            <div class="form-grid">
              <label>
                <div class="label">Payment Terms</div>
                <select v-model="form.payment_terms" class="input">
                  <option value="Due on Receipt">Due on Receipt</option>
                  <option value="Net 15">Net 15</option>
                  <option value="Net 30">Net 30</option>
                  <option value="Net 45">Net 45</option>
                  <option value="Net 60">Net 60</option>
                </select>
              </label>

              <label>
                <div class="label">Credit Limit (INR)</div>
                <input
                  v-model.number="form.credit_limit"
                  type="number"
                  min="0"
                  class="input"
                  placeholder="0.00 (Unlimited if zero)"
                />
              </label>

              <div class="span2 divider"></div>

              <div class="span2 flex-row gap-12">
                <label class="flex-1">
                  <div class="label">Opening Balance (INR)</div>
                  <input
                    v-model.number="form.opening_balance"
                    type="number"
                    min="0"
                    class="input"
                    placeholder="0.00"
                  />
                </label>

                <label class="flex-1">
                  <div class="label">Balance Type</div>
                  <div class="radio-group h-38">
                    <label class="radio-label">
                      <input type="radio" v-model="form.opening_balance_type" value="debit" />
                      <span>Debit (A/R)</span>
                    </label>
                    <label class="radio-label">
                      <input type="radio" v-model="form.opening_balance_type" value="credit" />
                      <span>Credit (Adv.)</span>
                    </label>
                  </div>
                </label>
              </div>

              <div v-if="form.opening_balance > 0" class="span2 alert-box">
                <span class="alert-icon">ℹ</span>
                <span class="alert-text">
                  A balanced opening journal entry will be automatically posted:
                  <strong>Debit Code 1200 (Accounts Receivable)</strong> and
                  <strong>Credit Code 3100 (Owner's Capital)</strong>.
                </span>
              </div>
            </div>
          </div>

          <!-- Step 6: Custom Fields & Notes -->
          <div v-show="currentStep === 5" class="form-section">
            <div class="flex-row justify-between align-center margin-b-12">
              <h3 class="section-title margin-0">Custom Fields</h3>
              <button type="button" class="add-btn" @click="addCustomField">+ Add Custom Field</button>
            </div>

            <div v-if="form.custom_fields.length === 0" class="empty-state">
              <p>No custom fields added. Custom fields allow you to track specialized customer parameters.</p>
            </div>

            <div v-else class="custom-fields-list">
              <div v-for="(cf, idx) in form.custom_fields" :key="idx" class="cf-row flex-row gap-12 align-center">
                <input v-model="cf.field_key" class="input flex-1" placeholder="Label / Name (e.g. Birthday)" />
                <input v-model="cf.field_value" class="input flex-1" placeholder="Value (e.g. 1995-12-05)" />
                <button type="button" class="cf-remove-btn" @click="removeCustomField(idx)">×</button>
              </div>
            </div>

            <div class="divider margin-y-24"></div>

            <h3 class="section-title">Internal Notes</h3>
            <textarea
              v-model="form.notes"
              class="textarea"
              rows="4"
              placeholder="Add important details, context, or special agreements with this customer..."
            ></textarea>
          </div>
        </div>
      </div>

      <!-- Footer Buttons -->
      <div class="footer">
        <span v-if="validationErrorMsg" class="footer-error-msg">{{ validationErrorMsg }}</span>
        <Button variant="secondary" @click="handleClose">Cancel</Button>
        <Button variant="secondary" :disabled="currentStep === 0" @click="currentStep--">Previous</Button>
        <Button v-if="currentStep < steps.length - 1" @click="goNext">Next</Button>
        <Button v-else :loading="saving" @click="save">
          {{ editing ? 'Save Changes' : 'Post & Create Customer' }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch, onMounted, computed } from 'vue'
import { useCustomersStore } from '../../stores/customers'
import { useToastStore } from '../../stores/toast'
import Button from '../../components/ui/Button.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  editing: { type: Object, default: null },
})

const emit = defineEmits(['close', 'saved'])

const store = useCustomersStore()
const toast = useToastStore()

const currentStep = ref(0)
const steps = ['General Info', 'Tax & Compliance', 'Addresses', 'Contact Persons', 'Banking & Credit', 'Custom Fields & Notes']

const validatingGstin = ref(false)
const prefillingGstin = ref(false)
const gstinValidationResult = ref(null)
const saving = ref(false)
const validationErrorMsg = ref('')

// Auto-save draft flags
const draftFound = ref(false)
const savingDraft = ref(false)
const draftSaved = ref(false)
const autoSaveTimer = ref(null)

const tagsInput = ref('')

const form = reactive({
  customer_code: '',
  customer_name: '',
  customer_type: 'business',
  display_name: '',
  currency: 'INR',
  email: '',
  mobile: '',
  phone: '',
  gst_registration_type: 'unregistered',
  gstin: '',
  pan: '',
  payment_terms: 'Due on Receipt',
  credit_limit: 0,
  opening_balance: 0,
  opening_balance_type: 'debit',
  msme_status: false,
  msme_registration_no: '',
  cin: '',
  invoice_delivery_preference: 'email',
  addresses: [],
  contacts: [],
  custom_fields: [],
  tags: [],
  notes: '',
})

// Address structures for internal editing
const billingAddr = reactive({
  attention: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  zip_code: '',
  country: 'India',
  phone: '',
})

const shippingAddr = reactive({
  attention: '',
  address_line1: '',
  address_line2: '',
  city: '',
  state: '',
  zip_code: '',
  country: 'India',
  phone: '',
})

const isGstRequired = computed(() => {
  return ['regular', 'composition', 'sez'].includes(form.gst_registration_type)
})

const stepErrors = reactive({
  0: false,
  1: false,
  2: false,
  3: false,
  4: false,
  5: false,
})

// Initialize or Reset
watch(() => props.open, (val) => {
  if (val) {
    currentStep.value = 0
    validationErrorMsg.value = ''
    gstinValidationResult.value = null
    resetStepErrors()

    if (props.editing) {
      // Edit mode: populate from existing customer object
      const c = props.editing
      Object.assign(form, {
        customer_code: c.customer_code || '',
        customer_name: c.customer_name || '',
        customer_type: c.customer_type || 'business',
        display_name: c.display_name || '',
        currency: c.currency || 'INR',
        email: c.email || '',
        mobile: c.mobile || '',
        phone: c.phone || '',
        gst_registration_type: c.gst_registration_type || 'unregistered',
        gstin: c.gstin || '',
        pan: c.pan || '',
        payment_terms: c.payment_terms || 'Due on Receipt',
        credit_limit: c.credit_limit || 0,
        opening_balance: c.opening_balance || 0,
        opening_balance_type: c.opening_balance_type || 'debit',
        msme_status: c.msme_status || false,
        msme_registration_no: c.msme_registration_no || '',
        cin: c.cin || '',
        invoice_delivery_preference: c.invoice_delivery_preference || 'email',
        contacts: JSON.parse(JSON.stringify(c.contacts || [])),
        custom_fields: JSON.parse(JSON.stringify(c.custom_fields || [])),
        tags: JSON.parse(JSON.stringify(c.tags || [])),
        notes: c.notes || '',
      })

      tagsInput.value = (c.tags || []).join(', ')

      // Address mapping
      const bAddr = c.addresses?.find(a => a.address_type === 'billing')
      if (bAddr) Object.assign(billingAddr, bAddr)
      else resetAddress(billingAddr)

      const sAddr = c.addresses?.find(a => a.address_type === 'shipping')
      if (sAddr) Object.assign(shippingAddr, sAddr)
      else resetAddress(shippingAddr)

      draftFound.value = false
    } else {
      // Create mode: reset form
      resetForm()
      // Check for local draft
      const draft = localStorage.getItem('optireach_customer_draft')
      if (draft) {
        draftFound.value = true
      } else {
        draftFound.value = false
      }
    }
  }
})

// Local storage auto-save watch
watch(form, () => {
  if (props.open && !props.editing) {
    triggerAutoSave()
  }
}, { deep: true })

watch(billingAddr, () => {
  if (props.open && !props.editing) {
    triggerAutoSave()
  }
}, { deep: true })

watch(shippingAddr, () => {
  if (props.open && !props.editing) {
    triggerAutoSave()
  }
}, { deep: true })

function triggerAutoSave() {
  savingDraft.value = true
  draftSaved.value = false
  if (autoSaveTimer.value) clearTimeout(autoSaveTimer.value)

  autoSaveTimer.value = setTimeout(() => {
    const fullDraft = {
      form: { ...form },
      billingAddr: { ...billingAddr },
      shippingAddr: { ...shippingAddr },
      tagsInput: tagsInput.value,
    }
    localStorage.setItem('optireach_customer_draft', JSON.stringify(fullDraft))
    savingDraft.value = false
    draftSaved.value = true
  }, 1000)
}

function restoreDraft() {
  try {
    const raw = localStorage.getItem('optireach_customer_draft')
    if (raw) {
      const data = JSON.parse(raw)
      if (data.form) Object.assign(form, data.form)
      if (data.billingAddr) Object.assign(billingAddr, data.billingAddr)
      if (data.shippingAddr) Object.assign(shippingAddr, data.shippingAddr)
      if (data.tagsInput !== undefined) tagsInput.value = data.tagsInput
      toast.success('Draft restored successfully')
    }
  } catch (e) {
    toast.error('Failed to restore draft')
  } finally {
    draftFound.value = false
  }
}

function discardDraft() {
  localStorage.removeItem('optireach_customer_draft')
  draftFound.value = false
  resetForm()
  toast.success('Draft discarded')
}

function resetForm() {
  Object.assign(form, {
    customer_code: '',
    customer_name: '',
    customer_type: 'business',
    display_name: '',
    currency: 'INR',
    email: '',
    mobile: '',
    phone: '',
    gst_registration_type: 'unregistered',
    gstin: '',
    pan: '',
    payment_terms: 'Due on Receipt',
    credit_limit: 0,
    opening_balance: 0,
    opening_balance_type: 'debit',
    msme_status: false,
    msme_registration_no: '',
    cin: '',
    invoice_delivery_preference: 'email',
    addresses: [],
    contacts: [],
    custom_fields: [],
    tags: [],
    notes: '',
  })
  tagsInput.value = ''
  resetAddress(billingAddr)
  resetAddress(shippingAddr)
}

function resetAddress(addr) {
  Object.assign(addr, {
    attention: '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    zip_code: '',
    country: 'India',
    phone: '',
  })
}

function resetStepErrors() {
  for (let k in stepErrors) {
    stepErrors[k] = false
  }
}

function handleNameInput() {
  if (!form.display_name || form.display_name === form.customer_name.slice(0, -1)) {
    form.display_name = form.customer_name
  }
}

function syncTags() {
  form.tags = tagsInput.value
    .split(',')
    .map(t => t.trim())
    .filter(t => t.length > 0)
}

function handleGstTypeChange() {
  if (!isGstRequired.value) {
    form.gstin = ''
    gstinValidationResult.value = null
  }
}

function handleGstinInput() {
  if (form.gstin) {
    form.gstin = form.gstin.toUpperCase().trim()
    if (form.gstin.length === 15) {
      runGstinValidation()
    }
  }
}

async function runGstinValidation() {
  if (!form.gstin || form.gstin.length !== 15) return
  validatingGstin.value = true
  try {
    const res = await store.validateGstin(form.gstin)
    gstinValidationResult.value = res
    if (res.valid && res.pan) {
      form.pan = res.pan
      toast.success('GSTIN is valid and PAN extracted successfully!')
    } else {
      toast.error(res.detail || 'Invalid GSTIN')
    }
  } catch (e) {
    gstinValidationResult.value = { valid: false }
    toast.error('GSTIN validation failed')
  } finally {
    validatingGstin.value = false
  }
}

async function runGstinPrefill() {
  if (!form.gstin || form.gstin.length !== 15) return
  prefillingGstin.value = true
  try {
    const res = await store.prefillGstin(form.gstin)
    if (res.success && res.data) {
      const data = res.data
      form.customer_name = data.legal_name
      form.display_name = data.trade_name
      form.gst_registration_type = data.gst_registration_type
      form.pan = data.pan

      if (data.billing_address) {
        Object.assign(billingAddr, {
          attention: data.billing_address.attention || '',
          address_line1: data.billing_address.address_line1 || '',
          address_line2: data.billing_address.address_line2 || '',
          city: data.billing_address.city || '',
          state: data.billing_address.state || '',
          zip_code: data.billing_address.zip_code || '',
          country: data.billing_address.country || 'India',
          phone: data.billing_address.phone || '',
        })
      }
      toast.success('Information successfully prefilled from GSTIN (Requires Form Submit to Save)')
    }
  } catch (e) {
    toast.error(e || 'Prefill failed')
  } finally {
    prefillingGstin.value = false
  }
}

function copyBillingToShipping() {
  Object.assign(shippingAddr, {
    attention: billingAddr.attention,
    address_line1: billingAddr.address_line1,
    address_line2: billingAddr.address_line2,
    city: billingAddr.city,
    state: billingAddr.state,
    zip_code: billingAddr.zip_code,
    country: billingAddr.country,
    phone: billingAddr.phone,
  })
  toast.success('Addresses copied successfully')
}

// Contacts array management
function addContactPerson() {
  form.contacts.push({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    mobile: '',
    designation: '',
    is_primary: form.contacts.length === 0, // default first contact to primary
  })
}

function removeContactPerson(idx) {
  form.contacts.splice(idx, 1)
  if (form.contacts.length > 0 && !form.contacts.some(c => c.is_primary)) {
    form.contacts[0].is_primary = true
  }
}

function setPrimaryContact(idx) {
  form.contacts.forEach((c, index) => {
    c.is_primary = index === idx
  })
}

// Custom fields management
function addCustomField() {
  form.custom_fields.push({
    field_key: '',
    field_value: '',
  })
}

function removeCustomField(idx) {
  form.custom_fields.splice(idx, 1)
}

function validateCurrentStep() {
  validationErrorMsg.value = ''
  let valid = true

  if (currentStep.value === 0) {
    if (!form.customer_name) {
      validationErrorMsg.value = 'Legal Name is required'
      stepErrors[0] = true
      return false
    }
    if (!form.display_name) {
      validationErrorMsg.value = 'Display Name is required'
      stepErrors[0] = true
      return false
    }
    stepErrors[0] = false
  }

  if (currentStep.value === 1) {
    if (isGstRequired.value) {
      if (!form.gstin) {
        validationErrorMsg.value = 'GSTIN is required for registered business types'
        stepErrors[1] = true
        return false
      }
      if (form.gstin.length !== 15) {
        validationErrorMsg.value = 'GSTIN must be exactly 15 characters'
        stepErrors[1] = true
        return false
      }
      if (!form.pan) {
        validationErrorMsg.value = 'PAN is required'
        stepErrors[1] = true
        return false
      }
    }
    if (form.msme_status && !form.msme_registration_no) {
      validationErrorMsg.value = 'MSME Registration Number is required when MSME status is checked'
      stepErrors[1] = true
      return false
    }
    stepErrors[1] = false
  }

  if (currentStep.value === 2) {
    // Street line1, city, state, zip are required for addresses if filled
    const isBillingFilled = billingAddr.address_line1 || billingAddr.city || billingAddr.state || billingAddr.zip_code
    if (isBillingFilled) {
      if (!billingAddr.address_line1 || !billingAddr.city || !billingAddr.state || !billingAddr.zip_code) {
        validationErrorMsg.value = 'Billing Address requires Line 1, City, State, and ZIP'
        stepErrors[2] = true
        return false
      }
    }

    const isShippingFilled = shippingAddr.address_line1 || shippingAddr.city || shippingAddr.state || shippingAddr.zip_code
    if (isShippingFilled) {
      if (!shippingAddr.address_line1 || !shippingAddr.city || !shippingAddr.state || !shippingAddr.zip_code) {
        validationErrorMsg.value = 'Shipping Address requires Line 1, City, State, and ZIP'
        stepErrors[2] = true
        return false
      }
    }
    stepErrors[2] = false
  }

  if (currentStep.value === 3) {
    for (let i = 0; i < form.contacts.length; i++) {
      const c = form.contacts[i]
      if (!c.first_name) {
        validationErrorMsg.value = `Contact #${i + 1} requires a First Name`
        stepErrors[3] = true
        return false
      }
      if (!c.email) {
        validationErrorMsg.value = `Contact #${i + 1} requires an Email Address`
        stepErrors[3] = true
        return false
      }
    }
    stepErrors[3] = false
  }

  return true
}

function goNext() {
  if (validateCurrentStep()) {
    currentStep.value++
  }
}

async function save() {
  // Validate all steps
  const stepsToValidate = [0, 1, 2, 3]
  let allValid = true

  const originalStep = currentStep.value
  for (let s of stepsToValidate) {
    currentStep.value = s
    if (!validateCurrentStep()) {
      allValid = false
      break
    }
  }

  if (!allValid) {
    toast.error('Please resolve validation errors in the highlighted sections.')
    return
  }

  // Restore current step
  currentStep.value = originalStep

  saving.value = true
  try {
    syncTags()

    // Structure addresses
    const finalAddresses = []
    const isBillingFilled = billingAddr.address_line1 && billingAddr.city && billingAddr.state && billingAddr.zip_code
    if (isBillingFilled) {
      finalAddresses.push({ ...billingAddr, address_type: 'billing' })
    }

    const isShippingFilled = shippingAddr.address_line1 && shippingAddr.city && shippingAddr.state && shippingAddr.zip_code
    if (isShippingFilled) {
      finalAddresses.push({ ...shippingAddr, address_type: 'shipping' })
    }

    // Construct Payload
    const payload = {
      customer_code: form.customer_code || null,
      customer_name: form.customer_name,
      customer_type: form.customer_type,
      display_name: form.display_name,
      currency: form.currency,
      email: form.email || null,
      mobile: form.mobile || null,
      phone: form.phone || null,
      gst_registration_type: form.gst_registration_type,
      gstin: form.gstin || null,
      pan: form.pan || null,
      payment_terms: form.payment_terms || null,
      credit_limit: parseFloat(form.credit_limit) || 0,
      opening_balance: parseFloat(form.opening_balance) || 0,
      opening_balance_type: form.opening_balance_type,
      msme_status: form.msme_status,
      msme_registration_no: form.msme_status ? form.msme_registration_no : null,
      cin: form.cin || null,
      invoice_delivery_preference: form.invoice_delivery_preference,
      addresses: finalAddresses,
      contacts: form.contacts,
      custom_fields: form.custom_fields.filter(cf => cf.field_key && cf.field_value),
      tags: form.tags,
    }

    if (props.editing) {
      await store.update(props.editing.customer_id, payload)
      toast.success('Customer updated successfully')
    } else {
      await store.create(payload)
      toast.success('Customer created & balance posted successfully')
      localStorage.removeItem('optireach_customer_draft') // clear local storage draft
    }

    emit('saved')
    emit('close')
  } catch (err) {
    toast.error(err || 'Failed to save customer details')
  } finally {
    saving.value = false
  }
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
  justify-content: flex-end;
  align-items: stretch;
  z-index: 1000;
  animation: fadeIn 0.25s ease-out;
}

.drawer {
  width: min(850px, 100vw);
  background: #ffffff;
  box-shadow: -10px 0 40px rgba(15, 23, 42, 0.15);
  display: flex;
  flex-direction: column;
  height: 100%;
  animation: slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.header {
  padding: 16px 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.h {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.draft-alert {
  background: #fef3c7;
  color: #92400e;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.draft-action-btn {
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 2px 4px;
}

.draft-action-btn.restore {
  color: #d97706;
}

.draft-action-btn.discard {
  color: #b91c1c;
}

.draft-status-badge {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
}

.draft-status-badge.saved {
  color: #10b981;
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

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  border-right: 1px solid #e2e8f0;
  background: #f8fafc;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: none;
  background: transparent;
  border-radius: 8px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.tab-btn:hover {
  background: #f1f5f9;
}

.tab-btn.active {
  background: #eff6ff;
  color: #1a73e8;
  font-weight: 600;
}

.step-num {
  width: 20px;
  height: 20px;
  border-radius: 99px;
  background: #e2e8f0;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
}

.tab-btn.active .step-num {
  background: #1a73e8;
  color: #ffffff;
}

.step-label {
  font-size: 13px;
  color: #334155;
  white-space: nowrap;
}

.tab-btn.active .step-label {
  color: #1a73e8;
}

.err-dot {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: #ef4444;
  color: #fff;
  width: 16px;
  height: 16px;
  border-radius: 99px;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: #ffffff;
}

.form-section {
  animation: fadeIn 0.2s ease-out;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 20px;
  margin-top: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
}

.span2 {
  grid-column: span 2;
}

.divider {
  border-bottom: 1px solid #e2e8f0;
  height: 1px;
}

.flex-row {
  display: flex;
  flex-direction: row;
}

.justify-between {
  justify-content: space-between;
}

.align-center {
  align-items: center;
}

.align-end {
  align-items: flex-end;
}

.flex-1 {
  flex: 1;
}

.gap-12 {
  gap: 12px;
}

.margin-0 {
  margin: 0;
}

.margin-b-16 {
  margin-bottom: 16px;
}

.margin-b-12 {
  margin-bottom: 12px;
}

.margin-y-24 {
  margin-top: 24px;
  margin-bottom: 24px;
}

.label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 6px;
}

.required-label::after {
  content: ' *';
  color: #ef4444;
}

.input, .textarea {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  padding: 8px 12px;
  font-size: 13px;
  outline: none;
  background: #ffffff;
  color: #0f172a;
  transition: all 0.2s ease;
  box-sizing: border-box;
}

.input:focus, .textarea:focus {
  border-color: #1a73e8;
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.12);
}

.textarea {
  resize: vertical;
}

.h-38 {
  height: 38px;
}

.code-input {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
}

.radio-group {
  display: flex;
  gap: 16px;
  align-items: center;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
}

.gstin-container {
  position: relative;
  display: flex;
  align-items: center;
}

.gstin-input {
  padding-right: 70px;
}

.gstin-badge {
  position: absolute;
  right: 8px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
}

.gstin-badge.valid {
  background: #d1fae5;
  color: #065f46;
}

.gstin-badge.invalid {
  background: #fee2e2;
  color: #991b1b;
}

/* MSME toggle switch */
.msme-section {
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 16px;
}

.msme-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.msme-title-group {
  display: flex;
  flex-direction: column;
}

.msme-label {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.msme-desc {
  font-size: 11px;
  color: #64748b;
}

.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background-color: #cbd5e1;
  transition: .3s;
  border-radius: 24px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: .3s;
  border-radius: 50%;
}

input:checked + .slider {
  background-color: #1a73e8;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.msme-body {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed #cbd5e1;
}

/* Address layouts */
.address-layout {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.address-col {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  background: #f8fafc;
}

.address-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #cbd5e1;
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

/* Contact persons list */
.add-btn {
  background: #eff6ff;
  color: #1a73e8;
  border: 1px dashed #3b82f6;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-btn:hover {
  background: #dbeafe;
}

.empty-state {
  text-align: center;
  padding: 32px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px dashed #cbd5e1;
}

.empty-state p {
  color: #64748b;
  font-size: 13px;
  margin-bottom: 8px;
}

.contacts-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.contact-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.contact-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.contact-index {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
}

.remove-btn {
  background: #fee2e2;
  color: #b91c1c;
  border: none;
  width: 20px;
  height: 20px;
  border-radius: 99px;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-weight: 700;
}

.remove-btn:hover {
  background: #fca5a5;
}

.checkbox-container {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
}

.checkbox-label {
  font-size: 13px;
  color: #334155;
}

/* Alert boxes */
.alert-box {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.alert-icon {
  color: #1a73e8;
  font-size: 16px;
  font-weight: 700;
}

.alert-text {
  color: #1e3a8a;
  font-size: 12px;
  line-height: 1.4;
}

/* Custom fields lists */
.custom-fields-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cf-row {
  display: flex;
  align-items: center;
}

.cf-remove-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 20px;
  cursor: pointer;
}

.cf-remove-btn:hover {
  color: #ef4444;
}

/* Footer style */
.footer {
  padding: 16px 24px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
}

.footer-error-msg {
  color: #ef4444;
  font-size: 12px;
  font-weight: 600;
  margin-right: auto;
}

/* Transitions */
.fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

/* Mobile responsive */
@media (max-width: 768px) {
  .backdrop {
    align-items: flex-end;
  }
  .drawer {
    width: 100vw;
    height: 90vh;
    border-radius: 20px 20px 0 0;
    animation: slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .main-layout {
    flex-direction: column;
  }
  .sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    flex-direction: row;
    padding: 8px;
    gap: 8px;
    overflow-x: auto;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .span2 {
    grid-column: span 1;
  }
  .flex-row {
    flex-direction: column;
    gap: 12px;
  }
  .align-end {
    align-items: stretch;
  }
  .checkbox-container {
    margin-top: 0;
  }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
</style>
