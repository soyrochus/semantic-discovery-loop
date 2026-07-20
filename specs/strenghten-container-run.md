# Specification: Strengthen Container Runner — Runtime State, Logs, and Crash Visibility

| | |
|---|---|
| **Status** | Implemented |
| **Date** | 2026-07-20 |
| **Applies to** | `container-runner/` — the Phase 1 non-interactive worker described in `docs/container-runner.md` |
| **Supersedes** | Nothing; extends the worker's exported artefact contract |
| **Precedes** | Phase 2 (local HTTP dispatcher) and Phase 3 (Cloud Run) from `docs/Local Podman Quick Start — Containerized Semantic Discovery Runner.md` |

The key words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** in this document are to
be interpreted as described in RFC 2119.

---

## 1. Purpose and scope

The Phase 1 container runner (`podman run` → one worker process → exit) currently
exposes almost nothing about a run's progress or failure short of watching its
container process directly. This specification adds the minimum set of changes needed
for a run's state, logs, and failure cause to be legible **from the mounted `/output`
volume alone**, without introducing a server, a queue, or a database — that remains
Phase 2/3's job (see section 6).

This is explicitly a hand-off requirement: the team taking this over needs to run it
in a cloud environment and be able to answer, for any run, "is it still going, did it
finish cleanly, or did it die" without needing a shell into the process that produced
it.

## 2. Motivation

As implemented before this specification:

- `result.json` is written exactly once, by `exportRun`, as the very last step of
  `executeRun`. Nothing is written to `/output/<runId>/` before that point.
- If anything throws before `exportRun` runs — a bad clone, an unknown `RUN_MODE`, a
  malformed request — the container exits 1, logs one JSON line to its own stderr, and
  **exports nothing**. A crashed run and a run that hasn't started yet are
  indistinguishable from the mounted output directory.
- Copilot's stdout/stderr are buffered in memory for the process's entire lifetime
  (up to `execution.timeoutSeconds`, default 7200s) and only flushed to disk at export
  time — so a long `full` run is completely opaque until it finishes.
- There is no phase/step signal at all: no way to tell "cloning" from "running Copilot"
  from "writing the report" without parsing raw Copilot output.

## 3. Design principles

- **Stay file-based.** Every artefact this specification adds lives under the already
  bind-mounted `/output/<runId>/`. Nothing new requires a server, a socket, or a
  database — consistent with the project's evidence-on-disk philosophy elsewhere in
  the repository.
- **Forward-compatible, not throwaway.** Everything added here MUST carry forward
  unchanged when `/output` becomes a Cloud Storage prefix in Phase 3, and structured
  stdout logging MUST use a shape that lands cleanly in Cloud Logging once the worker
  runs as a Cloud Run Job.
- **Minimum viable state machine.** One additional file (`status.json`), updated at
  phase boundaries, replaces the need for any run registry for the single-run-per-
  container case this phase actually has.

## 4. Requirements

### 4.1 `status.json`, written from the start of the run (OBS-1, OBS-2)

**OBS-1.** `worker.mjs` MUST create `/output/<runId>/` (and its `logs/` subdirectory)
and write an initial `status.json` and `request.json` **before** attempting to clone
the target repository — not after the run completes.

**OBS-2.** `worker.mjs` MUST update `status.json` at each of the following phase
transitions, in order: `initializing` → `checking-out` → `checked-out` →
`adapter-installed` → `running-copilot` → `copilot-finished` → `building-result` →
one of `complete` / `incomplete` / `failed`. `mock` mode MUST skip
`running-copilot`/`copilot-finished` directly to `building-result`, since Copilot is
never spawned.

`status.json` shape:

```json
{
  "runId": "string",
  "mode": "mock | smoke | full",
  "phase": "initializing | checking-out | checked-out | adapter-installed | running-copilot | copilot-finished | building-result | complete | incomplete | failed",
  "startedAt": "ISO 8601 timestamp",
  "updatedAt": "ISO 8601 timestamp, refreshed on every phase change and heartbeat",
  "resolvedCommit": "string | null — set once checkout resolves a SHA",
  "error": "string | null — set only when phase is failed"
}
```

A consumer determines run state with no container access at all:
- **still running** — `status.json` exists, `phase` is non-terminal, `updatedAt` is
  recent.
- **terminated cleanly** — `phase` is `complete` or `incomplete`; cross-check against
  `result.json`.
- **crashed** — `phase` is `failed`; `error` holds the cause.

### 4.2 Crash safety (OBS-3)

**OBS-3.** Once `status.json` exists for a run (i.e. once `runId` has been read from
the request), any error thrown during checkout, adapter install, Copilot execution, or
result building MUST result in:
- `status.json` written with `phase: "failed"` and a populated `error` field, and
- `result.json` written with `status: "failed"`, carrying whatever repository/copilot
  information was actually obtained before the failure (each MAY be `null`).

The error MUST still be rethrown afterward so the existing `main.mjs` exit-code
mapping (1 = crash) is unaffected. A request that fails validation before a `runId` is
known (unparsable JSON, missing `runId`) remains unattributable to any run directory —
this residual gap is accepted (see section 6) since there is no directory to write to.

### 4.3 Logs streamed to disk as they happen (OBS-4)

**OBS-4.** Copilot's stdout MUST be appended to
`/output/<runId>/logs/copilot.jsonl` and stderr to
`/output/<runId>/logs/copilot.stderr.log` as each chunk arrives, in addition to (not
instead of) being echoed live to the container's own stdout/stderr for `podman logs`.
Buffering the full output in memory for later export is no longer permitted for this
purpose.

### 4.4 Heartbeat during long-running Copilot calls (OBS-5)

**OBS-5.** While Copilot is executing, `worker.mjs` MUST refresh `status.json`'s
`updatedAt` on a fixed interval (60 seconds), independent of any phase change, so a
run legitimately taking a long time remains distinguishable from a stalled one purely
by checking whether `updatedAt` is advancing.

### 4.5 Structured phase logs on stdout (OBS-6)

**OBS-6.** Every phase transition SHOULD also be logged as one JSON line to the
container's stdout, following the shape already used by `main.mjs`'s existing crash
log (`{"level", "event", ...}`), e.g. `{"level":"info","event":"phase.changed",
"runId":"...","phase":"...","timestamp":"..."}`. This costs nothing today and requires
no format change when the container's stdout becomes a Cloud Run Job's Cloud Logging
stream in Phase 3.

## 5. Updated artefact contract

`result.json`'s `status` field gains a third value: `"failed"`, alongside the existing
`"complete"` and `"incomplete"`. Consumers that already treat "anything other than
complete" as not-successful (e.g. `container-runner/mode.js`) require no change; a
consumer that wants to distinguish "ran but didn't pass the gate" from "crashed"
now can.

## 6. Out of scope

This specification does not add: multi-run coordination, a run registry that survives
outside a single container's `/output` mount, an HTTP status endpoint, or collision
protection on `runId`. Those require a process outside any one container and remain
Phase 2's responsibility. A request that never yields a `runId` (fails validation
before that point) still produces no on-disk record — only the container's own stderr
line, per `main.mjs`'s existing top-level catch.

## 7. Acceptance criteria

- `node mode.js mock` produces `status.json` with `phase: "complete"` or
  `"incomplete"` matching `result.json`, and the directory + initial `status.json`
  are observable immediately after the container starts (not only after it exits).
- Deliberately pointing a request at an unreachable `repository.url` produces a
  `status.json` with `phase: "failed"` and a non-null `error`, plus a `result.json`
  with `status: "failed"` — where previously nothing was exported at all.
- During a `smoke` or `full` run, `logs/copilot.jsonl` grows while the container is
  still running, observable via `tail -f` on the host-mounted file.
