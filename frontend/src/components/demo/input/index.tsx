import getModelAPI from "@/api/model";
import { getClientSideAxios } from "@/axios";
import { setModelExample, setTrace, updateModelOutput } from "@/redux/singleModelSlice";
import DoubleArrowIcon from "@mui/icons-material/DoubleArrow";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { Box, Button, CircularProgress, Typography } from "@mui/material";
import { ChangeEvent, Dispatch, SetStateAction, useEffect, useState } from "react";
import { Control, Controller, FieldErrors, FieldValues, useForm } from "react-hook-form";
import { useQuery } from "react-query";
import { useDispatch, useSelector } from "react-redux";
import InputBoolean from "./InputBoolean";
import { default as InputDropzone } from "./InputDropzone";
import InputNumber from "./InputNumber";
import InputSelect from "./InputSelect";
import InputText from "./InputText";
import { Checkbox } from "@mantine/core";
import Appbar from "@/components/common/Appbar";
import { AppState } from "@/redux/store";

const buildInputComponent = (
  propName: string,
  propObj: inputProp,
  requiredArray: string [],
  components: JSX.Element[],
  control: Control<FieldValues>,
  errors: FieldErrors<FieldValues>,
) => {
  const inputTypesWithSelectOption = ["string", "integer", "number"];

  const required = requiredArray !== null && requiredArray.includes(propName) ? true : false;
  const choices : string[]|number[] = propObj.choices ?? [""];
  const description = propObj.description ?? "";
  const defaultValue = propObj.default ?? "";

  const controllerProps = {
    key: propName,
    name: propName,
    control: control,
    defaultValue: defaultValue,
    rules: { required: required },
  };

  const inputProps = {
    name: propName,
    description,
    required,
    options: choices,
    errors,
  };

  if (choices && inputTypesWithSelectOption.includes(propObj.type as string)) {
    // Select
    components.push(
      <Controller
        {...controllerProps}
        render={({ field: { onChange, value } }) => (
          <InputSelect {...inputProps} value={value} onChange={onChange} />
        )}
      />,
    );
  } else if (propObj.allOf) {  //TODO: check if .allOf is correct method of branching to media
    // Image
    components.push(
      <Controller
        {...controllerProps}
        defaultValue={defaultValue}
        render={({ field: { onChange, value } }) => {
          return (
            <InputDropzone
              {...inputProps}
              value={value}
              onChange={(e: ChangeEvent<HTMLInputElement>):void => {
                if ( (e.target as HTMLInputElement|null)?.files?.length==0) {  //The controller object cannot remove the input files by itself, so we have to do it ourselves 
                  const inputfield : HTMLElement|null = (document.getElementById("inputDropzone"));
                  if (inputfield) (inputfield as HTMLInputElement).value = ""
                }
                onChange(e.target?.files[0]);
              }}
            />
          );
        }}
      />,
    );
  } else if (propObj.type === "string") {
    // String
    components.push(
      <Controller
        {...controllerProps}
        render={({ field: { onChange, value } }) => (
          <InputText {...inputProps} value={value} onChange={onChange} />
        )}
      />,
    );
  } else if (propObj.type === "boolean") {
    // Boolean
    components.push(
      <Controller
        {...controllerProps}
        render={({ field: { onChange, value } }) => (
          <InputBoolean {...inputProps} value={value} onChange={onChange} />
        )}
      />,
    );
  } else if (propObj.type === "integer") {
    // Integer
    components.push(
      <Controller
        {...controllerProps}
        render={({ field: { onChange, value } }) => (
          <InputNumber
            {...inputProps}
            value={value}
            onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
              onChange(parseFloat((e.target as HTMLInputElement).value));
            }}
            integer={true}
            minimum={propObj.minimum ?? null}
            maximum={propObj.maximum ?? null}
          />
        )}
      />,
    );
  } else if (propObj.type === "number") {
    // float
    components.push(
      <Controller
        {...controllerProps}
        render={({ field: { onChange, value } }) => (
          <InputNumber
            {...inputProps}
            value={value}
            onChange={(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
              onChange(parseFloat((e.target as HTMLInputElement).value));
            }}
            integer={false}
            minimum={propObj.minimum ?? null}
            maximum={propObj.maximum ?? null}
          />
        )}
      />,
    );
  }
};

const buildAllInputComponents = (
  model: model,
  control: Control<FieldValues>,
  errors: FieldErrors<FieldValues>,
  showOptionalParams: boolean,
) => {
  const components: JSX.Element[] = [];

  if (model.input_schema) {
    const requiredArray = model.input_schema.required;
    for (const propName in model.input_schema.properties) {
      if (requiredArray.includes(propName) || showOptionalParams) {
        const propObj = model.input_schema.properties[propName];
        buildInputComponent(propName, propObj, requiredArray, components, control, errors);
      }
    }
  }
  return components;
};

function DemoInput({ model, doQuery, setDoQuery }: { model: model; doQuery: boolean; setDoQuery: Dispatch<SetStateAction<boolean>> }) {
  const [predictionId, setPredictionId] = useState("");
  const [showOptionalParams, setShowOptionalParams] = useState(false);
  const dispatch = useDispatch();

  const axiosInstance = getClientSideAxios();
  const modelAPI = getModelAPI(axiosInstance);

  const example : predictionData = useSelector((state: AppState ) => state.singleModel.example);
  const exampleInput = example.input
  const {
    control,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm();

  const inputComponents = buildAllInputComponents(model, control, errors, showOptionalParams);
  useEffect(() => {
    for (const propName in exampleInput) {
      setValue(propName, exampleInput[propName]);
    }
  }, []);

  const tabs = [
    <Box key={1} sx={{display:"flex"}}>
      <Typography variant="mainTextSmall" sx={{marginLeft:"5px"}}>Input</Typography>
    </Box>
  ]

  useQuery("", () => modelAPI.getPrediction(predictionId), {
    enabled: doQuery,
    refetchInterval: 750,
    onSuccess: (output: httpResponsePrediction) => {
      const status = output.data.status;
      const log = output.data.logs;
      dispatch(setTrace({ trace: `${log ?? status}\n` }));
      dispatch(updateModelOutput({ output:output.data,status}));
      if (status == "failure") {
        dispatch(setTrace({ trace: log }));
        setDoQuery(false);
        dispatch(updateModelOutput({ output: output.data, status }));
      }
      if (status == "success") {
        setDoQuery(false);
        dispatch(updateModelOutput({ output:output.data, status }));
      }
    },
    onError: (error: {message:string}) => {
      dispatch({ type: "ERROR", message: error.message });
    },
  });



  async function uploadFileAndModifyInput(inputToSend: FieldValues, inputFields:inputSchemaPropsObject) {
    for (const prop in inputFields) {
      if (inputFields[prop as keyof typeof inputFields].allOf) {
        const uploadedFileUrl = (await modelAPI.uploadFile(inputToSend, prop)).data.serving_url; //TODO: test
        inputToSend[prop as keyof typeof inputFields] = uploadedFileUrl;
      }
    }
  }

  async function modifyInputAndStartPrediction(data: FieldValues) {
    const inputToSend = { ...data };
    const inputFields = model.input_schema.properties;
    dispatch(setTrace({ trace: "" }));
    dispatch(setModelExample({}));
    await uploadFileAndModifyInput(inputToSend, inputFields);
    const prediction = await modelAPI.startPrediction(inputToSend)   //TODO: test
    setPredictionId(prediction.data.prediction_id);
  }

  async function submitUserInput(userInput: FieldValues) {
    await modifyInputAndStartPrediction(userInput);
    setDoQuery(!doQuery);
    scrollToTop();
  }

  const scrollToTop = () => {
    const currentScroll = document.documentElement.scrollTop || document.body.scrollTop;
    if (currentScroll > window.innerHeight/4) {
      window.requestAnimationFrame(scrollToTop);
      window.scrollTo(0, currentScroll - currentScroll / 8);
    }
  };

  return (
    <Box sx={{ width: "45%" }}>
      <Box
          sx={{ float: "left", marginTop: "0px", width:"100%" }}
      >
        <Box id="demoinput body header" sx={{ width:"100%"}}>
          <Box sx={{width:"60%", float:"left"}} >
            <Appbar menuOption={0} setMenuOption={()=>{}} tabs = {tabs}/>
          </Box>
          <Box sx={{width:"30%", height:"40px", float:"right"}}>
            <Checkbox
              sx={{marginTop:"20px",float:"right",display:"inline" }}
              onChange={() => {
                setShowOptionalParams(!showOptionalParams);
              }}
              label="Show optional fields"
            />
          </Box>
         </Box>
      </Box>
      <form onSubmit={handleSubmit(submitUserInput)} style={{ marginTop: "70px" }}>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 3.3 }}>
          {inputComponents.map((component: JSX.Element) => component)}
        </Box>
        <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2, marginBottom: "20px" }}>
          <Button
            size="medium"
            sx={{ mx: 0.5 }}
            variant="outlined"
            startIcon={<RestartAltIcon sx={{ marginTop: "-3px" }} />}
            onClick={reset}
          >
            Reset
          </Button>
          <Button
            size="medium"
            sx={{ marginLeft: 0.5 }}
            variant="contained"
            startIcon={!doQuery ? <DoubleArrowIcon sx={{ marginTop: "-3px" }} /> : <></>}
            disabled={doQuery}
            type="submit"
          >
            {doQuery ? <CircularProgress size={26} sx={{ color: "white" }} /> : "Run"}
          </Button>
        </Box>
      </form>
    </Box>
  );
}

export default DemoInput;
