// Modified from mantine/core/lib/Code/Code.styles.tsx

import { createStyles, MantineColor, rem } from "@mantine/styles";

export interface CodeBlockWithLinebreakStylesParams {
  color: MantineColor;
}

export default createStyles((theme, { color: _color }: CodeBlockWithLinebreakStylesParams) => {
  const color = _color || (theme.colorScheme === "dark" ? "dark" : "gray");
  const colors = theme.fn.variant({ color, variant: "light" });

  return {
    root: {
      ...theme.fn.fontStyles(),
      lineHeight: theme.lineHeight,
      padding: `${rem(2)} calc(${theme.spacing.xs} / 2)`,
      borderRadius: theme.radius.sm,
      color:
        theme.colorScheme === "dark"
          ? color === "dark"
            ? theme.colors.dark[0]
            : theme.white
          : theme.colors.dark[7],
      backgroundColor:
        theme.colorScheme === "dark" && color === "dark" ? theme.colors.dark[5] : colors.background,
      fontFamily: theme.fontFamilyMonospace,
      fontSize: theme.fontSizes.xs,
    },

    block: {
      padding: theme.spacing.xs,
      margin: 0,
      whiteSpace: "pre-wrap",
      wordBreak: "break-all",
    },
  };
});
