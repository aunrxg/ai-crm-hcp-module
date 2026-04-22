import { combineReducers, configureStore, createSlice } from '@reduxjs/toolkit'
import { v4 as uuid } from 'uuid'

const hcpSlice = createSlice({
  name: 'hcp',
  initialState: {
    hcps: [],
    selectedHCP: null,
    searchResults: [],
    loading: false,
  },
  reducers: {
    setHCPs: (state, action) => {
      state.hcps = action.payload
    },
    setSelectedHCP: (state, action) => {
      state.selectedHCP = action.payload
    },
    setSearchResults: (state, action) => {
      state.searchResults = action.payload
    },
    setLoading: (state, action) => {
      state.loading = action.payload
    },
  },
})

const initialDraft = {
  hcp_id: null,
  hcp_name: null,
  interaction_type: null,
  date: null,
  duration_minutes: null,
  products_discussed: [],
  sentiment: null,
  next_action: null,
  ai_summary: null,
  entities_json: null,
  follow_up_date: null,
  follow_up_task: null,
}

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    draft: initialDraft,
    lastSavedId: null,
    isSaved: false,
  },
  reducers: {
    updateDraft: (state, action) => {
      state.draft = { ...state.draft, ...action.payload }
    },
    clearDraft: (state) => {
      state.draft = { ...initialDraft }
      state.lastSavedId = null
      state.isSaved = false
    },
    setLastSavedId: (state, action) => {
      state.lastSavedId = action.payload
    },
    setIsSaved: (state, action) => {
      state.isSaved = action.payload
    },
  },
})

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [],
    sessionId: null,
    loading: false,
    error: null,
  },
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload)
    },
    setLoading: (state, action) => {
      state.loading = action.payload
    },
    setError: (state, action) => {
      state.error = action.payload
    },
    initSession: (state) => {
      if (!state.sessionId) {
        state.sessionId = uuid()
      }
    },
  },
})

const rootReducer = combineReducers({
  hcp: hcpSlice.reducer,
  interaction: interactionSlice.reducer,
  chat: chatSlice.reducer,
})

export const store = configureStore({
  reducer: rootReducer,
})

export const { setHCPs, setSelectedHCP, setSearchResults, setLoading: setHCPLoading } =
  hcpSlice.actions
export const { updateDraft, clearDraft, setLastSavedId, setIsSaved } = interactionSlice.actions
export const { addMessage, setLoading: setChatLoading, setError, initSession } = chatSlice.actions

export default store
