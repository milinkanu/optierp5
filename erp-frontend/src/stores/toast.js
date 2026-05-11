import { defineStore } from 'pinia'

export const useToastStore = defineStore('toast', {
  state: () => ({
    message: null,
    type: 'info',
    visible: false,
  }),
  actions: {
    show(message, type = 'info') {
      this.message = message
      this.type = type
      this.visible = true
      setTimeout(() => {
        this.visible = false
      }, 4000)
    },
  },
})
