import { spawn } from "node:child_process";

const args = process.argv.slice(2);

if (args.length === 0) {
  console.error("Usage: node scripts/docker-compose.mjs <docker compose args...>");
  process.exit(2);
}

const child = spawn("docker", ["compose", "-f", "deploy/docker-compose.yml", ...args], {
  cwd: process.cwd(),
  stdio: "inherit",
  shell: false,
});

child.on("error", (error) => {
  if (error.code === "ENOENT") {
    console.error("Docker CLI was not found. Install Docker Desktop before using docker:* scripts.");
    process.exit(127);
  }
  console.error(error.message);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
