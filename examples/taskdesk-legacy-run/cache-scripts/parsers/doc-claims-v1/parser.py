#!/usr/bin/env python3
"""doc-claims — documentation claim tooling for the semantic discovery loop.

Claim *extraction* is model-driven interpretation (skill 10-doc-alignment):
an LLM reads prose and states claims. This tool is the deterministic half
that keeps that interpretation honest:

  anchor mode   parser.py <doc.md> [...]
      Emit the claimable anchors of a documentation file — headings, list
      items, table rows — each with a line span. The extractor states claims
      against these anchors, so every claim starts from a real, addressable
      piece of the document.

  check mode    parser.py --check <doc-claims.json> --repo DIR
                          [--semantic-graph FILE]
      Re-resolve every claim in a doc-claims.json (contract:
      contracts/doc-claims.schema.json) onto the repository: the cited file
      must exist inside the repo, the span must fit the file, the verbatim
      excerpt must occur within the span, confirmed claims must map to
      semantic nodes (resolved against the graph when given). Exit 0 iff
      every claim withstands re-resolution.

  smoke         parser.py --smoke

The checker proves a claim was *read from* the document; whether the reading
is faithful stays a human-checkable judgement — that is why excerpts are
verbatim and spans are mandatory.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

PARSER_ID = "doc-claims-v1"

CLAIM_REQUIRED_KEYS = {
    "id", "claim_type", "text", "excerpt", "file", "span", "status",
    "mapped_nodes", "status_evidence",
}
CLAIM_TYPES = {"terminology", "feature", "rule", "boundary", "intent", "data", "other"}
CLAIM_STATUSES = {"confirmed", "contradicted", "unverifiable"}

MAX_ANCHOR_TEXT = 300

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_NUMBERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?[\s|:-]+\|?\s*$")


# ------------------------------------------------------------------- anchors

def extract_anchors(path: str, text: str) -> dict:
    """Deterministic list of claimable document anchors with line spans."""
    lines = text.splitlines()
    anchors = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _HEADING.match(line)
        if m:
            anchors.append(_anchor("heading", i + 1, i + 1, m.group(2)))
            i += 1
            continue
        m = _BULLET.match(line) or _NUMBERED.match(line)
        if m:
            indent = len(m.group(1))
            start, parts = i, [m.group(2)]
            while (i + 1 < len(lines) and lines[i + 1].strip()
                   and not _BULLET.match(lines[i + 1])
                   and not _NUMBERED.match(lines[i + 1])
                   and not _HEADING.match(lines[i + 1])
                   and len(lines[i + 1]) - len(lines[i + 1].lstrip()) > indent):
                i += 1
                parts.append(lines[i].strip())
            anchors.append(_anchor("list-item", start + 1, i + 1, " ".join(parts)))
            i += 1
            continue
        if line.lstrip().startswith("|") and line.count("|") >= 2:
            if not _TABLE_SEP.match(line):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                anchors.append(_anchor("table-row", i + 1, i + 1, " | ".join(cells)))
            i += 1
            continue
        i += 1
    return {"path": path, "anchors": anchors}


def _anchor(kind: str, start: int, end: int, text: str) -> dict:
    return {"anchor_type": kind,
            "span": {"start_line": start, "end_line": end},
            "text": text.strip()[:MAX_ANCHOR_TEXT]}


# -------------------------------------------------------------------- checks

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def check_claims(doc: dict, repo: Path, semantic: dict | None) -> dict:
    """Re-resolve every claim onto the repository; return errors found."""
    errors: list[str] = []
    claims = doc.get("claims", [])
    seen_ids: set[str] = set()
    node_ids = ({n.get("id") for n in semantic.get("nodes", [])}
                if semantic is not None else None)

    for c in claims:
        cid = c.get("id", "?")
        missing = CLAIM_REQUIRED_KEYS - c.keys()
        if missing:
            errors.append(f"{cid}: missing keys {sorted(missing)}")
            continue
        if not cid.startswith("claim:"):
            errors.append(f"{cid}: id must start with 'claim:'")
        if cid in seen_ids:
            errors.append(f"{cid}: duplicate id")
        seen_ids.add(cid)
        if c["claim_type"] not in CLAIM_TYPES:
            errors.append(f"{cid}: unknown claim_type {c['claim_type']!r}")
        if c["status"] not in CLAIM_STATUSES:
            errors.append(f"{cid}: unknown status {c['status']!r}")

        rel = c["file"]
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            errors.append(f"{cid}: file path escapes the repository: {rel}")
            continue
        f = repo / rel
        if not f.is_file():
            errors.append(f"{cid}: cited file missing: {rel}")
            continue
        file_lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        span = c["span"]
        if not (1 <= span["start_line"] <= span["end_line"] <= max(1, len(file_lines))):
            errors.append(f"{cid}: span {span} does not fit {rel} ({len(file_lines)} lines)")
            continue
        span_text = _norm(" ".join(file_lines[span["start_line"] - 1:span["end_line"]]))
        if not c["excerpt"].strip():
            errors.append(f"{cid}: empty excerpt")
        elif _norm(c["excerpt"]) not in span_text:
            errors.append(f"{cid}: excerpt not found within {rel}:"
                          f"{span['start_line']}-{span['end_line']}")

        if c["status"] == "confirmed" and not c["mapped_nodes"]:
            errors.append(f"{cid}: confirmed claim with no mapped_nodes")
        if node_ids is not None:
            for nid in c["mapped_nodes"]:
                if nid not in node_ids:
                    errors.append(f"{cid}: mapped node not in semantic graph: {nid}")

    if semantic is not None:
        for n in semantic.get("nodes", []):
            for conflict in n.get("conflicts", []):
                ref = conflict.get("claim_ref")
                if ref and ref not in seen_ids:
                    errors.append(f"{n.get('id')}: conflict claim_ref not in doc-claims: {ref}")

    return {"tool": PARSER_ID, "claims_checked": len(claims),
            "errors": errors, "passed": not errors}


# --------------------------------------------------------------------- smoke

SMOKE_DOC = """\
# TaskDesk functional notes

TaskDesk tracks work tickets ("tasks") assigned to operators.

## Business rules

- Managers may reopen closed tasks.
- Operators see only the tasks assigned to them,
  including tasks they created themselves.

| Route | Purpose |
|-------|---------|
| /taskSave.do | persist task edits |
"""


def smoke() -> None:
    result = extract_anchors("docs/notes.md", SMOKE_DOC)
    anchors = result["anchors"]
    kinds = [a["anchor_type"] for a in anchors]
    assert kinds == ["heading", "heading", "list-item", "list-item",
                     "table-row", "table-row"], kinds
    reopen = anchors[2]
    assert reopen["text"] == "Managers may reopen closed tasks."
    assert anchors[3]["span"] == {"start_line": 8, "end_line": 9}, "continuation line joined"
    assert anchors[5]["text"] == "/taskSave.do | persist task edits"
    assert extract_anchors("docs/notes.md", SMOKE_DOC) == result, "must be deterministic"

    with tempfile.TemporaryDirectory(prefix="doc-claims-smoke-") as tmp:
        repo = Path(tmp)
        (repo / "docs").mkdir()
        (repo / "docs" / "notes.md").write_text(SMOKE_DOC)
        semantic = {"nodes": [
            {"id": "sem:action:taskSave"},
            {"id": "sem:rule:owner-scoping",
             "conflicts": [{"claim_ref": "claim:notes:owner-scoping"}]},
        ]}
        good = {
            "repo_fingerprint": None, "extracted_by": PARSER_ID,
            "claims": [
                {"id": "claim:notes:save-route", "claim_type": "feature",
                 "text": "/taskSave.do persists task edits",
                 "excerpt": "/taskSave.do | persist task edits",
                 "file": "docs/notes.md",
                 "span": {"start_line": 13, "end_line": 13},
                 "status": "confirmed", "mapped_nodes": ["sem:action:taskSave"],
                 "status_evidence": "route exists in struts-config"},
                {"id": "claim:notes:owner-scoping", "claim_type": "rule",
                 "text": "operators see only their own tasks",
                 "excerpt": "Operators see only the tasks assigned to them",
                 "file": "docs/notes.md",
                 "span": {"start_line": 8, "end_line": 9},
                 "status": "unverifiable", "mapped_nodes": [],
                 "status_evidence": "no session-scoping code located"},
            ],
        }
        assert check_claims(good, repo, semantic)["passed"]
        assert check_claims(good, repo, None)["passed"], "graph is optional"

        def corrupt(mutate) -> dict:
            bad = json.loads(json.dumps(good))
            mutate(bad)
            return check_claims(bad, repo, semantic)

        forged_span = corrupt(lambda d: d["claims"][0]["span"].update(
            {"start_line": 2, "end_line": 2}))
        assert not forged_span["passed"], "forged span must be caught"
        forged_excerpt = corrupt(lambda d: d["claims"][0].update(
            {"excerpt": "approve task edits"}))
        assert not forged_excerpt["passed"], "reworded excerpt must be caught"
        assert not corrupt(lambda d: d["claims"][0].update({"mapped_nodes": []}))["passed"], \
            "confirmed claim without mapped nodes must be caught"
        assert not corrupt(lambda d: d["claims"][0].update(
            {"mapped_nodes": ["sem:action:ghost"]}))["passed"], \
            "mapped node absent from graph must be caught"
        assert not corrupt(lambda d: d["claims"][1].update(
            {"file": "../outside.md"}))["passed"], "path escape must be caught"
        assert not corrupt(lambda d: d["claims"][1].update(
            {"id": "claim:renamed"}))["passed"], "dangling conflict claim_ref must be caught"
    print("SMOKE PASS")


# ---------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--smoke":
        smoke()
        return 0
    if len(argv) >= 2 and argv[1] == "--check":
        args = argv[2:]
        if not args:
            print(__doc__, file=sys.stderr)
            return 2
        claims_path, repo, graph = Path(args[0]), Path("."), None
        rest = args[1:]
        while rest:
            flag = rest.pop(0)
            if flag == "--repo" and rest:
                repo = Path(rest.pop(0))
            elif flag == "--semantic-graph" and rest:
                graph = json.loads(Path(rest.pop(0)).read_text(encoding="utf-8"))
            else:
                print(f"unknown argument: {flag}", file=sys.stderr)
                return 2
        doc = json.loads(claims_path.read_text(encoding="utf-8"))
        result = check_claims(doc, repo, graph)
        json.dump(result, sys.stdout, indent=2)
        print()
        return 0 if result["passed"] else 1
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    files = []
    for arg in argv[1:]:
        p = Path(arg)
        files.append(extract_anchors(p.as_posix(),
                                     p.read_text(encoding="utf-8", errors="replace")))
    json.dump({"parser_id": PARSER_ID, "files": files}, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
