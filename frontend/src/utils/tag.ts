function humanFriendlyTag(str: string): string {
  const dashReplaced = str.replaceAll("-", " ").trim();
  return dashReplaced.toLowerCase().replace(/[^a-zA-Z0-9]+(.)/g, (m, chr) => chr.toUpperCase());
}

export { humanFriendlyTag };
