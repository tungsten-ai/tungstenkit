import { MantineSize, SegmentedControl, SegmentedControlProps, Center, Box } from "@mantine/core";
import { IconEye, IconCode, IconFileText } from "@tabler/icons-react";
import { ReactNode } from "react";

export type PredictionOutputMode = "preview" | "raw" | "logs";

export interface PredictionOutputControlProps
  extends Omit<SegmentedControlProps, "data" | "onChange"> {
  mode: "preview" | "raw" | "logs";
  onChange: (value: PredictionOutputMode) => void;
  iconSize?: MantineSize;
}
function LabelWithIcon({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <Center>
      {icon}
      <Box ml={10}>{label}</Box>
    </Center>
  );
}
export function PredictionOutputControl({
  mode,
  onChange,
  w,
  iconSize,
  ...others
}: PredictionOutputControlProps) {
  const iconProps = { size: iconSize === undefined ? "1rem" : iconSize };

  return (
    <SegmentedControl
      value={mode}
      onChange={onChange}
      w={w ?? "100%"}
      data={[
        {
          label: <LabelWithIcon icon={<IconEye {...iconProps} />} label="Preview" />,
          value: "preview",
        },
        { label: <LabelWithIcon icon={<IconCode {...iconProps} />} label="Raw" />, value: "raw" },
        {
          label: <LabelWithIcon icon={<IconFileText {...iconProps} />} label="Logs" />,
          value: "logs",
        },
      ]}
      {...others}
    />
  );
}
