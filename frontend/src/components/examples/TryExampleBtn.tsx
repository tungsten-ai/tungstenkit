import { Button, Typography } from '@mui/material'
import React from 'react'
import ContentPasteGoIcon from "@mui/icons-material/ContentPasteGo";

function TryExampleBtn({onTryExampleClick, example}:{example: predictionData, onTryExampleClick: (example: predictionData) => void}) {
  return (
    <Button
    size="medium"
    sx={{ float:"left",marginTop:"10px", borderRadius: "0px",height:"35px" }}
    variant="outlined"
    startIcon={<ContentPasteGoIcon sx={{width:"16px", marginTop:"-3px"}}/>}
    onClick={()=>onTryExampleClick(example)}
  >
    <Typography sx={{fontSize:"12px"}}>Try this example</Typography>
  </Button>  )
}

export default TryExampleBtn