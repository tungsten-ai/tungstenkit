import AudioComponent from "./AudioComponent";
import TextComponent from "@/components/common/TextComponent";
import VideoComponent from "./VideoComponent";
import { addMarginToComponent } from "@/utils";
import { Box, Typography } from "@mui/material";
import {  ReactElement } from "react";
import React from "react";

export default function ExampleInputAndOutputComponents({ prop, id, requiredArray }:{prop:propObject,id:string|number, requiredArray:string[]}) {
  if (prop) {
    //TODO: consider improving this implementation in the future
    const components : ReactElement[] = []
    Object.keys(prop).forEach((key, index) => {

      let component: ReactElement;
      
      if (typeof prop[key] == "object" && prop[key] instanceof Blob) {
        if ((prop[key] as Blob).type.includes("image")) {
          component= (
            <Box key={key} sx={{ marginTop: "0px" }}>
              <Typography fontWeight="10px" sx={{ fontSize: "18px" }}>
                {key}
              </Typography>
              <img
                key={key}
                src={prop[key].src}
                style={{ maxWidth: "60%" }}
                alt = "output image"
              />
            </Box>
          );
        } else if ((prop[key] as Blob).type.includes("video")) {
          const videoJsOptions = {
            autoplay: false,
            controls: true,
            responsive: true,
            fluid: true,
            sources: [
              {
                src: URL.createObjectURL((prop[key] as Blob)),
                type: (prop[key] as Blob).type,
              },
            ],
          };
          component = 
          <React.Fragment key={key}>
            <VideoComponent options={videoJsOptions} title={key} />;
          </React.Fragment>

        } else if ((prop[key] as Blob).type.includes("audio")) {
          component = (
            <React.Fragment key={key}>
              <AudioComponent
                url={URL.createObjectURL((prop[key] as Blob))}
                title={key}
                audioId={`${key}${id}`}
              />
            </React.Fragment>
          );
        }
      } else {
        component = (
          <Box key={key} sx={{ marginTop: "0px", overflow: "hidden" }}>
            <TextComponent header={key} content={JSON.stringify(prop[key])} />
          </Box>
        );
      }
      if (requiredArray.includes(key)) components.unshift(component)
      else components.push(component)
    });

    return <>{components.map((component) => addMarginToComponent(component))}</>;
  } else return <></>;
}
