import { useState } from "react";
import { IconButton, Snackbar } from "@mui/material";
import CopyAllIcon from "@mui/icons-material/CopyAll";

const CopyToClipboardButton = ({ output }: {output: predictionOutput}) => {
  const [open, setOpen] = useState(false);

  const handleClick = () => {
    setOpen(true);
    navigator.clipboard.writeText(JSON.stringify(output));
  };

  return (
    <>
      <IconButton
        onClick={handleClick}
        color="primary"
        size={"large"}
        sx={{ float: "right", padding: "0px" }}
      >
        <CopyAllIcon sx={{ width: "30px", height:"30px" }} />
      </IconButton>
      <Snackbar
        message="Copied to clibboard"
        anchorOrigin={{ vertical: "top", horizontal: "center" }}
        autoHideDuration={2000}
        onClose={() => setOpen(false)}
        open={open}
      />
    </>
  );
};

export default CopyToClipboardButton;
