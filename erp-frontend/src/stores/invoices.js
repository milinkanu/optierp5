import { defineStore } from 'pinia'
import { invoicesApi } from '../api/invoices'

export const useInvoicesStore = defineStore('invoices', {
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
        const data = await invoicesApi.list(params)
        this.items = data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload, opts = {}) {
      const row = await invoicesApi.create(payload, opts)
      this.items = [row, ...this.items]
      return row
    },
    async post(invoiceId, opts = {}) {
      const row = await invoicesApi.post(invoiceId, opts)
      this.items = this.items.map((x) => (x.invoice_id === row.invoice_id ? row : x))
      return row
    },
    async remove(invoiceId) {
      await invoicesApi.remove(invoiceId)
      this.items = this.items.filter((x) => x.invoice_id !== invoiceId)
    },
  },
})

