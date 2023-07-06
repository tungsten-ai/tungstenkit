import { Container, Avatar, Text  } from "@mantine/core";
import { Model } from "@/types";
import React from "react";
import Header from "../common/Header";

import GlobalLayout from "./GlobalLayout";

export interface ModelPageLayoutProps {
  model: Model;
  children?: React.ReactNode;
}

export default function ModelPageLayout({
  model,
  children,
}: ModelPageLayoutProps) {
  const name = (
    <Text size="xxl" fw={500} inline>
        {model.name}
      </Text>
  );

  const header = (
    <Header
      avatar={<Avatar src={model.avatar_url} size="70px" radius="0" />}
      align="center"
    >
      {name}
    </Header>
  );

  return (
    <GlobalLayout header={header}>
      <Container my="2rem" className="layout-container">
        <Container className="layout-container-inner">{children}</Container>
      </Container>
    </GlobalLayout>
  );
}
