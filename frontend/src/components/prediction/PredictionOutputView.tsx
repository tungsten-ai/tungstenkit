import { PredictionOutputFieldValue } from "@/api/prediction.types";
import { OutputSchema, IOFileType } from "@/types";
import { PredictionOutputFieldsContainer } from "./PredictionOutputFieldsContainer";
import { CodeBlockWithLinebreak } from "./CodeBlockWithLinebreak";
import { PredictionOutputMode } from "./PredictionOutputControl";
import PredictionLogsArea from "./PredictionLogsArea";

export interface PredictionOutputViewProps {
  mode: PredictionOutputMode;
  output: { [key: string]: PredictionOutputFieldValue };
  demoOutput: { [key: string]: PredictionOutputFieldValue };
  demoOutputSchema: OutputSchema;
  demoOutputFiletypes: { [key: string]: IOFileType };
  logs?: string;
}

export function PredictionOutputView({
  mode,
  output,
  demoOutput,
  demoOutputSchema,
  demoOutputFiletypes,
  logs,
}: PredictionOutputViewProps) {
  const previewArea = (
    <PredictionOutputFieldsContainer
      schema={demoOutputSchema}
      filetypes={demoOutputFiletypes}
      values={demoOutput}
    />
  );
  const jsonArea = (
    <CodeBlockWithLinebreak fz="xs" mono>
      {JSON.stringify(output, null, 2)}
    </CodeBlockWithLinebreak>
  );
  const logsArea = <PredictionLogsArea>{logs ?? ""}</PredictionLogsArea>;
  return (
    <>
      {mode === "preview" && previewArea}
      {mode === "raw" && jsonArea}
      {mode === "logs" && logsArea}
    </>
  );
}
