import { readdirSync, statSync } from "fs";
import { join } from "path";
import { build } from "esbuild";

const jsDir = "static/js";
const outDir = "static/js";

const files = readdirSync(jsDir).filter(
  (f) => f.endsWith(".js") && !f.endsWith(".min.js")
);

let totalSaved = 0;

for (const file of files) {
  const inPath = join(jsDir, file);
  const originalSize = statSync(inPath).size;

  await build({
    entryPoints: [inPath],
    outfile: inPath,
    allowOverwrite: true,
    minify: true,
    bundle: false,
    platform: "browser",
    target: ["es2020"],
    logLevel: "silent",
  });

  const newSize = statSync(inPath).size;
  const saved = originalSize - newSize;
  totalSaved += saved;
  const pct = originalSize ? ((saved / originalSize) * 100).toFixed(1) : "0.0";
  console.log(`  ${file}: ${originalSize} → ${newSize} bytes (−${pct}%)`);
}

console.log(`\nTotal saved: ${(totalSaved / 1024).toFixed(1)} KB`);
