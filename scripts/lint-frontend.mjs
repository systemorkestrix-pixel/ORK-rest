import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const ROOT = "src";
const VALID_EXTENSIONS = new Set([".ts", ".tsx"]);
const FORBIDDEN_PATTERNS = [
  { regex: /\bconsole\.log\s*\(/, message: "console.log is not allowed" },
  { regex: /\bdebugger\b/, message: "debugger statement is not allowed" },
];

function collectFiles(dir) {
  const files = [];
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      files.push(...collectFiles(fullPath));
      continue;
    }
    if (VALID_EXTENSIONS.has(extname(fullPath))) {
      files.push(fullPath);
    }
  }
  return files;
}

const violations = [];
for (const filePath of collectFiles(ROOT)) {
  const content = readFileSync(filePath, "utf-8");
  const lines = content.split(/\r?\n/);
  lines.forEach((line, index) => {
    FORBIDDEN_PATTERNS.forEach((rule) => {
      if (rule.regex.test(line)) {
        violations.push(`${filePath}:${index + 1}: ${rule.message}`);
      }
    });
  });
}

if (violations.length > 0) {
  console.error(`Frontend lint gate failed with ${violations.length} violation(s):`);
  for (const violation of violations) {
    console.error(`- ${violation}`);
  }
  process.exit(1);
}

console.log("Frontend lint gate passed with zero warnings.");
