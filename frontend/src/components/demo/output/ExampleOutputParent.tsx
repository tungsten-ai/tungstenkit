import React, { useState } from 'react'
import { useSelector } from 'react-redux';
import { Box, Typography } from "@mui/material";
import Appbar from '@/components/common/Appbar';
import TraceBlock from '../../common/TraceBlock';
import PredictionSuccessOutputJSON from './PredictionSuccessOutputJSON';
import ExampleInputAndOutputComponent from '@/components/common/ExampleInputAndOutputComponents';
import { AppState } from '@/redux/store';

const tabs = [
    <Box key={1} sx={{display:"flex"}}>
      <Typography variant="mainTextSmall" sx={{marginLeft:"5px"}}>Output</Typography>
    </Box>,
    <Box key={2} sx={{display:"flex"}}>
      <Typography variant='mainTextSmall' sx={{marginLeft:"5px"}}>Json</Typography>
    </Box>,
      <Box key={3} sx={{display:"flex"}}>
      <Typography variant='mainTextSmall' sx={{marginLeft:"5px"}}>Logs</Typography>
    </Box>
  ]

function ExampleOutputParent({id}: {id: string|number}) {
  const [outputMenuOption, setOutputMenuOption] = useState(0)
  const {demo_output, logs, demo_output_processed} = useSelector((state:AppState)=>state.singleModel.example)
  const predictionSuccessOutputJSON = <PredictionSuccessOutputJSON output={demo_output}/>
  const predictionSuccessLogs = <TraceBlock trace={logs} />
  
  return (
    <Box id="exampleOutput" sx={{ marginTop:"0px", display:"grid" }}>
        <Box sx={{width:"60%", float:"left", marginTop:"0px", gridColumn:0, marginBottom:"20px"}} >
            <Appbar menuOption={outputMenuOption} setMenuOption={setOutputMenuOption} tabs = {tabs}/>
        </Box>
        <Box sx={{marginTop:"0px", gridColumn:1}}>
            {outputMenuOption==0? <ExampleInputAndOutputComponent prop={demo_output_processed} requiredArray={[]} id={id}/> : outputMenuOption==1 ? predictionSuccessOutputJSON : predictionSuccessLogs}
        </Box>
    </Box>
  )
}

export default ExampleOutputParent