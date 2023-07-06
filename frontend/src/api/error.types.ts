export interface ValidationError {
  detail: {
    loc: string[];
    message: string;
  }[];
}
