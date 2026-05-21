import api from './axios'

export const invoicesApi = {
  async list({ page = 1, limit = 25, invoice_type = '' } = {}) {
    const params = { page, limit }
    if (invoice_type) params.invoice_type = invoice_type
    const { data } = await api.get('/invoices', { params })
    return data
  },
  async get(invoiceId) {
    const { data } = await api.get(`/invoices/${invoiceId}`)
    return data
  },
  async create(payload, { idempotencyKey } = {}) {
    const headers = {}
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
    const { data } = await api.post('/invoices', payload, { headers })
    return data
  },
  async post(invoiceId, { idempotencyKey } = {}) {
    const headers = {}
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey
    const { data } = await api.post(`/invoices/${invoiceId}/post`, null, { headers })
    return data
  },
  async remove(invoiceId) {
    const { data } = await api.delete(`/invoices/${invoiceId}`)
    return data
  },
  async pdf(invoiceId) {
    const { data } = await api.get(`/invoices/${invoiceId}/pdf`, { responseType: 'blob' })
    return data
  },
  async recordPayment(invoiceId, payload) {
    const { data } = await api.post(`/invoices/${invoiceId}/record-payment`, payload)
    return data
  },
  async getPayments(invoiceId) {
    const { data } = await api.get(`/invoices/${invoiceId}/payments`)
    return data
  },
}

