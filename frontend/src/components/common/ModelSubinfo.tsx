import React from 'react'
import { Box,Stack,Typography, Divider} from "@mui/material";

function ModelSubinfo({title, content, icon,}:{title:string, content:string, icon:JSX.Element}) {
  return (
    <Box id="with divider" display="flex" sx={{}} >
        <Box id="without divider root" display="inline">
            <Box id="without divider child" sx={{width:"fit-content", marginTop:"15px"}}>
                <Stack direction={"row"} alignItems={"center"}>
                    {/* <Icon sx={{marginTop:"0px", height:"20px",mx:"-7px",}}>{icon}</Icon>  */}
                    {icon}
                    <Typography variant='mainTextSmall' sx={{color:"#677285", display:"inline"}}> {title} </Typography>  
                </Stack>
                <Typography sx={{fontSize:13, color:"#677285", display:"column"}}> {content} </Typography>
            </Box>
        </Box>
        <Divider id="divider" orientation='vertical' sx={{height:"40px", display:"inline",width:"1px", color:"black", mx:"2vw", marginTop:"10px" }}></Divider>
    </Box>
    )
}

export default ModelSubinfo