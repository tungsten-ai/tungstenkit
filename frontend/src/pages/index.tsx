import { Box, LoadingOverlay } from "@mantine/core";
import Head from "next/head";
import getModelAPI from "@/api/model";
import ModelPageLayout from "@/components/layouts/ModelPageLayout";
import { getClientSideAxios } from "@/axios";
import ModelRun from "@/components/model-run/ModelRun";
import { useQuery, QueryClientProvider, QueryClient } from "react-query";

export default function ModelRunPage() {
  const queryClient = new QueryClient()
  const axiosInstance = getClientSideAxios();
  const modelAPI = getModelAPI(axiosInstance);

  const { data: model } = useQuery(["model"], () => modelAPI.get().then((resp) => resp.data))

  return (
    <QueryClientProvider client={queryClient}>
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
    </QueryClientProvider>
  );
}
