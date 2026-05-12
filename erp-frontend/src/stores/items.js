import { defineStore } from 'pinia'
import { itemsApi } from '../api/items'

// Centralized item state so invoices and item master reuse the same in-memory list.
export const useItemsStore = defineStore('items', {
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
        const data = await itemsApi.list(params)
        this.items = data
      } catch (error) {
        this.error = error
        throw error
      } finally {
        this.loading = false
      }
    },
    async create(payload) {
      const created = await itemsApi.create(payload)
      this.items = [created, ...this.items]
      return created
    },
    async update(itemId, payload) {
      const updated = await itemsApi.update(itemId, payload)
      this.items = this.items.map((it) => (it.inventory_item_id === itemId ? updated : it))
      return updated
    },
    async deactivate(itemId) {
      await itemsApi.deactivate(itemId)
      this.items = this.items.map((it) => (it.inventory_item_id === itemId ? { ...it, is_active: false } : it))
    },
  },
})

