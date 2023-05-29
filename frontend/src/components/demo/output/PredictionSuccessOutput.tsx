import React, { ReactElement, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import VideoComponent from "@/components/common/VideoComponent";
import { useSelector } from "react-redux";
import AudioComponent from "@/components/common/AudioComponent";
import TraceBlock from "../../common/TraceBlock";
import { useState } from "react";
import TextComponent from "@/components/common/TextComponent";
import { getClientSideAxios } from "@/axios";
import { addMarginToComponent } from "@/utils";
import AddToExamplesBtn from "./AddToExamplesBtn";
import { AppState } from "@/redux/store";
import { AxiosInstance } from "axios";

export default function PredictionSuccessOutput() {
  const { output, status ,trace } : {output : predictionData, status : string, trace: string} = useSelector((state: AppState) => state.singleModel);
  const [outputFields, setOutputFields] = useState<predictionOutput>({});
  const axiosInstance = getClientSideAxios();

  useEffect(() => {
    if (status == "success")
      processOutput(output, axiosInstance).then((res) => {
        setOutputFields(res);
      });
  }, []);

  const outputComponents = CreateOutputComponents(outputFields, status, trace);

  return (
    <Box
      id="mainContainerOutput"
      sx={{ overflow: "auto", height: "fit-content" }}
    >
      <Box
        sx={{
          marginBottom: "10px",
          width: "100%",
          height: "fit-content",
          overflowY: "auto",
        }}
      >
        {outputComponents}
      </Box>
      <Box style={{ marginBottom: "100px", height: "200px", width: "400px" }}>
        {status == "success" && <AddToExamplesBtn/>}
      </Box>
    </Box>
  );
}

const propIsFile = (prop: string|Object) =>
  typeof prop == "string" && prop.includes("http");

const processOutput = async (output: predictionData, axiosInstance: AxiosInstance) => {
  const outputFields: predictionOutput = {};
  const demoOutput = output.demo_output;
  
  for (const propName in demoOutput) {
    const prop = demoOutput[propName];
    if (propIsFile(prop)) {
      const name = (prop as string).split("files")[1];
      const file = await axiosInstance.get(`/files${name}`, {
        responseType: "arraybuffer",
        headers: {
        },
      });
      outputFields[propName] = file;
    } else outputFields[propName] = prop;
  }

  return outputFields;
};

const CreateOutputComponents = (
  outputSubFields: predictionOutput,
  status: string,
  trace: string
) => {
  if (status == "failure") {
    return (
      <Box>
        <Typography sx={{ color: "#FF0000" }}>
          Prediction failed. Log is shown below:
        </Typography>
        <TraceBlock trace={trace} />
      </Box>
    );
  }

  const components:ReactElement[] = [];
  for (const propName in outputSubFields) {
    const prop :Object|string|number = outputSubFields[propName];
 
    if (typeof prop == "object" && (prop as httpResponseForFile).data) {
      createMediaComponent((prop as httpResponseForFile), propName, components)
    } else if (typeof prop != "object") {
      createAndAddTextComponent((prop as string), propName, components)
    } else {
      createAndAddTextComponentForObject(prop, propName, components)
    }
  }

  return components.map((component) => addMarginToComponent(component));
};

const createMediaComponent = (prop : httpResponseForFile, propName : string, components:ReactElement[])=>{
  if (prop?.headers["content-type"]?.includes("image")) {
      createAndAddImageComponent(prop, propName, components)
  } else if (prop?.headers["content-type"]?.includes("video")) {
      createAndAddVideoComponent(prop, propName, components)
  } else if (prop?.headers["content-type"]?.includes("audio")) {
      createAndAddAudioComponent(prop, propName, components)
  }
}

const createAndAddImageComponent = (prop : httpResponseForFile, propName : string, components:ReactElement[])=>{
  const imgUrl = createFileUrl(prop);
  const imageComponent = createImgComponent(imgUrl, propName);
  components.unshift(imageComponent);
}


const createImgComponent = (imageObjectURL: string, propName: string) => {
  const img = (
    <Box>
      <Typography fontSize="18px" fontWeight="10px">
        {propName}
      </Typography>
      <img
        style={{ maxWidth: "60%", border: "0px solid black" }}
        src={imageObjectURL}
        alt="new"
      />
    </Box>
  );
  return img;
};

const createAndAddVideoComponent = (prop: httpResponseForFile, propName: string, components:ReactElement[])=>{
  const videoJsOptions = {
    autoplay: false,
    controls: true,
    responsive: true,
    fluid: true,
    sources: [
      {
        src: createFileUrl(prop),
        type: prop.headers["content-type"],
      },
    ],
  };
  const videoComponent = (
    <VideoComponent options={videoJsOptions} title={propName} />
  );
  components.unshift(videoComponent);
}

const createAndAddAudioComponent = (prop: httpResponseForFile, propName:string, components:ReactElement[])=>{
  const audioComponent = (
    <AudioComponent
      url={createFileUrl(prop)}
      title={propName}      
      audioId={`${propName}`}
    />
  );
  components.unshift(audioComponent);
}

const createAndAddTextComponent = (prop: string, propName:string, components:ReactElement[])=>{
  const component = <TextComponent header={propName} content={prop} />;
  components.push(component);
}

const createAndAddTextComponentForObject = (prop: Object, propName:string, components:ReactElement[])=>{
  const content = JSON.stringify(prop);
  components.push(
    <TextComponent
      header={`${propName} (non-visualizable data)`}
      content={content}
    />
  );
}

const createFileUrl = (prop: httpResponseForFile) => {
  const imageBlob = new Blob([prop.data], {
    type: prop.headers["content-type"],
  });
  const imageObjectURL = URL.createObjectURL(imageBlob);
  return imageObjectURL;
};
