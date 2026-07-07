#!/usr/bin/env python3
"""verifier — independent verification tool for the semantic discovery loop.

Scores all ten gate dimensions by *measuring* the artefacts in
.work/semantic-loop/ against the repository — never by asserting. Every score
is derived from named checks; the formulas are fixed in this file, which is
human-reviewed gallery code, not generated during the loop.

Independence rules this tool embodies:
  - it reads artefacts and the repository; it writes only verification.json;
  - it re-derives facts (recounts edges, re-resolves provenance, re-runs
    parser smoke tests, recomputes hashes) instead of trusting generator
    bookkeeping;
  - before a PASS verdict is trusted, it must demonstrate it can fail: the
    built-in self-test mutates copies of the artefacts and asserts the gate
    catches each mutation.

Usage:
  python3 verify.py [--work DIR] [--iteration N] [--no-self-test] [--no-write]
  python3 verify.py --self-test [--work DIR]   # mutation self-test only
  python3 verify.py --smoke                    # self-contained smoke test

Exit code 0 when the gate passes, 1 when it fails (ITERATING), 2 on usage or
artefact-loading errors.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from fnmatch import fnmatch
from pathlib import Path

TOOL_ID = "verifier-v1"
GALLERY_SOURCE = ".agent-loop/tools/verifier"

DIMENSIONS = [
    "inventory_coverage", "parser_validity", "source_graph_consistency",
    "semantic_type_quality", "semantic_graph_provenance", "assertion_grounding",
    "journey_corroboration", "report_coverage", "unknowns_handling",
    "reproducibility",
]

# RT-8 normalization rule for runtime artefacts: journeys.json and its trace
# files must be written pre-normalized. These patterns must not occur anywhere
# in the serialized artefact; screenshots are exempt from cross-run byte
# identity and are checked by recorded-hash integrity instead.
VOLATILE_PATTERNS = [
    (re.compile(r"jsessionid", re.IGNORECASE), "session id"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"), "wall-clock timestamp"),
    (re.compile(r'"(?:timestamp|started_at|finished_at|duration(?:_ms)?|session_id|cookies?|set-cookie|date)"', re.IGNORECASE), "volatile field name"),
    (re.compile(r"/(?:home|Users)/[A-Za-z0-9_.-]+/"), "absolute user path"),
]

EVIDENCE_KINDS = {"parsed", "observed", "asserted"}
CLAIM_STATUSES = {"confirmed", "contradicted", "unverifiable"}

KERNEL_TYPES = {
    "Application", "Module", "EntryPoint", "Interface", "Flow", "Action",
    "View", "Component", "DataObject", "DataStore", "Rule", "Integration",
    "Job", "Configuration", "SecurityElement", "UnknownSemanticConstruct",
}

# Node types the loop driver may assemble directly (file listing / doc
# headings). Everything else must name the registered parser that emitted it.
STRUCTURAL_TYPES = {"File", "Directory", "DocumentationSection"}

REQUIRED_REPORT_SECTIONS = [
    "Application overview", "Detected technology stack",
    "Source inventory summary", "Major modules/components", "Entrypoints",
    "Views/screens", "Controllers/actions/handlers", "Services/domain logic",
    "Data access and persistence", "External integrations",
    "Semantic type registry summary", "Unresolved unknowns", "Assumptions",
    "Confidence and evidence notes", "Limitations",
]

REGISTRY_REQUIRED_KEYS = {
    "parser_id", "artifact_type", "input_patterns", "script_path",
    "invocation", "output_schema", "validation_status", "tests",
    "known_limitations", "writes_source_tree", "network_required",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clamp(v: int) -> int:
    return max(0, min(10, v))


class Artefacts:
    """Loaded loop artefacts plus repo context."""

    def __init__(self, work: Path, repo: Path):
        self.work = work
        self.repo = repo
        self.inventory = self._load("inventory.json")
        self.registry = self._load("parser-registry.json")
        self.source = self._load("source-graph.json")
        self.types = self._load("semantic-types.json")
        self.semantic = self._load("semantic-graph.json")
        self.doc_claims = self._load("doc-claims.json", optional=True)
        self.journeys = self._load("runtime/journeys.json", optional=True)
        self.assumptions = self._load("assumptions.json")
        self.state = self._load("state.json", optional=True) or {}
        report = work / "reports" / "application-structure.md"
        self.report_text = report.read_text(encoding="utf-8") if report.exists() else None

    def _load(self, name: str, optional: bool = False):
        path = self.work / name
        if not path.exists():
            if optional:
                return None
            raise FileNotFoundError(f"required artefact missing: {path}")
        return json.loads(path.read_text(encoding="utf-8"))


class Result:
    def __init__(self):
        self.checks: list[dict] = []
        self.scores: dict[str, dict] = {}

    def check(self, dimension: str, check_id: str, ok: bool, detail: str, warn: bool = False) -> bool:
        self.checks.append({
            "check": check_id, "score": dimension,
            "result": "pass" if ok else ("warn" if warn else "fail"),
            "detail": detail,
        })
        return ok

    def score(self, dimension: str, value: int, measurement: str) -> None:
        derived = [c["check"] for c in self.checks if c["score"] == dimension]
        self.scores[dimension] = {
            "value": clamp(value), "derived_from": derived, "measurement": measurement,
        }

    def failed(self, dimension: str) -> int:
        return sum(1 for c in self.checks if c["score"] == dimension and c["result"] == "fail")


# ---------------------------------------------------------------- dimensions

def score_inventory(a: Artefacts, r: Result, run_subprocesses: bool) -> None:
    files = a.inventory.get("files", [])
    listed = {f["path"] for f in files}
    uncertainties = " ".join(a.inventory.get("uncertainties", []))
    scope_roots = a.inventory.get("summary", {}).get("scope_roots") or sorted(
        {p.split("/", 1)[0] for p in listed})

    unexplained: list[str] = []
    if run_subprocesses:
        proc = subprocess.run(["git", "ls-files", *scope_roots], cwd=a.repo,
                              text=True, capture_output=True)
        tracked = [l for l in proc.stdout.splitlines() if l]
        unexplained = [t for t in tracked if t not in listed and t not in uncertainties]
        r.check("inventory_coverage", "inv-scope-complete", not unexplained,
                f"{len(tracked)} tracked files under {scope_roots}; "
                f"{len(unexplained)} neither inventoried nor explained in uncertainties: {unexplained[:5]}")

    missing = [f["path"] for f in files if not (a.repo / f["path"]).is_file()]
    r.check("inventory_coverage", "inv-files-exist", not missing,
            f"{len(files)} inventoried files; {len(missing)} missing on disk: {missing[:5]}")

    mismatched = [f["path"] for f in files
                  if f.get("hash") and (a.repo / f["path"]).is_file()
                  and sha256(a.repo / f["path"]) != f["hash"]]
    r.check("inventory_coverage", "inv-hashes-match", not mismatched,
            f"recomputed sha256 for {len(files)} files; {len(mismatched)} mismatches: {mismatched[:5]}")

    value = 10 - 3 * len(unexplained) - 3 * len(missing) - 2 * len(mismatched)
    r.score("inventory_coverage", value,
            f"{len(files)} files inventoried; {len(unexplained)} unexplained tracked paths, "
            f"{len(missing)} missing, {len(mismatched)} hash mismatches")


def score_parsers(a: Artefacts, r: Result, run_subprocesses: bool) -> None:
    parsers = a.registry.get("parsers", [])
    incomplete = [p.get("parser_id", "?") for p in parsers
                  if not REGISTRY_REQUIRED_KEYS.issubset(p.keys())]
    r.check("parser_validity", "reg-manifests-complete", not incomplete,
            f"{len(parsers)} manifests; incomplete: {incomplete}")

    unvalidated = [p["parser_id"] for p in parsers
                   if p.get("validation_status") != "validated"]
    r.check("parser_validity", "reg-status-validated", not unvalidated,
            f"non-validated parsers: {unvalidated}")

    smoke_failures, fidelity_failures = [], []
    for p in parsers:
        script = a.repo / p.get("script_path", "")
        if not script.exists():
            smoke_failures.append(f"{p['parser_id']} (script missing)")
            continue
        if run_subprocesses:
            proc = subprocess.run(["python3", str(script), "--smoke"], cwd=a.repo,
                                  text=True, capture_output=True)
            if proc.returncode != 0 or "SMOKE PASS" not in proc.stdout:
                smoke_failures.append(p["parser_id"])
        if p.get("origin") == "gallery" and not p.get("adaptations"):
            gallery = a.repo / p.get("gallery_source", "") / script.name
            if not gallery.exists() or gallery.read_bytes() != script.read_bytes():
                fidelity_failures.append(p["parser_id"])
    if run_subprocesses:
        r.check("parser_validity", "reg-smoke-tests", not smoke_failures,
                f"re-ran --smoke for {len(parsers)} parsers; failures: {smoke_failures}")
    r.check("parser_validity", "reg-gallery-fidelity", not fidelity_failures,
            "gallery copies claiming no adaptations diverging from gallery source: "
            f"{fidelity_failures}")

    value = 10 - 3 * r.failed("parser_validity")
    r.score("parser_validity", value,
            f"{len(parsers)} parsers; {len(smoke_failures)} smoke failures, "
            f"{len(fidelity_failures)} fidelity failures, {len(incomplete)} incomplete manifests, "
            f"{len(unvalidated)} unvalidated")


def score_source_graph(a: Artefacts, r: Result) -> None:
    nodes = a.source.get("nodes", [])
    edges = a.source.get("edges", [])
    ids = [n["id"] for n in nodes]
    idset = set(ids)

    dangling = [e["id"] for e in edges
                if e["source_id"] not in idset or e["target_id"] not in idset]
    r.check("source_graph_consistency", "src-no-dangling", not dangling,
            f"{len(edges)} edges; dangling: {len(dangling)} {dangling[:5]}")

    dupes = len(ids) - len(idset)
    r.check("source_graph_consistency", "src-unique-ids", dupes == 0,
            f"{len(nodes)} nodes; duplicate ids: {dupes}")

    bad_spans = [n["id"] for n in nodes if n.get("span")
                 and (n["span"]["start_line"] < 1 or n["span"]["end_line"] < n["span"]["start_line"])]
    bad_prefix = [n["id"] for n in nodes if not n["id"].startswith("src:")]
    r.check("source_graph_consistency", "src-shape", not bad_spans and not bad_prefix,
            f"bad spans: {bad_spans[:5]}; bad id prefixes: {bad_prefix[:5]}")

    by_parser = {p["parser_id"]: p for p in a.registry.get("parsers", [])}
    bad_attr = []
    for n in nodes:
        pid = n.get("parser_id")
        if pid is None:
            if n["type"] not in STRUCTURAL_TYPES:
                bad_attr.append(f"{n['id']} (type {n['type']} needs a parser)")
        elif pid not in by_parser:
            bad_attr.append(f"{n['id']} (unregistered parser {pid})")
        elif n.get("path") and not any(
                fnmatch(n["path"], pat) for pat in by_parser[pid]["input_patterns"]):
            bad_attr.append(f"{n['id']} ({pid} does not match {n['path']})")
    r.check("source_graph_consistency", "src-parser-attribution", not bad_attr,
            f"nodes whose parser_id is unregistered, missing, or pattern-mismatched: "
            f"{len(bad_attr)} {bad_attr[:5]}")

    value = 10 - 3 * r.failed("source_graph_consistency")
    r.score("source_graph_consistency", value,
            f"{len(nodes)} nodes / {len(edges)} edges; {len(dangling)} dangling, "
            f"{dupes} duplicate ids, {len(bad_attr)} attribution violations")


def score_types(a: Artefacts, r: Result) -> None:
    types = {t["type_id"]: t for t in a.types.get("types", [])}
    missing_kernel = sorted(KERNEL_TYPES - set(types))
    r.check("semantic_type_quality", "types-kernel-present", not missing_kernel,
            f"kernel types missing: {missing_kernel}")

    used = {n["type"] for n in a.semantic.get("nodes", [])}
    unstable = [t for t in used
                if types.get(t, {}).get("status") not in ("accepted", "validated")]
    r.check("semantic_type_quality", "types-used-are-stable", not unstable,
            f"semantic graph uses types not accepted/validated: {unstable}")

    vague = [tid for tid, t in types.items()
             if not t.get("detection_rules") or not t.get("required_evidence")]
    r.check("semantic_type_quality", "types-operational", not vague,
            f"types without detection rules or required evidence: {vague[:5]}")

    value = 10 - 3 * r.failed("semantic_type_quality") - (1 if len(types) > 40 else 0)
    r.score("semantic_type_quality", value,
            f"{len(types)} types, {len(used)} in use; {len(unstable)} unstable in use, "
            f"{len(vague)} non-operational")


def score_provenance(a: Artefacts, r: Result) -> None:
    source_ids = {n["id"] for n in a.source.get("nodes", [])}
    nodes = a.semantic.get("nodes", [])

    ungrounded = [n["id"] for n in nodes if not n.get("grounded_in")]
    r.check("semantic_graph_provenance", "sem-all-grounded", not ungrounded,
            f"{len(nodes)} semantic nodes; without provenance: {ungrounded}")

    bad_refs = [f"{n['id']} -> {g['source_node']}"
                for n in nodes for g in n.get("grounded_in", [])
                if g.get("source_node") and g["source_node"] not in source_ids]
    r.check("semantic_graph_provenance", "sem-refs-resolve", not bad_refs,
            f"grounding refs not in source graph: {len(bad_refs)} {bad_refs[:5]}")

    bad_files, bad_spans = [], []
    for n in nodes:
        for g in n.get("grounded_in", []):
            if g.get("kind") == "observed":
                continue  # journey-shaped evidence; re-resolved by journey_corroboration
            f = a.repo / g.get("file", "")
            if not f.is_file():
                bad_files.append(f"{n['id']} -> {g.get('file')}")
            elif g.get("span"):
                lines = len(f.read_text(encoding="utf-8", errors="replace").splitlines()) or 1
                if g["span"]["end_line"] > lines:
                    bad_spans.append(f"{n['id']} -> {g['file']}:{g['span']['end_line']}>{lines}")
    r.check("semantic_graph_provenance", "sem-evidence-files", not bad_files and not bad_spans,
            f"missing evidence files: {bad_files[:5]}; spans past EOF: {bad_spans[:5]}")

    bad_conf = [n["id"] for n in nodes
                if not isinstance(n.get("confidence"), (int, float))
                or not 0 <= n["confidence"] <= 1]
    r.check("semantic_graph_provenance", "sem-confidence", not bad_conf,
            f"nodes without explicit confidence in [0,1]: {bad_conf[:5]}")

    # Authority rule (LOOP.md): kind absent = parsed; asserted evidence is
    # never sufficient for existence, so an asserted-only node must stay
    # candidate/proposed (or be an UnknownSemanticConstruct).
    bad_kinds = [f"{n['id']} ({g.get('kind')})"
                 for n in nodes for g in n.get("grounded_in", [])
                 if g.get("kind") is not None and g["kind"] not in EVIDENCE_KINDS]
    r.check("semantic_graph_provenance", "sem-kind-valid", not bad_kinds,
            f"provenance entries with unknown evidence kind: {bad_kinds[:5]}")

    asserted_existence = [
        n["id"] for n in nodes
        if n.get("grounded_in")
        and all(g.get("kind") == "asserted" for g in n["grounded_in"])
        and n["type"] != "UnknownSemanticConstruct"
        and n.get("status") in ("validated", "accepted")]
    r.check("semantic_graph_provenance", "sem-asserted-not-sufficient", not asserted_existence,
            f"nodes validated/accepted on asserted (documentation) evidence alone: "
            f"{asserted_existence[:5]}")

    if ungrounded or bad_refs or asserted_existence:
        value = min(5, 10 - 3 * r.failed("semantic_graph_provenance"))
    else:
        value = (10 - 2 * (len(bad_files) + len(bad_spans))
                 - (2 if bad_conf else 0) - (2 if bad_kinds else 0))
    r.score("semantic_graph_provenance", value,
            f"{len(nodes)} nodes, {sum(len(n.get('grounded_in', [])) for n in nodes)} grounding entries; "
            f"{len(ungrounded)} ungrounded, {len(bad_refs)} unresolved refs, "
            f"{len(bad_files) + len(bad_spans)} evidence file/span problems, "
            f"{len(asserted_existence)} asserted-only existence violations")


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def score_assertions(a: Artefacts, r: Result) -> None:
    """Documentation claims re-resolved onto the repository (doc-claims.json).

    The phase is degradable: an absent artefact is a recorded unknown, not a
    gate failure — but asserted evidence in the semantic graph without a
    claims artefact behind it is a violation either way.
    """
    sem_nodes = a.semantic.get("nodes", [])
    asserted_refs = [(n["id"], g) for n in sem_nodes for g in n.get("grounded_in", [])
                     if g.get("kind") == "asserted"]

    if a.doc_claims is None:
        r.check("assertion_grounding", "doc-claims-present", True,
                "doc-claims.json absent: doc-alignment phase not run or no "
                "documentation in scope; layer stands as a recorded unknown", warn=True)
        orphaned = [nid for nid, _ in asserted_refs]
        ok = r.check("assertion_grounding", "doc-asserted-backed", not orphaned,
                     f"asserted evidence with no doc-claims artefact behind it: {orphaned[:5]}")
        r.score("assertion_grounding", 10 if ok else 4,
                "doc alignment not run; "
                f"{len(orphaned)} unbacked asserted provenance entries")
        return

    claims = a.doc_claims.get("claims", [])
    claim_ids = {c.get("id") for c in claims}
    sem_ids = {n["id"] for n in sem_nodes}

    unresolved, bad_excerpts = [], []
    for c in claims:
        cid = c.get("id", "?")
        rel = c.get("file", "")
        parts = Path(rel).parts
        if Path(rel).is_absolute() or ".." in parts:
            unresolved.append(f"{cid} (path escapes repo: {rel})")
            continue
        f = a.repo / rel
        if not f.is_file():
            unresolved.append(f"{cid} (missing {rel})")
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        span = c.get("span") or {}
        if not (1 <= span.get("start_line", 0) <= span.get("end_line", 0) <= max(1, len(lines))):
            unresolved.append(f"{cid} (span {span} beyond {rel})")
            continue
        span_text = _norm_ws(" ".join(lines[span["start_line"] - 1:span["end_line"]]))
        excerpt = _norm_ws(c.get("excerpt", ""))
        if not excerpt or excerpt not in span_text:
            bad_excerpts.append(f"{cid} ({rel}:{span['start_line']}-{span['end_line']})")
    r.check("assertion_grounding", "doc-spans-resolve", not unresolved,
            f"{len(claims)} claims; provenance that does not resolve onto the "
            f"repository: {unresolved[:5]}")
    r.check("assertion_grounding", "doc-excerpts-match", not bad_excerpts,
            f"claims whose verbatim excerpt is not found within the cited span: "
            f"{bad_excerpts[:5]}")

    indefinite = [c.get("id", "?") for c in claims
                  if c.get("status") not in CLAIM_STATUSES]
    r.check("assertion_grounding", "doc-status-definite", not indefinite,
            f"claims without a definite confirmed/contradicted/unverifiable "
            f"status: {indefinite[:5]}")

    bad_maps = [f"{c.get('id', '?')} -> {nid}"
                for c in claims for nid in c.get("mapped_nodes", [])
                if nid not in sem_ids]
    unmapped_confirmed = [c.get("id", "?") for c in claims
                          if c.get("status") == "confirmed" and not c.get("mapped_nodes")]
    r.check("assertion_grounding", "doc-nodes-resolve",
            not bad_maps and not unmapped_confirmed,
            f"mapped nodes missing from semantic graph: {bad_maps[:5]}; "
            f"confirmed claims mapping to nothing: {unmapped_confirmed[:5]}")

    orphaned = [f"{nid} -> {g.get('claim_ref')}" for nid, g in asserted_refs
                if g.get("claim_ref") not in claim_ids]
    dangling_conflicts = [f"{n['id']} -> {c.get('claim_ref')}"
                          for n in sem_nodes for c in n.get("conflicts", [])
                          if c.get("claim_ref") and c["claim_ref"] not in claim_ids]
    r.check("assertion_grounding", "doc-refs-linked",
            not orphaned and not dangling_conflicts,
            f"asserted provenance without a resolvable claim_ref: {orphaned[:5]}; "
            f"node conflicts referencing unknown claims: {dangling_conflicts[:5]}")

    counts = {s: sum(1 for c in claims if c.get("status") == s) for s in sorted(CLAIM_STATUSES)}
    value = 10 - 3 * r.failed("assertion_grounding")
    r.score("assertion_grounding", value,
            f"{len(claims)} claims re-resolved ({counts}); {len(unresolved)} unresolved, "
            f"{len(bad_excerpts)} excerpt mismatches, {len(indefinite)} indefinite, "
            f"{len(bad_maps) + len(unmapped_confirmed)} node-mapping problems, "
            f"{len(orphaned) + len(dangling_conflicts)} broken claim links")


def score_journeys(a: Artefacts, r: Result) -> None:
    """Runtime journeys re-resolved (runtime/journeys.json).

    The phase is degradable: an absent artefact is a recorded unknown, not a
    gate failure — but observed evidence in the semantic graph without a
    journeys artefact behind it is a violation either way. When the artefact
    is present the verifier re-derives, not trusts: it recomputes every
    recorded trace/screenshot hash, re-resolves journey and node references,
    matches walked routes against parsed Route nodes, and recomputes the
    committed database file's hash to prove the source tree was untouched.
    """
    sem_nodes = a.semantic.get("nodes", [])
    observed_refs = [(n["id"], g) for n in sem_nodes for g in n.get("grounded_in", [])
                     if g.get("kind") == "observed"]

    if a.journeys is None:
        r.check("journey_corroboration", "jr-journeys-present", True,
                "runtime/journeys.json absent: runtime phase not run (no approval, "
                "missing dependency, or target not launchable); layer stands as a "
                "recorded unknown", warn=True)
        orphaned = [nid for nid, _ in observed_refs]
        ok = r.check("journey_corroboration", "jr-observed-backed", not orphaned,
                     f"observed evidence with no journeys artefact behind it: {orphaned[:5]}")
        r.score("journey_corroboration", 10 if ok else 4,
                "runtime phase not run; "
                f"{len(orphaned)} unbacked observed provenance entries")
        return

    journeys = a.journeys.get("journeys", [])
    jids = {j.get("id") for j in journeys}
    sem_ids = {n["id"] for n in sem_nodes}

    approval = a.journeys.get("approval") or {}
    r.check("journey_corroboration", "jr-approval-recorded", bool(approval.get("granted")),
            "explicit user approval recorded for executing the target"
            if approval.get("granted") else
            "journeys artefact present without recorded user approval (RT-3)")

    orphaned = [f"{nid} -> {g.get('journey_ref')}" for nid, g in observed_refs
                if g.get("journey_ref") not in jids]
    r.check("journey_corroboration", "jr-refs-resolve", not orphaned,
            f"observed provenance without a resolvable journey_ref: {orphaned[:5]}")

    bad_refs = []
    for j in journeys:
        for s in j.get("steps", []):
            for ref in (s.get("trace_ref"), s.get("screenshot")):
                if not ref:
                    continue
                p = a.work / ref.get("path", "")
                if not p.is_file() or sha256(p) != ref.get("sha256"):
                    bad_refs.append(f"{j.get('id', '?')}#s{s.get('index')} {ref.get('path')}")
    r.check("journey_corroboration", "jr-traces-resolve", not bad_refs,
            f"trace/screenshot refs whose file is missing or whose recomputed sha256 "
            f"differs from the recorded one: {bad_refs[:5]}")

    bad_nodes = [f"{j.get('id', '?')} -> {nid}" for j in journeys
                 for nid in j.get("corroborates", []) if nid not in sem_ids]
    r.check("journey_corroboration", "jr-corroborates-resolve", not bad_nodes,
            f"corroborated node ids missing from the semantic graph: {bad_nodes[:5]}")

    route_paths = {n["properties"].get("path") for n in a.source.get("nodes", [])
                   if n.get("type") == "Route"}
    bad_routes = [f"{j.get('id', '?')}#s{s.get('index')} {s.get('route')}"
                  for j in journeys for s in j.get("steps", [])
                  if s.get("route") and s["route"] not in route_paths]
    r.check("journey_corroboration", "jr-routes-match", not bad_routes,
            f"walked routes with no matching parsed Route node: {bad_routes[:5]}")

    snap = a.journeys.get("db_snapshot") or {}
    src = a.repo / snap.get("source_file", "")
    snap_ok = src.is_file() and sha256(src) == snap.get("source_sha256")
    r.check("journey_corroboration", "jr-source-db-untouched", snap_ok,
            f"committed database file {snap.get('source_file')} recomputed hash "
            f"{'matches' if snap_ok else 'DIFFERS from'} the recorded launch-time hash (RT-2)")

    counts = sum(len(j.get("steps", [])) for j in journeys)
    value = 10 - 3 * r.failed("journey_corroboration")
    r.score("journey_corroboration", value,
            f"{len(journeys)} journeys / {counts} steps re-resolved; "
            f"{len(orphaned)} broken journey refs, {len(bad_refs)} trace integrity failures, "
            f"{len(bad_nodes)} node-mapping problems, {len(bad_routes)} route mismatches, "
            f"source db untouched={snap_ok}")


def score_report(a: Artefacts, r: Result, provisional_pass: bool) -> None:
    if a.report_text is None:
        r.check("report_coverage", "report-exists", False, "report not written yet")
        r.score("report_coverage", 0, "reports/application-structure.md absent")
        return
    r.check("report_coverage", "report-exists", True, "report present")

    required = list(REQUIRED_REPORT_SECTIONS)
    if a.doc_claims is not None:
        required.append("Documentation drift")
    if a.journeys is not None:
        required.append("Runtime journeys")
    text = a.report_text.lower()
    missing = [s for s in required if s.lower() not in text]
    r.check("report_coverage", "report-sections", not missing,
            f"{len(required) - len(missing)}/{len(required)} "
            f"required sections present; missing: {missing}")

    says_final = bool(re.search(r"status:\s*final", text))
    says_partial = bool(re.search(r"status:\s*(partial|iterating)", text))
    consistent = (says_final and provisional_pass) or (says_partial and not provisional_pass)
    r.check("report_coverage", "report-status-consistent",
            consistent,
            f"report says final={says_final} partial={says_partial}; "
            f"other dimensions pass={provisional_pass} — a FINAL claim requires a passing gate",
            warn=(says_partial and provisional_pass))

    value = round(10 * (len(required) - len(missing)) / len(required))
    if not (says_final or says_partial):
        value -= 2
    if says_final and not provisional_pass:
        value = min(value, 7)
    r.score("report_coverage", value,
            f"{len(required) - len(missing)}/{len(required)} sections; "
            f"status marker final={says_final}/partial={says_partial}")


def score_unknowns(a: Artefacts, r: Result) -> None:
    unknown_nodes = [n for n in a.semantic.get("nodes", [])
                     if n["type"] == "UnknownSemanticConstruct"]
    r.check("unknowns_handling", "unk-represented", bool(unknown_nodes),
            f"UnknownSemanticConstruct nodes: {len(unknown_nodes)}")

    uncertainties = a.inventory.get("uncertainties", [])
    r.check("unknowns_handling", "unk-inventory-uncertainties", bool(uncertainties),
            f"inventory uncertainties recorded: {len(uncertainties)}")

    assum = a.assumptions.get("assumptions", [])
    bad = [x.get("id", "?") for x in assum
           if not all(k in x for k in ("id", "statement", "reason", "confidence", "status"))]
    r.check("unknowns_handling", "unk-assumptions-explicit", bool(assum) and not bad,
            f"{len(assum)} assumptions; malformed: {bad}")

    value = 10 - 3 * r.failed("unknowns_handling")
    r.score("unknowns_handling", value,
            f"{len(unknown_nodes)} unknown constructs, {len(uncertainties)} uncertainties, "
            f"{len(assum)} assumptions")


def score_reproducibility(a: Artefacts, r: Result, run_subprocesses: bool) -> None:
    artefact_list = [("inventory", a.inventory), ("source-graph", a.source),
                     ("semantic-graph", a.semantic), ("state", a.state)]
    if a.journeys is not None:
        artefact_list.append(("journeys", a.journeys))
    fingerprints = {name: art.get("repo_fingerprint") for name, art in artefact_list}
    distinct = set(fingerprints.values())
    head = None
    if run_subprocesses:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=a.repo,
                              text=True, capture_output=True).stdout.strip() or None
    consistent = len(distinct) == 1 and (head is None or distinct == {head})
    r.check("reproducibility", "rep-fingerprint-consistent", consistent,
            f"artefact fingerprints {fingerprints}; git HEAD {head}")

    nondeterministic = []
    if run_subprocesses:
        for p in a.registry.get("parsers", []):
            sample = next((f["path"] for f in a.inventory.get("files", [])
                           if any(fnmatch(f["path"], pat) for pat in p["input_patterns"])), None)
            script = a.repo / p["script_path"]
            if sample and script.exists():
                runs = [subprocess.run(["python3", str(script), sample], cwd=a.repo,
                                       text=True, capture_output=True).stdout
                        for _ in range(2)]
                if runs[0] != runs[1] or not runs[0]:
                    nondeterministic.append(p["parser_id"])
        r.check("reproducibility", "rep-parsers-deterministic", not nondeterministic,
                f"double-ran each parser on a repository sample; unstable output: {nondeterministic}")

    assumptions_stored = (a.work / "assumptions.json").exists()
    r.check("reproducibility", "rep-assumptions-stored", assumptions_stored,
            "assumptions.json present" if assumptions_stored else "assumptions.json missing")

    # RT-8 split standard: static artefacts stay byte-identical (checks above);
    # dynamic runtime artefacts must be *semantically* reproducible, which the
    # contract operationalizes as pre-normalization — volatile content
    # (timestamps, session ids, cookie/date values, durations, absolute user
    # paths) is prohibited in journeys.json and its trace files outright, so
    # two runs over the same state compare equal without a fuzzy diff.
    if a.journeys is not None:
        volatile: list[str] = []
        blobs = [("runtime/journeys.json", json.dumps(a.journeys))]
        for j in a.journeys.get("journeys", []):
            for s in j.get("steps", []):
                ref = s.get("trace_ref") or {}
                p = a.work / ref.get("path", "")
                if ref.get("path") and p.is_file():
                    blobs.append((ref["path"], p.read_text(encoding="utf-8", errors="replace")))
        for name, blob in blobs:
            for pattern, label in VOLATILE_PATTERNS:
                m = pattern.search(blob)
                if m:
                    volatile.append(f"{name}: {label} ({m.group(0)[:40]!r})")
        r.check("reproducibility", "rep-journeys-normalized", not volatile,
                f"volatile content prohibited by the normalization rule found in "
                f"runtime artefacts: {volatile[:5]}")

    value = 10 - 3 * r.failed("reproducibility")
    r.score("reproducibility", value,
            f"fingerprints consistent={consistent}; "
            f"{len(nondeterministic)} nondeterministic parsers")


# ------------------------------------------------------------------ assembly

def run_verification(work: Path, repo: Path, iteration: int,
                     run_subprocesses: bool = True) -> dict:
    a = Artefacts(work, repo)
    r = Result()
    score_inventory(a, r, run_subprocesses)
    score_parsers(a, r, run_subprocesses)
    score_source_graph(a, r)
    score_types(a, r)
    score_provenance(a, r)
    score_assertions(a, r)
    score_journeys(a, r)
    score_unknowns(a, r)
    score_reproducibility(a, r, run_subprocesses)
    provisional_pass = all(s["value"] >= 8 for s in r.scores.values())
    score_report(a, r, provisional_pass)

    failures = [f"{k} below 8" for k in DIMENSIONS if r.scores[k]["value"] < 8]
    passed = not failures
    weakest = None if passed else min(DIMENSIONS, key=lambda k: r.scores[k]["value"])
    action = None
    if not passed:
        failing_checks = [c for c in r.checks if c["score"] == weakest and c["result"] == "fail"]
        action = (f"Improve {weakest}: fix " +
                  "; ".join(c["check"] + " (" + c["detail"][:120] + ")" for c in failing_checks[:3]))
    return {
        "iteration": iteration,
        "passed": passed,
        "verifier": {"tool": TOOL_ID, "gallery_source": GALLERY_SOURCE, "self_test": None},
        "scores": {k: r.scores[k] for k in DIMENSIONS},
        "weakest_score": weakest,
        "required_next_action": action,
        "gate_failures": failures,
        "checks": r.checks,
    }


# ------------------------------------------------------------------ self-test

def _mutate_provenance(work: Path) -> str:
    p = work / "semantic-graph.json"
    data = json.loads(p.read_text())
    data["nodes"][0]["grounded_in"] = []
    p.write_text(json.dumps(data))
    return "semantic_graph_provenance"


def _mutate_dangling_edge(work: Path) -> str:
    p = work / "source-graph.json"
    data = json.loads(p.read_text())
    data["edges"].append({"id": "edge:selftest-dangling", "source_id": data["nodes"][0]["id"],
                          "target_id": "src:selftest:does-not-exist", "type": "contains",
                          "confidence": 1.0, "properties": {}})
    p.write_text(json.dumps(data))
    return "source_graph_consistency"


def _mutate_parser_attribution(work: Path) -> str:
    p = work / "source-graph.json"
    data = json.loads(p.read_text())
    node = next((n for n in data["nodes"] if n.get("parser_id")), None)
    if node is None:
        data["nodes"].append({
            "id": "src:selftest:unattributed", "layer": "source", "type": "Class",
            "name": "SelfTest", "path": "selftest.java", "span": None, "hash": None,
            "parser_id": "selftest-bogus-parser-v9", "properties": {}})
    else:
        node["parser_id"] = "selftest-bogus-parser-v9"
    p.write_text(json.dumps(data))
    return "source_graph_consistency"


def _mutate_inventory_gap(work: Path) -> str:
    # Point an inventoried path at a file that does not exist — detectable by
    # the pure inv-files-exist check, no git subprocess needed.
    p = work / "inventory.json"
    data = json.loads(p.read_text())
    entry = {"path": "selftest/does-not-exist.xyz", "role": "unknown",
             "language": None, "artifact_types": [], "size_bytes": 0,
             "hash": None, "uncertainty": None}
    if data["files"]:
        data["files"][0] = {**data["files"][0], "path": entry["path"]}
    else:
        data["files"].append(entry)
    p.write_text(json.dumps(data))
    return "inventory_coverage"


def _mutate_doc_claim(work: Path) -> str:
    # Forge a documentation claim's provenance: shift its span/excerpt so the
    # quoted text no longer occurs where cited. When no doc-claims.json
    # exists, plant one whose claim cites a file that is not on disk — either
    # way the forged reading must be caught.
    p = work / "doc-claims.json"
    if p.exists():
        data = json.loads(p.read_text())
    else:
        data = {"repo_fingerprint": None, "extracted_by": "selftest", "claims": []}
    if data["claims"]:
        c = data["claims"][0]
        c["excerpt"] = "selftest: text that the cited span does not contain"
    else:
        data["claims"].append({
            "id": "claim:selftest:forged", "claim_type": "feature",
            "text": "selftest forged claim",
            "excerpt": "selftest forged claim",
            "file": "selftest/does-not-exist.md",
            "span": {"start_line": 1, "end_line": 1},
            "status": "unverifiable", "mapped_nodes": [],
            "status_evidence": "selftest"})
    p.write_text(json.dumps(data))
    return "assertion_grounding"


def _mutate_asserted_existence(work: Path) -> str:
    # Break the authority rule: promote a node to accepted on documentation
    # evidence alone.
    p = work / "semantic-graph.json"
    data = json.loads(p.read_text())
    node = next((n for n in data["nodes"]
                 if n["type"] != "UnknownSemanticConstruct" and n.get("grounded_in")),
                None)
    if node is None:
        data["nodes"].append({
            "id": "sem:selftest:asserted-only", "layer": "semantic", "type": "Action",
            "name": "SelfTest", "confidence": 0.9, "status": "accepted",
            "grounded_in": [{"source_node": None, "file": "README.md", "span": None,
                             "evidence_type": "doc-claim", "kind": "asserted"}],
            "unknowns": [], "properties": {}})
    else:
        node["status"] = "accepted"
        for g in node["grounded_in"]:
            g["kind"] = "asserted"
    p.write_text(json.dumps(data))
    return "semantic_graph_provenance"


def _mutate_trace_ref(work: Path) -> str:
    # Corrupt a journey's trace reference: flip a recorded sha256 so the
    # recomputed hash no longer matches. When no journeys.json exists, plant
    # one whose step cites a trace file that is not on disk — either way the
    # broken observed evidence must be caught.
    p = work / "runtime" / "journeys.json"
    if p.exists():
        data = json.loads(p.read_text())
        data["journeys"][0]["steps"][0]["trace_ref"]["sha256"] = "0" * 64
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {"repo_fingerprint": None, "produced_by": "selftest",
                "approval": {"granted": True, "statement": "selftest"},
                "environment": {"declared_dependencies": [], "app_base_url": "http://selftest"},
                "db_snapshot": {"source_file": "selftest/missing.sqlite",
                                "source_sha256": "0" * 64,
                                "copy_path": "runtime/db/selftest.sqlite"},
                "journeys": [{"id": "journey:selftest", "name": "selftest",
                              "flow_hypothesis": "selftest", "actor": "selftest",
                              "steps": [{"index": 1, "action": "goto", "url": "/x",
                                         "response_status": 200,
                                         "trace_ref": {"path": "runtime/traces/missing.json",
                                                       "sha256": "0" * 64}}],
                              "corroborates": []}]}
    p.write_text(json.dumps(data))
    return "journey_corroboration"


def _mutate_observed_unbacked(work: Path) -> str:
    # Break the observed-evidence discipline: attach observed provenance whose
    # journey_ref resolves to nothing (or, with no journeys artefact at all,
    # observed evidence with nothing behind it).
    p = work / "semantic-graph.json"
    data = json.loads(p.read_text())
    data["nodes"][0].setdefault("grounded_in", []).append({
        "source_node": None, "evidence_type": "selftest-observed",
        "kind": "observed", "journey_ref": "journey:selftest-does-not-exist"})
    p.write_text(json.dumps(data))
    return "journey_corroboration"


MUTATIONS = [
    ("strip-provenance", _mutate_provenance),
    ("dangling-edge", _mutate_dangling_edge),
    ("bogus-parser-id", _mutate_parser_attribution),
    ("inventory-gap", _mutate_inventory_gap),
    ("forged-doc-claim", _mutate_doc_claim),
    ("asserted-only-accepted", _mutate_asserted_existence),
    ("corrupted-trace-ref", _mutate_trace_ref),
    ("observed-unbacked", _mutate_observed_unbacked),
]


def run_self_test(work: Path, repo: Path) -> dict:
    """Prove the gate can fail: each mutation must push its target dimension
    below 8 on a scored copy of the real artefacts."""
    detected, details = 0, []
    for name, mutate in MUTATIONS:
        with tempfile.TemporaryDirectory(prefix="verifier-selftest-") as tmp:
            tmp_work = Path(tmp) / "work"
            shutil.copytree(work, tmp_work)
            target = mutate(tmp_work)
            # Subprocess checks (smoke/determinism/git) are orthogonal to the
            # mutations and slow; the mutated dimensions are all pure checks.
            result = run_verification(tmp_work, repo, iteration=0,
                                      run_subprocesses=False)
            caught = (not result["passed"]
                      and result["scores"][target]["value"] < 8)
            detected += caught
            details.append({"mutation": name, "target": target, "detected": caught})
    return {"mutations_applied": len(MUTATIONS), "mutations_detected": detected,
            "passed": detected == len(MUTATIONS), "details": details}


# --------------------------------------------------------------------- smoke

def smoke() -> None:
    """Self-contained: builds a minimal artefact set, asserts the pure checks
    pass on the clean fixture and fail on corrupted variants."""
    clean = {
        "inventory.json": {"repo_fingerprint": "f" * 40, "generated_by": "smoke",
                           "summary": {"total_files": 0, "languages": {}, "scope_roots": []},
                           "files": [], "uncertainties": ["smoke fixture"]},
        "parser-registry.json": {"parsers": []},
        "source-graph.json": {"repo_fingerprint": "f" * 40, "nodes": [
            {"id": "src:file:a.java", "layer": "source", "type": "File", "name": "a.java",
             "path": "a.java", "span": {"start_line": 1, "end_line": 2}, "hash": None,
             "parser_id": None, "properties": {}}], "edges": []},
        "semantic-types.json": {"types": [
            {"type_id": t, "parent_type": None, "definition": t,
             "detection_rules": ["r"], "required_evidence": ["e"],
             "optional_evidence": [], "examples": [], "confidence": None,
             "status": "accepted", "version": 1} for t in sorted(KERNEL_TYPES)]},
        "semantic-graph.json": {"repo_fingerprint": "f" * 40, "nodes": [
            {"id": "sem:unknown:x", "layer": "semantic", "type": "UnknownSemanticConstruct",
             "name": "x", "confidence": 0.5, "status": "accepted",
             "grounded_in": [{"source_node": "src:file:a.java", "file": "a.java",
                              "span": None, "evidence_type": "smoke"}],
             "unknowns": [], "properties": {}}], "edges": []},
        "doc-claims.json": {"repo_fingerprint": "f" * 40, "extracted_by": "doc-claims-v1",
                            "documents": ["NOTES.md"], "claims": [
            {"id": "claim:notes:a", "claim_type": "feature",
             "text": "the app has an A class",
             "excerpt": "The system is built around class A.",
             "file": "NOTES.md", "span": {"start_line": 2, "end_line": 2},
             "status": "confirmed", "mapped_nodes": ["sem:unknown:x"],
             "status_evidence": "src:file:a.java"}]},
        "assumptions.json": {"assumptions": [
            {"id": "a1", "statement": "s", "reason": "r", "confidence": 1.0,
             "status": "accepted"}]},
        "state.json": {"repo_fingerprint": "f" * 40},
    }
    with tempfile.TemporaryDirectory(prefix="verifier-smoke-") as tmp:
        work = Path(tmp) / "work"
        (work / "reports").mkdir(parents=True)
        (work / "runtime" / "traces").mkdir(parents=True)
        repo = Path(tmp) / "repo"
        repo.mkdir()
        (repo / "a.java").write_text("class A {\n}\n")
        (repo / "NOTES.md").write_text("# Notes\nThe system is built around class A.\n")
        (repo / "demo.sqlite").write_bytes(b"smoke-db")
        trace = work / "runtime" / "traces" / "t1.json"
        trace.write_text('{"url": "/a.do", "status": 200}\n')
        clean["runtime/journeys.json"] = {
            "repo_fingerprint": "f" * 40, "produced_by": "runtime/scripts/smoke.mjs",
            "approval": {"granted": True, "statement": "smoke fixture"},
            "environment": {"declared_dependencies": [], "app_base_url": "http://localhost:0"},
            "db_snapshot": {"source_file": "demo.sqlite",
                            "source_sha256": hashlib.sha256(b"smoke-db").hexdigest(),
                            "copy_path": "runtime/db/demo.sqlite"},
            "journeys": [{"id": "journey:smoke", "name": "smoke journey",
                          "flow_hypothesis": "claim:notes:a", "actor": "smoke",
                          "steps": [{"index": 1, "action": "goto", "url": "/a.do",
                                     "route": None, "response_status": 200,
                                     "trace_ref": {"path": "runtime/traces/t1.json",
                                                   "sha256": sha256(trace)}}],
                          "corroborates": ["sem:unknown:x"]}]}
        clean["semantic-graph.json"]["nodes"][0]["grounded_in"].append(
            {"source_node": None, "evidence_type": "journey-step", "kind": "observed",
             "journey_ref": "journey:smoke"})
        for name, data in clean.items():
            (work / name).write_text(json.dumps(data))
        (work / "reports" / "application-structure.md").write_text(
            "Status: FINAL\n" + "\n".join(
                f"## {s}" for s in REQUIRED_REPORT_SECTIONS
                + ["Documentation drift", "Runtime journeys"]))

        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert result["passed"], f"clean fixture must pass, got {result['gate_failures']}"

        corrupt = copy.deepcopy(clean)
        corrupt["semantic-graph.json"]["nodes"][0]["grounded_in"] = []
        for name, data in corrupt.items():
            (work / name).write_text(json.dumps(data))
        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert not result["passed"], "ungrounded semantic node must fail the gate"
        assert result["scores"]["semantic_graph_provenance"]["value"] < 8
        assert result["weakest_score"] == "semantic_graph_provenance"
        assert result["required_next_action"], "failing gate must define a next action"

        corrupt = copy.deepcopy(clean)
        corrupt["doc-claims.json"]["claims"][0]["excerpt"] = "class B is the core"
        for name, data in corrupt.items():
            (work / name).write_text(json.dumps(data))
        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert not result["passed"], "forged doc excerpt must fail the gate"
        assert result["scores"]["assertion_grounding"]["value"] < 8

        corrupt = copy.deepcopy(clean)
        node = corrupt["semantic-graph.json"]["nodes"][0]
        node["type"] = "Action"
        node["grounded_in"] = [node["grounded_in"][0]]
        node["grounded_in"][0]["kind"] = "asserted"
        node["grounded_in"][0]["claim_ref"] = "claim:notes:a"
        for name, data in corrupt.items():
            (work / name).write_text(json.dumps(data))
        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert not result["passed"], "asserted-only accepted node must fail the gate"
        assert result["scores"]["semantic_graph_provenance"]["value"] <= 5

        corrupt = copy.deepcopy(clean)
        corrupt["runtime/journeys.json"]["journeys"][0]["steps"][0]["trace_ref"]["sha256"] = "0" * 64
        for name, data in corrupt.items():
            (work / name).write_text(json.dumps(data))
        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert not result["passed"], "corrupted trace hash must fail the gate"
        assert result["scores"]["journey_corroboration"]["value"] < 8

        corrupt = copy.deepcopy(clean)
        corrupt["runtime/journeys.json"]["journeys"][0]["properties"] = {
            "started_at": "2026-07-07T12:00:00Z"}
        for name, data in corrupt.items():
            (work / name).write_text(json.dumps(data))
        result = run_verification(work, repo, iteration=0, run_subprocesses=False)
        assert not result["passed"], "volatile field in journeys.json must fail the gate"
        assert result["scores"]["reproducibility"]["value"] < 8, \
            "normalization rule (RT-8) must be enforced by reproducibility"

        for name, data in clean.items():
            (work / name).write_text(json.dumps(data))
        st = run_self_test(work, repo)
        assert st["mutations_applied"] == len(MUTATIONS)
    print("SMOKE PASS")


# ---------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", default=".work/semantic-loop")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--iteration", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--no-self-test", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.smoke:
        smoke()
        return 0

    work, repo = Path(args.work), Path(args.repo)
    if args.self_test:
        result = run_self_test(work, repo)
        print(json.dumps(result, indent=2))
        return 0 if result["passed"] else 1

    self_test = None
    if not args.no_self_test:
        self_test = run_self_test(work, repo)
        if not self_test["passed"]:
            print("VERIFIER SELF-TEST FAILED — verdict would be untrustworthy", file=sys.stderr)
            print(json.dumps(self_test, indent=2), file=sys.stderr)
            return 2

    iteration = args.iteration
    if iteration is None:
        state = work / "state.json"
        iteration = json.loads(state.read_text()).get("iteration", 0) if state.exists() else 0
    result = run_verification(work, repo, iteration)
    result["verifier"]["self_test"] = (
        {k: self_test[k] for k in ("mutations_applied", "mutations_detected", "passed")}
        if self_test else None)

    if not args.no_write:
        out = work / "verification.json"
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if result["passed"]:
        print("VERIFICATION PASSED — all scores >= 8")
    else:
        print("ITERATING")
        print(f"weakest_score: {result['weakest_score']}")
        print(f"required_next_action: {result['required_next_action']}")
    print(json.dumps({k: v["value"] for k, v in result["scores"].items()}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
