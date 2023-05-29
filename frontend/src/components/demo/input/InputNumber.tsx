import InputWrapper from "./InputWrapper";
import { TextField, Typography } from "@mui/material";

const InputNumber = ({
  name,
  value,
  onChange,
  description,
  required,
  errors,
  integer,
  minimum,
  maximum,
}:{
  name:string,
  value:number|string,
  onChange:(e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>)=>void,
  description:string,
  required:boolean,
  errors:any,
  integer:boolean,
  minimum:number|null,
  maximum:number|null,
}) => {
  const step = integer ? 1 : 0.01;
  const hasError = errors && name in errors;

  let errorMessage = "";
  if (hasError) {
    if (errors[name].type === "required") {
      errorMessage = "Required";
    }
  }

  const component = (
    <TextField
      fullWidth
      type="number"
      inputProps={{ step: step, min:minimum, max:maximum }}
      size="medium"
      value={value}
      onChange={onChange}
      error={hasError}
    />
  );

  return (
    <InputWrapper name={name} description={description} required={required} isDropzone={false}>
      {component}
      {hasError && (
        <Typography color="red" variant="mainTextMedium" sx={{ mt: 0.6 }}>
          {errorMessage}
        </Typography>
      )}
    </InputWrapper>
  );
};

export default InputNumber;
