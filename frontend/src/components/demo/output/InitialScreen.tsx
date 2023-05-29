import React from 'react'
import { Box, Typography } from "@mui/material";

function InitialScreen() {
  return (
    <Box id="preloadscreen" sx={{width:"100%", display:"column", textAlign:"center"}}>
      <Box 
        component="img"
        sx={{height:"20%", width:"25%", colorScheme:"black",marginTop : "100px",  opacity: 0.6}}
        alt = "tungsten_logo"
        src="/tungsten_greyed_out_logo.png"
      ></Box>
      <Typography  fontSize="18px" sx={{width:"100%",margin:"auto", marginTop:"50px", textAlign:"center",  opacity: 0.5 }}>Please fill in the input fields to see the results</Typography> 
    </Box>
    )
}

export default InitialScreen   
