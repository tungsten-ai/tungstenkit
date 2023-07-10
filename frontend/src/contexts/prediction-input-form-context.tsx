import { createFormContext } from "@mantine/form";

import { getInputFieldType, InputFieldType as T } from "@/utils/prediction";
import { isValidHttpUrl } from "@/utils/validators";
import { InputSchema, IOFileType } from "@/types";

type InputFormFieldValue = File | string | number | boolean | null;

interface InputFormData {
  [key: string]: InputFormFieldValue;
}

// Data stored in session storage
interface StoredInputFormData {
  path: string;
  schema: InputSchema;
  filetypes: { [key: string]: IOFileType };
  values: { [key: string]: InputFormFieldValue };
}

type FormValidator = (value: InputFormFieldValue) => string | undefined;

const REQUIRED_ERR_MSG = "This field is required.";

const [InputFormProvider, useInputFormContext, useInputFormOriginal] =
  createFormContext<InputFormData>();

const useInputForm = ({
  schema,
  filetypes,
  initialValues,
}: {
  schema: InputSchema;
  filetypes: { [key: string]: IOFileType };
  initialValues?: { [key: string]: InputFormFieldValue };
}) => {
  const inputFieldNames = Object.keys(schema.properties);

  function getInitialInputValue(fieldName: string) {
    /** Set the user-defined default value or the form's default */
    const propObj = schema.properties[fieldName];
    const fieldtype = getInputFieldType(propObj, filetypes[fieldName]);

    let defaultValue: InputFormFieldValue | undefined = propObj.default;
    if (defaultValue == null) {
      switch (fieldtype) {
        case T.STR:
        case T.CONSTR:
        case T.INT:
        case T.FLOAT:
        case T.CONINT:
        case T.CONFLOAT:
          defaultValue = "";
          break;
        case T.BOOL:
          defaultValue = false;
          break;
        default:
          defaultValue = null;
          break;
      }
    }
    return defaultValue;
  }

  function buildInputFieldValidator(fieldName: string) {
    const propObj = schema.properties[fieldName];
    const isRequired = schema.required != null && schema.required.includes(fieldName);
    const formType = getInputFieldType(propObj, filetypes[fieldName]);

    const fileValidator: FormValidator = (value) => {
      if (value == null) return isRequired ? REQUIRED_ERR_MSG : undefined;
      const valueType = typeof value;
      if (valueType !== "string") {
        if (typeof value === "string" && !isValidHttpUrl(value)) {
          return "Not an HTTP(s) URL.";
        }
      }
      return undefined;
    };

    const strValidator: FormValidator = (value) => {
      if (value == null) return isRequired ? REQUIRED_ERR_MSG : undefined;
      if (typeof value !== "string") throw TypeError("Invalid type for string form");
      if (value.length === 0) return isRequired ? REQUIRED_ERR_MSG : undefined;

      if (propObj.max_length !== undefined && value.length > propObj.max_length) {
        return `Maximum length is ${propObj.max_length} characters.`;
      }
      if (propObj.min_length !== undefined && value.length < propObj.min_length) {
        return `Minimum length is ${propObj.min_length} characters.`;
      }
      return undefined;
    };

    const numberValidator: FormValidator = (value) => {
      if (value == null || (typeof value === "string" && value.length === 0))
        return isRequired ? REQUIRED_ERR_MSG : undefined;
      if (typeof value !== "number") throw TypeError("Invalid type for number form");

      if (propObj.maximum !== undefined && value > propObj.maximum) {
        return `Maximum value is ${propObj.maximum}`;
      }
      if (propObj.minimum !== undefined && value < propObj.minimum) {
        return `Minimum value is ${propObj.minimum}.`;
      }
      return undefined;
    };

    switch (formType) {
      case T.FILE:
        return fileValidator;
      case T.STR:
      case T.CONSTR:
      case T.STR_CHOICE:
        return strValidator;
      case T.CONFLOAT:
      case T.FLOAT:
      case T.CONINT:
      case T.INT:
      case T.INT_CHOICE:
      case T.FLOAT_CHOICE:
        return numberValidator;
      default:
        return undefined;
    }
  }

  function fillDefault(fieldName: string, value: InputFormFieldValue) {
    /** Fill default value if invalid */
    const propObj = schema.properties[fieldName];
    let transformedValue: File | string | number | boolean;

    if (value == null) {
      transformedValue = propObj.default as File | string | number | boolean;
    } else {
      transformedValue = value;
    }
    return transformedValue;
  }

  const formInitialValues = Object.fromEntries(
    inputFieldNames.map((n) => [
      n,
      initialValues && initialValues[n] ? initialValues[n] : getInitialInputValue(n),
    ]),
  );
  const {
    onSubmit: onSubmitOriginal,
    values,
    setFieldValue,
    isTouched,
    setTouched,
    ...formMembers
  } = useInputFormOriginal({
    initialValues: formInitialValues,
    validate: Object.fromEntries(inputFieldNames.map((n) => [n, buildInputFieldValidator(n)])),
  });

  // Wrap the original onSubmit callback for the case where an optional field is nullified
  const onSubmit: typeof onSubmitOriginal = (handleSubmit, handleValidationFailure) => {
    const wrapped: typeof handleSubmit = (v, event) =>
      handleSubmit(
        Object.fromEntries(inputFieldNames.map((n) => [n, fillDefault(n, v[n])])),
        event,
      );
    return onSubmitOriginal(wrapped, handleValidationFailure);
  };

  return {
    onSubmit,
    values,
    setFieldValue,
    isTouched,
    setTouched,
    ...formMembers,
  };
};

export type { InputFormFieldValue, InputFormData };
export { InputFormProvider, useInputFormContext, useInputForm };
