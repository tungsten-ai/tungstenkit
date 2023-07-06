import MD5 from "crypto-js/md5";

const GRAVATAR_BASE_URL = "https://www.gravatar.com";

export function stringToColor(string: string) {
  let hash = 0;
  let i;

  /* eslint-disable no-bitwise */
  for (i = 0; i < string.length; i += 1) {
    hash = string.charCodeAt(i) + ((hash << 5) - hash);
  }

  let color = "#";

  for (i = 0; i < 3; i += 1) {
    const value = (hash >> (i * 8)) & 0xff;
    color += `00${value.toString(16)}`.slice(-2);
  }
  /* eslint-enable no-bitwise */
  return color;
}

export function buildGravatarURL(
  hashKey: string,
  defaultTheme: string,
  size: number,
  extension = ".png",
) {
  const sizeString = Math.round(size).toString();
  const digestString = MD5(hashKey).toString();
  const url = new URL("/avatar/" + digestString + extension, GRAVATAR_BASE_URL);

  url.searchParams.set("d", defaultTheme);
  url.searchParams.set("s", sizeString);

  return url;
}
