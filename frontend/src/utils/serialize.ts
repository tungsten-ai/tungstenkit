import superjson from "superjson";

superjson.registerCustom<File, string>(
  {
    isApplicable: (v): v is File => v instanceof File,
    serialize: (v) => "null",
    deserialize: (v) => null,
  },
  "decimal.js",
);

const { stringify } = superjson;
const { parse } = superjson;

export { stringify, parse };
