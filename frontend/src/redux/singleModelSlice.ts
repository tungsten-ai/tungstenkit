import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  output: <predictionData> {},
  menuOption: 0,
  example: <predictionData> {},
  trace: "",
  predictionId:null, 
  status:<string>""
};

const singleModelSlice = createSlice({
  name: "model",
  initialState,
  reducers: {
    //consider joining these reducers together in a single reducer function
    setMenuOption(state, action) {
      return { ...state, menuOption: action.payload };
    },
    updateModelOutput(state, action) {
      return { ...state, output: action.payload.output, status: action.payload.status};
    },
    updateModelStatus(state, action) {
      return { ...state, status: action.payload.status };
    },
    setModelExample(state, action) {
      return { ...state, example: action.payload };
    },
    setTrace(state, action) {
      return { ...state, trace: action.payload.trace };
    },
  },
});

export const {
  updateModelOutput,
  setMenuOption,
  setModelExample,
  updateModelStatus,
  setTrace,
} = singleModelSlice.actions;

export default singleModelSlice.reducer;
