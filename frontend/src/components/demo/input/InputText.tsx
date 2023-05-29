import { ChangeEventHandler } from "react";
import InputWrapper from "./InputWrapper";
import { TextField, Typography } from "@mui/material";

const InputText = ({ name, value, onChange, description, required, errors }:{ name:string, value:string, onChange:ChangeEventHandler<HTMLTextAreaElement | HTMLInputElement>, description:string, required:boolean, errors:any }) => {
  const hasError = name in errors;
  let errorMessage = "";
  if (hasError) {
    if (errors[name].type === "required") {
      errorMessage = "Required";
    }
  }
  return (
    <InputWrapper name={name} description={description} required={required} isDropzone={false}>
      <TextField
        fullWidth
        size="medium"
        name={name}
        value={value}
        onChange={onChange}
        error={hasError}
      ></TextField>
      {hasError ? (
        <Typography color="red" variant="mainTextMedium" sx={{ mt: 0.6}}>
          {errorMessage}
        </Typography>
      ):<></>}
    </InputWrapper>
  );
};

export default InputText;
