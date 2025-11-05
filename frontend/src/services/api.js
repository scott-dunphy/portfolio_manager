import axios from 'axios'

const API_BASE_URL = 'http://localhost:5000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Portfolio API
export const portfolioAPI = {
  getAll: () => api.get('/portfolios'),
  getById: (id) => api.get(`/portfolios/${id}`),
  create: (data) => api.post('/portfolios', data),
  update: (id, data) => api.put(`/portfolios/${id}`, data),
  delete: (id) => api.delete(`/portfolios/${id}`),
}

// Property API
export const propertyAPI = {
  getAll: (portfolioId = null) => {
    const url = portfolioId ? `/properties?portfolio_id=${portfolioId}` : '/properties'
    return api.get(url)
  },
  getById: (id) => api.get(`/properties/${id}`),
  create: (data) => api.post('/properties', data),
  update: (id, data) => api.put(`/properties/${id}`, data),
  delete: (id) => api.delete(`/properties/${id}`),
}

// Loan API
export const loanAPI = {
  getAll: (portfolioId = null) => {
    const url = portfolioId ? `/loans?portfolio_id=${portfolioId}` : '/loans'
    return api.get(url)
  },
  getById: (id) => api.get(`/loans/${id}`),
  create: (data) => api.post('/loans', data),
  update: (id, data) => api.put(`/loans/${id}`, data),
  delete: (id) => api.delete(`/loans/${id}`),
}

// Preferred Equity API
export const preferredEquityAPI = {
  getAll: (portfolioId = null) => {
    const url = portfolioId ? `/preferred-equities?portfolio_id=${portfolioId}` : '/preferred-equities'
    return api.get(url)
  },
  getById: (id) => api.get(`/preferred-equities/${id}`),
  create: (data) => api.post('/preferred-equities', data),
  update: (id, data) => api.put(`/preferred-equities/${id}`, data),
  delete: (id) => api.delete(`/preferred-equities/${id}`),
}

// Cash Flow API
export const cashFlowAPI = {
  getAll: (portfolioId = null) => {
    const url = portfolioId ? `/cash-flows?portfolio_id=${portfolioId}` : '/cash-flows'
    return api.get(url)
  },
  getById: (id) => api.get(`/cash-flows/${id}`),
  create: (data) => api.post('/cash-flows', data),
  update: (id, data) => api.put(`/cash-flows/${id}`, data),
  delete: (id) => api.delete(`/cash-flows/${id}`),
}

// Upload API
export const uploadAPI = {
  uploadExcel: (file, portfolioId) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('portfolio_id', portfolioId)
    return api.post('/upload/excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  downloadTemplate: () => api.get('/upload/template', { responseType: 'blob' }),
}

export default api
