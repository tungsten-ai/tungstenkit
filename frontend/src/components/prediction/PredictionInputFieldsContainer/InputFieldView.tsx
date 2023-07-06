import FileView from "@/components/files/FileView";
import { IOFileType } from "@/types";
import { CodeBlockWithLinebreak } from "../CodeBlockWithLinebreak";

export interface InputFieldViewProps {
  filetype?: IOFileType;
  value: any;
}

export default function InputFieldView({ filetype, value }: InputFieldViewProps) {
  if (filetype) {
    return <FileView file={value} filetype={filetype} />;
  }
  if (value !== undefined) {
    return (
      <CodeBlockWithLinebreak>
        {typeof value !== "string" ? value.toString() : value}
      </CodeBlockWithLinebreak>
    );
  }
  throw Error("`value` is undefined");
}
