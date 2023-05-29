import { configureStore } from "@reduxjs/toolkit";
import { createWrapper } from "next-redux-wrapper";
import singleModelSlice from "./singleModelSlice";

const makeStore = () =>
  configureStore({
    reducer: {
      singleModel: singleModelSlice,
    },
    devTools: true,
  });

export type AppStore = ReturnType<typeof makeStore>;

export const wrapper = createWrapper<AppStore>(makeStore);

export type AppState = ReturnType<AppStore["getState"]>;