import { Project } from "@/types";
import { isValidHttpUrl } from "./validators";

const OWNER_ACCESS_LEVEL = 50;
const MAINTAINER_ACCESS_LEVEL = 30;
const PROJECT_SLUG_REGEX = "^(?!-)[a-z0-9-]+$";
const PROJECT_TAG_REGEX = "^[a-z0-9]+(-?[a-z0-9]+)?$";

function canDeleteModel(project: Project): boolean {
  return !!project?.access_level && project?.access_level >= OWNER_ACCESS_LEVEL;
}

function canDeleteProject(project: Project): boolean {
  return !!project?.access_level && project?.access_level >= OWNER_ACCESS_LEVEL;
}

function canEditProject(project: Project): boolean {
  return !!project?.access_level && project?.access_level >= MAINTAINER_ACCESS_LEVEL;
}

function validateProjectSlug(slug: string) {
  if (!slug) {
    return "This field is required.";
  }

  if (slug.length > 20) {
    return "Maximum length is 20 characters.";
  }

  if (slug.startsWith("-")) {
    return "A project name should start with a lowercase letter or a digit.";
  }

  if (!slug.match(PROJECT_SLUG_REGEX)) {
    return "Project name can only contain lowercase letters, digits, and dashes.";
  }

  return null;
}

const validateDescription = (desc: string | null) => {
  if (!desc) {
    return null;
  }

  if (desc.length > 100) {
    return "Project description must be at most 100 characters long.";
  }

  return null;
};

const validateWebURL = (url: string | null) => {
  if (!url) {
    return null;
  }

  if (url?.length > 50) {
    return "Please provide a shorter url.";
  }

  if (!isValidHttpUrl(url)) {
    return "Invalid URL.";
  }

  return null;
};

const validateGithubURL = (githubUrl: string | null) => {
  if (!githubUrl) {
    return null;
  }

  if (githubUrl?.length > 50) {
    return "Please provide a shorter url.";
  }

  if (!githubUrl.startsWith("https://github.com/")) {
    return "Invalid Github URL.";
  }

  return null;
};

const validateTag = (tag: string) => {
  if (tag.length > 20) {
    return "Maximum length is 20 characters.";
  }

  if (tag.startsWith("-")) {
    return "A tag should start with a lowercase lettter or a digit.";
  }

  if (!tag.match(PROJECT_TAG_REGEX)) {
    return "A tag can only contain lowercase letters, digits, and a single dash positioned in the middle (e.g. hello-world).";
  }

  return null;
};

export {
  canDeleteModel,
  canEditProject,
  canDeleteProject,
  validateProjectSlug,
  validateDescription,
  validateWebURL,
  validateTag,
  validateGithubURL,
};
