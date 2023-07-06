import { AxiosInstance, AxiosResponse } from "axios";
import { FileUploadResp } from "./file.types";

function getFileAPI(axiosInstance: AxiosInstance) {
  function upload(
    file: File,
  ): Promise<AxiosResponse<FileUploadResp, any>> {
    const formData = new FormData();
    formData.append("file", file);
    return axiosInstance.post("/files", formData, {
      timeout: 5 * 60 * 1000 /** 5 min */,
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
  }

  return Object.freeze({
    axiosInstance,
    upload,
  });
}

export default getFileAPI;
