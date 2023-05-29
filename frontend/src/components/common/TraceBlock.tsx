import { Box } from "@mui/material";
import { CSSProperties, useEffect, useRef } from "react";
import SyntaxHighlighter from "react-syntax-highlighter";
// import { irBlack } from "react-syntax-highlighter/dist/esm/styles/hljs";
import { default as irBlack } from '../../styles/syntaxHighlighter';

function TraceBlock({trace}:{trace:string}) {
  const bottomRef:ref = useRef(null);
  
  const scrollToBottom = () => {
    if (bottomRef.current) {
      bottomRef.current.scrollTop = bottomRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  });
  return (
    <Box
      sx={{
        height: "450px",
        overflow: "auto",
        backgroundColor: "black",
        marginTop:"10px"
      }}
      ref={bottomRef}
    >
        <SyntaxHighlighter
            language="plaintext"
            style = {irBlack as {
              [key: string]: CSSProperties;
            }}
            customStyle={{
              padding: "2px",
              margin: "2px",
              fontSize: "16px",
              width: "98%",
              maxWidth: "98%",
            }}
            wrapLines={true}
            wrapLongLines
            lineProps={{ style: { wordBreak: "break-all", whiteSpace: "pre-wrap" } }}
          >
            {trace}
        </SyntaxHighlighter>
    </Box>
  );
}
export default TraceBlock;