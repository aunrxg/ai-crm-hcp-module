import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 422) {
      console.error('Validation Error (422):', error.response.data)
      throw new Error(
        `Validation Failed: ${JSON.stringify(error.response.data.detail || error.response.data)}`
      )
    }
    return Promise.reject(error)
  }
)

export const sendMessage = (message, sessionId, hcpId, hcpName, draft, history) => {
  const interaction_draft = draft ? {
    hcp_id: draft.hcp_id ?? null,
    hcp_name: draft.hcp_name ?? null,
    interaction_type: draft.interaction_type ?? "Meeting",
    date: draft.date ?? null,
    time: draft.time ?? null,
    attendees: draft.attendees ?? [],
    topics_discussed: draft.topics_discussed ?? "",
    materials_shared: draft.materials_shared ?? [],
    samples_distributed: draft.samples_distributed ?? [],
    sentiment: draft.sentiment ?? "neutral",
    outcomes: draft.outcomes ?? "",
    follow_up_actions: draft.follow_up_actions ?? "",
    ai_suggested_follow_ups: draft.ai_suggested_follow_ups ?? [],
    ai_summary: draft.ai_summary ?? null,
    entities_json: draft.entities_json ?? null,
    interaction_id: draft.interaction_id ?? null,
    isSaved: draft.isSaved ?? false,
  } : {};

  return api.post('/api/chat', {
    message,
    session_id: sessionId,
    hcp_id: hcpId ?? null,
    hcp_name: hcpName,
    interaction_draft,
    history: history ?? [],
  });
};

export const submitForm = (draft) => api.post('/api/interactions', {
  hcp_id:              draft.hcp_id,
  interaction_type:    draft.interaction_type?.toLowerCase() || 'visit',
  date:                draft.date || new Date().toISOString().split('T')[0],
  time:                draft.time,
  duration_minutes:    null,
  products_discussed:  draft.materials_shared || [],
  sentiment:           draft.sentiment || 'neutral',
  raw_input:           draft.topics_discussed || '',
  next_action:         draft.follow_up_actions || '',
  attendees:           draft.attendees || [],
  outcomes:            draft.outcomes || '',
});

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
