import React from 'react'
import { Box, Typography } from '@mui/material'

function InitialView() {
  return (
    <Box>
    <Box id="preloadscreen" sx={{width:"100%",marginTop:"1%", display:"column", textAlign:"center"}}>
      <Box 
        component="img"
        sx={{height:"40%", width:"15%", colorScheme:"black", opacity:0.6}}
        alt = "tungsten_logo"
        src="/tungsten_greyed_out_logo.png"
      ></Box>
      <Typography  fontSize="18px" sx={{width:"100%",opacity:0.6,margin:"auto", marginTop:"50px", textAlign:"center" }}>select a file to view its contents</Typography> 
    </Box>
  </Box>
  )
}

export default InitialView