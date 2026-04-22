import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

interface HCPState {
  id: string;
  name: string;
  specialty: string;
  hospital: string;
  tier: string;
}

const initialState = {
  hcps: [] as HCPState[],
  selectedHCP: null as HCPState | null,
  searchResults: [] as HCPState[],
  loading: false,
}

const HCPSlice = createSlice({
    name: "hcp",
    initialState,
    reducers: {
        getHCPs: (state, action: PayloadAction<HCPState[]>) => {
            state.hcps = action.payload;
        },
        setSelectedHCP: (state, action: PayloadAction<HCPState, null>) => {
            state.selectedHCP = action.payload
        },
        setSearchResult: (state, action: PayloadAction<HCPState[]>) => {
            state.searchResults = action.payload;
        },
        setLoading: (state, action: PayloadAction<boolean>) => {
            state.loading = action.payload;
        },
    },
});

export const { getHCPs, setSelectedHCP, setSearchResult, setLoading } = HCPSlice.actions
export default HCPSlice.reducer;