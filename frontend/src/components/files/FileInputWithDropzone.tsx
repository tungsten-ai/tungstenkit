import {
  Box,
  CloseButton,
  Group,
  Input,
  InputWrapperBaseProps,
  MantineSize,
  Stack,
  Text,
  TextProps,
  useInputProps,
  useMantineTheme,
} from "@mantine/core";
import { Dropzone } from "@mantine/dropzone";
import { useUncontrolled } from "@mantine/hooks";
import {
  IconFile,
  IconHeadphones,
  IconPhoto,
  IconUpload,
  IconVideo,
  IconX,
  TablerIconsProps,
} from "@tabler/icons-react";
import { extensions } from "mime-types";

import { IOFileType } from "@/types";
import { formatBytes } from "@/utils/bytesize";
import { Accept } from "react-dropzone";
import FileView from "./FileView";

export interface FileInputWithDropzoneProps extends InputWrapperBaseProps {
  filetype: IOFileType;

  /** Called when user picks files */
  onChange?: (file: File | string) => void;

  /** Controlled input value */
  value?: File | string | null;

  /** Uncontrolled input value */
  defaultValue?: File | string | null;

  /** Max file size */
  maxsize?: number;

  /** Icon size */
  iconSize?: MantineSize;

  /** Text props */
  textProps?: TextProps;
}

const defaultProps = {
  iconSize: "1.1rem",
  textProps: { fz: "md" },
};

export default function FileInputWithDropzone(props: FileInputWithDropzoneProps) {
  const { wrapperProps, value, defaultValue, filetype, onChange, textProps, maxsize, iconSize } =
    useInputProps("DropzoneInput", defaultProps, props);
  const [file, setFile] = useUncontrolled<File | string | null | undefined>({
    value,
    onChange,
    finalValue: null,
  });

  const hasFile = !!file;
  const theme = useMantineTheme();

  function buildPreview(f: File | string) {
    const fileView = <FileView file={f} filetype={filetype} />;
    const fileDescription =
      typeof f !== defaultValue ? (
        <Group maw="100%" spacing="xs">
          <Text fz="xs" color="gray.7">
            {typeof f === "string"
              ? decodeURI(f.split("/").pop() as string)
              : `${f.name} (${formatBytes(f.size)})`}
          </Text>

          <CloseButton title="Delete file" color="gray.7" onClick={() => setFile(null)} />
        </Group>
      ) : undefined;
    return (
      <Stack spacing="xs" maw="100%">
        {filetype === "image" ? <Box maw="50%">{fileView}</Box> : fileView}
        {fileDescription}
      </Stack>
    );
  }

  function buildIdleIcon() {
    let IconIdle: (props: TablerIconsProps) => JSX.Element;
    if (filetype === "image") {
      IconIdle = IconPhoto;
    } else if (filetype === "video") {
      IconIdle = IconVideo;
    } else if (filetype === "audio") {
      IconIdle = IconHeadphones;
    } else {
      IconIdle = IconFile;
    }
    return <IconIdle size={iconSize} />;
  }

  function buildAcceptTypes(): string[] | Accept | undefined {
    if (["audio", "video", "image"].includes(filetype)) {
      const accept: { [key: string]: string[] } = {};
      for (const [t, exts] of Object.entries(extensions)) {
        if (t.startsWith(filetype)) {
          accept[t] = exts.map((ext) => `.${ext}`);
        }
      }
      return accept;
    }
    return undefined;
  }

  if (defaultValue) {
    setFile(defaultValue);
  }

  return (
    <Input.Wrapper {...wrapperProps}>
      <Stack spacing="xs">
        {hasFile ? buildPreview(file) : undefined}
        <Dropzone
          onDrop={(files) => {
            if (files.length > 0 && onChange !== undefined) {
              setFile(files[0]);
              onChange(files[0]);
            }
          }}
          maxSize={maxsize}
          accept={buildAcceptTypes()}
          maxFiles={1}
        >
          <Group position="center" spacing="md" style={{ pointerEvents: "none" }}>
            <Dropzone.Accept>
              <IconUpload color={theme.colors[theme.primaryColor][5]} size={iconSize} />
            </Dropzone.Accept>
            <Dropzone.Reject>
              <IconX color={theme.colors.red[6]} size={iconSize} />
            </Dropzone.Reject>
            <Dropzone.Idle>{buildIdleIcon()}</Dropzone.Idle>

            <Text inline {...textProps}>
              Drag {filetype} file here or click to select
            </Text>
          </Group>
        </Dropzone>
      </Stack>
    </Input.Wrapper>
  );
}
