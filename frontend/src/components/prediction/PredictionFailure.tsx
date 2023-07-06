import { Stack, Text } from "@mantine/core";
import { ReactNode } from "react";
import { FailureReason } from "@/api/prediction.types";

function buildFailureMessage(failureReason: FailureReason) {
  switch (failureReason) {
    case "user_failure":
      return "Model run failed. See the logs below.";

    case "system_failure":
      return "An unexpected error occurred. If you encounter this repeatedly, please send us feedback.";

    case "timeout":
      return "Timeout Reached";

    default:
      return `ERROR${failureReason ? `: ${failureReason}` : ""}`;
  }
}

export default function PredictionFailure({
  failureReason,
  logsArea,
}: {
  failureReason: FailureReason;
  logsArea: ReactNode;
}) {
  return (
    <Stack>
      <Text color="red.6" fw={500}>
        {buildFailureMessage(failureReason)}
      </Text>
      {logsArea}
    </Stack>
  );
}
