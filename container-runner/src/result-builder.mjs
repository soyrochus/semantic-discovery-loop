// container-runner/src/result-builder.mjs

import { readFile } from "node:fs/promises";
import path from "node:path";

export async function buildResult({ request, repository, copilot, mode }) {
  const semanticLoopDirectory = path.join(
    repository.directory,
    ".work",
    "semantic-loop"
  );

  const state = await readJsonIfPresent(
    path.join(semanticLoopDirectory, "state.json")
  );

  const verification = await readJsonIfPresent(
    path.join(semanticLoopDirectory, "verification.json")
  );

  const scoreValues = verification?.scores
    ? Object.values(verification.scores).map(score => score.value)
    : [];

  const verificationPassed = verification?.passed === true;
  const minimumScore = scoreValues.length > 0 ? Math.min(...scoreValues) : null;

  const status =
    copilot.exitCode === 0 && verificationPassed ? "complete" : "incomplete";

  return {
    runId: request.runId,
    mode,
    status,
    repository: {
      requestedRef: repository.requestedRef,
      resolvedCommit: repository.resolvedCommit
    },
    copilot: {
      exitCode: copilot.exitCode,
      skipped: copilot.skipped === true
    },
    loop: {
      status: state?.status ?? "unknown",
      verificationPassed,
      minimumScore
    }
  };
}

async function readJsonIfPresent(filePath) {
  try {
    return JSON.parse(await readFile(filePath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      return null;
    }

    throw error;
  }
}
