import { Stack, createStyles, rem, Center, Flex } from "@mantine/core";

const useStyles = createStyles((theme) => ({
  statusCode: {
    fontSize: rem(150),
    fontWeight: 600,
    color: theme.colors["tungsten-main"],
  },
  reason: {
    fontSize: rem(38),
    fontWeight: 600,
    color: theme.colors["tungsten-main"],
  },
  explanation: {
    fontSize: rem(22),
    fontWeight: 500,
  },
}));

function ErrorContainer(statusCode: string, reason: string, explanation: string) {
  const { classes } = useStyles();

  return (
    <Flex sx={{ flexGrow: 1 }} justify="center" direction="column">
      <Center style={{ height: "100%" }}>
        <Stack spacing={0} align="center">
          <div className={classes.statusCode}>{statusCode}</div>
          <div className={classes.reason}>{reason}</div>
          <div className={classes.explanation}>{explanation}</div>
        </Stack>
      </Center>
    </Flex>
  );
}

export default ErrorContainer;
