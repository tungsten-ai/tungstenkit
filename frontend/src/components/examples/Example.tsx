import React, { Dispatch, SetStateAction, useState } from "react";
import { Box, Typography, Divider } from "@mui/material";
import DeleteExampleBtn from "./DeleteExampleBtn";
import Appbar from "../common/Appbar";
import TraceBlock from "../common/TraceBlock";
import PredictionSuccessOutputJSON from "../demo/output/PredictionSuccessOutputJSON";
import TryExampleBtn from "./TryExampleBtn";
import ExampleInputAndOutputComponent from "../common/ExampleInputAndOutputComponents";
import { Checkbox } from "@mantine/core";

function Example({
  example,
  onTryExampleClick,
  exampleIndex,
  setExamples,
  examples,
  requiredArray,
}: {
  example: predictionData;
  onTryExampleClick: (example: predictionData) => void;
  exampleIndex: number;
  setExamples: Dispatch<SetStateAction<predictionData[]>>;
  examples: predictionData[];
  requiredArray: string[];
}) {
  const [outputMenuOption, setOutputMenuOption] = useState(0);
  const [showOptionalFields, setShowOptionalFields] = useState(false);

  const trace = example.logs;

  const exampleOutputJSON = (
    <PredictionSuccessOutputJSON output={example.demo_output} />
  );
  const exampleLogs = <TraceBlock trace={trace} />;

  const selectInputFieldsToShow = () => {
    const filteredInputs: exampleInputAndOutputProp = {};
    Object.keys(example.input).forEach((propName) => {
      if (showOptionalFields || requiredArray.includes(propName)) {
        filteredInputs[propName] = example.input[propName];
      }
    });
    return filteredInputs;
  };

  const inputFieldsToShow = selectInputFieldsToShow();

  return (
    <Box key={exampleIndex} sx={{ mx: "4%", marginBottom: "30px" }}>
      <Box sx={{ display: "flex" }}>
        <Box sx={{ width: "49%" }}>
          <Box sx={{ width: "60%", float: "left" }}>
            <Appbar menuOption={0} setMenuOption={() => {}} tabs={InputTabs} />
          </Box>
          <Box sx={{ float: "right" }}>
            <Checkbox
              sx={{ marginTop: "20px", float: "right", display: "inline" }}
              onChange={() => setShowOptionalFields(!showOptionalFields)}
              label="Show optional fields"
            />
          </Box>
          <Box sx={{ marginTop: "70px" }}>
            <ExampleInputAndOutputComponent
              prop={inputFieldsToShow}
              requiredArray={requiredArray}
              id={example.id}
            />
            <TryExampleBtn
              onTryExampleClick={onTryExampleClick}
              example={example}
            />
            <DeleteExampleBtn
              styles={{
                marginTop: "10px",
                float: "left",
                marginLeft: "10px",
                height: "35px",
                borderRadius: "0px",
                borderColor: "red",
                color: "red",
              }}
              ind={`${exampleIndex + 1}`}
              exampleID={example.id}
              examples={examples}
              setExamples={setExamples}
            />
          </Box>
        </Box>
        <Box sx={{ marginLeft: "2%", width: "49%" }}>
          <Box sx={{ width: "60%", float: "left" }}>
            <Appbar
              menuOption={outputMenuOption}
              setMenuOption={setOutputMenuOption}
              tabs={outputTabs}
            />
          </Box>
          <Box sx={{ float: "right" }}></Box>
          <Box sx={{ marginTop: "70px" }}>
            {outputMenuOption == 0 ? (
              <ExampleInputAndOutputComponent
                prop={example.demo_output_processed as propObject}
                requiredArray={[]}
                id={example.id}
              />
            ) : outputMenuOption == 1 ? (
              exampleOutputJSON
            ) : (
              exampleLogs
            )}
          </Box>
        </Box>
      </Box>
      <Divider
        sx={{ marginTop: "40px", marginBottom: "5px", width: "100%" }}
      ></Divider>
    </Box>
  );
}

export default Example;

const InputTabs = [
  <Box key={1} sx={{ display: "flex" }}>
    <Typography variant="mainTextSmall" sx={{ marginLeft: "5px" }}>
      Input
    </Typography>
  </Box>,
];

const outputTabs = [
  <Box key={1} sx={{ display: "flex" }}>
    <Typography variant="mainTextSmall" sx={{ marginLeft: "5px" }}>
      Output
    </Typography>
  </Box>,
  <Box key={2} sx={{ display: "flex" }}>
    <Typography variant="mainTextSmall" sx={{ marginLeft: "5px" }}>
      Json
    </Typography>
  </Box>,
  <Box key={3} sx={{ display: "flex" }}>
    <Typography variant="mainTextSmall" sx={{ marginLeft: "5px" }}>
      Logs
    </Typography>
  </Box>,
];
