import FileUploadIcon from "@mui/icons-material/FileUpload";
import { Box, Typography, Button,Icon } from "@mui/material";
import React, { ChangeEvent, ChangeEventHandler, useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import InputWrapper from "./InputWrapper";
import DeleteIcon from '@mui/icons-material/Delete';
import VideoComponent from "@/components/common/VideoComponent";
import AudioComponent from "@/components/common/AudioComponent";
import { MouseEvent } from "react";

function getBase64(f:File) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.readAsDataURL(f);
    reader.onload = () => {
      resolve(reader.result);
    };
  });
}

const createImgUrl=(value:File)=>{
  if(typeof value=="object"){
    const imageBlob = new Blob([value as BlobPart], {
      type: (value as File).type
    })
    return URL.createObjectURL(imageBlob)
  }

  else if (typeof value == "string"){
    return value    
  }
}

// onChange, Value
function InputDropzone({ name, value, onChange, description, required, errors }:{ name:string, value:File, onChange:(e: ChangeEvent<HTMLInputElement>)=>void, description:string, required:boolean, errors:any }) {
  const filename = value.name
  const onDrop = useCallback((files: File[]) => {
    if (files.length > 0) {
      onChange({ target: { files} });
    }
  }, []);

  const { getRootProps, getInputProps } = useDropzone({ onDrop });
  const hasError = errors && name in errors;

  let errorMessage = "";
  if (hasError) {
    if (errors[name].type === "required") {
      errorMessage = "Required";
    }
  }
  
  const inputFileComponent = (value:File)=>{
    if(value.type.includes("video")){
      const videoJsOptions = {
        autoplay: false,
        controls: true,
        responsive: true,
        fluid: true,
        sources: [{
          src: URL.createObjectURL(value),
          type: 'video/mp4'
        }]
      };
      return <VideoComponent options={videoJsOptions} title = {value.name}></VideoComponent>
    }
    else if ( value.type.includes("image")){
      const imageObjectURL = createImgUrl(value)
      return <Box
      component="img"
      sx={{
        height: "100px",
        width: "100%",
        objectFit: "contain",
        objectPosition: "0 0",
        mb: 1,
      }}
      alt={filename}
      src={imageObjectURL}
    />
    }
    else if (value.type.includes("audio")){
      const audioUrl = URL.createObjectURL(value)
      return <AudioComponent url = {audioUrl} title={value.name} audioId={value.name}></AudioComponent>
    }
  }
  

  const onDeleteClick = (e:React.MouseEvent)=>{
    e.stopPropagation()
    onChange({target:{files:[]}})
  }
  
  return (
  <InputWrapper name={name} description={description} required={required} isDropzone={true}>
      {value && (
        inputFileComponent(value)
      )}

      {filename && (
        <Box sx={{ display: "flex", alignItems: "center", flexWrap: "wrap", mb: 0.5 }}>
          <Typography variant="mainTextMedium">
            {filename}
          </Typography>
        </Box>
      )}

      <Box
       sx={{
        borderStyle: "dashed",
        borderColor: "#d3d3d3",
        backgroundColor:"#E9E9E9", 
        height:"60px",
        display:"grid"
      }}
      >
        <Box
          component="div"
          id="inputfield"
          sx={{
            backgroundColor:"#E9E9E9", 
            height:"53px",
            display:"grid"
          }}
          {...getRootProps()}
        >
          <input {...getInputProps()} 
            onChange={onChange} id="inputDropzone" style={{display:"inline", opacity:"0", width:"100%", height:"100%", gridColumn:1, gridRow:1}}/>
          <Box sx={{ display: "inline", alignItems: "center", flexWrap: "wrap", ml: 0, gridColumn:1, gridRow:1, marginTop:"0px", marginBottom:"5px", padding:"6px"}}>
            <Icon><FileUploadIcon sx={{width:"100%", mx:"4px"}} /></Icon> 
            <Typography variant="mainTextMedium" color="grey" sx={{ ml: 1, py: 1,width:"77%", overflow:"hidden", whiteSpace:"nowrap", textOverflow:"ellipsis",height:"100%", paddingLeft:"5px" }}>
              Drag a file or click to select
            </Typography>
            {filename? <Button onClick={(e:MouseEvent)=>onDeleteClick(e)} sx={{display:"inline", fontSize:"0px", float:"right"}}><DeleteIcon sx={{}} /></Button>:<></>}
          </Box>
        </Box>
      </Box>
      {hasError && (
        <Typography color="red" variant="mainTextMedium" sx={{ mt: 0.6 }}>
          {errorMessage}
        </Typography>
      )}
    </InputWrapper>
  )
}

export default InputDropzone;
