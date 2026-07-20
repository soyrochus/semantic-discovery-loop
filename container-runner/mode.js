// container-runner/mode.js
//
// Runs the already-built semantic-discovery-runner image once per RUN_MODE tier
// (mock, smoke, full) against local/request.example.json and reports whether each
// behaved as expected. Does not build the image — see docs/container-runner.md.
//
// Usage:
//   node mode.js              # run mock, smoke, full in order
//   node mode.js mock         # run a single mode
//   node mode.js mock smoke   # run a subset, in the given order

import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.join(
  path.dirname(fileURLToPath(import.meta.url)),
  ".."
);
const IMAGE = process.env.RUNNER_IMAGE ?? "semantic-discovery-runner:local";
const REQUEST_TEMPLATE = path.join(
  REPO_ROOT,
  "local",
  "request.example.json"
);
const OUTPUT_ROOT = path.join(REPO_ROOT, "local", "output", "mode-check");

const MODES = ["mock", "smoke", "full"];
const requestedModes = process.argv.slice(2);
const modesToRun = requestedModes.length > 0 ? requestedModes : MODES;

for (const mode of modesToRun) {
  if (!MODES.includes(mode)) {
    console.error(`Unknown mode "${mode}"; expected one of ${MODES.join(", ")}`);
    process.exit(1);
  }
}

assertPodmanAvailable();
assertImageExists();

const results = modesToRun.map(runMode);

printSummary(results);

const failed = results.filter(r => !r.skipped && !r.ok);
process.exit(failed.length > 0 ? 1 : 0);

function assertPodmanAvailable() {
  const check = spawnSync("podman", ["--version"], { stdio: "ignore" });
  if (check.error || check.status !== 0) {
    console.error("podman is not available on PATH.");
    process.exit(1);
  }
}

function assertImageExists() {
  const check = spawnSync("podman", ["image", "exists", IMAGE]);
  if (check.status !== 0) {
    console.error(
      `Image "${IMAGE}" not found. Build it first:\n\n` +
        `  podman build --build-arg COPILOT_CLI_VERSION=<tested-version> ` +
        `--tag ${IMAGE} .\n`
    );
    process.exit(1);
  }
}

function runMode(mode) {
  console.log(`\n=== RUN_MODE=${mode} ===`);

  const needsToken = mode === "smoke" || mode === "full";
  if (needsToken && !process.env.COPILOT_GITHUB_TOKEN) {
    console.log(`skipped: COPILOT_GITHUB_TOKEN is not set (required for "${mode}")`);
    return { mode, skipped: true };
  }

  const runId = `mode-check-${mode}`;
  const requestPath = writeRequestFile(runId);
  const outputDir = path.join(OUTPUT_ROOT, mode);
  rmSync(outputDir, { recursive: true, force: true });
  mkdirSync(outputDir, { recursive: true });

  const args = [
    "run",
    "--rm",
    "--init",
    "--env",
    `RUN_MODE=${mode}`,
    "--mount",
    `type=bind,src=${requestPath},dst=/input/request.json,ro`,
    "--mount",
    `type=bind,src=${outputDir},dst=/output,rw`
  ];

  if (needsToken) {
    args.push("--env", "COPILOT_GITHUB_TOKEN");
  }

  args.push(IMAGE);

  const run = spawnSync("podman", args, { stdio: "inherit", env: process.env });
  const resultPath = path.join(outputDir, runId, "result.json");

  if (!existsSync(resultPath)) {
    const notes = `no result.json exported (podman exit code ${run.status})`;
    console.log(`FAIL: ${notes}`);
    return { mode, ok: false, notes };
  }

  const result = JSON.parse(readFileSync(resultPath, "utf8"));
  const { ok, notes } = evaluate(mode, result, outputDir, runId);

  console.log(`result: ${JSON.stringify(result)}`);
  console.log(`${ok ? "PASS" : "FAIL"}: ${notes}`);

  return { mode, ok, notes };
}

function writeRequestFile(runId) {
  const request = JSON.parse(readFileSync(REQUEST_TEMPLATE, "utf8"));
  request.runId = runId;

  const dir = mkdtempSync(path.join(tmpdir(), "mode-check-request-"));
  const requestPath = path.join(dir, "request.json");
  writeFileSync(requestPath, JSON.stringify(request, null, 2));

  return requestPath;
}

function evaluate(mode, result, outputDir, runId) {
  if (mode === "mock") {
    if (result.mode !== "mock" || result.copilot.skipped !== true) {
      return { ok: false, notes: "expected copilot.skipped=true" };
    }
    return {
      ok: true,
      notes: "checkout/adapter-install/export ran without invoking Copilot"
    };
  }

  if (mode === "smoke") {
    if (result.copilot.exitCode !== 0) {
      return { ok: false, notes: `copilot exited ${result.copilot.exitCode}` };
    }

    const smokeFile = path.join(outputDir, runId, "semantic-loop", "smoke.json");
    if (!existsSync(smokeFile)) {
      return { ok: false, notes: "smoke.json was not written by Copilot" };
    }

    const smoke = JSON.parse(readFileSync(smokeFile, "utf8"));
    if (smoke.smoke !== "ok") {
      return {
        ok: false,
        notes: `unexpected smoke.json content: ${JSON.stringify(smoke)}`
      };
    }

    return { ok: true, notes: "Copilot CLI ran non-interactively and wrote smoke.json" };
  }

  if (result.status !== "complete") {
    return {
      ok: false,
      notes:
        `status="${result.status}" ` +
        `(verificationPassed=${result.loop.verificationPassed}, ` +
        `minimumScore=${result.loop.minimumScore})`
    };
  }

  return { ok: true, notes: "loop completed and the verification gate passed" };
}

function printSummary(results) {
  console.log("\n=== summary ===");
  for (const r of results) {
    const status = r.skipped ? "SKIPPED" : r.ok ? "PASS" : "FAIL";
    console.log(`${r.mode.padEnd(6)} ${status}${r.notes ? ` — ${r.notes}` : ""}`);
  }
}
