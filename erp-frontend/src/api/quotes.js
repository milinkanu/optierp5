import api from './axios'

export const quotesApi = {
  async list({ page = 1, limit = 25, q = '', status = '' } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (status) params.status = status
    const { data } = await api.get('/quotes', { params })
    return data
  },
  async get(quoteId) {
    const { data } = await api.get(`/quotes/${quoteId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/quotes', payload)
    return data
  },
  async update(quoteId, payload) {
    const { data } = await api.patch(`/quotes/${quoteId}`, payload)
    return data
  },
  async remove(quoteId) {
    const { data } = await api.delete(`/quotes/${quoteId}`)
    return data
  },
  async convertToSalesOrder(quoteId) {
    const { data } = await api.post(`/quotes/${quoteId}/convert-so`)
    return data
  },
  async convertToInvoice(quoteId) {
    const { data } = await api.post(`/quotes/${quoteId}/convert-invoice`)
    return data
  },
}
