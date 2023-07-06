interface InputSchemaPropsObject {
  title: string;
  description: string;
  type: "string" | "integer" | "number" | "boolean";
  default?: string | number | boolean;
  maximum?: number;
  minimum?: number;
  min_length?: number;
  max_length?: number;
  choices?: string[] | number[];
}

interface InputSchema {
  required?: string[];
  properties: {
    [key: string]: InputSchemaPropsObject;
  };
}

interface OutputSchemaPropsObject {
  type?: "object" | "array" | "string" | "integer" | "number" | "boolean";
  $ref?: string;
  additionalProperties?: OutputSchemaPropsObject;
  items?: OutputSchemaPropsObject;
}

interface OutputSchema {
  properties: { [key: string]: OutputSchemaPropsObject };
  definitions: {
    [key: string]: OutputSchema;
  };
}

type IOFileType = "image" | "audio" | "video" | "binary";

interface Model {
  name: string;
  avatar_url: string;

  input_schema: InputSchema;
  output_schema: OutputSchema;
  demo_output_schema: OutputSchema;

  input_filetypes: {
    [key: string]: IOFileType;
  };
  output_filetypes: {
    [key: string]: IOFileType;
  };
  demo_output_filetypes: {
    [key: string]: IOFileType;
  };
}


export type {
  Model,
  IOFileType,
  InputSchema,
  InputSchemaPropsObject,
  OutputSchema,
  OutputSchemaPropsObject,
};
