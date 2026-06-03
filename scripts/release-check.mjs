import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";

const checks = [
  ["node", ["scripts/check-productization.mjs"]],
  ["node", ["scripts/backend-command.mjs", "-m", "ruff", "check", "."]],
  ["node", ["scripts/backend-command.mjs", "manage.py", "check"]],
  ["node", ["scripts/backend-command.mjs", "manage.py", "makemigrations", "--check", "--dry-run"]],
  ["node", ["scripts/backend-command.mjs", "manage.py", "spectacular", "--validate", "--file", "openapi.yaml"]],
  ["node", ["scripts/backend-command.mjs", "-m", "pytest"]],
  ["npm", ["--prefix", "frontend", "run", "lint"]],
  ["npm", ["--prefix", "frontend", "run", "typecheck"]],
  ["npm", ["--prefix", "frontend", "run", "test"]],
  ["npm", ["--prefix", "frontend", "run", "build"]],
];

function run(command, args) {
  return new Promise((resolve, reject) => {
    console.log(`\n> ${command} ${args.join(" ")}`);
    const child = spawn(command, args, {
      cwd: process.cwd(),
      stdio: "inherit",
      shell: process.platform === "win32",
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`${command} ${args.join(" ")} exited with ${code}`));
      }
    });
  });
}

function validateJson(path) {
  JSON.parse(readFileSync(path, "utf8"));
  console.log(`json ok: ${path}`);
}

async function main() {
  validateJson("package.json");
  validateJson("postman/saas-core-template.postman_collection.json");
  validateJson("postman/local.postman_environment.json");

  for (const [command, args] of checks) {
    await run(command, args);
  }

  console.log("\nRelease candidate check passed.");
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
