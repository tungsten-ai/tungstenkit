import { Box, Card, Group, Text, CardProps } from "@mantine/core";
import { ReactNode } from "react";

export interface PredictionIOCardProps extends CardProps {
  title: string | JSX.Element;
  rightIcon?: ReactNode;
}

export function PredictionIOCard({
  title,
  rightIcon,
  children,
  ...others
}: PredictionIOCardProps) {
  return (
    <Card withBorder padding="lg" radius="lg" h="fit-content" {...others}>
      <Card.Section withBorder inheritPadding py="sm">
        <Group position="apart">
          {typeof title === "string" ? (
            <Text fz="xl" fw={600}>
              {title}
            </Text>
          ) : (
            title
          )}
          {rightIcon}
        </Group>
      </Card.Section>
      <Box pt="md">{children}</Box>
    </Card>
  );
}

// PredictionIOCard.defaultProps = {
//   radius: "10px",
//   shadow: "md",
//   p: "0px",
//   withBorder: true,
// }
