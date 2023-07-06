import { InputSchemaPropsObject, OutputSchemaPropsObject, IOFileType, InputSchema } from "@/types";

export enum InputFieldType {
  FILE,
  STR,
  CONSTR,
  INT,
  CONINT,
  FLOAT,
  CONFLOAT,
  BOOL,
  STR_CHOICE,
  INT_CHOICE,
  FLOAT_CHOICE,
}

export enum OutputFieldType {
  FILE,
  FILE_LIST,
  FILE_DICT,
  STR,
  NUMBER,
  BOOL,
  JSON,
}

export function getInputFieldType(
  propObj: InputSchemaPropsObject,
  filetype: IOFileType | undefined,
): InputFieldType {
  // File
  if (filetype) {
    return InputFieldType.FILE;
  }

  // Choices
  if (
    !!propObj.choices &&
    propObj.type &&
    ["string", "number", "integer"].includes(propObj.type)
  ) {
    if (propObj.type === "string") {
      return InputFieldType.STR_CHOICE;
    }

    if (propObj.type === "integer") {
      return InputFieldType.INT_CHOICE;
    }

    if (propObj.type === "number") {
      return InputFieldType.FLOAT_CHOICE;
    }
  }

  // Integer
  if (propObj.type === "integer") {
    if (propObj.minimum !== undefined || propObj.maximum !== undefined) {
      return InputFieldType.CONINT;
    }
    return InputFieldType.INT;
  }

  // Float
  if (propObj.type === "number") {
    if (propObj.minimum !== undefined || propObj.maximum !== undefined) {
      return InputFieldType.CONFLOAT;
    }
    return InputFieldType.FLOAT;
  }

  // Bool
  if (propObj.type === "boolean") {
    return InputFieldType.BOOL;
  }

  // String
  if (propObj.min_length !== undefined || propObj.max_length !== undefined) {
    return InputFieldType.CONSTR;
  }
  return InputFieldType.STR;
}

export function getOutputFieldType(
  propObj: OutputSchemaPropsObject,
  filetype: IOFileType | undefined,
  itemFiletype: IOFileType | undefined,
): OutputFieldType {
  const propKeys = Object.keys(propObj);
  const isArray = propObj.type === "array";
  const isDict = propObj.type === "object" && propKeys.includes("additionalProperties");

  if (filetype) {
    return OutputFieldType.FILE;
  }

  if (isArray && itemFiletype) {
    return OutputFieldType.FILE_LIST;
  }

  if (isDict && itemFiletype) {
    return OutputFieldType.FILE_DICT;
  }

  if (propObj.type === "integer" || propObj.type === "number") {
    return OutputFieldType.NUMBER;
  }

  if (propObj.type === "boolean") {
    return OutputFieldType.BOOL;
  }

  if (propObj.type === "string") {
    return OutputFieldType.STR;
  }

  return OutputFieldType.JSON;
}

export function hasInputOptions(inputSchema: InputSchema) {
  return (
    inputSchema.required != null &&
    Object.keys(inputSchema.properties).some(
      (fieldName) => !inputSchema.required?.includes(fieldName),
    )
  );
}
