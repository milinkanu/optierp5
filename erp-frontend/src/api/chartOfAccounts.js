import api from './axios'

export const chartOfAccountsApi = {
  async seed() {
    const { data } = await api.post('/chart-of-accounts/seed')
    return data
  },
  async list({ page = 1, limit = 25, q = '', is_active = undefined } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (is_active !== undefined) params.is_active = is_active
    const { data } = await api.get('/chart-of-accounts', { params })
    return data
  },
  async get(accountId) {
    const { data } = await api.get(`/chart-of-accounts/${accountId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/chart-of-accounts', payload)
    return data
  },
  async update(accountId, payload) {
    const { data } = await api.patch(`/chart-of-accounts/${accountId}`, payload)
    return data
  },
  async deactivate(accountId) {
    const { data } = await api.delete(`/chart-of-accounts/${accountId}`)
    return data
  },
}

