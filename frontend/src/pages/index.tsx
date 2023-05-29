import DemoInput from "@/components/demo/input";
import DemoOutput from "@/components/demo/output";
import ModelHeader from "@/components/common/ModelHeader";
import { Box } from "@mui/material";
import { useEffect, useState } from "react";
// import FilesView from "@/components/files/filesMainView";
import Examples from "@/components/examples";
import Readme from "@/components/readme/";
import { getClientSideAxios } from "@/axios";

function ModelScreen() {
  const [doQuery, setDoQuery] = useState(false);
  const [model, setModel] = useState<model>({} as model);
  const [appbarIndex, setAppbarIndex] = useState(0);

  const axiosInstance = getClientSideAxios()

  const modelBodyViews = [   
    <Box key={1} sx={{ marginTop:"20px", mx: "4%", minWidth: "0px" }}>
      <Box id="modelbodydemo" sx={{ display: "flex", width: "100%"}}>
        <DemoInput model={model} doQuery={doQuery} setDoQuery={setDoQuery} />
        <DemoOutput doQuery={doQuery} setDoQuery={setDoQuery} />
      </Box>
    </Box>,
    // <FilesView model={model}/>, 
  ]
  if (model.readme) modelBodyViews.push(<Readme readme={model.readme} key={1}/>);
  if (model.examples_count>0) modelBodyViews.push(<Examples model={model} setAppbarIndex = {setAppbarIndex} key={1}/>);

  useEffect(() => {
    const fetchModel = async () => {
      const modelFromServer = (
        await axiosInstance.get("/metadata").catch(() => {
          return undefined;
        })
      )?.data; //handle error case better in the future
      if (modelFromServer) setModel(modelFromServer);
    };
    fetchModel();
  }, []);

  return (
    <Box id="main header" sx={{ backgroundColor: "white", minHeight:"100vh" }}>
      <ModelHeader
        model={model}
        appbarIndex={appbarIndex}
        setAppbarIndex={setAppbarIndex}
      />
      {modelBodyViews[appbarIndex]}
    </Box>
  );
}

export default ModelScreen;
