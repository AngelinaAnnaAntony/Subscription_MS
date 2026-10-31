import axios from 'axios'

export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach token from localStorage
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('brightloop_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor: handle 401 and extract error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response ? error.response.status : null
    
    // Auto logout & redirect on 401 Unauthorized if not already on login page
    if (status === 401) {
      localStorage.removeItem('brightloop_token')
      localStorage.removeItem('brightloop_user')
      if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
        window.location.href = '/login'
      }
    }

    const message =
      error.response?.data?.message ||
      error.response?.data?.error ||
      error.message ||
      'An unexpected error occurred. Please try again.'

    return Promise.reject(new Error(message))
  }
)

export const authAPI = {
  register: (data) => api.post('/auth/register', data).then((res) => res.data),
  login: (credentials) => api.post('/auth/login', credentials).then((res) => res.data),
  logout: () => api.post('/auth/logout').then((res) => res.data).catch(() => ({})),
  getMe: () => api.get('/auth/me').then((res) => res.data),
  updateMe: (data) => api.put('/auth/me', data).then((res) => res.data),
  requestPasswordReset: (email) => api.post('/auth/forgot-password', { email }).then((res) => res.data),
  resetPassword: (token, password) => api.post('/auth/reset-password', { token, password }).then((res) => res.data),
}

export const usersAPI = {
  list: (params) => api.get('/users', { params }).then((res) => res.data),
  create: (data) => api.post('/users', data).then((res) => res.data),
  getById: (id) => api.get(`/users/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/users/${id}`, data).then((res) => res.data),
  deactivate: (id) => api.delete(`/users/${id}`).then((res) => res.data),
}

export const productsAPI = {
  list: (params) => api.get('/products', { params }).then((res) => res.data),
  create: (data) => api.post('/products', data).then((res) => res.data),
  getById: (id) => api.get(`/products/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/products/${id}`, data).then((res) => res.data),
  deactivate: (id) => api.delete(`/products/${id}`).then((res) => res.data),
  getVariants: (productId) => api.get(`/products/${productId}/variants`).then((res) => res.data),
  addVariant: (productId, data) => api.post(`/products/${productId}/variants`, data).then((res) => res.data),
  updateVariant: (productId, variantId, data) => api.put(`/products/${productId}/variants/${variantId}`, data).then((res) => res.data),
  removeVariant: (productId, variantId) => api.delete(`/products/${productId}/variants/${variantId}`).then((res) => res.data),
}

export const plansAPI = {
  list: (params) => api.get('/plans', { params }).then((res) => res.data),
  create: (data) => api.post('/plans', data).then((res) => res.data),
  getById: (id) => api.get(`/plans/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/plans/${id}`, data).then((res) => res.data),
  deactivate: (id) => api.delete(`/plans/${id}`).then((res) => res.data),
}

export const quotationsAPI = {
  list: (params) => api.get('/quotations', { params }).then((res) => res.data),
  create: (data) => api.post('/quotations', data).then((res) => res.data),
  getById: (id) => api.get(`/quotations/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/quotations/${id}`, data).then((res) => res.data),
  confirm: (id) => api.post(`/quotations/${id}/confirm`).then((res) => res.data),
  convert: (id) => api.post(`/quotations/${id}/convert`).then((res) => res.data),
  overrideExpiry: (id, data) => api.post(`/quotations/${id}/override-expiry`, data).then((res) => res.data),
  getTemplates: () => api.get('/quotations/templates').then((res) => res.data),
  createTemplate: (data) => api.post('/quotations/templates', data).then((res) => res.data),
}

export const subscriptionsAPI = {
  list: (params) => api.get('/subscriptions', { params }).then((res) => res.data),
  create: (data) => api.post('/subscriptions', data).then((res) => res.data),
  getById: (id) => api.get(`/subscriptions/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/subscriptions/${id}`, data).then((res) => res.data),
  activate: (id) => api.post(`/subscriptions/${id}/activate`).then((res) => res.data),
  pause: (id) => api.post(`/subscriptions/${id}/pause`).then((res) => res.data),
  resume: (id) => api.post(`/subscriptions/${id}/resume`).then((res) => res.data),
  close: (id, data) => api.post(`/subscriptions/${id}/close`, data).then((res) => res.data),
  getInvoices: (id) => api.get(`/subscriptions/${id}/invoices`).then((res) => res.data),
  getMy: () => api.get('/subscriptions/my').then((res) => res.data),
}

export const billingAPI = {
  generate: (data) => api.post('/billing/generate', data).then((res) => res.data),
  generateDue: () => api.post('/billing/generate-due').then((res) => res.data),
  getDueToday: () => api.get('/billing/due-today').then((res) => res.data),
}

export const invoicesAPI = {
  list: (params) => api.get('/invoices', { params }).then((res) => res.data),
  getById: (id) => api.get(`/invoices/${id}`).then((res) => res.data),
  confirm: (id) => api.post(`/invoices/${id}/confirm`).then((res) => res.data),
  cancel: (id) => api.post(`/invoices/${id}/cancel`).then((res) => res.data),
  send: (id) => api.post(`/invoices/${id}/send`).then((res) => res.data),
  getMy: () => api.get('/invoices/my').then((res) => res.data),
  getOverdue: () => api.get('/invoices/overdue').then((res) => res.data),
}

export const taxesAPI = {
  list: (params) => api.get('/taxes', { params }).then((res) => res.data),
  create: (data) => api.post('/taxes', data).then((res) => res.data),
  update: (id, data) => api.put(`/taxes/${id}`, data).then((res) => res.data),
  deactivate: (id) => api.delete(`/taxes/${id}`).then((res) => res.data),
}

export const discountsAPI = {
  list: (params) => api.get('/discounts', { params }).then((res) => res.data),
  create: (data) => api.post('/discounts', data).then((res) => res.data),
  getById: (id) => api.get(`/discounts/${id}`).then((res) => res.data),
  update: (id, data) => api.put(`/discounts/${id}`, data).then((res) => res.data),
  deactivate: (id) => api.delete(`/discounts/${id}`).then((res) => res.data),
}

export const paymentsAPI = {
  list: (params) => api.get('/payments', { params }).then((res) => res.data),
  record: (data) => api.post('/payments', data).then((res) => res.data),
  getById: (id) => api.get(`/payments/${id}`).then((res) => res.data),
  getByInvoice: (invoiceId) => api.get(`/payments/invoice/${invoiceId}`).then((res) => res.data),
}

export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats').then((res) => res.data),
  getRecentPayments: () => api.get('/dashboard/recent-payments').then((res) => res.data),
  getUpcomingRenewals: () => api.get('/dashboard/upcoming-renewals').then((res) => res.data),
  getRevenueByPeriod: (params) => api.get('/dashboard/revenue', { params }).then((res) => res.data),
  getCustomerStats: () => api.get('/dashboard/customer-stats').then((res) => res.data),
}

export const radarAPI = {
  getAll: (params) => api.get('/radar', { params }).then((res) => res.data),
  getSummary: () => api.get('/radar/summary').then((res) => res.data),
  getOne: (id) => api.get(`/radar/${id}`).then((res) => res.data),
  recalculate: () => api.post('/radar/recalculate').then((res) => res.data),
}

export default api
