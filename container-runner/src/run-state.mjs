// container-runner/src/run-state.mjs
//
// status.json is the run's only externally visible state while its container is
// alive: created before checkout starts, updated at each phase boundary, and
// heartbeat-touched during the long Copilot call, so a consumer with no container
// access can tell "still running" from "stalled" from "failed" (specs/strenghten-container-run.md).

import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

export async function createRunState({ outputDirectory, runId, mode }) {
  await mkdir(outputDirectory, { recursive: true });
  await mkdir(path.join(outputDirectory, "logs"), { recursive: true });

  const statusPath = path.join(outputDirectory, "status.json");
  const startedAt = new Date().toISOString();

  const status = {
    runId,
    mode,
    phase: "initializing",
    startedAt,
    updatedAt: startedAt,
    resolvedCommit: null,
    error: null
  };

  await persist();
  logEvent("phase.changed", { runId, phase: status.phase });

  async function persist() {
    await writeFile(statusPath, JSON.stringify(status, null, 2));
  }

  return {
    async phase(name, extra = {}) {
      status.phase = name;
      status.updatedAt = new Date().toISOString();
      Object.assign(status, extra);
      await persist();
      logEvent("phase.changed", { runId, phase: name, ...extra });
    },

    async touch() {
      status.updatedAt = new Date().toISOString();
      await persist();
    },

    async fail(error) {
      status.phase = "failed";
      status.updatedAt = new Date().toISOString();
      status.error = error instanceof Error ? error.message : String(error);
      await persist();
      logEvent("phase.changed", { runId, phase: "failed", error: status.error });
    }
  };
}

function logEvent(event, fields) {
  console.log(
    JSON.stringify({
      level: "info",
      event,
      timestamp: new Date().toISOString(),
      ...fields
    })
  );
}
