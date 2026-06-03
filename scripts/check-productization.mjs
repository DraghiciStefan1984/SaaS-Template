import { existsSync, readFileSync } from "node:fs";

const requiredPaths = [
  "scripts/scaffold-product.mjs",
  "backend/apps/products/example_insights",
  "backend/apps/products/example_insights/services.py",
  "frontend/src/pages/ExampleProductPage.tsx",
  "postman/saas-core-template.postman_collection.json",
];

const secretScanFiles = [
  ".env.example",
  "backend/.env.example",
  "frontend/.env.example",
  "deploy/aws.env.example",
];

const secretPatterns = [
  /sk_live_[A-Za-z0-9]+/,
  /sk_test_[A-Za-z0-9]+/,
  /AKIA[0-9A-Z]{16}/,
  /OPENAI_API_KEY=sk-[A-Za-z0-9_-]+/,
  /ANTHROPIC_API_KEY=sk-ant-[A-Za-z0-9_-]+/,
];

const failures = [];

for (const path of requiredPaths) {
  if (!existsSync(path)) {
    failures.push(`Missing required template path: ${path}`);
  }
}

for (const path of secretScanFiles) {
  if (!existsSync(path)) {
    failures.push(`Missing env example: ${path}`);
    continue;
  }
  const content = readFileSync(path, "utf8");
  for (const pattern of secretPatterns) {
    if (pattern.test(content)) {
      failures.push(`Possible real secret in ${path}: ${pattern}`);
    }
  }
}

if (failures.length) {
  console.error("Productization check failed:");
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("Productization check passed.");
