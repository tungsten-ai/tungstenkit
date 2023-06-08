interface model {
  name: string;
  description: string;
  input_schema: {
    title: string;
    type: string;
    required: string[];
    properties: inputSchemaPropsObject 
  };
  output_schema: {
    title: string;
    type: string;
    required: string[];
    properties: {
      [key: string]: Object|string|number
    };
  };
  demo_output_schema: {
    title: string;
    type: string;
    required: string[];
    properties: {
      [key: string]: Object|string|number
    };
  };
  input_filetypes: fileTypes;
  output_filetypes: fileTypes;
  demo_output_filetypes: fileTypes;
  avatar_url: string;
  readme: string;
}

interface inputSchemaPropsObject { 
    [key: string]: inputProp
}

interface fileTypes {
    [key: string]: string
}

interface httpResponsePrediction { 
    config : Object;
    data: {
      demo_output: Object,
      files: Array<string>,
      id:string,
      input:Object,
      logs:string,
      output:Object,
      status:string
    };
    headers: {
      [key: string]: string
    };
    status : number;
    statusText: string;
    request : XMLHttpRequest
}

interface httpResponseForFile { 
  config : Object;
  data: ArrayBuffer;
  headers: {
    [key: string]: string
  };
  status : number;
  statusText: string;
  request : XMLHttpRequest
}

interface ref {
  current : HTMLElement|null
}

interface inputProp {
  title : string;
  description : string;
  allOf?:Array<Object>|null;
  default?:number|null;
  maximum?:number|null;
  minimum?:number|null;
  type:string|null;
  format:string|null;
  choices?:Array<string>|Array<number>|null
}

interface predictionData {
  id:string;
  demo_output:predictionOutput;
  demo_output_processed: propObject;
  files?:Array<string>;
  input:exampleInputAndOutputProp;
  output:exampleInputAndOutputProp;
  logs:string;
}

interface exampleInputAndOutputProp { 
  [key: string]: Object|string|number
}

interface predictionOutput {
  [key: string]: Object|Blob|string|number
}

interface propObject { 
  [key: string]: Object|Blob|string|number
}