import { Box, Typography } from "@mui/material";
import React from "react";
import TraceBlock from "../../common/TraceBlock";

function PredictionFail({ output }: { output: predictionData }) {
  return (
    <Box>
      <Typography sx={{ color: "#FF0000" }}>
        Prediction failed. Log is shown below:
      </Typography>
      <TraceBlock trace={ output.logs } />
    </Box>
  );
}

export default PredictionFail;
