import { Badge, Box, Container, Group, Space, Stack, Tabs } from "@mantine/core";
import { useElementSize } from "@mantine/hooks";
import { useRouter } from "next/router";
import { ReactNode } from "react";

export interface TabProps {
  value: string;
  label: string | number;
  badgeLabel?: string | number;
  link: string;
}

export interface HeaderProps {
  avatar: ReactNode;
  buttons?: ReactNode;
  tabs?: TabProps[];
  activeTab?: string;
  align?: string;
  children?: ReactNode;
}

export default function Header(props: HeaderProps) {
  const router = useRouter();
  const { ref } = useElementSize();

  const { avatar, buttons, tabs, activeTab, align, children } = props;

  const onTabChange = (value: string) => {
    const tab = tabs.find((element) => element.value === value);
    if (tab) {
      router.push(tab.link);
    }
  };
  const tabsComponent = tabs != null ? (
    <Tabs
      value={activeTab}
      defaultValue={activeTab}
      onTabChange={onTabChange}
      color="violet-manual.3"
      styles={(theme) => ({
        tab: {
          "&:hover": {
            backgroundColor: theme.colors.gray[0],
            borderColor: theme.colors.gray[5],
          },
          "&[data-active]": {
            fontWeight: 600,
          },
          fontSize: theme.fontSizes.md,
          height: "2rem",
          minWidth: "100px",
          borderWidth: "3px",
        },
        tabsList: {
          display: "flex",
          borderBottom: "none",
          gap: "1rem",
        },
        tabLabel: {
          marginBottom: "5px",
        },
        tabRightSection: {
          paddingLeft: "5px",
          marginBottom: "3px",
        },
      })}
    >
      <Tabs.List>
        {tabs.map((tab: TabProps) => (
          <Tabs.Tab
            key={tab.value}
            value={tab.value}
            rightSection={
              tab.badgeLabel !== undefined && tab.badgeLabel !== null ? (
                <Badge size="sm">{tab.badgeLabel}</Badge>
              ) : null
            }
          >
            {tab.label}
          </Tabs.Tab>
        ))}
      </Tabs.List>
    </Tabs> 
  ): undefined;

  return (
    <Container
      pt="1.5rem"
      bg="#F7F8FA"
      sx={(theme) => ({
        borderBottom: `1.5px solid ${theme.colors.gray[3]}`,
      })}
      className="layout-container"
    >
      <Container className="layout-container-inner">
        <Group spacing="0rem" position="apart" align={align ?? "center"}>
          <Group spacing="1.5rem" align={align ?? "center"}>
            <Box ref={ref}>{avatar}</Box>
            <Stack spacing="sm">
              {Array.isArray(children)
                ? children.map((element, index) => (
                    <div key={`header-body-element-${index.toString()}`}>{element}</div>
                  ))
                : children}
            </Stack>
          </Group>
          <Box mt="5px">
            {Array.isArray(buttons)
              ? buttons.map((element, index) => (
                  <div key={`header-button-${index.toString()}`}>{element}</div>
                ))
              : buttons}
          </Box>
        </Group>
        <Space h="1.5rem" w="100%" mt="0.5rem" />
        {tabsComponent}
      </Container>
    </Container>
  );
}
