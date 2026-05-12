import { defineStore } from 'pinia'
import { chartOfAccountsApi } from '../api/chartOfAccounts'

export const useChartOfAccountsStore = defineStore('chartOfAccounts', {
  state: () => ({
    items: [],
    loading: false,
    error: null,
  }),
  actions: {
    async seed() {
      return await chartOfAccountsApi.seed()
    },
    async fetchList(params = {}) {
      this.loading = true
      this.error = null
      try {
        const data = await chartOfAccountsApi.list(params)
        this.items = data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const row = await chartOfAccountsApi.create(payload)
      this.items = [row, ...this.items]
      return row
    },
    async update(accountId, payload) {
      const row = await chartOfAccountsApi.update(accountId, payload)
      this.items = this.items.map((x) => (x.account_id === row.account_id ? row : x))
      return row
    },
    async deactivate(accountId) {
      await chartOfAccountsApi.deactivate(accountId)
      this.items = this.items.map((x) => (x.account_id === accountId ? { ...x, is_active: false } : x))
    },
  },
})

