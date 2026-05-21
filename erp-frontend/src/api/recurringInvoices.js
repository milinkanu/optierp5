import api from './axios'

export const recurringInvoicesApi = {
  async list() {
    const { data } = await api.get('/recurring-invoices')
    return data
  },
  async get(profileId) {
    const { data } = await api.get(`/recurring-invoices/${profileId}`)
    return data
  },
  async create(payload) {
    const { data } = await api.post('/recurring-invoices', payload)
    return data
  },
  async updateStatus(profileId, statusVal) {
    const { data } = await api.put(`/recurring-invoices/${profileId}/status`, null, {
      params: { status_val: statusVal }
    })
    return data
  },
  async trigger(profileId, runDate = null) {
    const params = {}
    if (runDate) params.run_date = runDate
    const { data } = await api.post(`/recurring-invoices/${profileId}/trigger`, null, { params })
    return data
  },
  async logs(profileId) {
    const { data } = await api.get(`/recurring-invoices/${profileId}/logs`)
    return data
  }
}
