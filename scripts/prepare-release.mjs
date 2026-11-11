// Stamp a built landing with its revision and write an integrity manifest.
// Usage: node scripts/prepare-release.mjs <dist> <git-sha>
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const [dist, revision] = process.argv.slice(2);
if (!dist || !/^[a-f0-9]{40}$/.test(revision ?? "")) {
  throw new Error("Usage: prepare-release.mjs <dist> <40-char git sha>");
}

// "/deployment.json" on the apex belongs to the client app, so the deploy
// health check reads the revision from this tag on the landing home (/home).
const indexPath = path.join(dist, "index.html");
const html = fs.readFileSync(indexPath, "utf8");
if (!html.includes("</head>")) throw new Error("index.html has no </head>");
fs.writeFileSync(
  indexPath,
  html.replace("</head>", `<meta name="barbersoftly-release" content="${revision}"></head>`),
);

function walk(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const files = walk(dist)
  .map((full) => path.relative(dist, full).split(path.sep).join("/"))
  .filter((relative) => relative !== "deployment.json")
  .sort()
  .map((relative) => ({
    path: relative,
    sha256: createHash("sha256").update(fs.readFileSync(path.join(dist, relative))).digest("hex"),
  }));

fs.writeFileSync(
  path.join(dist, "deployment.json"),
  JSON.stringify(
    { schemaVersion: 1, application: "landing", revision, builtAt: new Date().toISOString(), files },
    null,
    2,
  ) + "\n",
);
console.log(`Prepared landing ${revision} with ${files.length} files`);
