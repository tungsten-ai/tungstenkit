import { Box, MantineSize, ScrollArea } from "@mantine/core";
import { useElementSize, useMouse, useMergedRef } from "@mantine/hooks";
import { useEffect, useRef } from "react";

import { CodeBlockWithLinebreak } from "./CodeBlockWithLinebreak";
import { CopyToClipboardOverlay } from "./CopyToClipboardOverlay";

export default function PredictionLogsArea({
  children,
  autoScroll,
  fz,
  h,
}: {
  children?: string;
  autoScroll?: "smooth" | "auto";
  fz?: MantineSize;
  h?: MantineSize;
}) {
  const viewport = useRef<HTMLDivElement>(null);
  const { ref: sizeRef, width, height } = useElementSize();
  const { ref: mouseRef, x: mouseX, y: mouseY } = useMouse({ resetOnExit: true });
  const mergedRef = useMergedRef(sizeRef, mouseRef);

  const notFocused = !!autoScroll && (mouseX === 0 || mouseY === 0);

  const scrollToBottom = (behavior: "smooth" | "auto") => {
    viewport?.current?.scrollTo({
      top: viewport.current.scrollHeight,
      behavior,
    });
  };

  useEffect(() => {
    if (autoScroll && notFocused) {
      scrollToBottom(autoScroll);
    }
  }, [notFocused, autoScroll, children]);

  return (
    <Box pos="relative" ref={mergedRef}>
      <ScrollArea viewportRef={viewport} h={h}>
        <CodeBlockWithLinebreak fz={fz} miw={width} mih={height} mono noCopy>
          {children}
        </CodeBlockWithLinebreak>
      </ScrollArea>
      {(mouseX !== 0 || mouseY !== 0) && (
        <CopyToClipboardOverlay p=".3rem" value={children != null ? children : ""} />
      )}
    </Box>
  );
}

PredictionLogsArea.defaultProps = {
  fz: "xs",
  h: "30vh",
  children: "",
};
