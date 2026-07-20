# Container Runner

`container-runner/` is a small Node.js worker that drives one Semantic Discovery Loop
run **non-interactively**, inside a disposable container, using GitHub Copilot CLI as
the executing agent instead of an interactive assistant session.

It is the implementation of Phase 1 described in
[Local Podman Quick Start — Containerized Semantic Discovery Runner](Local%20Podman%20Quick%20Start%20%E2%80%94%20Containerized%20Semantic%20Discovery%20Runner.md).
That document is the original design/spec and the source of truth for the longer-term
plan (local HTTP dispatcher, then Cloud Run). This document describes what is actually
implemented today and how to use it; where the two disagree on a detail (for example,
the real shape of `verification.json`), this document and the code are authoritative.

The runner does not replace the loop itself — it still delegates entirely to
[`.agent-loop/`](../.agent-loop/LOOP.md). It only automates the part a human assistant
session normally does by hand: cloning the target repository, installing the
`.agent-loop` adapter, invoking the coding assistant (here, Copilot CLI) with the loop
prompt, and exporting the resulting artefacts.

## Repository layout

| Path | Purpose |
| --- | --- |
| `Dockerfile` | Builds the worker image: Node 22, Copilot CLI, the runner source, and a copy of `.agent-loop`. |
| `.dockerignore` | Keeps unrelated repo content (git history, build output, examples, docs) out of the build context. |
| `container-runner/package.json` | Worker package manifest. No runtime dependencies — Node 22 built-ins only. |
| `container-runner/src/main.mjs` | Entry point. Reads env vars, calls `executeRun`, sets the process exit code. |
| `container-runner/src/worker.mjs` | Orchestration: read request → checkout → install adapter → run Copilot (per mode) → build result → export. |
| `container-runner/src/repository-checkout.mjs` | Clones the requested repository and resolves `ref` to a commit SHA. |
| `container-runner/src/prompt-compiler.mjs` | Selects and fills in the prompt template for the requested run mode. |
| `container-runner/src/copilot-process.mjs` | Spawns `copilot` non-interactively and captures stdout/stderr/exit code. |
| `container-runner/src/result-builder.mjs` | Reads `state.json`/`verification.json` from the checkout and builds `result.json`. |
| `container-runner/prompts/execute-semantic-loop.prompt.txt` | The real loop prompt (`full` mode), adapted from `.agent-loop/prompts/run-discovery-loop.md`. |
| `container-runner/prompts/smoke-test.prompt.txt` | Trivial prompt used by `smoke` mode. |
| `local/request.example.json` | Example request; copy to `local/request.json` for a real run. |
| `local/output/` | Default host mount point for exported run artefacts (gitignored contents, directory kept via `.gitkeep`). |

## Execution flow

For every mode, `worker.mjs` performs the same shape of run:

```text
1. Read and validate /input/request.json (runId, repository.url/ref, analysisScope).
2. Create a disposable temporary workspace.
3. Clone the requested repository and resolve ref to a commit SHA.
4. Copy the image-owned .agent-loop into the checkout; create .work/semantic-loop
   and .cache/scripts.
5. Run Copilot CLI (mock: skipped; smoke/full: with the mode's prompt).
6. Read .work/semantic-loop/state.json and verification.json (if present) and
   build result.json.
7. Export request.json, result.json, logs/, repository/metadata.json, and
   .work/semantic-loop/ (if present) to /output/<run-id>/.
8. Exit 0 if result.status is "complete", otherwise 2 (or 1 on a hard failure).
```

The host source tree is never mounted into the container. Only the request file and
the output directory cross the container boundary; the repository clone is disposable
internal storage.

## Run modes (`RUN_MODE`)

The worker supports three tiers of execution, selected by the `RUN_MODE` environment
variable — not by a request field, since it is a way of testing the runner itself
rather than part of the request contract that will later map to the Cloud API.

| `RUN_MODE` | Copilot CLI invoked? | Prompt used | Validates |
| --- | --- | --- | --- |
| `mock` (default not used; must opt in) | No — `executeCopilot` is never called | none | Request parsing, git clone, ref resolution, `.agent-loop` install, artefact export — the plumbing around Copilot. |
| `smoke` | Yes | `prompts/smoke-test.prompt.txt` — write one fixed file and print `SMOKE_OK` | Non-interactive Copilot CLI execution, authentication, and tool access inside the container, without running the full loop. |
| `full` (default) | Yes | `prompts/execute-semantic-loop.prompt.txt` — the real loop prompt | An actual Semantic Discovery Loop run, gated on `verification.json`. |

`result.json` always records which mode produced it (`result.mode`) and whether
Copilot was skipped (`result.copilot.skipped`). In `mock` and `smoke` modes,
`result.status` is always `"incomplete"` — the loop never ran, so there is no
`verification.json` to pass.

Run each tier in order when validating a new environment or Copilot CLI version:
`mock` first (no external calls at all), then `smoke` (proves Copilot + auth work),
then `full`.

## Request format

`local/request.json` (copy from `local/request.example.json`):

| Field | Required | Meaning |
| --- | --- | --- |
| `runId` | yes | Identifier; also the output subdirectory name. |
| `repository.url` | yes | Git URL to clone. |
| `repository.ref` | yes | Branch, tag, or commit to check out. |
| `analysisScope` | yes | Free-text scope, substituted into the `full`-mode prompt. |
| `runtime.approved` | no | Whether the runtime journey phase (skill 09) may execute the target. Defaults to not approved. |
| `execution.maxIterations` | no | Passed into the `full`-mode prompt; defaults to `6`. |
| `execution.timeoutSeconds` | no | Hard timeout for the Copilot CLI process; defaults to `7200`. |

## Authentication

Copilot CLI authenticates from a single environment variable, `COPILOT_GITHUB_TOKEN`.
Nothing is baked into the image, and no credential is persisted between runs:

1. Export the token in your **host** shell: `export COPILOT_GITHUB_TOKEN="github_pat_..."`.
   It must be a fine-grained personal access token with the Copilot Requests
   permission — classic `ghp_` tokens are not accepted.
2. Pass it into the container with the bare `--env COPILOT_GITHUB_TOKEN` flag (no
   `=value`) shown in the run commands below. Podman forwards the host shell's
   variable of the same name.
3. Inside the container, [copilot-process.mjs](../container-runner/src/copilot-process.mjs)
   reads `process.env.COPILOT_GITHUB_TOKEN` and hands it to the spawned `copilot`
   process through an explicit `env` object — `{ PATH, HOME, COPILOT_HOME,
   COPILOT_GITHUB_TOKEN }` — rather than inheriting the full parent environment, so
   nothing else from the container's process env reaches Copilot CLI.
4. `HOME`/`COPILOT_HOME` are set to `/tmp/copilot-home`, a directory local to that
   one container run and never mounted from the host. There is no persisted OAuth
   session or credential cache — every run authenticates fresh from the env var.

The token is never written to `request.json`, `result.json`, or any other artefact
the runner exports (see [Output](#output) below) — the worker only ever writes the
request object (which has no token field), the computed result, and Copilot's own
stdout/stderr. `mock` mode never spawns Copilot at all, so it needs no token.

Do not store `COPILOT_GITHUB_TOKEN` in `request.json` or commit it anywhere.

## Build and run

`COPILOT_CLI_VERSION` is optional. Set it to pin the npm-distributed CLI to a tested
version; leave it unset to install the latest release via GitHub's standalone
installer (`curl -fsSL https://gh.io/copilot-install | bash`), which does not require
Node/npm and installs to `/usr/local/bin`.

```bash
# pinned version
podman build \
  --build-arg COPILOT_CLI_VERSION=<tested-version> \
  --tag semantic-discovery-runner:local \
  .

# latest release, via the standalone installer
podman build --tag semantic-discovery-runner:local .

cp local/request.example.json local/request.json
mkdir -p local/output
```

After the first successful run, pin `COPILOT_CLI_VERSION` in the build so future
builds are reproducible rather than always tracking latest.

Mock run (no Copilot, no token needed):

```bash
podman run --rm --init \
  --env RUN_MODE=mock \
  --mount type=bind,src="$(pwd)/local/request.json",dst=/input/request.json,ro \
  --mount type=bind,src="$(pwd)/local/output",dst=/output,rw \
  semantic-discovery-runner:local
```

Smoke run (needs `COPILOT_GITHUB_TOKEN` in the host shell):

```bash
podman run --rm --init \
  --env RUN_MODE=smoke \
  --env COPILOT_GITHUB_TOKEN \
  --mount type=bind,src="$(pwd)/local/request.json",dst=/input/request.json,ro \
  --mount type=bind,src="$(pwd)/local/output",dst=/output,rw \
  semantic-discovery-runner:local
```

Full run (as `RUN_MODE` defaults to `full`, the flag can be omitted):

```bash
podman run --rm --init \
  --env COPILOT_GITHUB_TOKEN \
  --mount type=bind,src="$(pwd)/local/request.json",dst=/input/request.json,ro \
  --mount type=bind,src="$(pwd)/local/output",dst=/output,rw \
  semantic-discovery-runner:local
```

### Running all three tiers with `mode.js`

`container-runner/mode.js` drives the three `podman run` invocations above for you —
one per `RUN_MODE` tier — against `local/request.example.json`, and checks each
result against what that tier is supposed to prove (plumbing for `mock`, a written
`smoke.json` for `smoke`, a passing verification gate for `full`). It does not build
the image; build it first as shown above.

```bash
cd container-runner
node mode.js              # mock, smoke, full, in order
node mode.js mock         # a single tier
node mode.js mock smoke   # a subset, in the given order
```

`smoke` and `full` are skipped automatically if `COPILOT_GITHUB_TOKEN` is not set in
the environment. Each run's artefacts land under
`local/output/mode-check/<mode>/mode-check-<mode>/`. The script exits non-zero if any
non-skipped tier fails its check.

## Output

```text
local/output/<run-id>/
  request.json
  result.json
  logs/
    copilot.jsonl
    copilot.stderr.log
  repository/
    metadata.json
  semantic-loop/            # copy of the checkout's .work/semantic-loop, if present
    state.json
    verification.json
    reports/
      application-structure.md
    ...
```

Example `result.json` from a `full` run:

```json
{
  "runId": "local-taskdesk-001",
  "mode": "full",
  "status": "complete",
  "repository": {
    "requestedRef": "main",
    "resolvedCommit": "..."
  },
  "copilot": {
    "exitCode": 0,
    "skipped": false
  },
  "loop": {
    "status": "complete",
    "verificationPassed": true,
    "minimumScore": 8
  }
}
```

`status` is `"complete"` only when Copilot exited `0` **and** `verification.json`'s
`passed` field is `true` — a clean Copilot exit code alone is not sufficient.

## Environment variables

| Variable | Set by | Purpose |
| --- | --- | --- |
| `RUN_REQUEST_PATH` | Dockerfile default `/input/request.json` | Where the worker reads the request. |
| `RUN_OUTPUT_PATH` | Dockerfile default `/output` | Where the worker writes `<run-id>/`. |
| `RUN_MODE` | Dockerfile default `full` | `mock`, `smoke`, or `full`; see above. |
| `SEMANTIC_LOOP_HOME` | Dockerfile default `/opt/semantic-discovery-loop/.agent-loop` | Source directory copied into the checkout as `.agent-loop`. |
| `COPILOT_HOME` | Dockerfile default `/tmp/copilot-home` | Copilot CLI's writable home inside the container. |
| `COPILOT_GITHUB_TOKEN` | Host shell, passed with `--env` | Copilot CLI authentication; see [Authentication](#authentication). Required for `smoke` and `full`; not needed for `mock`. |

## What is not built yet

Per the design doc's phased plan, only Phase 1 (this direct `podman run` worker)
exists. There is no local HTTP dispatcher (`POST /runs` / `GET /runs/{runId}`, Phase 2)
and no Cloud Run/Firestore/Cloud Storage deployment (Phase 3).
