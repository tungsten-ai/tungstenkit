import React from 'react'
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { Button } from '@mui/material';

function DownloadBtn({onClick}:{onClick: React.MouseEventHandler<HTMLButtonElement> | undefined}) {
  return (
    <Button size="medium"
        sx={{ marginLeft:"20%", marginTop:"20px", width:"100%" }}
        variant="contained"
        startIcon={<FileDownloadIcon />} 
        onClick={onClick}>
        download as zip
    </Button>  )
}

export default DownloadBtn