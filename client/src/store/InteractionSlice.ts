import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface InteractionDraft {
  hcp_id: string | null;
  hcp_name: string | null;
  interaction_type: string;
  date: string | null;
  time: string | null;
  attendees: string[];
  topics_discussed: string;
  materials_shared: string[];
  samples_distributed: string[];
  sentiment: string;
  outcomes: string;
  follow_up_actions: string;
  ai_suggested_follow_ups: string[];
  ai_summary: string | null;
  entities_json: any;
  interaction_id: string | null;
  isSaved: boolean;
}

interface InteractionState {
  draft: InteractionDraft;
  isSaved: boolean;
}

const initialDraft: InteractionDraft = {
  hcp_id: null,
  hcp_name: null,
  interaction_type: "Meeting",
  date: null,
  time: null,
  attendees: [],
  topics_discussed: "",
  materials_shared: [],
  samples_distributed: [],
  sentiment: "neutral",
  outcomes: "",
  follow_up_actions: "",
  ai_suggested_follow_ups: [],
  ai_summary: null,
  entities_json: null,
  interaction_id: null,
  isSaved: false,
};

const initialState: InteractionState = {
  draft: initialDraft,
  isSaved: false,
};

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    updateDraft: (state, action: PayloadAction<any>) => {
      const p = action.payload;
      
      // Map 1:1 fields first
      state.draft = { ...state.draft, ...p };
      
      if (p.entities_json?.action_items) {
        state.draft.ai_suggested_follow_ups = p.entities_json.action_items;
      }
      
      if (p.next_action) {
        state.draft.follow_up_actions = p.next_action;
        if (!state.draft.ai_suggested_follow_ups) {
          state.draft.ai_suggested_follow_ups = [];
        }
        if (!state.draft.ai_suggested_follow_ups.includes(p.next_action)) {
          state.draft.ai_suggested_follow_ups.push(p.next_action);
        }
      }
      
      if (p.entities_json?.drugs_mentioned) {
        state.draft.materials_shared = p.entities_json.drugs_mentioned;
      }
      
      if (p.products_discussed) {
        state.draft.materials_shared = p.products_discussed;
      }
      
      if (p.raw_input) {
        state.draft.topics_discussed = p.raw_input;
      }
    },
    clearDraft: (state) => {
      state.draft = { ...initialDraft };
    },
    setIsSaved: (state, action: PayloadAction<boolean>) => {
      state.isSaved = action.payload;
      state.draft.isSaved = action.payload;
    },
    setAISuggestions: (state, action: PayloadAction<string[]>) => {
      state.draft.ai_suggested_follow_ups = action.payload;
    },
  },
});

export const { updateDraft, clearDraft, setIsSaved, setAISuggestions } = interactionSlice.actions;
export default interactionSlice.reducer;