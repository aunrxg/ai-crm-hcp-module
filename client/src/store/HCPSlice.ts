import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export interface HCP {
  id: string;
  name: string;
  specialty: string;
  hospital: string;
  tier: string;
}

interface HCPState {
  hcps: HCP[];
  selectedHCP: HCP | null;
  searchResults: HCP[];
  loading: boolean;
}

const initialState: HCPState = {
  hcps: [],
  selectedHCP: null,
  searchResults: [],
  loading: false,
};

const hcpSlice = createSlice({
  name: "hcp",
  initialState,
  reducers: {
    setHCPs: (state, action: PayloadAction<HCP[]>) => {
      state.hcps = action.payload;
    },
    setSelectedHCP: (state, action: PayloadAction<HCP | null>) => {
      state.selectedHCP = action.payload;
    },
    setSearchResults: (state, action: PayloadAction<HCP[]>) => {
      state.searchResults = action.payload;
    },
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.loading = action.payload;
    },
  },
});

export const { setHCPs, setSelectedHCP, setSearchResults, setLoading } = hcpSlice.actions;
export default hcpSlice.reducer;