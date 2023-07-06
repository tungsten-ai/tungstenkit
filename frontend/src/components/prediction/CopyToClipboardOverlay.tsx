import {
  Overlay, Group, CopyButton, Tooltip, ActionIcon, MantineSize, OverlayProps,
} from "@mantine/core";
import { IconCheck, IconCopy } from "@tabler/icons-react";

export interface CopyToClipboardOverlayProps extends Omit<OverlayProps, "children" | "opacity" | "sx"> {
  value: string | number | boolean;
  iconSize?: MantineSize
}

export function CopyToClipboardOverlay(
  { value, iconSize, ...others }: CopyToClipboardOverlayProps,
) {
  return (
    <Overlay opacity={0} sx={{ pointerEvents: "none" }} {...others}>
      <Group position="right" align="center">
        <CopyButton value={typeof value === "string" ? value : value.toString()} timeout={2000}>
          {({ copied, copy }) => (
            <Tooltip label={copied ? "Copied" : "Copy"} withArrow position="bottom">
              <ActionIcon variant="light" color={copied ? "button-blue" : "gray"} onClick={copy} sx={{ pointerEvents: "all" }}>
                {copied ? <IconCheck size={iconSize} /> : <IconCopy size={iconSize} />}
              </ActionIcon>

            </Tooltip>
          )}

        </CopyButton>
      </Group>
    </Overlay>
  );
}

CopyToClipboardOverlay.defaultProps = {
  iconSize: "1rem",
};
