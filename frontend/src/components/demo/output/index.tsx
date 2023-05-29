import React, { Dispatch, SetStateAction } from 'react'
import { Box, Typography } from "@mui/material";
import { useSelector } from 'react-redux';
import { useState } from 'react';
import PredictionSuccessOutputJSON from './PredictionSuccessOutputJSON';
import InitialScreen from './InitialScreen';
import PredictionSuccessOutput from './PredictionSuccessOutput';
import Appbar from '@/components/common/Appbar';
import PredictionInProgress from './PredictionInProgress';
import TraceBlock from '../../common/TraceBlock';
import ExampleOutputParent from './ExampleOutputParent';
import PredictionFail from './PredictionFail';
import { AppState } from '@/redux/store';

function DemoOutput({doQuery, setDoQuery}:{doQuery: boolean; setDoQuery: Dispatch<SetStateAction<boolean>>}) {
  const [toggleView, setToggleView] = useState(0)
  const {status, example, output, trace} = useSelector((state:AppState)=>state.singleModel)

  const predictionNotStarted = example.output?<ExampleOutputParent id={example.id}/> : <InitialScreen/>
  const predictionInProgress = <PredictionInProgress trace = {trace} doQuery = {doQuery} setDoQuery = {setDoQuery}/>
  const predictionSuccessOutputJSON = <PredictionSuccessOutputJSON output={output?.demo_output}/>
  const predictionSuccessOutput = <PredictionSuccessOutput />
  const predictionFail = <PredictionFail output={output}></PredictionFail>
  const predictionSuccessLogs = <TraceBlock trace={trace} />
  const predictionOutputParent =
    <Box>
      <Box sx={{width:"60%", marginBottom:"30px"}} >
        <Appbar menuOption={toggleView} setMenuOption={setToggleView} tabs = {tabs}/>
      </Box>
      {toggleView==0?predictionSuccessOutput:toggleView==1?predictionSuccessOutputJSON:predictionSuccessLogs}
    </Box>


  const showOutput =()=> {
    switch (status){
      case "success":
        return predictionOutputParent
      case "failure":
        return predictionFail
      case "running":
      case "pending":
        return predictionInProgress
      default:
        return predictionNotStarted
  }}
  
  return (
    <Box id="modelbodydemooutput" sx={{width:"50%", marginLeft:"5%", marginTop:"0%"}}>
      {showOutput()}
    </Box>
  )
}

export default DemoOutput


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
