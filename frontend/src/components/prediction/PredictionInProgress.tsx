import { Group, Stack, Text, Loader } from "@mantine/core";
import { ReactNode } from "react";

export default function PredictionInProgress({
  status,
  logsArea,
}: {
  status: "pending" | "running";
  logsArea: ReactNode;
}) {
  return (
    <Stack>
      <Group>
        <Text fw={500}>{status.charAt(0).toUpperCase() + status.slice(1)}</Text>
        <Loader color="gray" variant="dots" size="sm" />
      </Group>
      {logsArea}
    </Stack>
  );
}
