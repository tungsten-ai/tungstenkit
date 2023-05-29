import { Box, Typography } from "@mui/material"
import { ReactElement } from "react"
export const creaetImgComponent = (imageObjectURL:string, propName:string)=>{
    const img = (
      <Box>
        <Typography fontSize="24px" fontWeight="10px" >{propName}</Typography>
        <img style={{maxWidth:"100%", border:"2px solid black"}}
          src={imageObjectURL}
          alt="new"
          />
      </Box>
    )
    return img
  }

export const addMarginToComponent =(component:ReactElement)=>{
  return (
    <Box sx={{marginBottom:"15px"}}>
      {component}
    </Box>
  )
}
