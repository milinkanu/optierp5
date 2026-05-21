import api from './axios'

export const paymentsApi = {
  async list() {
    const { data } = await api.get('/payments')
    return data
  },
  async get(paymentId) {
    const { data } = await api.get(`/payments/${paymentId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/payments', payload)
    return data
  },
  async pdf(paymentId) {
    const { data } = await api.get(`/payments/${paymentId}/pdf`, { responseType: 'blob' })
    return data
  }
}
