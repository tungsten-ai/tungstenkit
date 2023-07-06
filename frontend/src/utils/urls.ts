export function buildSignInPath() {
  return "/sign_in";
}

export function buildUserSettingsPath(section = "profile") {
  return `/settings/${section}`;
}

export function buildProjectPath(namespaceSlug: string, projectSlug: string) {
  return `/${namespaceSlug}/${projectSlug}`;
}

export function buildModelPath(namespaceSlug: string, projectSlug: string, modelVersion: string) {
  return `/${namespaceSlug}/${projectSlug}/${modelVersion}`;
}

export function buildPredictionPath(predictionUUID: string) {
  return `/runs/${predictionUUID}`;
}
