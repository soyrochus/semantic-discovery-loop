# Copilot instructions

This repository, {{PROJECT_NAME}}, contains a semantic discovery loop: a bounded, evidence-backed process
that inventories the codebase, builds a deterministic Source Construct Graph and a
provenance-backed Semantic Construct Graph, and verifies its own output before calling
anything complete. The tool-neutral method lives in `.agent-loop/`.

Loop-specific work must follow `.agent-loop/LOOP.md`. Use
`.github/prompts/run-semantic-discovery-loop.prompt.md` to run it.

Non-negotiable constraints for any loop-related work:

- The source tree is read-only. Never modify source, build, dependency, or application
  configuration files.
- During loop execution, write only under `.work/semantic-loop/**` and
  `.cache/scripts/**`.
- Every semantic claim must be grounded in local repository evidence with provenance;
  web search may explain framework concepts but never proves local existence.
- Represent what cannot be determined as unknown, with recorded assumptions.
- Never mark the loop complete while any score in
  `.work/semantic-loop/verification.json` is below 8.