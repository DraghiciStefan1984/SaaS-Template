import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const backendDir = join(process.cwd(), "backend");
const windowsPython = join(backendDir, ".venv", "Scripts", "python.exe");
const unixPython = join(backendDir, ".venv", "bin", "python");
const python = existsSync(windowsPython)
  ? windowsPython
  : existsSync(unixPython)
    ? unixPython
    : "python";

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error("Usage: node scripts/backend-command.mjs <python args...>");
  process.exit(2);
}

const child = spawn(python, args, {
  cwd: backendDir,
  stdio: "inherit",
  shell: false,
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
