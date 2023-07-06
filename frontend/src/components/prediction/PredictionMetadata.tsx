import {
  Group,
  GroupPosition,
  MantineColor,
  MantineSize,
  Stack,
  Text,
  useMantineTheme,
} from "@mantine/core";

const predictionDateDiff = (start: Date, end: Date, fractionDigits = 2) => {
  const microseconds = end - start;
  return `${(microseconds / 1000).toFixed(fractionDigits)} seconds`;
};

export interface PredictionMetadataProps {
  startedAt: string;
  exitedAt: string;
  predictionId?: string | null;
  position?: GroupPosition;
  size?: MantineSize;
  color?: MantineColor;
  spacing?: MantineSize;
}

export function PredictionMetadata({
  startedAt,
  exitedAt,
  predictionId,
  position,
  size,
  color,
  spacing,
}: PredictionMetadataProps) {
  const theme = useMantineTheme();

  return (
    <Stack spacing={spacing} fz={size}>
      {predictionId ? (
        <Group position={position} spacing="0">
          <Text color={color} ff={theme.fontFamilyMonospace}>
            Run ID:&nbsp;
          </Text>
          <Text color={color} ff={theme.fontFamilyMonospace}>
            {predictionId}
          </Text>
        </Group>
      ) : undefined}

      <Group position={position} spacing="0">
        <Text color={color} ff={theme.fontFamilyMonospace}>
          Processing time:&nbsp;
        </Text>
        <Text color={color} ff={theme.fontFamilyMonospace}>
          {predictionDateDiff(new Date(startedAt), new Date(exitedAt), 2)}
        </Text>
      </Group>
    </Stack>
  );
}

PredictionMetadata.defaultProps = {
  predictionId: null,
  color: "gray.7",
  position: "right",
  size: "xs",
  spacing: "xxs",
};
