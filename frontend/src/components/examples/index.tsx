import { Box } from '@mui/material'
import React, { Dispatch, SetStateAction, useEffect, useState } from 'react'
import { getClientSideAxios } from "@/axios";
import getModelAPI from '@/api/model';
import { useDispatch } from 'react-redux';
import { setModelExample, updateModelStatus } from '@/redux/singleModelSlice';
import Example from './Example';
import { ModalsProvider } from '@mantine/modals';

function Examples({ model, setAppbarIndex}:{model:model, setAppbarIndex:Dispatch<SetStateAction<number>>}) {
  const dispatch = useDispatch()
  const examplesInitial:predictionData[] = []
  const axiosInstance = getClientSideAxios()
  const modelAPI = getModelAPI(axiosInstance)
 
  const [examples, setExamples]= useState(examplesInitial)

  const onTryExampleCLick=(example:predictionData)=>{
    dispatch(updateModelStatus(""))
    dispatch(setModelExample(example))
    setAppbarIndex(0)
  }
  

  const processExample = async (exampleProp:exampleInputAndOutputProp) => {
    const processedExampleProp = {...exampleProp}
    const propIsFileUrl = (prop: string|Object) => typeof prop == "string" && prop.includes("http"); //TODO: check if this handles edge cases
    
    for await (const key of Object.keys(processedExampleProp)) {
      if (propIsFileUrl(processedExampleProp[key])) {
        const fileUrl :string = (processedExampleProp[key] as string);
        const file = await axiosInstance
          .get(fileUrl, { responseType: "arraybuffer" })
          .catch(() => {
            return undefined;
          });
        if (file) {
          const { headers, data } = file;
          const fileBlob = new Blob([data], {
            type: headers["content-type"], //TODO: non-image media
          });
          processedExampleProp[key] = fileBlob;
          processedExampleProp[key].src = URL.createObjectURL(processedExampleProp[key] as File);
        }
      }
    }
    return processedExampleProp;
  };

  useEffect(()=>{  //TODO: test
    const fetchExamples = async()=>{
      const examples =(await modelAPI.getExamples()).data
      return examples
    }
    const processAllExamples = async(examples:predictionData[])=>{
      for await (const example of examples){
        example.input = await processExample(example.input)
        example.demo_output_processed = await processExample(example.demo_output)
      }
      return examples
    }
    fetchExamples().
      then(examples=>{
        processAllExamples(examples).
          then(
            res=> {
              setExamples(res)
            }
          )
    }) 
  }, [])

  return (
    <ModalsProvider>
    <Box sx={{width:"100%"}}>
      <Box sx={{marginTop:"20px", width:"100%"}}>
        <Box sx={{ mx: "4%", display:"flex", width:"100%" }}>
        </Box>
        {createExamplesComponent( onTryExampleCLick, setExamples, examples, model.input_schema.required )}
      </Box>
    </Box>
    </ModalsProvider>
    )
}

export default Examples

const createExamplesComponent = ( onExampleClickHandler:(example: predictionData) => void, setExamples: Dispatch<SetStateAction<predictionData[]>>, examples:predictionData[], requiredArray:string[])=>{
  return examples.map((example:predictionData, index:number)=>
  <Example key={index} example={example} onTryExampleClick = {onExampleClickHandler} exampleIndex={index} setExamples={setExamples} examples={examples} requiredArray={requiredArray}/>
  )
}