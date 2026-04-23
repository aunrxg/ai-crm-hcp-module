import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { v4 as uuid } from "uuid";

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  toolCalled?: string;
}

interface ChatState {
  messages: Message[];
  sessionId: string | null;
  loading: boolean;
  error: string | null;
}

const initialState: ChatState = {
  messages: [],
  sessionId: null,
  loading: false,
  error: null,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addMessage: (state, action: PayloadAction<Message>) => {
      state.messages.push(action.payload);
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    initSession: (state) => {
      if (!state.sessionId) {
        state.sessionId = uuid();
      }
    },
    resetChat: (state) => {
      state.messages = [];
      state.sessionId = uuid();
      state.loading = false;
      state.error = null;
    },
  },
});

export const { addMessage, setLoading, setError, initSession, resetChat } = chatSlice.actions;
export default chatSlice.reducer;