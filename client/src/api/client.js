import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const sendMessage = (message, sessionId, hcpId, draft, history) =>
  api.post('/api/chat', {
    message,
    session_id: sessionId,
    hcp_id: hcpId ?? null,
    interaction_draft: draft ?? {},
    history: history ?? [],
  })

export const getHCPs = () => api.get('/api/hcp')

export const searchHCPs = (q) =>
  api.get('/api/hcp/search', {
    params: { q },
  })

export const getHCPProfile = (id) => api.get(`/api/hcp/${id}`)

export const getInteractions = (hcpId) =>
  api.get('/api/interactions', {
    params: { hcp_id: hcpId },
  })

export default api
