import '@/styles/globals.css'
import type { AppProps } from 'next/app'
import { wrapper } from "@/redux/store";
import { MantineProvider } from "@mantine/core";
import { ThemeProvider } from "@mui/material/styles";
import { QueryClient, QueryClientProvider } from "react-query";
import "../styles/App.css";
import theme from "@/styles/mui-theme";
import { Provider } from "react-redux";

function App({ Component, pageProps }: AppProps) {
  const queryClient = new QueryClient();
  const { store, props } = wrapper.useWrappedStore(pageProps);

  return (
    <>
      <Provider store={store}>
        <MantineProvider
          withGlobalStyles
          withNormalizeCSS
          theme={{
            colorScheme: "light",
          }}
        >
          <ThemeProvider theme={theme}>
            <QueryClientProvider client={queryClient}><Component {...pageProps} /></QueryClientProvider>
          </ThemeProvider>
        </MantineProvider>
        </Provider>
    </>
  );
}

export default wrapper.withRedux(App);
