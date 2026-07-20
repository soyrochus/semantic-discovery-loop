// container-runner/src/worker.mjs

import { cp, mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import { checkoutRepository } from "./repository-checkout.mjs";
import { compilePrompt } from "./prompt-compiler.mjs";
import { executeCopilot } from "./copilot-process.mjs";
import { buildResult } from "./result-builder.mjs";

const REQUIRED_REQUEST_FIELDS = ["runId", "repository", "analysisScope"];

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
  const workspace = await createTemporaryWorkspace(request.runId);

  const repository = await checkoutRepository({
    workspace,
    repository: request.repository
  });

  await installLoopAdapter(repository.directory);

  const copilot = await runCopilotForMode({ mode, repository, request });

  const result = await buildResult({
    request,
    repository,
    copilot,
    mode
  });

  await exportRun({
    repositoryDirectory: repository.directory,
    outputDirectory: `${outputRoot}/${request.runId}`,
    request,
    result,
    copilot
  });

  return result;
}

async function runCopilotForMode({ mode, repository, request }) {
  if (mode === "mock") {
    return {
      exitCode: 0,
      stdout: "",
      stderr: "",
      skipped: true
    };
  }

  const prompt = await compilePrompt({
    mode,
    analysisScope: request.analysisScope,
    runtimeApproved: request.runtime?.approved === true,
    maxIterations: request.execution?.maxIterations ?? 6
  });

  const copilotResult = await executeCopilot({
    cwd: repository.directory,
    prompt,
    timeoutSeconds: request.execution?.timeoutSeconds ?? 7200
  });

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

async function exportRun({
  repositoryDirectory,
  outputDirectory,
  request,
  result,
  copilot
}) {
  const logsDirectory = path.join(outputDirectory, "logs");
  const repositoryMetaDirectory = path.join(outputDirectory, "repository");

  await mkdir(logsDirectory, { recursive: true });
  await mkdir(repositoryMetaDirectory, { recursive: true });

  await writeFile(
    path.join(outputDirectory, "request.json"),
    JSON.stringify(request, null, 2)
  );

  await writeFile(
    path.join(outputDirectory, "result.json"),
    JSON.stringify(result, null, 2)
  );

  await writeFile(path.join(logsDirectory, "copilot.jsonl"), copilot.stdout);
  await writeFile(
    path.join(logsDirectory, "copilot.stderr.log"),
    copilot.stderr
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
