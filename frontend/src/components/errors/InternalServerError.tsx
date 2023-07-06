import ErrorContainer from './ErrorContainer';

function InternalServerError() {
  const container = ErrorContainer(
    "500", 
    "Internal Server Error", 
    "The server encountered an error and counld not complete your request."
  );
  return container
}

export default InternalServerError;