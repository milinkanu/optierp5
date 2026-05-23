import api from './axios'

export const customersApi = {
  async list({ page = 1, limit = 25, q = '', is_active = null } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (is_active !== null) params.is_active = is_active
    const { data } = await api.get('/customers', { params })
    return data
  },
  async get(customerId) {
    const { data } = await api.get(`/customers/${customerId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/customers', payload)
    return data
  },
  async update(customerId, payload) {
    const { data } = await api.put(`/customers/${customerId}`, payload)
    return data
  },
  async delete(customerId) {
    const { data } = await api.delete(`/customers/${customerId}`)
    return data
  },
  async validateGstin(gstin) {
    const { data } = await api.post('/customers/validate-gstin', { gstin })
    return data
  },
  async prefillGstin(gstin) {
    const { data } = await api.post('/customers/prefill-gstin', { gstin })
    return data
  },
  async importCsv(file, mapping) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/customers/import', form, {
      params: { mapping: JSON.stringify(mapping) },
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}
