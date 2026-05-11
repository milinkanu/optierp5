import api from './axios'

export const authApi = {
  login(credentials) {
    return api.post('/auth/login', credentials)
  },
  signup(payload) {
    return api.post('/auth/signup', payload)
  },
  refresh(refreshToken) {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  },
  logout(refreshToken) {
    return api.post('/auth/logout', { refresh_token: refreshToken })
  },
  forgotPassword(data) {
    return api.post('/auth/forgot-password', data)
  },
  resetPassword(data) {
    return api.post('/auth/reset-password', data)
  },
  verifyEmail(token) {
    return api.get('/auth/verify-email', { params: { token } })
  },
  me() {
    return api.get('/auth/me')
  },
}
