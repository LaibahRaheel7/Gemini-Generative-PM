/**
 * Ensures ajv-keywords _formatLimit.js works with ajv v8 (guard for missing _formats).
 * Run after npm install so the patch persists across installs.
 */
const fs = require("fs");
const path = require("path");

const guard = "  if (!formats) return;\n";
const search =
  "function extendFormats(ajv) {\n  var formats = ajv._formats;\n  for (var name in COMPARE_FORMATS)";

function walkDir(dir, callback) {
  if (!fs.existsSync(dir)) return;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory() && e.name !== "." && e.name !== "..")
      walkDir(full, callback);
    else if (e.isFile()) callback(full);
  }
}

const nodeModules = path.join(__dirname, "..", "node_modules");
walkDir(nodeModules, (file) => {
  if (path.basename(file) !== "_formatLimit.js") return;
  if (!file.includes("ajv-keywords")) return;
  let content = fs.readFileSync(file, "utf8");
  if (content.includes("if (!formats) return")) return;
  if (!content.includes("var formats = ajv._formats;")) return;
  content = content.replace(
    "var formats = ajv._formats;\n  for (var name in COMPARE_FORMATS)",
    "var formats = ajv._formats;\n  if (!formats) return;\n  for (var name in COMPARE_FORMATS)"
  );
  fs.writeFileSync(file, content);
});
