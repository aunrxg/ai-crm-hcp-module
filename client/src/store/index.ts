import { configureStore } from "@reduxjs/toolkit";
import HCPSlice from "./HCPSlice";
import InteractionSlice from "./InteractionSlice"
import ChatSlice from "./chatSlice";

export const store = configureStore({
  reducer: {
    hcp: HCPSlice,
    interaction: InteractionSlice,
    chat: ChatSlice,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
