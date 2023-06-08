import CollectionsBookmarkOutlinedIcon from "@mui/icons-material/CollectionsBookmarkOutlined";
import FolderCopyOutlinedIcon from "@mui/icons-material/FolderCopyOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import { Box, Typography } from "@mui/material";
import { Avatar } from "@mantine/core";
import { stringToColor } from "@/utils/avatar";
import Appbar from "./Appbar";

export default function ModelHeader({ model, appbarIndex, setAppbarIndex }: { model: model,appbarIndex:number, setAppbarIndex:Function }) {
  const tabs = createTabs(model);
  return (
    //TODO:remove px in the future
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        backgroundColor:"white",
        border: "1px solid #E1E2E6",
        minWidth:"900px"
      }}>
      <Box sx={{ display: "flex", mx: "4%", minWidth: "800px" }}>
        <Box style={{ width: "100%", marginTop: "2%", display: "inline" }}>
          <Box sx={{ display: "flex" }}>
            <Avatar
                color={stringToColor(model.name)}
                radius="0"
                styles={{
                  placeholder: {
                    float: "left",
                    backgroundColor: stringToColor(model.name),
                    color: "white",
                  },
                }}
                size="100px"
                src={model.avatar_url}
              >
                {/* {model?.name?.charAt(0)} */}
              </Avatar>

            <Box style={{ marginLeft: "20px", height: "75px", display: "inline" }}>
              <Box
                style={{ height: "fit-content", width: "100%", position: "relative", float: "left" }}
              >
                <Typography sx={{ float: "left" }} variant="h5">
                  {model.name}
                </Typography>
              </Box>
              <Box style={{ width: "100%", height: "fit-content", float: "left", marginTop:"0px" }}>
                <Typography  sx={{ float: "left", color: "#677285", fontSize:"18px"}}>
                  {model.description}
                </Typography>
              </Box>
            </Box>
          </Box>
          <Box sx={{ width: "40%", marginTop: "15px" }}>
            <Appbar
              tabs={tabs}
              menuOption={appbarIndex}
              setMenuOption={setAppbarIndex}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

const createTabs = (model: model) => {
  const demoBtn = (
    <PlayArrowOutlinedIcon sx={{ marginTop: "-3px", fontSize: "20px" }}></PlayArrowOutlinedIcon>
  );
  const readmeBtn = (
    <MenuBookOutlinedIcon sx={{ marginTop: "-3px", fontSize: "18px" }}></MenuBookOutlinedIcon>
  );
  const tabs = [createTab("demo", demoBtn)];
  if (model.readme) tabs.push(createTab("readme", readmeBtn));
  return tabs;
};

const createTab = (title: string, icon: JSX.Element) => {
  return (
      <Box sx={{ display: "flex" }}>
        {icon}
        <Typography variant="mainTextSmall" sx={{ marginLeft: "5px" }}>
          {title}
        </Typography>
      </Box>
  )
};
