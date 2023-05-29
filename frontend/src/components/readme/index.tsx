import {Divider, Typography } from '@mui/material';
import { Box } from '@mui/system';
import React from 'react'
import ReactMarkdown from "react-markdown";
import gfm from "remark-gfm";
import TocIcon from '@mui/icons-material/Toc';
import { PluggableList } from 'react-markdown/lib/react-markdown';

function Readme({readme}:{readme:string}) {
  const plugins:PluggableList = [gfm]
  return (
    <Box>
        <Box sx={{border:"1px solid #D3D3D3", width :"90%", borderRadius:"10px",marginBottom:"20px", paddingRight:"30px", paddingLeft:"30px",paddingTop:"15px", mx:"4%",marginTop:"35px" }}>
            <Box sx={{display:"inline"}}>
                <TocIcon sx={{display:"inline", marginLeft:"0px",marginBottom:"-7px", fontSize:"26px"}} ></TocIcon>
                <Typography  sx={{width:"50%", display:"inline", marginLeft:"10px"}} fontSize={18}>README.md</Typography>
            </Box>
            <Divider sx={{marginBottom:"20px", marginTop:"10px"}}></Divider>
            <ReactMarkdown remarkPlugins={plugins} components={{img:({node,...props})=><img style={{maxWidth:'300px'}}{...props}/>}} >{readme}</ReactMarkdown>
        </Box>
    </Box>
  )
}

export default Readme