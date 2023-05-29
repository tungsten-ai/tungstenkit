import React from "react";
import { Box } from "@mui/material";
import CopyToClipboardButton from "./CopyJsonBtn";
import { JSONTree } from "react-json-tree";

function PredictionSuccessOutputJSON({ output }: { output: predictionOutput }) {
  return (
    <Box id="postloadscreen" sx={{marginBottom:"10px"}}>
      <Box
        id="postloadscreenchild"
        sx={{
          height: "450px",
          border: 1,
          backgroundColor: "#E9E9E9",
          wordBreak: "break-all",
          whiteSpace: "pre-wrap",
          marginTop: "10px",
        }}
      >
        <CopyToClipboardButton output={output} />
        <JSONTree
          getItemString={() => <></>}
          data={output}
          theme={{
            tree: ({ style }) => ({
              style: {
                ...style,
                backgroundColor: "#E9E9E9",
                width: "95%",
                paddingLeft: "15px",
                height: "430px",
              },
            }),
            base00: "#000000",
            base01: "#000000",
            base02: "#000000",
            base03: "#000000",
            base04: "#000000",
            base05: "#000000",
            base06: "#000000",
            base07: "#000000",
            base08: "#000000",
            base09: "#000000",
            base0A: "#000000",
            base0B: "#000000",
            base0C: "#000000",
            base0D: "#000000",
            base0E: "#000000",
            base0F: "#000000",
          }}
        />
      </Box>
    </Box>
  );
}

export default PredictionSuccessOutputJSON;
