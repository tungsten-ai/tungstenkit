import { Button } from "@mantine/core";
import { IconDownload } from "@tabler/icons-react";

export default function FileDownloadButton({ src }: { src: string }) {
  return (
    <Button
      component="a"
      href={src}
      target="_blank"
      variant="default"
      leftIcon={<IconDownload size="1rem" />}
    >
      Download file
    </Button>
  );
}
