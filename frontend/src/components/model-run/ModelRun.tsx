import { Group } from "@mantine/core";
import { useScrollIntoView } from "@mantine/hooks";
import { Cookies } from "react-cookie";
import { useState } from "react";
import { useMutation, useQuery } from "react-query";
import getPredictionAPI from "@/api/prediction";
import { PredictionIOCard } from "@/components/prediction";
import { getClientSideAxios } from "@/axios";
import { Model } from "@/types";
import { Prediction, PredictionInputFieldValue } from "@/api/prediction.types";
import { showFailureNotification } from "@/components/common/notifications";
import { ModelRunProgress } from "./ModelRunProgress";
import { ModelRunInputForm } from "./ModelRunInputForm";

export interface ModelRunProps {
  model: Model;
  currentPrediction: Prediction | null;
}

const FAILURE_MESSAGE = "Failed to run by unexpected server error";

export default function ModelRun({ model, currentPrediction }: ModelRunProps) {
  const axiosInstance = getClientSideAxios();
  const predictionAPI = getPredictionAPI(axiosInstance);

  const cookies = new Cookies();

  const [prediction, setPrediction] = useState<Prediction | null>(currentPrediction);
  const { scrollIntoView: scrollIntoProgress, targetRef: progressRef } =
    useScrollIntoView<HTMLDivElement>({ axis: "y" });

  const createPrediction = useMutation({
    mutationFn: (input: { [key: string]: PredictionInputFieldValue }) => {
      // Cancel not finished prediction and create a new one.
      const createPromise = predictionAPI.create(input);
      if (prediction != null && ["pending", "running"].includes(prediction.status)) {
        return predictionAPI.cancel(prediction.id).then(() => createPromise);
      }
      return createPromise;
    },
    onSuccess: ({ data }) => {
      // TODO tab-specific cookie? or full client-side rendering to prevent flickering?
      cookies.set("current_prediction", data.id, { path: "/" });
      console.log(data)
      setPrediction(data);
      scrollIntoProgress({ alignment: "start" });
    },
    onError: () => {
      showFailureNotification(FAILURE_MESSAGE);
    },
  });

  useQuery({
    enabled:
      prediction != null && (prediction.status === "running" || prediction.status === "pending"),
    retry: 5,
    refetchInterval: 500,
    queryKey: "",
    queryFn: () => predictionAPI.get((prediction as Prediction).id),
    onSuccess: (resp) => setPrediction(resp.data),
    onError: () => showFailureNotification("Failed to update the status from server"),
  });

  return (
    <Group w="100%" spacing="2rem" align="top" grow>
      <PredictionIOCard title="Input">
        <ModelRunInputForm
          model={model}
          currentPrediction={currentPrediction}
          onFormSubmit={createPrediction.mutate}
          onError={() => showFailureNotification(FAILURE_MESSAGE)}
        />
      </PredictionIOCard>
      <PredictionIOCard title="Output">
          <ModelRunProgress
            ref={progressRef}
            prediction={prediction}
            model={model}
            setPrediction={setPrediction}
          />
        
      </PredictionIOCard>
    </Group>
  );
}
