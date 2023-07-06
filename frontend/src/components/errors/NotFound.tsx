import ErrorContainer from "./ErrorContainer";

function NotFound() {
  const container = ErrorContainer(
    "404",
    "Page Not Found",
    "The page you are looking for doesn’t exist.",
  );
  return container;
}

export default NotFound;
