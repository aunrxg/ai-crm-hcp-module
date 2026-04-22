import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface InteractionState {
    hcp_id: string;
    hcp_name: string;
    interaction_type: string;
    date: string;
    duration_minutes: string;
    products_discussed: string[];
    sentiment: "positive" | "negative" | "neutral" | null;
    next_action: string;
    ai_summary: string;
    entities_json: string;
    follow_up_date: string;
    follow_up_task: string;
}

const initialDraft: InteractionState = {
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
};

const InteractionSlice = createSlice({
    name: "interaction",
    initialState: {
        draft: initialDraft,
        lastSavedId: null,
        isSaved: false,
    },
    reducers: {
        updateDraft: (state, action: PayloadAction<InteractionState>) => {
            state.draft = { ...state.draft, ...action.payload };
            state.lastSavedId = action.payload.hcp_id;
            state.isSaved = true;
        },
        clearDraft: (state) => {
            state.draft = { ...initialDraft };
            state.lastSavedId = null;
            state.isSaved = false;
        },
        setLastSaveId: (state, action: PayloadAction<InteractionState>) => {
            state.lastSavedId = action.payload.hcp_id;
        },
        setIsSaved: (state, action: PayloadAction<boolean>) => {
            state.isSaved = action.payload;
        },
    },
});

export const { updateDraft, clearDraft, setLastSaveId, setIsSaved } = InteractionSlice.actions;
export default InteractionSlice.reducer;