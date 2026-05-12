import api from './axios'

// Items API wrapper used by item master screens and invoice item picker.
export const itemsApi = {
  async list({ page = 1, limit = 25, q = '', is_active = undefined, item_type = '' } = {}) {
    const params = { page, limit }
    if (q) params.q = q
    if (is_active !== undefined) params.is_active = is_active
    if (item_type) params.item_type = item_type
    const { data } = await api.get('/items', { params })
    return data
  },
  async create(payload) {
    const { data } = await api.post('/items', payload)
    return data
  },
  async update(itemId, payload) {
    const { data } = await api.patch(`/items/${itemId}`, payload)
    return data
  },
  async deactivate(itemId) {
    const { data } = await api.delete(`/items/${itemId}`)
    return data
  },
}

