import { defineStore } from 'pinia'
import { contactsApi } from '../api/contacts'

export const useContactsStore = defineStore('contacts', {
  state: () => ({
    items: [],
    loading: false,
    error: null,
  }),
  actions: {
    async fetchList(params = {}) {
      this.loading = true
      this.error = null
      try {
        const data = await contactsApi.list(params)
        this.items = data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const row = await contactsApi.create(payload)
      this.items = [row, ...this.items]
      return row
    },
    async update(contactId, payload) {
      const row = await contactsApi.update(contactId, payload)
      this.items = this.items.map((x) => (x.contact_id === row.contact_id ? row : x))
      return row
    },
    async importCsv(file) {
      return await contactsApi.importCsv(file)
    },
  },
})

