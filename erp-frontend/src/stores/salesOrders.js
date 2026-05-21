import { defineStore } from 'pinia'
import { salesOrdersApi } from '../api/salesOrders'

export const useSalesOrdersStore = defineStore('salesOrders', {
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
        const data = await salesOrdersApi.list(params)
        this.items = data
      } catch (e) {
        this.error = e
        throw e
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const row = await salesOrdersApi.create(payload)
      this.items = [row, ...this.items]
      return row
    },
    async update(salesOrderId, payload) {
      const row = await salesOrdersApi.update(salesOrderId, payload)
      this.items = this.items.map((x) => (x.sales_order_id === row.sales_order_id ? row : x))
      return row
    },
    async remove(salesOrderId) {
      await salesOrdersApi.remove(salesOrderId)
      this.items = this.items.filter((x) => x.sales_order_id !== salesOrderId)
    },
  },
})
