import { Box, LoadingOverlay } from "@mantine/core";
import Head from "next/head";
import getModelAPI from "@/api/model";
import { Cookies } from "react-cookie";
import ModelPageLayout from "@/components/layouts/ModelPageLayout";
import { getClientSideAxios } from "@/axios";
import ModelRun from "@/components/model-run/ModelRun";
import { Model } from "@/types";
import { Prediction } from "@/api/prediction.types";
import getPredictionAPI from "@/api/prediction";
import { useEffect, useState, useLayoutEffect } from "react";
import { showFailureNotification } from "@/components/common/notifications";

export default function ModelRunPage() {
  const axiosInstance = getClientSideAxios();
  const modelAPI = getModelAPI(axiosInstance);


  const [model, setModel] = useState<Model | null>(null);
  
  useLayoutEffect(() => {
    async function load_model() {
      await modelAPI
        .get()
        .then((response) => setModel(response.data))
        .catch(() => {
          showFailureNotification("Failed to load model metadata by unexpected server error")
        });
    }
    load_model()
  }, [])


  return (
    <Box>
      {model ? (
        <>
          <Head>
            <title>{`${model.name} - Run | Tungsten`}</title>
            <meta name="viewport" content="initial-scale=1.0, width=device-width" />
          </Head>
          <ModelPageLayout model={model}>
            <ModelRun
              model={model}
            />
          </ModelPageLayout>
        </>
      ) : undefined}
      <LoadingOverlay visible={model == null}/>
    </Box>
  );
}
