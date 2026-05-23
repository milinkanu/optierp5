import api from './axios'

export const creditNotesApi = {
  async list() {
    const { data } = await api.get('/credit-notes')
    return data
  },
  async get(creditNoteId) {
    const { data } = await api.get(`/credit-notes/${creditNoteId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/credit-notes', payload)
    return data
  },
  async update(creditNoteId, payload) {
    const { data } = await api.put(`/credit-notes/${creditNoteId}`, payload)
    return data
  },
  async remove(creditNoteId) {
    const { data } = await api.delete(`/credit-notes/${creditNoteId}`)
    return data
  },
  async applyToInvoice(creditNoteId, payload) {
    const { data } = await api.post(`/credit-notes/${creditNoteId}/apply-to-invoice`, payload)
    return data
  },
  async activities(creditNoteId) {
    const { data } = await api.get(`/credit-notes/${creditNoteId}/activities`)
    return data
  },
  async mappings(creditNoteId) {
    const { data } = await api.get(`/credit-notes/${creditNoteId}/mappings`)
    return data
  },
  async pdf(creditNoteId) {
    const { data } = await api.get(`/credit-notes/${creditNoteId}/pdf`, { responseType: 'blob' })
    return data
  },
}
