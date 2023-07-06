import { AxiosInstance, AxiosResponse } from "axios";
import { PredictionInputFieldValue, Prediction } from "./prediction.types"

function getPredictionAPI(axiosInstance: AxiosInstance) {
  function create(input: {
    [key: string]: PredictionInputFieldValue;
  }): Promise<AxiosResponse<Prediction, any>> {
    const requestQuery = `/predictions`;
    return axiosInstance.post(
      requestQuery,
      input,
      {
        headers: {
          accept: "application/json",
          "Content-Type": "application/json",
        },
      },
    );
  }

  function get(predictionId: string): Promise<AxiosResponse<Prediction, any>> {
    const requestQuery = `/predictions/${predictionId}`;
    return axiosInstance.get(requestQuery);
  }

  function cancel(predictionId: string): Promise<AxiosResponse<undefined, any>> {
    return axiosInstance.post(`/predictions/${predictionId}/cancel`);
  }

  return Object.freeze({
    axiosInstance,
    create,
    get,
    cancel,
  });
}

export default getPredictionAPI;
