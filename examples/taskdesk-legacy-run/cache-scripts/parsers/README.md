# .cache/scripts/parsers/

**Working area** for parsers and extractors used by the semantic source-discovery loop
(see `.agent-loop/LOOP.md`). The curated source of prepared parsers is the **gallery**
at `.agent-loop/tools/` — the loop copies gallery tools here, adapts the copies if the
repository needs it, and validates them. Gallery originals are never modified.

Each parser lives in its own subfolder:

```text
.cache/scripts/parsers/
  <parser-id>/
    parser.<ext>        # the parser/extractor (copied from the gallery, or generated)
    manifest.json       # manifest per .agent-loop/contracts/parser-registry.schema.json
    samples/            # optional extra smoke-test inputs from this repository
```

Rules (from `.agent-loop/skills/02-parser-broker.md` and `03-parser-generator.md`):

- Selection order: project tooling → cached → **gallery** → standard local parser →
  custom extractor → generated (last resort).
- One parser per artifact type — no monolithic suite scripts.
- Parsers are read-only over the source tree and emit JSON source-graph fragments.
- Every parser needs a manifest recording its `origin` (`gallery`, `gallery-adapted`,
  `generated`, …) and, for gallery copies, its `gallery_source` and any `adaptations`.
- Gallery copies must pass their built-in smoke test (`parser.py --smoke`) **and** a
  trial run against real repository files before use; generated parsers need their own
  smoke tests before `validation_status` may become `validated`.
- Only validated parsers may produce final artefacts.
- No dependency installation without explicit approval.

Parsers here are a **cache**: reused across runs instead of re-copied or regenerated.
A generated parser that proved solid may be proposed for promotion into the gallery
(human-reviewed; the loop never writes to `.agent-loop/tools/`). All manifests are
aggregated into `.work/semantic-loop/parser-registry.json` during a run.
