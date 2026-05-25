import api from './axios'

export const contactsApi = {
  async list({ page = 1, limit = 25, q = '', is_active = null } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (is_active !== null) params.is_active = is_active
    const { data } = await api.get('/contacts', { params })
    return data
  },
  async get(contactId) {
    const { data } = await api.get(`/contacts/${contactId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/contacts', payload)
    return data
  },
  async update(contactId, payload) {
    const { data } = await api.patch(`/contacts/${contactId}`, payload)
    return data
  },
  async delete(contactId) {
    const { data } = await api.delete(`/contacts/${contactId}`)
    return data
  },
  async importCsv(file) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/contacts/import-csv', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  async validateGstin(gstin) {
    const { data } = await api.post('/contacts/validate-gstin', { gstin })
    return data
  },
  async prefillGstin(gstin) {
    const { data } = await api.post('/contacts/prefill-gstin', { gstin })
    return data
  },
}
