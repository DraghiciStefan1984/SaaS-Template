import { existsSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";

const backendDir = join(process.cwd(), "backend");
const windowsPython = join(backendDir, ".venv", "Scripts", "python.exe");
const unixPython = join(backendDir, ".venv", "bin", "python");

function selectPython() {
  if (process.platform === "win32") {
    if (existsSync(windowsPython)) return windowsPython;
    if (existsSync(unixPython)) return unixPython;
    return "python";
  }

  if (existsSync(unixPython)) return unixPython;
  return "python3";
}

const python = selectPython();
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

child.on("error", (error) => {
  if (error.code === "ENOENT") {
    console.error(`Python executable not found: ${python}`);
    console.error("Create a backend virtual environment or install Python on PATH.");
    process.exit(127);
  }
  console.error(error.message);
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
