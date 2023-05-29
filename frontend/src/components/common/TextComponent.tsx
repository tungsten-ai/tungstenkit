import React from 'react'
import { Box, Typography } from '@mui/material'

function TextComponent({header, content}:{header:string, content:string}) {
    return (
    <Box sx={{marginTop:"0px"}}>
        <Typography fontWeight="10px" fontSize="18px"> {header}</Typography>
        <Typography fontFamily={"monospace"} sx={{border:"0px solid black",wordBreak:"break-all",backgroundColor:"#e7e7e7",marginTop:"5px",padding:"5px",paddingLeft:"10px", fontSize:"14px"}}>{content}</Typography>
    </Box>
  )
}

export default TextComponent