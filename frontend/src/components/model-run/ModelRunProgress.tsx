import { Box, Space, Button, Group } from "@mantine/core";
import { ReactNode, forwardRef, useState } from "react";
import {
  PredictionLogsArea,
  PredictionFailure,
  PredictionInProgress,
  PredictionNotStarted,
  PredictionOutputView,
  PredictionOutputControl,
  PredictionOutputMode,
} from "@/components/prediction";
import { Model } from "@/types";
import { Prediction } from "@/api/prediction.types";
import { IconTrash } from "@tabler/icons-react";
import { useMutation } from "react-query";
import { getClientSideAxios } from "@/axios";
import getPredictionAPI from "@/api/prediction";
import { Cookies } from "react-cookie";

export interface ModelRunProgressProps {
  prediction: Prediction | null;
  model: Model;
  editable?: boolean;
  setPrediction: (value: Prediction | null) => void;
}

export const ModelRunProgress = forwardRef<HTMLDivElement, ModelRunProgressProps>(
  (props: ModelRunProgressProps, ref) => {
    const { prediction, model, setPrediction } = props;
    const {
      demo_output_schema: demoOutputSchema,
      demo_output_filetypes: demoOutputFileTypes,
    } = model;

    const cookies = new Cookies();

    const axiosInstance = getClientSideAxios();
    const predictionAPI = getPredictionAPI(axiosInstance);

    const [mode, setMode] = useState<PredictionOutputMode>("preview");

    const cancelPrediction = useMutation({
      mutationFn: () => {
        cookies.remove("current_prediction", { path: "/" });
        setPrediction(null);
        return predictionAPI.cancel(prediction.id);
      },
    });

    const logsAutoscroll =
      prediction?.status && ["pending", "running"].includes(prediction.status) ? "auto" : "smooth";
    const logsArea = (
      <PredictionLogsArea autoScroll={logsAutoscroll}>{prediction?.logs ?? ""}</PredictionLogsArea>
    );
    const mediumSpace = <Space h="md" />;
    const largeSpace = <Space h="xl" />;
    let component: ReactNode;

    switch (prediction?.status) {
      case "pending":
      case "running":
        component = (
          <>
            <PredictionInProgress
              status={prediction.status}
              logsArea={prediction.status === "running" ? logsArea : undefined}
            />
            {mediumSpace}
            <Button onClick={() => cancelPrediction.mutate()} variant="default" fullWidth>
              Cancel
            </Button>
          </>
        );
        break;
      case "failed":
        component = (
          <>
            <PredictionFailure failureReason={prediction.failure_reason} logsArea={logsArea} />
            {largeSpace}
          </>
        );
        break;
      case "success":
        component = (
          <>
            <PredictionOutputControl mode={mode} onChange={setMode} />
            {mediumSpace}
            <PredictionOutputView
              mode={mode}
              output={prediction.output}
              demoOutput={prediction.demo_output}
              demoOutputSchema={demoOutputSchema}
              demoOutputFiletypes={demoOutputFileTypes}
              logs={prediction?.logs ?? ""}
            />
            {largeSpace}
            <Group position="right">
              <Button
                variant="default"
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: "auto" });
                  cookies.remove("current_prediction", { path: "/" });
                  setPrediction(null);
                }}
                leftIcon={<IconTrash size="1rem" />}
              >
                Clear
              </Button>
              </Group>
          </>
        );
        break;
      default:
        component = <PredictionNotStarted />;
    }

    return <Box ref={ref}>{component}</Box>;
  },
);

ModelRunProgress.displayName = "ModelRunProgress";
