import React, { Dispatch, SetStateAction } from 'react'
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import { setTrace, updateModelStatus } from '@/redux/singleModelSlice';
import { useDispatch, useSelector} from 'react-redux';
import { Button} from '@mui/material'
import { getClientSideAxios } from '@/axios';
import getModelAPI from '@/api/model';
import { AppState } from '@/redux/store';

function CancelPredictionBtn({setDoQuery}:{setDoQuery:Dispatch<SetStateAction<boolean>>}) {
    const dispatch = useDispatch()
    const axiosInstance = getClientSideAxios()
    const modelAPI = getModelAPI(axiosInstance)
    const predictionId = useSelector((state: AppState)=>state.singleModel.output?.id)
    return (
        <Button 
            size="medium"
            sx={{ my: 0.5 }}
            variant="outlined"
            startIcon={<HighlightOffIcon sx={{marginTop:"-3px"}}/>}
            onClick ={async ()=>{
                setDoQuery(false)
                await modelAPI.cancelPrediction(predictionId)
                dispatch(updateModelStatus({status:"stopped"}))
                dispatch(setTrace({trace:"initializing model prediction \n"}))
            }}>
            Cancel
        </Button>
    )
}

export default CancelPredictionBtn