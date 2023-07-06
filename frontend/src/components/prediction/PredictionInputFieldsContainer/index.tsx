import { Box, Collapse, MantineSize, Space, Stack } from "@mantine/core";
import { ReactNode } from "react";

import { InputSchema, IOFileType } from "@/types";
import IOFieldLabel from "../IOFieldLabel";

import InputFieldForm from "./InputFieldForm";
import InputFieldView from "./InputFieldView";

export interface PredictionInputFieldsContainerProps {
  showOptions?: boolean;
  schema: InputSchema;
  filetypes: { [key: string]: IOFileType };
  values?: { [key: string]: string | number | boolean };
  withForm?: boolean;
  spacing?: MantineSize;
}

export function PredictionInputFieldsContainer({
  withForm,
  schema,
  filetypes,
  values,
  showOptions,
  spacing,
}: PredictionInputFieldsContainerProps) {
  const requiredFieldComponents: {
    name: string;
    component: ReactNode;
  }[] = [];
  const optionalFieldComponents: {
    name: string;
    component: ReactNode;
  }[] = [];

  function checkIfRequired(fieldName: string) {
    return schema?.required != null && schema?.required.includes(fieldName);
  }

  function buildFieldComponent(fieldName: string) {
    const fieldProp = schema.properties[fieldName];
    const filetype = filetypes[fieldName];
    return withForm ? (
      <InputFieldForm fieldName={fieldName} fieldProp={fieldProp} filetype={filetype} />
    ) : (
      <InputFieldView
        filetype={filetype}
        value={values === undefined ? undefined : values[fieldName]}
      />
    );
  }

  // Build required components
  Object.keys(schema.properties).forEach((fieldName) => {
    if (checkIfRequired(fieldName)) {
      requiredFieldComponents.push({
        name: fieldName,
        component: buildFieldComponent(fieldName),
      });
    }
  });

  // Build optional components
  Object.keys(schema.properties).forEach((fieldName) => {
    if (!checkIfRequired(fieldName)) {
      optionalFieldComponents.push({
        name: fieldName,
        component: buildFieldComponent(fieldName),
      });
    }
  });

  return (
    <Box fz="md">
      <Stack spacing={spacing}>
        {requiredFieldComponents.map((nc) => (
          <div key={`input-field-${nc.name}`}>
            <IOFieldLabel
              name={nc.name}
              required={!!withForm}
              description={withForm ? schema.properties[nc.name].description : undefined}
            />
            {nc.component}
          </div>
        ))}
      </Stack>
      {showOptions && optionalFieldComponents.length > 0 ? <Space h={spacing} /> : undefined}
      <Collapse in={showOptions ?? false}>
        <Stack spacing={spacing}>
          {optionalFieldComponents.map((nc) => (
            <div key={`input-field-${nc.name}`}>
              <IOFieldLabel
                name={nc.name}
                required={false}
                description={withForm ? schema.properties[nc.name].description : undefined}
              />
              {nc.component}
            </div>
          ))}
        </Stack>
      </Collapse>
    </Box>
  );
}

PredictionInputFieldsContainer.defaultProps = {
  spacing: "md",
  values: undefined,
  showOptions: false,
};
