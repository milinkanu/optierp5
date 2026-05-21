import api from './axios'

export const deliveryChallansApi = {
  async list() {
    const { data } = await api.get('/delivery-challans')
    return data
  },
  async get(challanId) {
    const { data } = await api.get(`/delivery-challans/${challanId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/delivery-challans', payload)
    return data
  },
  async pdf(challanId) {
    const { data } = await api.get(`/delivery-challans/${challanId}/pdf`, { responseType: 'blob' })
    return data
  },
  async convert(challanId) {
    const { data } = await api.post(`/delivery-challans/${challanId}/convert`)
    return data
  }
}
