import { defineStore } from 'pinia'
import { quotesApi } from '../api/quotes'

export const useQuotesStore = defineStore('quotes', {
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
        const data = await quotesApi.list(params)
        this.items = data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const row = await quotesApi.create(payload)
      this.items = [row, ...this.items]
      return row
    },
    async update(quoteId, payload) {
      const row = await quotesApi.update(quoteId, payload)
      this.items = this.items.map((x) => (x.quote_id === row.quote_id ? row : x))
      return row
    },
    async remove(quoteId) {
      await quotesApi.remove(quoteId)
      this.items = this.items.filter((x) => x.quote_id !== quoteId)
    },
  },
})
