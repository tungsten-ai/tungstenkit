import { Stack } from "@mantine/core";

import FileView from "@/components/files/FileView";
import { getOutputFieldType, OutputFieldType as T } from "@/utils/prediction";
import { OutputSchemaPropsObject, IOFileType } from "@/types";
import { CodeBlockWithLinebreak } from "../CodeBlockWithLinebreak";
import IOFieldLabel from "../IOFieldLabel";

export interface OutputFieldViewProps {
  fieldName: string;
  propObj: OutputSchemaPropsObject;
  filetype?: IOFileType;
  itemFiletype?: IOFileType;
  value: any;
}

export default function OutputFieldView({
  fieldName,
  propObj,
  filetype,
  itemFiletype,
  value,
}: OutputFieldViewProps) {
  const fieldtype = getOutputFieldType(propObj, filetype, itemFiletype);

  switch (fieldtype) {
    case T.FILE:
      return <FileView file={value} filetype={filetype} />;

    case T.FILE_LIST:
      return (
        <Stack spacing="xxs">
          {value.map((v: any, i: number) => (
            <OutputFieldView
              key={`${fieldName}-${i.toString()}`}
              fieldName={`${fieldName}-${i.toString()}`}
              propObj={propObj.items as OutputSchemaPropsObject}
              filetype={itemFiletype}
              value={v}
            />
          ))}
        </Stack>
      );

    case T.FILE_DICT:
      return (
        <Stack spacing="xxs">
          {Object.keys(value).map((key) => (
            <div key={`${fieldName}-${key}`}>
              <IOFieldLabel key={key} description={key} />
              <OutputFieldView
                fieldName={`${fieldName}-${key}`}
                propObj={propObj.additionalProperties as OutputSchemaPropsObject}
                filetype={itemFiletype}
                value={value[key]}
              />
            </div>
          ))}
        </Stack>
      );

    case T.STR:
      return <CodeBlockWithLinebreak>{value}</CodeBlockWithLinebreak>;

    case T.BOOL:
    case T.NUMBER:
      return <CodeBlockWithLinebreak>{value.toString()}</CodeBlockWithLinebreak>;

    case T.JSON:
      return (
        <CodeBlockWithLinebreak>{JSON.stringify(value, undefined, 2)}</CodeBlockWithLinebreak>
      );

    default:
      throw TypeError(`Unkown output field type ${fieldtype} `);
  }
}
