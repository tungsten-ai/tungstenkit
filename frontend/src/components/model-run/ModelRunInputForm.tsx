import { Button, Group, Stack, Space } from "@mantine/core";
import { IconPlayerPlayFilled, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import {
  PredictionInputFieldsContainer,
  PredictionInputOptionCheckbox,
} from "@/components/prediction";
import {
  InputFormData,
  InputFormProvider,
  useInputForm,
} from "@/contexts/prediction-input-form-context";
import { Model } from "@/types";
import { getClientSideAxios } from "@/axios";
import getFileAPI from "@/api/file";
import { useRouter } from "next/router";
import { PredictionInputFieldValue } from "@/api/prediction.types";
import { useTimeout } from "@mantine/hooks";
import { hasInputOptions } from "@/utils/prediction";

export interface ModelRunInputFormProps {
  model: Model;
  onFormSubmit: (input: { [key: string]: PredictionInputFieldValue }) => void;
  onError: () => void;
}

export function ModelRunInputForm({
  model,
  onFormSubmit,
  onError,
}: ModelRunInputFormProps) {
  const { input_schema: schema, input_filetypes: filetypes } = model;

  const router = useRouter();
  const axiosInstance = getClientSideAxios();
  const fileAPI = getFileAPI(axiosInstance);

  const [showOptions, setShowOptions] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [throttling, setThrottling] = useState(false);
  const { start: startThrottlingTimeout } = useTimeout(() => setThrottling(false), 2000);

  const startThrottling = () => {
    setThrottling(true);
    startThrottlingTimeout();
  };

  const form = useInputForm({
    schema,
    filetypes,
  });

  router.events?.on("routeChangeComplete", () => {
    setSubmitting(false);
    setThrottling(false);
  });
  router.events?.on("routeChangeError", () => {
    setSubmitting(false);
    setThrottling(false);
  });

  const uploadFile = async (file: File | string | null) => {
    let url: string | null | undefined;

    if (file instanceof File) {
      // Upload file
      url = await fileAPI
        .upload(file)
        .then((resp) => resp.data.serving_url)
        .catch(() => {
          return "";
        });
    } else {
      // Pass if file is already url or null
      url = file;
    }

    return url;
  };

  const onSubmit = async (formData: InputFormData) => {
    setSubmitting(true);
    startThrottling();
    const inputFieldNames = Object.keys(model.input_schema.properties);

    const fileFieldKeys = inputFieldNames.filter((n) => !!model.input_filetypes[n]);
    const promises = fileFieldKeys.map((n) => uploadFile(formData[n] as File | string | null));
    const fileFieldValues = await Promise.all(promises);

    // On error, return without mutation.
    if (fileFieldValues.some((value) => value === "")) {
      onError();
      setSubmitting(false);
      return;
    }

    const input = Object.fromEntries(
      inputFieldNames.map((fieldName) => {
        const fileIndex = fileFieldKeys.indexOf(fieldName);
        if (fileIndex >= 0) {
          return [fieldName, fileFieldValues[fileIndex] as PredictionInputFieldValue];
        }
        return [fieldName, formData[fieldName] as PredictionInputFieldValue];
      }),
    );

    onFormSubmit(input);
    setSubmitting(false);
  };

  const { setValues: setFormValues } = form;


  return (
    <Stack w="100%" spacing="0">
      {hasInputOptions(model.input_schema) ? (
        <Group position="right">
          <PredictionInputOptionCheckbox checked={showOptions} onChange={setShowOptions} />
        </Group>
      ) : undefined}
      <InputFormProvider form={form}>
        <form onSubmit={form.onSubmit(onSubmit)}>
          <PredictionInputFieldsContainer
            withForm
            schema={schema}
            filetypes={filetypes}
            showOptions={showOptions}
          />
          <Space h="xxl" />
          <Group position="right" grow>
            <Button onClick={form.reset} leftIcon={<IconTrash size="1rem" />} variant="default">
              Reset
            </Button>
            <Button
              leftIcon={<IconPlayerPlayFilled size="1rem" />}
              color="run-green.4"
              loading={submitting || throttling}
              type={!submitting && !throttling ? "submit" : undefined}
            >
              Run
            </Button>
          </Group>
        </form>
      </InputFormProvider>
    </Stack>
  );
}
