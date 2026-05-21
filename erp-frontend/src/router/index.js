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
import QuotesListView from '../views/sales/QuotesListView.vue'
import QuoteCreateView from '../views/sales/QuoteCreateView.vue'
import QuoteDetailView from '../views/sales/QuoteDetailView.vue'
import SalesOrdersListView from '../views/sales/SalesOrdersListView.vue'
import SalesOrderCreateView from '../views/sales/SalesOrderCreateView.vue'
import SalesOrderDetailView from '../views/sales/SalesOrderDetailView.vue'
import ItemsView from '../views/items/ItemsView.vue'
import RecurringInvoicesView from '../views/sales/RecurringInvoicesView.vue'
import RecurringInvoiceCreateView from '../views/sales/RecurringInvoiceCreateView.vue'
import DeliveryChallansView from '../views/sales/DeliveryChallansView.vue'
import DeliveryChallanCreateView from '../views/sales/DeliveryChallanCreateView.vue'
import PaymentsReceivedView from '../views/sales/PaymentsReceivedView.vue'
import PaymentReceivedDetailView from '../views/sales/PaymentReceivedDetailView.vue'


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
      { path: 'sales/quotes', name: 'Quotes', component: QuotesListView },
      { path: 'sales/quotes/new', name: 'QuoteNew', component: QuoteCreateView },
      { path: 'sales/quotes/:quoteId', name: 'QuoteDetail', component: QuoteDetailView },
      { path: 'sales/quotes/:quoteId/edit', name: 'QuoteEdit', component: QuoteCreateView },
      { path: 'sales/orders', name: 'SalesOrders', component: SalesOrdersListView },
      { path: 'sales/orders/new', name: 'SalesOrderNew', component: SalesOrderCreateView },
      { path: 'sales/orders/:salesOrderId', name: 'SalesOrderDetail', component: SalesOrderDetailView },
      { path: 'sales/orders/:salesOrderId/edit', name: 'SalesOrderEdit', component: SalesOrderCreateView },
      { path: 'items', name: 'Items', component: ItemsView },
      { path: 'sales/recurring-invoices', name: 'RecurringInvoices', component: RecurringInvoicesView },
      { path: 'sales/recurring-invoices/new', name: 'RecurringInvoiceNew', component: RecurringInvoiceCreateView },
      { path: 'sales/delivery-challans', name: 'DeliveryChallans', component: DeliveryChallansView },
      { path: 'sales/delivery-challans/new', name: 'DeliveryChallanNew', component: DeliveryChallanCreateView },
      { path: 'sales/payments-received', name: 'PaymentsReceived', component: PaymentsReceivedView },
      { path: 'sales/payments-received/:paymentId', name: 'PaymentReceivedDetail', component: PaymentReceivedDetailView },
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
