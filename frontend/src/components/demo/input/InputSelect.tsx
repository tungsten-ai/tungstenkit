import { ReactNode } from "react";
import InputWrapper from "./InputWrapper";
import { MenuItem, Select, SelectChangeEvent } from "@mui/material";

const InputSelect = (props:{name:string, description:string, required:boolean, onChange:(event: SelectChangeEvent<string|number>, child: ReactNode) => void, value:string|number, options : string[]|number[]}) => {
  return (
    <InputWrapper name={props.name} description={props.description} required={props.required} isDropzone={false}>
      <Select size="medium" sx={{ width: "100%" }} value={props.value} onChange={props.onChange}>
        {props.options.map((item:string|number, i:number) => {
          return (
            <MenuItem key={i} value={item}>
              {item}
            </MenuItem>
          );
        })}
      </Select>
    </InputWrapper>
  );
};

export default InputSelect;
