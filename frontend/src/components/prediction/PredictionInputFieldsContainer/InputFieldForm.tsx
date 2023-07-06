import { Group, NumberInput, Select, Slider, Switch, Textarea } from "@mantine/core";
import { IconChevronDown } from "@tabler/icons-react";

import FileInputWithDropzone from "@/components/files/FileInputWithDropzone";
import { useInputFormContext } from "@/contexts/prediction-input-form-context";
import { InputFieldType as T, getInputFieldType } from "@/utils/prediction";
import { InputSchemaPropsObject, IOFileType } from "@/types";

const MAX_FILE_SIZE = 1 * 1024 ** 3;

const buildSelectBaseProps = () => ({
  placeholder: "Select one",
  rightSection: <IconChevronDown size="1rem" />,
});

const buildSliderBaseProps = (fieldProp: InputSchemaPropsObject) => ({
  min: fieldProp.minimum ?? undefined,
  max: fieldProp.maximum ?? undefined,
  styles: { markLabel: { display: "none" }, label: { display: "none" } },
});

const buildNumberInputBaseProps = (fieldProp: InputSchemaPropsObject) => ({
  min: fieldProp.minimum ?? undefined,
  max: fieldProp.maximum ?? undefined,
  stepHoldDelay: 500,
  stepHoldInterval: 100,
  removeTrailingZeros: true,
});

export interface InputFieldFormProps {
  fieldName: string;
  fieldProp: InputSchemaPropsObject;
  filetype: IOFileType;
}

export default function InputFieldForm({ fieldName, fieldProp, filetype }: InputFieldFormProps) {
  const form = useInputFormContext();
  const formInputProps = form.getInputProps(fieldName);
  const fieldtype = getInputFieldType(fieldProp, filetype);

  switch (fieldtype) {
    case T.FILE:
      return (
        <FileInputWithDropzone
          filetype={filetype}
          maxsize={MAX_FILE_SIZE}
          iconSize="1.1rem"
          textProps={{ size: "sm" }}
          {...formInputProps}
        />
      );

    case T.STR:
    case T.CONSTR:
      return <Textarea autosize minRows={1} {...formInputProps} />;

    case T.INT:
    case T.FLOAT:
      return (
        <NumberInput
          w="100%"
          precision={fieldtype === T.INT ? 1 : 10}
          step={fieldtype === T.INT ? 1 : 0.01}
          {...buildNumberInputBaseProps(fieldProp)}
          {...formInputProps}
        />
      );
    case T.CONINT:
    case T.CONFLOAT:
      return (
        <Group spacing="1rem">
          <NumberInput
            w="calc(30% - 1rem)"
            precision={fieldtype === T.CONINT ? 0 : 10}
            step={fieldtype === T.CONINT ? 1 : 0.01}
            {...buildNumberInputBaseProps(fieldProp)}
            {...formInputProps}
          />
          <Slider
            w="70%"
            value={formInputProps.value}
            onChange={formInputProps.onChange}
            step={fieldtype === T.CONINT ? 1 : 0.01}
            {...buildSliderBaseProps(fieldProp)}
          />
        </Group>
      );

    case T.STR_CHOICE:
      if (fieldProp.choices == null) throw TypeError("No choices");
      return (
        <Select
          data={fieldProp.choices as string[]}
          {...formInputProps}
          {...buildSelectBaseProps()}
        />
      );

    case T.BOOL:
      return <Switch {...formInputProps} />;

    case T.INT_CHOICE:
    case T.FLOAT_CHOICE:
      if (fieldProp.choices == null) throw TypeError("No choices");
      return (
        <Select
          value={formInputProps.value != null ? formInputProps.value.toString() : null}
          data={fieldProp.choices.map((v) => v.toString())}
          onChange={(v) => {
            let transformedValue: number | null = null;
            if (typeof v === "string") {
              transformedValue = Number(v);
            }
            formInputProps.onChange(transformedValue);
          }}
          {...Object.fromEntries(
            Object.entries(formInputProps).filter((e) => !["onChange", "value"].includes(e[0])),
          )}
        />
      );

    default:
      throw TypeError(`Unknown field type ${fieldtype}`);
  }
}
