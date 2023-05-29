import { CircularProgress, Typography } from '@mui/material'
import { Box } from '@mui/material'
import React, { Dispatch, SetStateAction } from 'react'
import TraceBlock from '../../common/TraceBlock'
import { useSelector} from 'react-redux';
import CancelPredictionBtn from './CancelPredictionBtn';
import { AppState } from '@/redux/store';

function PredictionInProgress({trace,doQuery, setDoQuery}:{trace:string,doQuery:boolean, setDoQuery:Dispatch<SetStateAction<boolean>>}) {
  const status = useSelector((state:AppState)=>state.singleModel.status)
  if (status=="pending"){
    return (
      <Box>
        <Box sx={{display:"flex"}}>
          <CircularProgress size={20}></CircularProgress>
          <Typography sx={{marginLeft:"10px", fontSize:"20px"}}>{status.charAt(0).toUpperCase()+status.slice(1)}</Typography>
        </Box>
   
        {doQuery&&
          <CancelPredictionBtn setDoQuery={setDoQuery}/>
          }
      </Box>
    )
  }

  return (

    <Box>
        <Box>
          <Box sx={{display:"flex"}}>
            <CircularProgress size={20}></CircularProgress>
            <Typography sx={{marginLeft:"10px", fontSize:"20px"}}>{status.charAt(0).toUpperCase()+status.slice(1)}</Typography>
          </Box>
        </Box>
        <TraceBlock trace={trace.charAt(0).toUpperCase()+trace.slice(1)} ></TraceBlock>
        {doQuery&&
        <CancelPredictionBtn setDoQuery={setDoQuery}/>
        }
    </Box>
  )
}

export default PredictionInProgress