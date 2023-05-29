import { Box, Typography } from "@mui/material";
import { ReactElement } from "react";

const InputWrapper = ({ name, description, required, children, isDropzone = false }:{ name:string, description:string, required:boolean, children:ReactElement|ReactElement[], isDropzone:boolean }) => {
  const color = isDropzone? "":"#E9E9E9"
  return (
    <Box id={`${description}input`}> 
      <Box sx={{display:"inline-block"}}>
        <Box>
        <Typography fontSize={"18px"} sx={{display:"column"}}> {name} {required && "*"} </Typography>
        </Box>
        <Typography color="grey" variant="mainTextMedium" sx={{ mt: 0.5, display:"column" }}>
          {description}
        </Typography>
      </Box>
      <Box id="input wrapper" sx={{ mt: 0.5, backgroundColor:color }}>{children}</Box>
    </Box>
  )
};

export default InputWrapper;
