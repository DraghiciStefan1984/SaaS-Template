import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const schemaPath = join(root, "backend", "openapi.json");
const outputPath = join(root, "frontend", "src", "lib", "api-paths.generated.ts");
const checkOnly = process.argv.includes("--check");
const methods = ["get", "post", "put", "patch", "delete"];

if (!existsSync(schemaPath)) {
  console.error("backend/openapi.json is missing. Generate it with drf-spectacular first.");
  process.exit(2);
}

try {
  const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
  const entries = Object.entries(schema.paths ?? {})
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([path, operations]) => {
      const availableMethods = methods.filter((method) => operations?.[method]);
      return `  ${JSON.stringify(path)}: ${JSON.stringify(availableMethods)},`;
    });
  const generated = [
    "// Generated from backend OpenAPI. Run `npm run api:types` after API contract changes.",
    "",
    "export const apiPaths = {",
    ...entries,
    "} as const;",
    "",
    "export type ApiPath = keyof typeof apiPaths;",
    "export type ApiMethodFor<TPath extends ApiPath> = (typeof apiPaths)[TPath][number];",
    "",
  ].join("\n");

  if (checkOnly) {
    const current = existsSync(outputPath) ? readFileSync(outputPath, "utf8") : "";
    if (current !== generated) {
      console.error("Generated frontend API path types are out of date. Run `npm run api:types`.");
      process.exitCode = 1;
    } else {
      console.log("Generated frontend API path types are current.");
    }
  } else {
    writeFileSync(outputPath, generated, "utf8");
    console.log("Generated frontend/src/lib/api-paths.generated.ts.");
  }
} finally {
  unlinkSync(schemaPath);
}
