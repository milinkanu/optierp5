import { defineStore } from 'pinia'
import { customersApi } from '../api/customers'

export const useCustomersStore = defineStore('customers', {
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
        const data = await customersApi.list(params)
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
        const row = await customersApi.create(payload)
        this.items = [row, ...this.items]
        return row
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async update(customerId, payload) {
      this.loading = true
      this.error = null
      try {
        const row = await customersApi.update(customerId, payload)
        this.items = this.items.map((x) => (x.customer_id === row.customer_id ? row : x))
        return row
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async delete(customerId) {
      this.loading = true
      this.error = null
      try {
        await customersApi.delete(customerId)
        this.items = this.items.filter((x) => x.customer_id !== customerId)
      } catch (e) {
        this.error = e.response?.data?.detail || e.message
        throw e
      } finally {
        this.loading = false
      }
    },
    async validateGstin(gstin) {
      try {
        return await customersApi.validateGstin(gstin)
      } catch (e) {
        throw e.response?.data?.detail || e.message
      }
    },
    async prefillGstin(gstin) {
      try {
        return await customersApi.prefillGstin(gstin)
      } catch (e) {
        throw e.response?.data?.detail || e.message
      }
    },
    async importCsv(file, mapping) {
      this.loading = true
      this.error = null
      try {
        const report = await customersApi.importCsv(file, mapping)
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
