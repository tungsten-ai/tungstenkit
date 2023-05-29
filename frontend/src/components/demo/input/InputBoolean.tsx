import { ChangeEvent } from "react";
import InputWrapper from "./InputWrapper";
import { Switch  } from "@mui/material";

const InputBoolean = (props:{name:string,description:string, required:boolean, value:string, onChange:(event: ChangeEvent<HTMLInputElement>, checked: boolean) => void }) => {
  return (
    <InputWrapper name={props.name} description={props.description} required={props.required} isDropzone={false}>
      <Switch
        onChange={props.onChange}
        name={props.name}
        value={props.value}
        checked={!!props.value}
        size="medium"
      />
    </InputWrapper>
  );
};

export default InputBoolean;
