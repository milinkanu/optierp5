import api from './axios'

export const salesOrdersApi = {
  async list({ page = 1, limit = 25, q = '', status = '' } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (status) params.status = status
    const { data } = await api.get('/sales-orders', { params })
    return data
  },
  async get(salesOrderId) {
    const { data } = await api.get(`/sales-orders/${salesOrderId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/sales-orders', payload)
    return data
  },
  async update(salesOrderId, payload) {
    const { data } = await api.patch(`/sales-orders/${salesOrderId}`, payload)
    return data
  },
  async remove(salesOrderId) {
    const { data } = await api.delete(`/sales-orders/${salesOrderId}`)
    return data
  },
  async convertToInvoice(salesOrderId) {
    const { data } = await api.post(`/sales-orders/${salesOrderId}/convert-invoice`)
    return data
  },
}
