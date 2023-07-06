// Modified from mantine/core/lib/Code/Code.tsx

import { Box, useMantineTheme } from "@mantine/core";
import { useMergedRef, useMouse } from "@mantine/hooks";
import { DefaultProps, MantineColor, useComponentDefaultProps } from "@mantine/styles";
import React, { forwardRef } from "react";

import { CopyToClipboardOverlay } from "../CopyToClipboardOverlay";

import useStyles, { CodeBlockWithLinebreakStylesParams } from "./CodeBlockWithLinebreak.styles";

export interface CodeBlockWithLinebreakProps
  extends DefaultProps<never, CodeBlockWithLinebreakStylesParams>,
    React.ComponentPropsWithoutRef<"code"> {
  variant?: string;

  /** Code content */
  children?: string | number | boolean | null;

  /** Code color and background from theme, defaults to gray in light theme and to dark in dark theme */
  color?: MantineColor;

  /** Use theme.fontFamilyMonospace */
  mono?: boolean;

  /** Don't show copy-to-clipboard button */
  noCopy?: boolean;
}

const defaultProps: Partial<CodeBlockWithLinebreakProps> = {
  fz: "sm",
};

export const CodeBlockWithLinebreak = forwardRef<HTMLElement, CodeBlockWithLinebreakProps>(
  (props: CodeBlockWithLinebreakProps, ref) => {
    const { className, children, color, unstyled, variant, mono, ff, noCopy, ...others } =
      useComponentDefaultProps("Code", defaultProps, props);

    const { classes, cx } = useStyles({ color }, { name: "Code", unstyled, variant });
    const theme = useMantineTheme();

    const { ref: mouseRef, x: mouseX, y: mouseY } = useMouse({ resetOnExit: true });
    const mergedRef = useMergedRef<HTMLDivElement>(mouseRef, ref);

    return (
      <Box
        ff={ff ?? (mono ? theme.fontFamilyMonospace : theme.fontFamily)}
        className={cx(classes.root, classes.block, className)}
        ref={mergedRef}
        {...others}
      >
        <Box pos="relative">
          {children != null && children !== "" ? children : <Box>&nbsp;</Box>}
          {noCopy !== true &&
            (mouseX !== 0 || mouseY !== 0) &&
            children != null &&
            children !== "" && (
              <CopyToClipboardOverlay
                value={typeof children === "string" ? children : children.toString()}
                iconSize="1rem"
              />
            )}
        </Box>
      </Box>
    );
  },
);

CodeBlockWithLinebreak.displayName = "CodeBlockWithLinebreak";
