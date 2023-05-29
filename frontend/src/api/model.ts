import { AxiosInstance } from "axios";
import { FieldValues } from "react-hook-form";

function getModelAPI(axiosInstance: AxiosInstance) {
    function list(projectSlug: string, namespaceSlug: string, queryparams?: string) {
      const requestQuery = `/projects/${namespaceSlug}/${projectSlug}/models`;
      return axiosInstance.get(requestQuery, { params: queryparams });
    }
  
    function get(namespaceSlug: string, projectSlug: string, modelVersion: string) {
      const requestQuery = `projects/${namespaceSlug}/${projectSlug}/models/${modelVersion}`;
      return axiosInstance.get(requestQuery);
    }

    function getFile(
      filePath: string,
      headers? : Object,
    ) {
      const requestQuery = `/files/${filePath}`;
      return axiosInstance.get(requestQuery, headers);
    }

    function uploadFile(inputToSend: FieldValues, prop: string) {
      const requestQuery = `/files`;
      const file = inputToSend[prop];
      const form = new FormData();
      form.append("file", file);
      const uploadedFileUrl = (
        axiosInstance.post(requestQuery, form, {
          headers: {
            accept: "application/json",
            "Content-Type": "multipart/form-data",
          },
        })
      );
  
      return uploadedFileUrl;
    }

    function startPrediction(
      input: FieldValues,
    ) {
      
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

    function getPrediction(predictionId: string) {
      const requestQuery = `/predictions/${predictionId}`;
      return axiosInstance.get(requestQuery);
    }

    function cancelPrediction(predictionId:string){
      return axiosInstance.post(`/predictions/${predictionId}/cancel`)
    }

    function getExamples() {
      return axiosInstance.get("/examples");
    }

    function addExample(predictionId : string|number){
      return axiosInstance.post(`/predictions/${predictionId}/save`)
    }

    function deleteExample(exampleID: string){
      return axiosInstance.delete(`examples/${exampleID}`)
    }

    function getModelZipFile(
      projectSlug: string,
      namespaceSlug: string,
      modelVersion: string,
      headers?:Object,
    ) {
      const requestQuery = `/projects/${namespaceSlug}/${projectSlug}/models/${modelVersion}/archive.zip`;
      return axiosInstance.get(requestQuery, headers);
    }  

    function getModelTree(
      projectSlug: string,
      namespaceSlug: string,
      modelVersion: string,
      path?: string,
    ) {
      let requestQuery = `/projects/${namespaceSlug}/${projectSlug}/models/${modelVersion}/tree`;
      if (path) requestQuery += `?path=${path}`;
      return axiosInstance.get(requestQuery).catch(function (error:Error){return []});
    }
  
    // function fileUpload(projectSlug: string, namespaceSlug: string, input: File) {
    //   const requestQuery = `/projects/${namespaceSlug}/${projectSlug}/uploads`;
    //   const formData = new FormData();
    //   formData.append("file", input);
    //   return axiosInstance.post(requestQuery, formData, {
    //     headers: {
    //       "Content-Type": "multipart/form-data",
    //     },
    //   });
    // }
  
    return Object.freeze({
      axiosInstance,
      list,
      get,
      getFile,
      uploadFile,
      startPrediction,
      getPrediction,
      cancelPrediction,
      getExamples,
      addExample,
      deleteExample,
      getModelTree,
      getModelZipFile,
    });
  }
  
  export default getModelAPI;
  