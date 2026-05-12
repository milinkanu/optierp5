<template>
  <div class="page">
    <PageHeader :title="invoice ? invoice.invoice_number : 'Invoice'" subtitle="Details and PDF preview.">
      <template #actions>
        <Button variant="secondary" @click="$router.push({ name: 'Invoices' })">Back</Button>
        <Button variant="secondary" :disabled="!invoice" @click="openPdf">Open PDF</Button>
        <Button v-if="invoice?.status === 'draft'" :disabled="posting" :loading="posting" @click="postInvoice">Post</Button>
        <Button v-if="invoice?.status === 'draft'" variant="danger" :disabled="deleting" :loading="deleting" @click="remove">Delete</Button>
      </template>
    </PageHeader>

    <Card class="card">
      <div v-if="loading" class="muted">Loading…</div>
      <div v-else-if="!invoice" class="muted">Invoice not found.</div>
      <div v-else class="grid">
        <div class="kv"><div class="k">Type</div><div class="v pill">{{ invoice.invoice_type }}</div></div>
        <div class="kv"><div class="k">Status</div><div class="v">{{ invoice.status }}</div></div>
        <div class="kv"><div class="k">Total</div><div class="v mono">₹{{ fmt(invoice.invoice_grand_total) }}</div></div>
        <div class="kv"><div class="k">Paid</div><div class="v mono">₹{{ fmt(invoice.paid_amount) }}</div></div>
        <div class="kv"><div class="k">Balance</div><div class="v mono">₹{{ fmt(invoice.balance_due) }}</div></div>
        <div class="kv"><div class="k">Created</div><div class="v">{{ fmtDate(invoice.created_at) }}</div></div>
      </div>
    </Card>

    <Card class="card pdf">
      <div class="pdf-head">
        <div class="muted">Inline PDF preview</div>
      </div>
      <iframe v-if="pdfUrl" class="frame" :src="pdfUrl" title="Invoice PDF" />
      <div v-else class="muted">Load the PDF using “Open PDF”.</div>
    </Card>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useToastStore } from '../../stores/toast'
import { invoicesApi } from '../../api/invoices'
import Button from '../../components/ui/Button.vue'
import Card from '../../components/ui/Card.vue'
import PageHeader from '../../components/ui/PageHeader.vue'

const route = useRoute()
const toast = useToastStore()

const loading = ref(false)
const invoice = ref(null)
const pdfUrl = ref('')
const posting = ref(false)
const deleting = ref(false)

const fmt = (n) => Number(n || 0).toFixed(2)
const fmtDate = (d) => (d ? new Date(d).toLocaleString() : '—')

const load = async () => {
  loading.value = true
  try {
    invoice.value = await invoicesApi.get(route.params.invoiceId)
  } catch (e) {
    invoice.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

const openPdf = async () => {
  try {
    const blob = await invoicesApi.pdf(route.params.invoiceId)
    const url = URL.createObjectURL(blob)
    if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
    pdfUrl.value = url
    window.open(url, '_blank', 'noopener,noreferrer')
  } catch (e) {
    toast.error('Failed to load PDF')
  }
}

const postInvoice = async () => {
  posting.value = true
  try {
    const key = crypto.randomUUID()
    invoice.value = await invoicesApi.post(route.params.invoiceId, { idempotencyKey: key })
    toast.success('Invoice posted')
  } catch (e) {
    toast.error('Post failed')
  } finally {
    posting.value = false
  }
}

const remove = async () => {
  if (!confirm('Delete (soft-delete) this invoice?')) return
  deleting.value = true
  try {
    await invoicesApi.remove(route.params.invoiceId)
    toast.success('Invoice deleted')
    history.back()
  } catch (e) {
    toast.error('Delete failed')
  } finally {
    deleting.value = false
  }
}

onBeforeUnmount(() => {
  if (pdfUrl.value) URL.revokeObjectURL(pdfUrl.value)
})
</script>

<style scoped>
.page {
  max-width: 1200px;
  margin: 0 auto;
}
.card {
  padding: 14px;
  margin-bottom: 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.kv {
  background: #f9fafb;
  border: 1px solid #eef2f7;
  border-radius: 12px;
  padding: 10px;
}
.k {
  font-size: 12px;
  color: #6b7280;
  font-weight: 700;
  margin-bottom: 6px;
}
.v {
  font-size: 13px;
  color: #111827;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
}
.pill {
  text-transform: lowercase;
}
.muted {
  color: #6b7280;
}
.pdf {
  padding: 0;
}
.pdf-head {
  padding: 12px 14px;
  border-bottom: 1px solid #eef2f7;
}
.frame {
  width: 100%;
  height: 75vh;
  border: none;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>

