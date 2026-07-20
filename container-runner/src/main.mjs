// container-runner/src/main.mjs

import { executeRun } from "./worker.mjs";

try {
  const result = await executeRun({
    requestPath:
      process.env.RUN_REQUEST_PATH ?? "/input/request.json",
    outputRoot:
      process.env.RUN_OUTPUT_PATH ?? "/output",
    mode: process.env.RUN_MODE ?? "full"
  });

  process.exitCode = result.status === "complete" ? 0 : 2;
} catch (error) {
  console.error(
    JSON.stringify({
      level: "error",
      event: "run.failed",
      message: error instanceof Error ? error.message : String(error)
    })
  );

  process.exitCode = 1;
}
