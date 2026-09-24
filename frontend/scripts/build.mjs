import { copyFile, mkdir } from "node:fs/promises";
import { join, resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const destination = join(root, "dist");

await mkdir(join(destination, "js"), { recursive: true });
for (const file of ["index.html", "styles.css", "config.js", "favicon.svg"]) {
  await copyFile(join(root, file), join(destination, file));
}
for (const file of ["app.js", "api-client.js", "formatters.js"]) {
  await copyFile(join(root, "js", file), join(destination, "js", file));
}

process.stdout.write(`Static frontend built at ${destination}\n`);
