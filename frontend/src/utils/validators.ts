import isEmail from "validator/lib/isEmail";

const passwordRequirements = [
  { re: /[0-9]/, label: "Includes number" },
  { re: /[a-z]/, label: "Includes lowercase letter" },
  { re: /[A-Z]/, label: "Includes uppercase letter" },
  { re: /[$&+,:;=?@#|'<>.^*()%!-]/, label: "Includes special symbol" },
];
const passwordMinLength = 8;

const slugRegex = /^(?!-)[a-z0-9]+$/;

function isValidHttpUrl(value: string) {
  let url;

  try {
    url = new URL(value);
  } catch (_) {
    return false;
  }

  return url.protocol === "http:" || url.protocol === "https:";
}

function isValidEmail(value: string) {
  return isEmail(value);
}

function isValidSlug(value: string) {
  return slugRegex.test(value);
}

function isValidPassword(value: string) {
  let weak = false;
  passwordRequirements.forEach((requirement) => {
    if (!requirement.re.test(value)) {
      weak = true;
    }
  });
  if (weak) return false;
  if (value.length < passwordMinLength) return false;
  return true;
}

const validateUsername = (value: str) => {
  if (!value.length) {
    return "This field is required.";
  }
  if (value.length > 20) {
    return "Username must be at most 20 characters long.";
  }
  if (!isValidSlug(value)) {
    return "Username can only contain alphanumeric characters.";
  }

  return null;
};

const validatePassword = (value: str) => {
  if (!value.length) {
    return "This field is required.";
  }
  if (value.length > 40) {
    return "Password must be at most 40 characters long.";
  }

  if (!isValidPassword(value)) {
    return "Password too weak.";
  }
  return null;
};

export {
  isValidHttpUrl,
  isValidEmail,
  isValidSlug,
  isValidPassword,
  validateUsername,
  validatePassword,
  passwordRequirements,
  passwordMinLength,
};
