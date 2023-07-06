import { ReactNode } from "react";
import { Flex } from "@mantine/core";
import Footer from "../common/Footer";

function GlobalLayout({
  header,
  children,
}: {
  header?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Flex direction="column" sx={{ minHeight: "100vh" }}>
      {header}

      <Flex direction="column" sx={{ flexGrow: 1 }}>
        {children}
      </Flex>

      <Flex direction="column" sx={{ flexGrow: 0 }}>
        <Footer />
      </Flex>
    </Flex>
  );
}

export default GlobalLayout;
