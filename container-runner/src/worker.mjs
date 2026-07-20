// container-runner/src/worker.mjs

import { cp, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { checkoutRepository } from "./repository-checkout.mjs";
import { compilePrompt } from "./prompt-compiler.mjs";
import { executeCopilot } from "./copilot-process.mjs";
import { buildResult, buildFailureResult } from "./result-builder.mjs";
import { createRunState } from "./run-state.mjs";

const REQUIRED_REQUEST_FIELDS = ["runId", "repository", "analysisScope"];
const HEARTBEAT_INTERVAL_MS = 60_000;

// mock  — exercise checkout/adapter-install/export only; Copilot CLI is never spawned.
// smoke — spawn Copilot CLI with a trivial fixed prompt to prove non-interactive
//         execution, auth, and tool access work, without running the real loop.
// full  — compile and run the actual Semantic Discovery Loop prompt.
const VALID_MODES = new Set(["mock", "smoke", "full"]);

export async function executeRun({ requestPath, outputRoot, mode = "full" }) {
  if (!VALID_MODES.has(mode)) {
    throw new Error(
      `Unknown RUN_MODE "${mode}"; expected one of ${[...VALID_MODES].join(", ")}`
    );
  }

  const request = await readRequest(requestPath);
  const outputDirectory = path.join(outputRoot, request.runId);

  // status.json/logs/ and request.json exist before checkout even starts, so a
  // consumer watching /output can tell a run has begun from the outside.
  const runState = await createRunState({
    outputDirectory,
    runId: request.runId,
    mode
  });

  await writeFile(
    path.join(outputDirectory, "request.json"),
    JSON.stringify(request, null, 2)
  );

  let repository;
  let copilot;

  try {
    await runState.phase("checking-out");

    const workspace = await createTemporaryWorkspace(request.runId);
    repository = await checkoutRepository({
      workspace,
      repository: request.repository
    });

    await runState.phase("checked-out", { resolvedCommit: repository.resolvedCommit });

    await installLoopAdapter(repository.directory);
    await runState.phase("adapter-installed");

    copilot = await runCopilotForMode({
      mode,
      repository,
      request,
      outputDirectory,
      runState
    });

    await runState.phase("building-result");
    const result = await buildResult({ request, repository, copilot, mode });
    await runState.phase(result.status);

    await exportRun({
      repositoryDirectory: repository.directory,
      outputDirectory,
      result
    });

    return result;
  } catch (error) {
    await runState.fail(error);

    await writeFile(
      path.join(outputDirectory, "result.json"),
      JSON.stringify(
        buildFailureResult({ request, mode, repository, copilot, error }),
        null,
        2
      )
    );

    throw error;
  }
}

async function runCopilotForMode({ mode, repository, request, outputDirectory, runState }) {
  if (mode === "mock") {
    return { exitCode: 0, skipped: true };
  }

  const prompt = await compilePrompt({
    mode,
    analysisScope: request.analysisScope,
    runtimeApproved: request.runtime?.approved === true,
    maxIterations: request.execution?.maxIterations ?? 6
  });

  await runState.phase("running-copilot");

  // touch(), not phase(): a long Copilot call must not look stalled, but it also
  // hasn't changed phase — only updatedAt needs to move.
  const heartbeat = setInterval(() => {
    runState.touch().catch(() => {});
  }, HEARTBEAT_INTERVAL_MS);

  let copilotResult;
  try {
    copilotResult = await executeCopilot({
      cwd: repository.directory,
      prompt,
      timeoutSeconds: request.execution?.timeoutSeconds ?? 7200,
      logsDirectory: path.join(outputDirectory, "logs")
    });
  } finally {
    clearInterval(heartbeat);
  }

  await runState.phase("copilot-finished");

  return { ...copilotResult, skipped: false };
}

async function readRequest(requestPath) {
  const raw = await readFile(requestPath, "utf8");
  const request = JSON.parse(raw);

  for (const field of REQUIRED_REQUEST_FIELDS) {
    if (request[field] === undefined || request[field] === null) {
      throw new Error(`Missing required request field: ${field}`);
    }
  }

  if (!request.repository.url || !request.repository.ref) {
    throw new Error("request.repository must include url and ref");
  }

  return request;
}

async function createTemporaryWorkspace(runId) {
  return mkdtemp(path.join(tmpdir(), `semantic-loop-${runId}-`));
}

async function installLoopAdapter(repositoryDirectory) {
  const source =
    process.env.SEMANTIC_LOOP_HOME ??
    "/opt/semantic-discovery-loop/.agent-loop";
  const destination = path.join(repositoryDirectory, ".agent-loop");

  await cp(source, destination, { recursive: true });
  await mkdir(path.join(repositoryDirectory, ".work", "semantic-loop"), {
    recursive: true
  });
  await mkdir(path.join(repositoryDirectory, ".cache", "scripts"), {
    recursive: true
  });
}

async function exportRun({ repositoryDirectory, outputDirectory, result }) {
  const repositoryMetaDirectory = path.join(outputDirectory, "repository");
  await mkdir(repositoryMetaDirectory, { recursive: true });

  await writeFile(
    path.join(outputDirectory, "result.json"),
    JSON.stringify(result, null, 2)
  );

  await writeFile(
    path.join(repositoryMetaDirectory, "metadata.json"),
    JSON.stringify(
      {
        requestedRef: result.repository.requestedRef,
        resolvedCommit: result.repository.resolvedCommit
      },
      null,
      2
    )
  );

  await copyIfExists(
    path.join(repositoryDirectory, ".work", "semantic-loop"),
    path.join(outputDirectory, "semantic-loop")
  );
}

async function copyIfExists(source, destination) {
  try {
    await cp(source, destination, { recursive: true });
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }
}
