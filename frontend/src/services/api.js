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
  saveManualCashFlows: (propertyId, payload) =>
    api.put(`/properties/${propertyId}/manual-cash-flows`, payload),
  getManualCashFlows: (propertyId) => api.get(`/properties/${propertyId}/manual-cash-flows`),
  getTypes: (portfolioId = null) => {
    const url = portfolioId ? `/properties/types?portfolio_id=${portfolioId}` : '/properties/types'
    return api.get(url)
  }
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

export const propertyOwnershipAPI = {
  getAll: (propertyId) => api.get(`/properties/${propertyId}/ownership-events`),
  create: (propertyId, data) => api.post(`/properties/${propertyId}/ownership-events`, data),
  delete: (propertyId, eventId) => api.delete(`/properties/${propertyId}/ownership-events/${eventId}`)
}

// Cash Flow API
export const cashFlowAPI = {
  getAll: (filters = {}) => {
    const params = new URLSearchParams()

    if (typeof filters === 'number' || typeof filters === 'string') {
      if (filters) {
        params.append('portfolio_id', filters)
      }
    } else if (filters && typeof filters === 'object') {
      const { portfolioId, propertyId, loanId } = filters
      if (portfolioId) params.append('portfolio_id', portfolioId)
      if (propertyId) params.append('property_id', propertyId)
      if (loanId) params.append('loan_id', loanId)
    }

    const query = params.toString()
    const url = query ? `/cash-flows?${query}` : '/cash-flows'
    return api.get(url)
  },
  getById: (id) => api.get(`/cash-flows/${id}`),
  create: (data) => api.post('/cash-flows', data),
  update: (id, data) => api.put(`/cash-flows/${id}`, data),
  delete: (id) => api.delete(`/cash-flows/${id}`),
  downloadReport: (portfolioId) =>
    api.get(`/cash-flows/export?portfolio_id=${portfolioId}`, { responseType: 'blob' }),
  downloadReportWithProperties: (portfolioId) =>
    api.get(`/cash-flows/export?portfolio_id=${portfolioId}`, { responseType: 'blob' }),
  getPerformance: (portfolioId, applyOwnership = false) =>
    api.get(`/cash-flows/performance?portfolio_id=${portfolioId}&apply_ownership=${applyOwnership ? 1 : 0}`),
}

export const covenantAPI = {
  getMetrics: (portfolioId, applyOwnership = false) =>
    api.get(`/covenants?portfolio_id=${portfolioId}&apply_ownership=${applyOwnership ? 1 : 0}`)
}

// Property Type Exposure API
export const propertyTypeExposureAPI = {
  getExposure: (portfolioId) =>
    api.get(`/portfolios/${portfolioId}/property-type-exposure`),
  downloadExcel: (portfolioId) =>
    api.get(`/portfolios/${portfolioId}/property-type-exposure/export`, { responseType: 'blob' })
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
