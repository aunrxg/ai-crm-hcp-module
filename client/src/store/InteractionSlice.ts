import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface InteractionDraft {
  hcp_id: string | null;
  hcp_name: string | null;
  interaction_type: string | null;
  date: string | null;
  duration_minutes: number | null;
  products_discussed: string[];
  sentiment: string | null;
  next_action: string | null;
  ai_summary: string | null;
  entities_json: any;
  follow_up_date: string | null;
  follow_up_task: string | null;
}

interface InteractionState {
  draft: InteractionDraft;
  lastSavedId: string | null;
  isSaved: boolean;
}

const initialDraft: InteractionDraft = {
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

const initialState: InteractionState = {
  draft: initialDraft,
  lastSavedId: null,
  isSaved: false,
};

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    updateDraft: (state, action: PayloadAction<Partial<InteractionDraft>>) => {
      state.draft = { ...state.draft, ...action.payload };
    },
    clearDraft: (state) => {
      state.draft = { ...initialDraft };
    },
    setLastSavedId: (state, action: PayloadAction<string | null>) => {
      state.lastSavedId = action.payload;
    },
    setIsSaved: (state, action: PayloadAction<boolean>) => {
      state.isSaved = action.payload;
    },
  },
});

export const { updateDraft, clearDraft, setLastSavedId, setIsSaved } = interactionSlice.actions;
export default interactionSlice.reducer;