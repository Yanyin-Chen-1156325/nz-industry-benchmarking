import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { extname, join, relative, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");

function sourceFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "dist" ? [] : sourceFiles(path);
    }
    return [".js", ".mjs"].includes(extname(path)) ? [path] : [];
  });
}

for (const file of sourceFiles(root)) {
  execFileSync(process.execPath, ["--check", file], { stdio: "inherit" });
  process.stdout.write(`checked ${relative(root, file)}\n`);
}
