/* eslint-disable @typescript-eslint/no-shadow */
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "react-query";
import { NextPage } from "next";
import customMantineTheme from "@/styles/mantine-theme";
import type { AppProps } from "next/app";

import "../styles/App.css";
import { Notifications } from "@mantine/notifications";
import { ReactNode, ReactElement } from "react";

export type NextPageWithLayout<P = NonNullable<unknown>, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement, pageProps: object) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

function App({ Component, pageProps }: AppPropsWithLayout) {
  const queryClient = new QueryClient();

  const getLayout = Component.getLayout ?? ((page) => page);
  const componentWithLayout = getLayout(<Component {...pageProps} />, pageProps);

  return (
    <QueryClientProvider client={queryClient}>
      <MantineProvider withGlobalStyles withNormalizeCSS theme={customMantineTheme}>
        <Notifications />
        {componentWithLayout}
      </MantineProvider>
    </QueryClientProvider>
  );
}

export default App;
