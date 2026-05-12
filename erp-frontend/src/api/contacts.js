import api from './axios'

export const contactsApi = {
  async list({ page = 1, limit = 25, q = '', contact_type = '' } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (contact_type) params.contact_type = contact_type
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
  async importCsv(file) {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/contacts/import-csv', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
}

