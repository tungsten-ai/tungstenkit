import getModelAPI from "@/api/model";
import { getClientSideAxios } from "@/axios";
import {  Text } from "@mantine/core";
import { Button } from "@mui/material";
import { modals } from "@mantine/modals";
import { IconTrash } from "@tabler/icons-react";
import { useRouter } from "next/router";
import { Dispatch, SetStateAction } from "react";

export default function DeleteExampleModal({ styles, ind, exampleID, setExamples, examples }: { styles: React.CSSProperties, ind : string, exampleID:string, examples: predictionData[], setExamples: Dispatch<SetStateAction<predictionData[]>> }) {
  const axiosInstance = getClientSideAxios()
  const router = useRouter()
  const modelAPI = getModelAPI(axiosInstance)  
  const deleteExample = async()=>{
    modelAPI.deleteExample(exampleID)
    setExamples([...examples].filter(example=>example.id!=exampleID))
    if ([...examples].filter(example=>example.id!=exampleID).length==0){
      router.reload()   //TODO: improve this part in the future
    }
  }
  const openDeleteModal = () => {
    modals.openConfirmModal({
      modalId: ind,
      key: ind,
      title: "Deletexample",
      centered: true,
      children: <Text size="sm">Are you sure you want to delete this example? </Text>,
      labels: { confirm: "Delete example", cancel: "No don't delete it" },
      confirmProps: { color: "red" },
      onConfirm: () =>deleteExample(),
    });
  };
  return (
    <Button
      key={ind}
      onClick={() => openDeleteModal()}
      variant="outlined"
      sx={styles}
      startIcon={<IconTrash style={{ width: "16px", marginBottom: "6px" }} />}
    >
      <Text sx={{ fontWeight: "lighter", fontSize:"12px" }}>DELETE</Text>
    </Button>
  );
}
