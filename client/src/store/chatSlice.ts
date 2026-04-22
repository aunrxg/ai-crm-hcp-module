import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { v4 as uuid } from "uuid";

interface ChatInterface {
    messages: string[];
    sessionId: string;
    loading: boolean;
    error: string;
}

const initialState = {
    messages: [],
    sessionId: null,
    loading: false,
    error: null,
}

const chatSlice = createSlice({
    name: "chat",
    initialState,
    reducers: {
        addMessage: (state, action: PayloadAction<ChatInterface>) => {
            state.messages.push(action.payload.messages);
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.loading = action.payload;
        },
        setError: (state, action: PayloadAction<string>) => {
            state.error = action.payload;
        },
        initSession: (state) => {
            if (!state.sessionId) {
                state.sessionId = uuid();
            }
        },
    }
});

export const { addMessage, setError, setLoading, initSession } = chatSlice.actions;
export default chatSlice.reducer;