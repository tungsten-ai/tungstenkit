export type PredictionStatus = "pending" | "running" | "success" | "failed" | "canceled";

export type FailureReason = "user_failure" | "system_failure" | "timeout" | "unknown_failure";

export type PredictionInputFieldValue = string | number | boolean;

export type PredictionOutputFieldValue =
  | string
  | number
  | boolean
  | object
  | string[]
  | number[]
  | boolean[]
  | object[];

export interface BasePrediction {
  id: string;

  input: {
    [key: string]: PredictionInputFieldValue;
  };
  output?: {
    [key: string]: PredictionOutputFieldValue;
  } | null;
  demo_output?: {
    [key: string]: PredictionOutputFieldValue;
  } | null;

  is_demo: boolean;

  status: PredictionStatus;
  failure_reason?: FailureReason;
  logs?: string | null;

  created_at: string;
  started_at?: string;
  exited_at?: string;
}

export interface SucceededDemoPrediction extends BasePrediction {
  output: {
    [key: string]: PredictionOutputFieldValue;
  };
  demo_output: {
    [key: string]: PredictionOutputFieldValue;
  };
  is_demo: true;

  status: "success";

  started_at: string;
  exited_at: string;
}

export interface SucceededNonDemoPrediction extends BasePrediction {
  output: {
    [key: string]: PredictionOutputFieldValue;
  };
  demo_output?: null;
  is_demo: false;

  status: "success";

  started_at: string;
  exited_at: string;
}

export type SucceededPrediction = SucceededDemoPrediction | SucceededNonDemoPrediction;

export interface FailedPrediction extends BasePrediction {
  output?: null;
  demo_output?: null;

  status: "failed";

  started_at: string;
  exited_at: string;
}

export interface CanceledPrediction extends BasePrediction {
  output?: null;
  demo_output?: null;

  status: "canceled";

  started_at: string;
  exited_at: string;
}

export interface RunningPrediction extends BasePrediction {
  output?: null;
  demo_output?: null;

  status: "running";

  started_at: string;
}

export interface PendingPrediction extends BasePrediction {
  output?: null;
  demo_output?: null;

  status: "pending";
}

export type Prediction =
  | SucceededPrediction
  | FailedPrediction
  | CanceledPrediction
  | RunningPrediction
  | PendingPrediction;