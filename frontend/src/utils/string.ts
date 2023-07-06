// @ts-nocheck
export function isEmpty(value) {
  return value == null || (typeof value === "string" && value.trim().length === 0);
}

export function isEmail(value) {
  const regex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$/;
  return regex.test(value);
}

export function isSlug(value) {
  return true;
}

export function isPasswordStrongEnough(value) {
  const stripped = value.trim();
  return stripped.length >= 8;
}

export function readablizeCounts(counts: number | null | undefined) {
  const suffices = ["", "k", "M", "G", "T", "P"];
  if (!counts || counts <= 0.5) {
    return "0";
  }
  const e = Math.floor(Math.log(counts) / Math.log(1000));
  return (counts / Math.pow(1000, e)).toFixed(0) + suffices[e];
}
