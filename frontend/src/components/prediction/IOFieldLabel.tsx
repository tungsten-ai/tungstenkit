import { Stack, Text, Box, useMantineTheme } from "@mantine/core";

interface IOFieldLabelProps {
  name?: string;
  description?: string;
  required?: boolean;
}

export default function IOFieldLabel({ name, description, required }: IOFieldLabelProps) {
  const theme = useMantineTheme();
  const colorRed = theme.fn.variant({ variant: "filled", color: "red" }).background;
  return (
    <Stack spacing="xxs" mb="xs">
      <Box>
        <Text fw={500} fz="md" span>
          {name}{" "}
        </Text>
        {required && (
          <Text span color={colorRed}>
            *
          </Text>
        )}
      </Box>

      {description ? (
        <Text color="gray.7" fz="sm">
          {description}
        </Text>
      ) : undefined}
    </Stack>
  );
}
