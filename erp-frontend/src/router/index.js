import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AuthLayout from '../layouts/AuthLayout.vue'
import DashboardLayout from '../layouts/DashboardLayout.vue'
import LoginView from '../views/auth/LoginView.vue'
import SignupView from '../views/auth/SignupView.vue'
import ForgotPasswordView from '../views/auth/ForgotPasswordView.vue'
import ResetPasswordView from '../views/auth/ResetPasswordView.vue'
import VerifyEmailView from '../views/auth/VerifyEmailView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'
import ChartOfAccountsView from '../views/accountant/ChartOfAccountsView.vue'
import ContactsView from '../views/contacts/ContactsView.vue'
import InvoicesListView from '../views/sales/InvoicesListView.vue'
import InvoiceCreateView from '../views/sales/InvoiceCreateView.vue'
import InvoiceDetailView from '../views/sales/InvoiceDetailView.vue'
import ItemsView from '../views/items/ItemsView.vue'

const routes = [
  {
    path: '/auth',
    component: AuthLayout,
    children: [
      { path: 'login', name: 'Login', component: LoginView, meta: { guest: true } },
      { path: 'signup', name: 'Signup', component: SignupView, meta: { guest: true } },
      { path: 'forgot-password', name: 'ForgotPassword', component: ForgotPasswordView, meta: { guest: true } },
      { path: 'reset-password', name: 'ResetPassword', component: ResetPasswordView, meta: { guest: true } },
      { path: 'verify-email', name: 'VerifyEmail', component: VerifyEmailView, meta: { guest: true } },
    ],
  },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'Dashboard', component: DashboardView },
      { path: 'accountant/chart-of-accounts', name: 'ChartOfAccounts', component: ChartOfAccountsView },
      { path: 'contacts', name: 'Contacts', component: ContactsView },
      { path: 'sales/invoices', name: 'Invoices', component: InvoicesListView },
      { path: 'sales/invoices/new', name: 'InvoiceNew', component: InvoiceCreateView },
      { path: 'sales/invoices/:invoiceId', name: 'InvoiceDetail', component: InvoiceDetailView },
      { path: 'items', name: 'Items', component: ItemsView },
    ],
  },
  {
    path: '/index.html',
    redirect: '/',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'Login' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from) => {
  const auth = useAuthStore()
  if (!auth.accessToken) {
    auth.initialize()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'Login' }
  }

  if (to.meta.guest && auth.isAuthenticated) {
    return { name: 'Dashboard' }
  }

  return true
})

export default router
