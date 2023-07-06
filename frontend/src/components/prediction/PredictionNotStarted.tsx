import { Stack, Center, Image, Text } from "@mantine/core";

export default function PredictionNotStarted() {
  return (
    <Stack align="center" justify="center" spacing="lg" py="xl">
      <Center>
        <Image
          mx="auto"
          maw="40%"
          opacity={0.3}
          alt="tungsten_logo"
          src="/tungsten_greyed_out_logo.png"
        />
      </Center>
      <Text color="gray.6" fz="md">
        Click &#34;Run&#34; to see amazing results.
      </Text>
    </Stack>
  );
}
