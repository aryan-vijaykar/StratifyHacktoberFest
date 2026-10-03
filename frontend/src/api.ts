import axios from 'axios'

const api = axios.create({ baseURL: '/api/v1' })

export const getDashboard   = () => api.get('/dashboard')
export const getHealth      = () => api.get('/business-health')
export const getAlerts      = () => api.get('/alerts')
export const getTimeline    = () => api.get('/timeline')
export const getRevenueForecast  = () => api.get('/forecast/revenue')
export const getCashflowForecast = () => api.get('/forecast/cashflow')
export const getDemandForecast   = () => api.get('/forecast/demand')
export const getCustomerRisk     = () => api.get('/risk/customers')
export const getSupplierRisk     = () => api.get('/risk/suppliers')
export const getPricing          = () => api.get('/pricing')
export const getAgents       = () => api.get('/agents')
export const getRecommendations  = () => api.get('/recommendations')
export const simulate = (data: object) => api.post('/simulate', data)
export const sendChat = (question: string) =>
  api.post('/ai/chat', { question })
export const getExecutiveBrief = () => api.get('/ai/executive-brief')
export const getDecisionHistory  = () => api.get('/decision-history')

// Materials API Endpoints
export const getMaterials = () => api.get('/materials')
export const getProducts = () => api.get('/business/products')
export const createMaterial = (data: object) => api.post('/materials', data)
export const updateMaterial = (id: number, data: object) => api.patch(`/materials/${id}`, data)
export const deleteMaterial = (id: number) => api.delete(`/materials/${id}`)
export const getMaterialPriceHistory = (id: number) => api.get(`/materials/price-history/${id}`)
export const createPriceHistory = (data: object) => api.post('/materials/price-history', data)
export const getMaterialForecast = (productId: number) => api.post('/materials/forecast', { product_id: productId })

// Supply Chain API Endpoints
export const getPurchaseOrders = () => api.get('/supply-chain/purchase-orders')
export const createPurchaseOrder = (data: object) => api.post('/supply-chain/purchase-orders', data)
export const getTransportLogs = () => api.get('/supply-chain/transport-logs')
export const createTransportLog = (data: object) => api.post('/supply-chain/transport-logs', data)
export const getShipmentMargins = () => api.get('/supply-chain/margins')

// Strategy Brief API Endpoints
export const getStrategyBrief = () => api.get('/recommendations/strategy')

// Raw Materials Buying Advice API
export const getMaterialBuyingAdvice = () => api.get('/materials/buying-advice')

export const uploadFile = (category: string, file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/upload/${category}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export const uploadSampleDoc = (sampleKey: string) =>
  api.post('/upload/sample', { sample_key: sampleKey })

export default api
