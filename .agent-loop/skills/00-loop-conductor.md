# Skill 00 — Loop Conductor

## Purpose

Coordinate the semantic source-discovery loop defined in `.agent-loop/LOOP.md`.

## Responsibilities

- **Maintain state.** Read `.work/semantic-loop/state.json` at the start of every run;
  create it from the shape in `contracts/state.schema.json` if missing (iteration 0,
  status `initialized`, max_iterations 6, repo_fingerprint set to the current git HEAD
  hash if available). Update it after every phase (`last_completed_phase`) and every
  verification (`iteration`, `weakest_score`, `next_action`, `status`).
- **Enforce allowed write locations.** During loop execution, writes go only to
  `.work/semantic-loop/**` and `.cache/scripts/**`. Refuse any step that would write
  elsewhere.
- **Stop source modification.** The source tree is read-only. Never edit, move, or
  delete source, build, dependency, or configuration files.
- **Coordinate phases** in the order given in LOOP.md, invoking skills 01–06, then 10
  (doc alignment — optional and degradable: with no documentation in scope, record the
  layer as an explicit unknown and continue), then 07–08. Skip to the corrective
  action in `state.json.next_action` when resuming a failed verification.
- **Call verification** (skill 07) after every full pass over the artefacts.
- **Identify the weakest score** from `verification.json` and record it in state.
- **Trigger the next iteration** when verification fails: print `ITERATING`, increment
  `iteration`, set the corrective action, and improve the weakest score first.
- **Write the final or partial report** via skill 08: final when verification passes;
  partial (clearly marked) when `max_iterations` is reached without passing.

## Operational procedure

1. Read `LOOP.md`, then this skill.
2. Load or create `state.json`. If `iteration >= max_iterations` and not passed, go to
   step 7 (partial report) instead of iterating further.
3. Run phases 01–06 and 10 (or resume from `next_action`), validating each artefact
   against its schema in `contracts/` before moving on.
4. Run skill 07 (verifier) and write `verification.json`.
5. If `passed` is true: run skill 08 for the final report, set `status: complete`, stop.
6. If `passed` is false: print `ITERATING`, name the weakest score, define the next
   corrective action, update `state.json` (status `iterating`), and loop back to step 3
   targeting the weakest score first.
7. If `max_iterations` is reached: run skill 08 in partial mode, set `status: partial`,
   list unresolved items, stop.

## Completion rule

**Never call the loop complete unless verification passes** — that is, every score in
`verification.json` is 8 or higher and `passed` is true. There are no exceptions.
