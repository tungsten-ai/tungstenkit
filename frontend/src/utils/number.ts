const compactNumberFormatter = new Intl.NumberFormat("en", {
  notation: "compact",
});

function compactNumber(number: number): string {
  return compactNumberFormatter.format(number);
}

export { compactNumber, compactNumberFormatter };
