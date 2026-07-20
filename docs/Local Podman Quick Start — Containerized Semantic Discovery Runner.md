# Local Podman Quick Start

## 1. Objective

The first implementation shall run one complete Semantic Discovery Loop inside a disposable local Podman container.

This phase validates the core execution model without introducing:

* an HTTP dispatcher;
* Cloud Run;
* Firestore;
* Cloud Storage;
* Secret Manager;
* asynchronous job management.

The container receives a JSON request, clones the target Git repository, invokes GitHub Copilot CLI, writes the Semantic Discovery Loop artefacts to a mounted output directory and terminates.

```text
request.json
    |
    v
podman run --rm
    |
    +-- clone target repository
    +-- install .agent-loop adapter
    +-- invoke Copilot CLI
    +-- inspect verification.json
    +-- copy results to /output
    |
    v
local/output/<run-id>/
```

The local worker should be implemented first. The same worker image can later become the Cloud Run Job image.

---

## 2. Minimal Repository Structure

Add only the following files initially:

```text
container-runner/
  package.json
  package-lock.json

  src/
    main.mjs
    worker.mjs
    repository-checkout.mjs
    prompt-compiler.mjs
    copilot-process.mjs
    result-builder.mjs

  prompts/
    execute-semantic-loop.prompt.txt

local/
  request.example.json
  output/
    .gitkeep

Dockerfile
.dockerignore
```

There is no local dispatcher in the first iteration.

The container is started directly with `podman run`. This keeps the initial test focused on the difficult part: whether Copilot CLI can execute the loop reliably in an isolated container.

---

## 3. Local Request

Create:

```text
local/request.json
```

Example:

```json
{
  "runId": "local-taskdesk-001",
  "repository": {
    "url": "https://github.com/soyrochus/semantic-discovery-loop.git",
    "ref": "main"
  },
  "analysisScope": "Analyze the bundled taskdesk-legacy application. Focus on application structure, flows, persistence and integrations.",
  "runtime": {
    "approved": false
  },
  "execution": {
    "maxIterations": 6,
    "timeoutSeconds": 7200
  }
}
```

For the first test, using `semantic-discovery-loop` itself as the checked-out repository is convenient because it contains the bundled `taskdesk-legacy` target and known reference artefacts.

The request format should already resemble the later Cloud API contract, even though it is currently read from a file.

---

## 4. Container Behaviour

The worker shall perform the following steps:

```text
1. Read /input/request.json.
2. Validate the required fields.
3. Create /workspace/repository.
4. Clone the requested repository.
5. Resolve the requested ref to a commit SHA.
6. Copy or link the image-owned .agent-loop into the checkout.
7. Create .work/semantic-loop and .cache/scripts.
8. Compile the fixed loop prompt plus analysisScope.
9. Run Copilot CLI from the repository directory.
10. Inspect state.json and verification.json.
11. Write result.json.
12. Copy all generated artefacts to /output/<run-id>/.
13. Exit.
```

The worker shall use its internal clone as disposable storage. The host source tree is not mounted into the container.

Only the request and final output are mounted from the host.

---

## 5. Minimal Dockerfile

GitHub currently distributes Copilot CLI through the `@github/copilot` npm package and requires Node.js 22 or later for that installation path. ([GitHub Docs][1])

```dockerfile
FROM node:22-bookworm-slim

ARG COPILOT_CLI_VERSION

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ca-certificates \
       git \
       jq \
       python3 \
       tini \
    && rm -rf /var/lib/apt/lists/*

RUN npm install --global "@github/copilot@${COPILOT_CLI_VERSION}"

WORKDIR /app

COPY container-runner/package.json container-runner/package-lock.json ./
RUN npm ci --omit=dev

COPY container-runner/src ./src
COPY container-runner/prompts ./prompts

COPY .agent-loop /opt/semantic-discovery-loop/.agent-loop

ENV NODE_ENV=production
ENV SEMANTIC_LOOP_HOME=/opt/semantic-discovery-loop/.agent-loop
ENV RUN_REQUEST_PATH=/input/request.json
ENV RUN_OUTPUT_PATH=/output
ENV COPILOT_HOME=/tmp/copilot-home

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "src/main.mjs"]
```

During early experimentation, the CLI version may be supplied explicitly during the build:

```bash
podman build \
  --build-arg COPILOT_CLI_VERSION=<tested-version> \
  --tag semantic-discovery-runner:local \
  .
```

After the first successful run, the tested version shall be fixed in the build configuration.

---

## 6. Minimal Worker Entry Point

```js
// container-runner/src/main.mjs

import { executeRun } from "./worker.mjs";

try {
  const result = await executeRun({
    requestPath:
      process.env.RUN_REQUEST_PATH ?? "/input/request.json",
    outputRoot:
      process.env.RUN_OUTPUT_PATH ?? "/output"
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
```

The worker should expose one main function:

```js
async function executeRun({ requestPath, outputRoot }) {
  const request = await readRequest(requestPath);
  const workspace = await createTemporaryWorkspace(request.runId);

  const repository = await checkoutRepository({
    workspace,
    repository: request.repository
  });

  await installLoopAdapter(repository.directory);

  const prompt = await compilePrompt({
    analysisScope: request.analysisScope,
    runtimeApproved: request.runtime?.approved === true,
    maxIterations: request.execution?.maxIterations ?? 6
  });

  const copilot = await executeCopilot({
    cwd: repository.directory,
    prompt,
    timeoutSeconds: request.execution?.timeoutSeconds ?? 7200
  });

  const result = await buildResult({
    request,
    repository,
    copilot
  });

  await exportRun({
    repositoryDirectory: repository.directory,
    outputDirectory: `${outputRoot}/${request.runId}`,
    result
  });

  return result;
}
```

The first implementation does not need a general orchestration framework. Straight-line Node.js code is preferable.

---

## 7. Copilot CLI Invocation

Copilot CLI supports programmatic prompt execution, JSONL output, autonomous execution without clarification requests and disabling repository-controlled custom instructions. ([GitHub Docs][2])

The Node.js adapter should use `spawn` directly:

```js
import { spawn } from "node:child_process";

export function executeCopilot({
  cwd,
  prompt,
  timeoutSeconds
}) {
  return new Promise((resolve, reject) => {
    const args = [
      "--prompt",
      prompt,
      "--output-format=json",
      "--no-ask-user",
      "--no-auto-update",
      "--no-custom-instructions",
      "--no-remote",
      "--no-remote-export",
      "--allow-all-tools",
      "--deny-tool=shell(git push)",
      "--deny-tool=shell(gh:*)"
    ];

    const child = spawn("copilot", args, {
      cwd,
      shell: false,
      env: {
        PATH: process.env.PATH,
        HOME: "/tmp/copilot-home",
        COPILOT_HOME: "/tmp/copilot-home",
        COPILOT_GITHUB_TOKEN:
          process.env.COPILOT_GITHUB_TOKEN
      },
      stdio: ["ignore", "pipe", "pipe"]
    });

    let stdout = "";
    let stderr = "";

    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");

    child.stdout.on("data", chunk => {
      stdout += chunk;
      process.stdout.write(chunk);
    });

    child.stderr.on("data", chunk => {
      stderr += chunk;
      process.stderr.write(chunk);
    });

    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
    }, timeoutSeconds * 1000);

    child.on("error", error => {
      clearTimeout(timeout);
      reject(error);
    });

    child.on("close", exitCode => {
      clearTimeout(timeout);

      resolve({
        exitCode,
        stdout,
        stderr
      });
    });
  });
}
```

`--allow-all-tools` is currently required for unattended programmatic execution. Deny rules take precedence over allow rules, allowing commands such as `git push` to remain blocked. ([GitHub Docs][3])

This broad permission model is acceptable for the local proof of concept only when the container contains no valuable credentials besides the Copilot token and analyzes disposable clones.

---

## 8. Authentication

Export a supported Copilot token in the host shell:

```bash
export COPILOT_GITHUB_TOKEN="github_pat_..."
```

Copilot CLI recommends environment-variable authentication for containers and other non-interactive environments. `COPILOT_GITHUB_TOKEN` has precedence over `GH_TOKEN` and `GITHUB_TOKEN`. Classic `ghp_` personal access tokens are not supported; a fine-grained token requires the Copilot Requests account permission. ([GitHub Docs][4])

For this local phase, the token can be passed directly from the host environment:

```bash
--env COPILOT_GITHUB_TOKEN
```

Do not store the token in `request.json` or commit it to the repository.

---

## 9. Build and Run

Prepare the request and output directories:

```bash
cp local/request.example.json local/request.json
mkdir -p local/output
```

Build the image:

```bash
podman build \
  --build-arg COPILOT_CLI_VERSION=<tested-version> \
  --tag semantic-discovery-runner:local \
  .
```

Run one disposable analysis:

```bash
podman run \
  --rm \
  --init \
  --name semantic-discovery-local \
  --env COPILOT_GITHUB_TOKEN \
  --mount type=bind,src="$(pwd)/local/request.json",dst=/input/request.json,ro \
  --mount type=bind,src="$(pwd)/local/output",dst=/output,rw \
  semantic-discovery-runner:local
```

Podman supports passing host environment variables with `--env` and bind-mounting host directories or files into absolute container paths. The `ro` and `rw` mount options control whether the container can modify the mounted content. ([Podman Documentation][5])

On an SELinux-enforcing Linux host, the output mount may require relabelling:

```bash
--mount type=bind,src="$(pwd)/local/output",dst=/output,rw,relabel=private
```

Alternatively, use the equivalent `:Z` volume syntax supported by the local Podman installation.

---

## 10. Expected Output

After execution:

```text
local/output/local-taskdesk-001/
  request.json
  result.json

  logs/
    copilot.jsonl
    copilot.stderr.log

  repository/
    metadata.json

  semantic-loop/
    state.json
    assumptions.json
    inventory.json
    parser-registry.json
    source-graph.json
    semantic-types.json
    semantic-graph.json
    doc-claims.json
    verification.json
    reports/
      application-structure.md
```

The result should contain at least:

```json
{
  "runId": "local-taskdesk-001",
  "status": "complete",
  "repository": {
    "requestedRef": "main",
    "resolvedCommit": "..."
  },
  "copilot": {
    "exitCode": 0
  },
  "loop": {
    "status": "complete",
    "verificationPassed": true,
    "minimumScore": 8
  }
}
```

A Copilot exit code of zero is not sufficient. The local worker shall report `complete` only when the generated `verification.json` passes the Semantic Discovery Loop gate.

---

## 11. First Validation Sequence

The first local milestone should consist of four tests.

### Test 1 — Container and authentication

Run a trivial fixed Copilot prompt inside the image:

```bash
podman run \
  --rm \
  --env COPILOT_GITHUB_TOKEN \
  semantic-discovery-runner:local \
  copilot \
  --prompt "Return only the text COPILOT_OK" \
  --no-ask-user
```

This establishes that:

* Copilot CLI is installed;
* the token works;
* outbound networking works;
* non-interactive execution works.

### Test 2 — Repository checkout

Run the worker without invoking Copilot and verify that:

* the repository is cloned;
* the requested ref resolves correctly;
* the exact commit SHA is recorded;
* `.agent-loop` is available;
* `.work` and `.cache` are created.

### Test 3 — Limited loop execution

Run a prompt that performs only the inventory phase.

Verify that:

```text
.work/semantic-loop/inventory.json
.work/semantic-loop/assumptions.json
.work/semantic-loop/state.json
```

are created and exported.

### Test 4 — Complete loop

Run the full Semantic Discovery Loop.

Verify that:

* Copilot completes without human interaction;
* the source tree remains unchanged;
* all expected artefacts are present;
* schemas validate;
* the verifier executes;
* `result.json` reflects the real gate outcome;
* the container disappears after execution;
* the output remains available on the host.

---

## 12. Local HTTP Phase

The HTTP dispatcher should be added only after direct container execution is stable.

The local HTTP version can initially expose:

```text
POST /runs
GET /runs/{runId}
```

It may run as a second local Node.js process or container that starts worker containers through Podman.

The worker contract shall remain unchanged:

```text
request JSON in
artefact directory out
process exit code
```

This boundary is important. The Cloud Run implementation should replace the local Podman launcher, not rewrite the semantic worker.

The progression is:

```text
Phase 1
request file
  → podman worker
  → local output directory

Phase 2
local HTTP dispatcher
  → podman worker
  → local output directory

Phase 3
Cloud Run dispatcher
  → Cloud Run Job using the same worker image
  → Cloud Storage
```

---

## 13. Local Acceptance Criteria

The local proof of concept is complete when:

1. one Podman command starts the run;
2. the container clones the requested repository;
3. Copilot CLI runs non-interactively;
4. the Semantic Discovery Loop produces its artefacts;
5. the target source remains unchanged;
6. verification determines the final status;
7. results are exported to the host;
8. the container terminates and is removed;
9. no Cloud services are required;
10. the worker code can later run unchanged as a Cloud Run Job.

This local phase isolates the technical uncertainty around Copilot CLI, filesystem permissions and loop completion before introducing distributed infrastructure.

[1]: https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-getting-started "Getting started with GitHub Copilot CLI - GitHub Docs"
[2]: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference?utm_source=chatgpt.com "GitHub Copilot CLI command reference - GitHub Docs"
[3]: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference "GitHub Copilot CLI command reference - GitHub Docs"
[4]: https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/authenticate-copilot-cli?utm_source=chatgpt.com "Authenticating GitHub Copilot CLI - GitHub Docs"
[5]: https://docs.podman.io/en/latest/markdown/podman-run.1.html?utm_source=chatgpt.com "podman-run — Podman documentation"
