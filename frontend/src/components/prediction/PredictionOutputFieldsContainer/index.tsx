import { MantineSize, Stack } from "@mantine/core";
import { ReactNode } from "react";

import { OutputSchema, IOFileType } from "@/types";
import IOFieldLabel from "../IOFieldLabel";

import OutputFieldView from "./OutputFieldView";

export interface PredictionOutputFieldsContainerProps {
  schema: OutputSchema;
  filetypes: { [key: string]: IOFileType };
  values: { [key: string]: string | number | object | boolean };
  spacing?: MantineSize;
}

export function PredictionOutputFieldsContainer({
  schema,
  filetypes,
  values,
  spacing,
}: PredictionOutputFieldsContainerProps) {
  const namedComponents: {
    name: string;
    component: ReactNode;
  }[] = [];

  function buildFieldComponent(fieldName: string) {
    const fieldProp = schema.properties[fieldName];
    const filetype = filetypes[fieldName];
    return (
      <OutputFieldView
        fieldName={fieldName}
        propObj={fieldProp}
        filetype={filetype}
        itemFiletype={filetypes[`${fieldName}.$item`]}
        value={values[fieldName]}
      />
    );
  }
  // Build components
  Object.keys(schema.properties).forEach((fieldName) => {
    namedComponents.push({
      name: fieldName,
      component: buildFieldComponent(fieldName),
    });
  });
  return (
    <Stack fz="md" spacing={spacing}>
      {namedComponents.map((nc) => (
        <div key={`output-field-${nc.name}`}>
          <IOFieldLabel name={nc.name} />
          {nc.component}
        </div>
      ))}
    </Stack>
  );
}

PredictionOutputFieldsContainer.defaultProps = {
  spacing: "md",
};
