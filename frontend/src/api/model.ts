import { AxiosInstance, AxiosResponse } from "axios";
import { Model } from "@/types";
function getModelAPI(axiosInstance: AxiosInstance) {
  function get(
  ): Promise<AxiosResponse<Model, any>> {
    return axiosInstance.get("/metadata");
  }


  return Object.freeze({
    axiosInstance,
    get,
  });
}

export default getModelAPI;
