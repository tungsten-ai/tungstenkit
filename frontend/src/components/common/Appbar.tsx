import AppBar from "@mui/material/AppBar";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { SyntheticEvent } from "react";

function a11yProps(index: number) {
  return {
    id: `action-tab-${index}`,
    "aria-controls": `action-tabpanel-${index}`,
  };
}

function Appbar({
  menuOption,
  setMenuOption,
  tabs,
}: {
  menuOption: number;
  setMenuOption: Function;
  tabs: JSX.Element[];
}) {
  const handleChange = (event: SyntheticEvent, newValue: number) => {
    setMenuOption(newValue);
  };

  return (
    <div>
      <AppBar position="static" color="transparent" sx={{ border: 0, boxShadow: "none" , width:`${tabs.length/4*100}%`, minWidth:"100px"}}>
        <Tabs
          value={menuOption}
          onChange={handleChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
          aria-label="action tabs example"
        >
          {tabs.map((tab: JSX.Element, index: number) => {
            return <Tab key={index} label={tab} {...a11yProps(0)} />;
          })}
        </Tabs>
      </AppBar>
    </div>
  );
}

export default Appbar;
