import { defineStore } from 'pinia'
import { authApi } from '../api/auth'

const STORAGE_KEY = 'finops_auth_state'

function loadStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveStorage(state) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: null,
    refreshToken: null,
    user: null,
    isLoading: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken && state.user),
  },
  actions: {
    initialize() {
      const stored = loadStorage()
      this.accessToken = stored.accessToken || null
      this.refreshToken = stored.refreshToken || null
      this.user = stored.user || null
    },
    setSession({ access_token, refresh_token, user }) {
      this.accessToken = access_token
      this.refreshToken = refresh_token
      this.user = user || this.user
      saveStorage({ accessToken: this.accessToken, refreshToken: this.refreshToken, user: this.user })
    },
    clearSession() {
      this.accessToken = null
      this.refreshToken = null
      this.user = null
      localStorage.removeItem(STORAGE_KEY)
    },
    async login(payload) {
      this.isLoading = true
      try {
        const response = await authApi.login(payload)
        const { access_token, refresh_token } = response.data
        this.setSession({ access_token, refresh_token })
        await this.fetchProfile()
        return response
      } finally {
        this.isLoading = false
      }
    },
    async signup(payload) {
      this.isLoading = true
      try {
        const response = await authApi.signup(payload)
        const { access_token, refresh_token } = response.data
        this.setSession({ access_token, refresh_token })
        await this.fetchProfile()
        return response
      } finally {
        this.isLoading = false
      }
    },
    async refreshToken() {
      if (!this.refreshToken) {
        throw new Error('No refresh token available')
      }
      const response = await authApi.refresh(this.refreshToken)
      const { access_token, refresh_token } = response.data
      this.setSession({ access_token, refresh_token })
      return response.data
    },
    async logout() {
      try {
        await authApi.logout(this.refreshToken)
      } catch {
        // ignore network errors on logout
      }
      this.clearSession()
    },
    async fetchProfile() {
      try {
        const response = await authApi.me()
        this.user = response.data
        saveStorage({ accessToken: this.accessToken, refreshToken: this.refreshToken, user: this.user })
        return response
      } catch {
        this.clearSession()
        throw new Error('Unable to fetch profile')
      }
    },
  },
})
