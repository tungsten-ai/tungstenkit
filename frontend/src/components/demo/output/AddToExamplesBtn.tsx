import { Button, Tooltip } from "@mantine/core";
import { IconFolderPlus } from "@tabler/icons-react";
import { Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { getClientSideAxios } from "@/axios";
import getModelAPI from "@/api/model";
import { useRouter } from "next/router";
import { useSelector } from "react-redux";
import { AppState } from "@/redux/store";

function AddToExamplesBtn() {
  const [messageIsShown, setMessageIsShown] = useState(false);
  const axiosInstance = getClientSideAxios();
  const modelAPI = getModelAPI(axiosInstance);
  const router = useRouter();
  const { output }: {output: predictionData} = useSelector((state: AppState) => state.singleModel);
  const predictionId = output?.id;
  
  useEffect(() => {
    if (messageIsShown) {
      setTimeout(() => setMessageIsShown(false), 1000);
    }
  });

  const addToExamples = () => {
    modelAPI.addExample(predictionId); //TODO: test
    axiosInstance.get("/metadata").then((res) => {
      if (res.data.examples_count == 0) router.reload();
    });
    setMessageIsShown(true);
  };


  return (
    <Tooltip
      label="Added to examples"
      offset={5}
      position="bottom"
      radius="xl"
      transitionProps={{ duration: 100, transition: "slide-down" }}
      opened={messageIsShown}
    >
      <Button
        onClick={addToExamples}
        variant="outline"
        color="dark"
        sx={{ borderRadius: "0", float: "left" }}
      >
        <IconFolderPlus style={{ width: "20px", marginRight: "10px" }} />
        <Typography variant="mainTextMedium" fontWeight={80}>
          Add to examples
        </Typography>
      </Button>
    </Tooltip>
  );
}

export default AddToExamplesBtn;
