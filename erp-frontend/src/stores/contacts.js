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
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      this.loading = true
      this.error = null
      try {
        const row = await contactsApi.create(payload)
        this.items = [row, ...this.items]
        return row
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async update(contactId, payload) {
      this.loading = true
      this.error = null
      try {
        const row = await contactsApi.update(contactId, payload)
        this.items = this.items.map((x) => (x.contact_id === row.contact_id ? row : x))
        return row
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async delete(contactId) {
      this.loading = true
      this.error = null
      try {
        await contactsApi.delete(contactId)
        this.items = this.items.filter((x) => x.contact_id !== contactId)
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async validateGstin(gstin) {
      try {
        return await contactsApi.validateGstin(gstin)
      } catch (e) {
        throw e.response?.data?.detail || e.message
      }
    },
    async prefillGstin(gstin) {
      try {
        return await contactsApi.prefillGstin(gstin)
      } catch (e) {
        throw e.response?.data?.detail || e.message
      }
    },
    async importCsv(file) {
      this.loading = true
      this.error = null
      try {
        const report = await contactsApi.importCsv(file)
        return report
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
  },
})
