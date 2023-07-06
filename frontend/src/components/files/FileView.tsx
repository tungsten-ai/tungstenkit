import { Box } from "@mantine/core";
import { IOFileType } from "@/types";
import { ReactNode, forwardRef, useEffect, useState } from "react";
import { lookup } from "mime-types";
import { LazyLoadImage } from "react-lazy-load-image-component";
import AudioComponent from "./AudioComponent";
import FileDownloadButton from "./FileDownloadButton";
import VideoComponent from "./VideoComponent";

export interface FileViewProps {
  file: File | string;
  filetype?: IOFileType;
}

const getMimeType = (file: string | File) => {
  if (typeof file !== "string") {
    return file.type;
  }
  const gussedMimeType = lookup(file);
  if (gussedMimeType) {
    return gussedMimeType;
  }
  return "application/octet-stream";
};

const FileView = forwardRef<HTMLDivElement, FileViewProps>((props: FileViewProps, ref) => {
  const { file, filetype } = props;
  const [url, setURL] = useState<string>(
    typeof file === "string" ? file : URL.createObjectURL(file),
  );
  const mimeType = getMimeType(file);
  const emptyBox = <Box />;
  let component: ReactNode;

  useEffect(() => {
    setURL(typeof file === "string" ? file : URL.createObjectURL(file));
  }, [file]);

  switch (filetype) {
    case "image":
      component = url ? (
        <LazyLoadImage
          src={url}
          style={{ maxWidth: "100%", maxHeight: "100%" }}
          alt={filetype}
          // loading="lazy"
        />
      ) : (
        emptyBox
      );
      break;
    case "video":
      component = url ? <VideoComponent src={url} mimeType={mimeType} /> : emptyBox;
      break;
    case "audio":
      component = url ? <AudioComponent src={url} /> : emptyBox;
      break;
    default:
      component = url ? <FileDownloadButton src={url} /> : emptyBox;
  }
  return (
    <Box maw="100%" mah="100%" ref={ref}>
      {component}
    </Box>
  );
});

FileView.defaultProps = {
  filetype: "binary",
};

FileView.displayName = "FileView";

export default FileView;
