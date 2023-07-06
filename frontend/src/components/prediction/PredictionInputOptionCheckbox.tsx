import { Checkbox, CheckboxProps } from "@mantine/core";

export interface PredictionInputOptionCheckboxProps
  extends Omit<CheckboxProps, "checked" | "onChange"> {
  checked: boolean;
  onChange: (value: boolean) => void;
}

export function PredictionInputOptionCheckbox({
  checked,
  onChange,
  ...others
}: PredictionInputOptionCheckboxProps) {
  return (
    <Checkbox
      label="Show options"
      checked={checked}
      onChange={(event) => onChange(event.currentTarget.checked)}
      {...others}
    />
  );
}
