#!/usr/bin/env python3
"""Assemble semantic-loop artefacts for taskdesk-legacy plus db.

Orchestration only: all content parsing is delegated to the registered parsers
under .cache/scripts/parsers/ (gallery copies), and verification is delegated
to the independent verifier at .cache/scripts/verifier-v1/. This script builds
no source nodes beyond structural File/DocumentationSection listing, and it
never writes verification.json itself.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path.cwd()
SCOPE_ROOTS = ["taskdesk-legacy", "db"]
WORK = Path(".work/semantic-loop")
REPORTS = WORK / "reports"
CACHE = Path(".cache/scripts")
PARSERS = CACHE / "parsers"
VERIFIER = CACHE / "verifier-v1" / "verify.py"
HEAD = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True).stdout.strip() or None


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_count(path: Path) -> int:
    return max(1, len(read(path).splitlines()))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def run_parser(parser_id: str, files: list[str]) -> dict:
    if not files:
        return {"parser_id": parser_id, "nodes": [], "edges": []}
    cmd = ["python3", str(PARSERS / parser_id / "parser.py"), *files]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=True)
    return json.loads(proc.stdout)


def file_node(path: str, language: str | None, role: str | None = None) -> dict:
    p = ROOT / path
    return {
        "id": f"src:file:{path}",
        "layer": "source",
        "type": "File",
        "name": Path(path).name,
        "path": path,
        "span": {"start_line": 1, "end_line": line_count(p)},
        "hash": sha256(p),
        "parser_id": None,
        "properties": {"language": language, **({"role": role} if role else {})},
    }


def first_line_containing(path: str, needle: str) -> int:
    for idx, line in enumerate(read(ROOT / path).splitlines(), start=1):
        if needle in line:
            return idx
    return 1


def classify(path: str) -> tuple[str | None, str, list[str], str | None]:
    if path.endswith(".java"):
        return "Java", "source", ["java-source"], None
    if path.endswith("pom.xml"):
        return "XML", "build", ["maven-pom", "xml-file"], None
    if path.endswith("struts-config.xml") or path.endswith("validation.xml"):
        return "XML", "configuration", ["struts-xml", "xml-file"], None
    if path.endswith(".jsp"):
        return "JSP", "template", ["jsp-template"], None
    if path.endswith(".xml"):
        return "XML", "configuration", ["xml-file"], None
    if path.endswith(".properties"):
        return "Properties", "configuration", ["properties-file"], None
    if path.endswith(".sql"):
        return "SQL", "data", ["sql-script"], None
    if path.endswith(".sqlite") or path.endswith(".db") or path.endswith(".sqlite3"):
        return "SQLite", "data", ["sqlite-database"], None
    if path.endswith(".css"):
        return "CSS", "source", [], None
    if path.endswith(".md"):
        return "Markdown", "documentation", [], None
    return None, "unknown", [], "No deterministic classification rule matched."


def inventory(files: list[str], skipped_tracked: list[str]) -> dict:
    entries = []
    languages: dict[str, int] = {}
    for path in files:
        lang, role, artifact_types, uncertainty = classify(path)
        if lang:
            languages[lang] = languages.get(lang, 0) + 1
        entries.append({
            "path": path,
            "language": lang,
            "role": role,
            "artifact_types": artifact_types,
            "size_bytes": (ROOT / path).stat().st_size,
            "hash": sha256(ROOT / path),
            "uncertainty": uncertainty,
        })
    frameworks = [
        {"name": "Maven WAR", "evidence": ["taskdesk-legacy/pom.xml"], "confidence": 1.0},
        {"name": "Struts 1.x", "evidence": ["taskdesk-legacy/pom.xml", "taskdesk-legacy/src/main/webapp/WEB-INF/struts-config.xml", "taskdesk-legacy/src/main/webapp/WEB-INF/web.xml"], "confidence": 1.0},
        {"name": "JSP/JSTL", "evidence": ["taskdesk-legacy/pom.xml", "taskdesk-legacy/src/main/webapp/jsp/login.jsp"], "confidence": 0.95},
        {"name": "SQLite JDBC", "evidence": ["taskdesk-legacy/pom.xml", "taskdesk-legacy/src/main/resources/taskdesk.properties", "taskdesk-legacy/src/main/java/com/example/taskdesk/dao/JdbcConnectionManager.java"], "confidence": 1.0},
    ]
    uncertainties = [
        "SQLite schema and DDL are analyzed, but row-level data semantics are not read by the sqlite-schema parser.",
        "The scope is taskdesk-legacy plus db; other repository areas are not analyzed as application evidence.",
    ]
    for path in skipped_tracked:
        uncertainties.append(
            f"Tracked path {path} is not a regular file (symlink or special file) and was "
            f"skipped; its link target was not followed.")
    return {
        "repo_fingerprint": HEAD,
        "generated_by": "git ls-files taskdesk-legacy db with deterministic extension classification",
        "summary": {
            "total_files": len(entries),
            "scope_roots": SCOPE_ROOTS,
            "languages": languages,
            "frameworks_detected": frameworks,
            "excluded": [
                {"pattern": ".work/**", "reason": "semantic-loop generated artefacts are outside requested application/database scope"},
                {"pattern": ".cache/**", "reason": "parser cache and loop scripts are outside requested application/database scope"},
                {"pattern": ".agent-loop/**", "reason": "loop instructions/tools are not application source"},
                {"pattern": "target/**", "reason": "build output excluded if present"},
            ],
        },
        "files": entries,
        "uncertainties": uncertainties,
    }


def parser_registry() -> dict:
    def tool(parser_id: str, artifact_type: str, patterns: list[str], source: str, tests: list[str], limitations: list[str]) -> dict:
        return {
            "parser_id": parser_id,
            "artifact_type": artifact_type,
            "input_patterns": patterns,
            "origin": "gallery",
            "gallery_source": source,
            "adaptations": [],
            "script_path": f".cache/scripts/parsers/{parser_id}/parser.py",
            "invocation": f"python3 .cache/scripts/parsers/{parser_id}/parser.py <files...>",
            "output_schema": "source-graph-fragment-v1",
            "validation_status": "validated",
            "tests": tests,
            "known_limitations": limitations,
            "writes_source_tree": False,
            "network_required": False,
        }
    return {"parsers": [
        tool("java-structure-v1", "java-source", ["taskdesk-legacy/**/*.java"], ".agent-loop/tools/java-structure", ["python3 .cache/scripts/parsers/java-structure-v1/parser.py --smoke", "parsed LoginAction.java real sample"], ["No expression-level symbol resolution; method bodies are not fully parsed."]),
        tool("xml-structure-v1", "xml-file", ["taskdesk-legacy/**/*.xml", "taskdesk-legacy/pom.xml"], ".agent-loop/tools/xml-structure", ["python3 .cache/scripts/parsers/xml-structure-v1/parser.py --smoke", "parsed struts-config.xml real sample"], ["Generic XML structure only; Struts and Maven interpretation come from struts-config-v1 and maven-pom-v1."]),
        tool("struts-config-v1", "struts-xml", ["taskdesk-legacy/**/struts-config.xml", "taskdesk-legacy/**/validation.xml"], ".agent-loop/tools/struts-config", ["python3 .cache/scripts/parsers/struts-config-v1/parser.py --smoke", "parsed struts-config.xml and validation.xml real samples"], ["Struts 1.x vocabulary only; URL suffix derivation (e.g. '.do' from web.xml) is the semantic builder's job."]),
        tool("maven-pom-v1", "maven-pom", ["taskdesk-legacy/pom.xml"], ".agent-loop/tools/maven-pom", ["python3 .cache/scripts/parsers/maven-pom-v1/parser.py --smoke", "parsed taskdesk-legacy/pom.xml real sample"], ["Single-POM view: no parent resolution or property interpolation; plugins/profiles not extracted."]),
        tool("jsp-structure-v1", "jsp-template", ["taskdesk-legacy/**/*.jsp"], ".agent-loop/tools/jsp-structure", ["python3 .cache/scripts/parsers/jsp-structure-v1/parser.py --smoke", "parsed login.jsp real sample"], ["Lexical JSP extraction; scriptlet code is counted, not parsed."]),
        tool("properties-config-v1", "properties-file", ["taskdesk-legacy/**/*.properties"], ".agent-loop/tools/properties-config", ["python3 .cache/scripts/parsers/properties-config-v1/parser.py --smoke", "parsed taskdesk.properties real sample"], ["Duplicate keys collapse to a stable key node if present."]),
        tool("sql-ddl-v1", "sql-script", ["db/**/*.sql"], ".agent-loop/tools/sql-ddl", ["python3 .cache/scripts/parsers/sql-ddl-v1/parser.py --smoke", "parsed db/sql/001_schema_sqlite.sql real sample"], ["Not a full SQL grammar; seed/reset statements are kept as statement nodes, while table/foreign-key details come from CREATE TABLE statements."]),
        tool("sqlite-schema-v1", "sqlite-database", ["db/**/*.sqlite"], ".agent-loop/tools/sqlite-schema", ["python3 .cache/scripts/parsers/sqlite-schema-v1/parser.py --smoke", "introspected db/runtime-data/taskdesk-demo.sqlite real sample"], ["Schema only; row data is not read."]),
    ]}


def build_source(files: list[str]) -> dict:
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    by_parser = {
        "java-structure-v1": [p for p in files if p.endswith(".java")],
        "xml-structure-v1": [p for p in files if p.endswith(".xml")],
        "struts-config-v1": [p for p in files if p.endswith("struts-config.xml") or p.endswith("validation.xml")],
        "maven-pom-v1": [p for p in files if p.endswith("pom.xml")],
        "jsp-structure-v1": [p for p in files if p.endswith(".jsp")],
        "properties-config-v1": [p for p in files if p.endswith(".properties")],
        "sql-ddl-v1": [p for p in files if p.endswith(".sql")],
        "sqlite-schema-v1": [p for p in files if p.endswith(".sqlite") or p.endswith(".db") or p.endswith(".sqlite3")],
    }
    for parser_id, paths in by_parser.items():
        frag = run_parser(parser_id, paths)
        for node in frag["nodes"]:
            nodes.setdefault(node["id"], node)
        for edge in frag["edges"]:
            edges.setdefault(edge["id"], edge)

    # Structural listing only — no content interpretation here.
    for path in files:
        if path.endswith(".md"):
            node = file_node(path, "Markdown", "documentation")
            nodes.setdefault(node["id"], node)
            for idx, line in enumerate(read(ROOT / path).splitlines(), start=1):
                if line.startswith("#"):
                    name = line.lstrip("#").strip()
                    hid = f"src:doc-heading:{path}:{idx}"
                    nodes[hid] = {"id": hid, "layer": "source", "type": "DocumentationSection", "name": name, "path": path, "span": {"start_line": idx, "end_line": idx}, "hash": None, "parser_id": None, "properties": {}}
                    edges[f"edge:{hid}:contained-by-file"] = {"id": f"edge:{hid}:contained-by-file", "source_id": node["id"], "target_id": hid, "type": "contains", "confidence": 1.0, "properties": {}}
        elif path.endswith(".css"):
            nodes.setdefault(f"src:file:{path}", file_node(path, "CSS", "source"))

    return {"repo_fingerprint": HEAD, "nodes": list(nodes.values()), "edges": [e for e in edges.values() if e["source_id"] in nodes and e["target_id"] in nodes]}


def semantic_types() -> dict:
    defs = {
        "Application": "The deployable application as a whole.",
        "Module": "A cohesive package, directory, or layer grouping source constructs.",
        "EntryPoint": "A framework or runtime entry into application code.",
        "Interface": "A user-facing or external-facing surface such as a route or page.",
        "Flow": "A multi-step user or system activity evidenced by related actions/views/data access.",
        "Action": "A controller, handler, or operation that responds to an entrypoint or route.",
        "View": "A rendered user-facing template or screen.",
        "Component": "A reusable source-level implementation unit such as a service, DAO, utility, or form.",
        "DataObject": "A domain object or transfer object represented by model/form classes.",
        "DataStore": "A persistence target such as a database, table, or configured JDBC store.",
        "Rule": "A validation, authorization, or business constraint enforced by configuration or code.",
        "Integration": "A dependency or external technology boundary used by the application.",
        "Job": "Scheduled or asynchronous work.",
        "Configuration": "Runtime or build-time configuration that shapes application behavior.",
        "SecurityElement": "Authentication, authorization, or session-security construct.",
        "UnknownSemanticConstruct": "A source-backed construct whose application meaning remains unresolved.",
    }
    return {"types": [{
        "type_id": t,
        "parent_type": None,
        "definition": d,
        "detection_rules": [f"Instantiate {t} only when a source node or file evidence directly supports the construct."],
        "required_evidence": ["At least one local source file path and span or source-node id."],
        "optional_evidence": ["Corroborating Java class, XML mapping, JSP template, dependency, or documentation catalog evidence."],
        "examples": [],
        "confidence": None,
        "status": "accepted",
        "version": 1,
    } for t, d in defs.items()]}


def build_semantic(source: dict) -> dict:
    source_nodes = {n["id"]: n for n in source["nodes"]}
    sem_nodes: dict[str, dict] = {}
    sem_edges: list[dict] = []

    def prov_node(node_id: str, evidence_type: str) -> dict:
        """Provenance derived from an actual source node — id, path, and span."""
        n = source_nodes[node_id]
        span = n["span"] or {"start_line": 1, "end_line": 1}
        return {"source_node": node_id, "file": n["path"], "span": dict(span), "evidence_type": evidence_type}

    def prov_line(node_id: str, path: str, line: int, evidence_type: str) -> dict:
        return {"source_node": node_id if node_id in source_nodes else None, "file": path,
                "span": {"start_line": line, "end_line": line}, "evidence_type": evidence_type}

    def add(id_: str, typ: str, name: str, confidence: float, grounded: list[dict], props: dict | None = None, unknowns: list[str] | None = None) -> None:
        sem_nodes[id_] = {"id": id_, "layer": "semantic", "type": typ, "name": name, "confidence": confidence, "status": "accepted", "grounded_in": grounded, "unknowns": unknowns or [], "properties": props or {}}

    def edge(src: str, dst: str, typ: str, confidence: float, grounded: list[dict] | None = None, props: dict | None = None) -> None:
        if src in sem_nodes and dst in sem_nodes:
            sem_edges.append({"id": f"sem-edge:{len(sem_edges)+1}:{src}:{typ}:{dst}", "source_id": src, "target_id": dst, "type": typ, "confidence": confidence, "grounded_in": grounded or [], "properties": props or {}})

    web_xml = "taskdesk-legacy/src/main/webapp/WEB-INF/web.xml"
    struts_xml = "taskdesk-legacy/src/main/webapp/WEB-INF/struts-config.xml"

    add("sem:application:taskdesk-legacy", "Application", "TaskDesk Legacy", 0.98, [
        prov_node("src:build-module:taskdesk-legacy", "maven-war-module"),
        prov_node(f"src:file:{web_xml}", "struts-servlet-mapping"),
    ], {"packaging": "war"})

    modules = {
        "action": ("Actions", "taskdesk-legacy/src/main/java/com/example/taskdesk/action/BaseTaskDeskAction.java"),
        "service": ("Services", "taskdesk-legacy/src/main/java/com/example/taskdesk/service/TaskService.java"),
        "dao": ("DAO", "taskdesk-legacy/src/main/java/com/example/taskdesk/dao/TaskDAO.java"),
        "form": ("Forms", "taskdesk-legacy/src/main/java/com/example/taskdesk/form/LoginForm.java"),
        "model": ("Models", "taskdesk-legacy/src/main/java/com/example/taskdesk/model/Task.java"),
        "util": ("Utilities", "taskdesk-legacy/src/main/java/com/example/taskdesk/util/SecurityUtils.java"),
        "view": ("JSP Views", "taskdesk-legacy/src/main/webapp/jsp/login.jsp"),
        "config": ("Configuration", struts_xml),
    }
    for key, (name, path) in modules.items():
        sid = next((n["id"] for n in source["nodes"] if n["path"] == path and n["type"] in ("Class", "Template", "File", "Route")), f"src:file:{path}")
        add(f"sem:module:{key}", "Module", name, 0.9, [prov_node(sid, "directory/package evidence")] if sid in source_nodes else [])
        edge(f"sem:module:{key}", "sem:application:taskdesk-legacy", "part-of", 1.0)

    # EntryPoint: the servlet url-pattern is a parsed XmlElement, so the URL
    # suffix is derived from source evidence, not assumed.
    url_pattern_node = next(
        (n for n in source["nodes"] if n["type"] == "XmlElement" and n["name"] == "url-pattern"
         and n["path"] == web_xml and n["properties"].get("text", "").startswith("*.")), None)
    suffix = url_pattern_node["properties"]["text"][1:] if url_pattern_node else ""
    entry_grounds = [prov_node(f"src:file:{web_xml}", "servlet-and-url-mapping")]
    if url_pattern_node:
        entry_grounds.append(prov_node(url_pattern_node["id"], "servlet-url-pattern"))
    add("sem:entrypoint:struts-action-servlet-do", "EntryPoint", f"Struts ActionServlet *{suffix}", 1.0,
        entry_grounds, {"url_pattern": f"*{suffix}"})
    edge("sem:entrypoint:struts-action-servlet-do", "sem:application:taskdesk-legacy", "part-of", 1.0)

    def add_view(view_path: str, grounds: list[dict]) -> str | None:
        full = "taskdesk-legacy/src/main/webapp" + view_path
        template_id = f"src:template:{full}"
        if template_id not in source_nodes:
            return None
        vid = f"sem:view:{Path(view_path).stem}"
        if vid not in sem_nodes:
            add(vid, "View", view_path, 0.96,
                [prov_node(template_id, "jsp-template")] + grounds, {"view_path": view_path})
            edge(vid, "sem:module:view", "part-of", 1.0)
        return vid

    # Actions and views from the struts-config parser's Route nodes.
    for route_node in [n for n in source["nodes"] if n["type"] == "Route"]:
        props = route_node["properties"]
        route_path = props["path"]
        route = route_path + suffix
        action_class = props.get("action_class") or ""
        class_node_id = f"src:class:{action_class}"
        action_sem = f"sem:action:{route_path.strip('/')}"
        grounds = [prov_node(route_node["id"], "struts-action-mapping")]
        if class_node_id in source_nodes:
            grounds.append(prov_node(class_node_id, "action-class"))
        add(action_sem, "Action", f"{action_class.split('.')[-1]} ({route})", 0.97, grounds,
            {"route": route, "form": props.get("form_bean"), "action_class": action_class})
        edge(action_sem, "sem:entrypoint:struts-action-servlet-do", "triggers", 0.95,
             [prov_node(route_node["id"], "struts-action-mapping")])
        edge(action_sem, "sem:module:action", "part-of", 1.0)
        view_paths = [(props["input"], "input")] if props.get("input") else []
        view_paths.extend((f["path"], f["name"]) for f in props.get("forwards", [])
                          if f.get("path", "").startswith("/jsp/"))
        for view_path, forward_name in view_paths:
            vid = add_view(view_path, [])
            if vid:
                edge(action_sem, vid, "renders", 0.92,
                     [prov_node(route_node["id"], f"forward:{forward_name}")])

    # Views reachable only through global-forwards (e.g. error pages).
    for gf in [n for n in source["nodes"]
               if n["type"] == "ConfigurationEntry" and n["properties"].get("kind") == "global-forward"]:
        target = gf["properties"].get("forward_path", "")
        if target.startswith("/jsp/"):
            add_view(target, [prov_node(gf["id"], "struts-global-forward")])

    # Components/data objects from Java classes.
    for node in source["nodes"]:
        if node["type"] == "Class" and node["path"]:
            path = node["path"]
            qn = node["properties"].get("qualified_name", node["name"])
            if "/service/" in path:
                sid = f"sem:component:service:{node['name']}"
                add(sid, "Component", node["name"], 0.92, [prov_node(node["id"], "service-class")])
                edge(sid, "sem:module:service", "part-of", 1.0)
            elif "/dao/" in path:
                sid = f"sem:component:dao:{node['name']}"
                add(sid, "Component", node["name"], 0.93, [prov_node(node["id"], "dao-class")])
                edge(sid, "sem:module:dao", "part-of", 1.0)
            elif "/util/" in path:
                sid = f"sem:component:util:{node['name']}"
                add(sid, "Component", node["name"], 0.9, [prov_node(node["id"], "utility-class")])
                edge(sid, "sem:module:util", "part-of", 1.0)
            elif "/form/" in path:
                sid = f"sem:dataobject:form:{node['name']}"
                add(sid, "DataObject", node["name"], 0.88, [prov_node(node["id"], "struts-actionform-class")], {"qualified_name": qn})
                edge(sid, "sem:module:form", "part-of", 1.0)
            elif "/model/" in path:
                sid = f"sem:dataobject:model:{node['name']}"
                add(sid, "DataObject", node["name"], 0.9, [prov_node(node["id"], "model-class")], {"qualified_name": qn})
                edge(sid, "sem:module:model", "part-of", 1.0)

    # Class → class `uses` edges (heuristic, word-boundary simple-name match
    # with line evidence). This catches same-package collaborators that
    # import-based traversal misses (e.g. `new AuditService()` needs no
    # import), without expression-level parsing.
    class_sem_by_qname: dict[str, tuple[str, str]] = {}
    for sn in sem_nodes.values():
        if sn["type"] in ("Action", "Component", "DataObject"):
            for g in sn["grounded_in"]:
                src_id = g.get("source_node") or ""
                if src_id.startswith("src:class:"):
                    class_sem_by_qname[src_id[len("src:class:"):]] = (sn["id"], g["file"])
    name_patterns = {qn: re.compile(rf"\b{qn.rsplit('.', 1)[-1]}\b") for qn in class_sem_by_qname}
    for qn, (sid, path) in sorted(class_sem_by_qname.items()):
        hits: dict[str, list[int]] = {}
        for idx, line in enumerate(read(ROOT / path).splitlines(), 1):
            for other, pattern in name_patterns.items():
                if other != qn and pattern.search(line):
                    hits.setdefault(other, []).append(idx)
        for other, lines in sorted(hits.items()):
            other_sid = class_sem_by_qname[other][0]
            if other_sid != sid:
                edge(sid, other_sid, "uses", 0.85,
                     [prov_line(f"src:file:{path}", path, i, "class-name-reference") for i in lines[:3]],
                     {"reference_lines": lines,
                      "heuristic": "word-boundary class-name match in class source; not a call graph"})

    # Data stores: Java SQL literals + DDL statements + live SQLite schema.
    # The database node comes first so table part-of edges can attach to it.
    jdbc_mgr = "taskdesk-legacy/src/main/java/com/example/taskdesk/dao/JdbcConnectionManager.java"
    jdbc_class = "src:class:com.example.taskdesk.dao.JdbcConnectionManager"
    add("sem:datastore:sqlite", "DataStore", "SQLite taskdesk demo database", 0.94, [
        prov_node("src:config:taskdesk-legacy/src/main/resources/taskdesk.properties:taskdesk.db.url", "jdbc-url"),
        prov_node(jdbc_class, "jdbc-connection-manager"),
        prov_node("src:file:db/runtime-data/taskdesk-demo.sqlite", "sqlite-database-file"),
    ], {"jdbc": "sqlite"})
    add("sem:integration:sqlite-jdbc", "Integration", "SQLite JDBC driver", 0.98, [
        prov_node("src:dependency:org.xerial:sqlite-jdbc", "maven-dependency"),
        prov_line(jdbc_class, jdbc_mgr, first_line_containing(jdbc_mgr, "Class.forName"), "driver-load"),
    ])
    edge("sem:datastore:sqlite", "sem:integration:sqlite-jdbc", "integrates-with", 1.0)

    tables = {"TASK": [], "APP_USER": [], "TASK_COMMENT": [], "TASK_AUDIT": []}
    table_patterns = {t: re.compile(rf"\b{t}\b") for t in tables}
    java_paths = sorted(n["path"] for n in source["nodes"] if n["type"] == "Class")
    for rpath in java_paths:
        for idx, line in enumerate(read(ROOT / rpath).splitlines(), 1):
            for table, pattern in table_patterns.items():
                if pattern.search(line):
                    tables[table].append((rpath, idx))
    ddl_nodes = {n["properties"].get("object"): n["id"] for n in source["nodes"]
                 if n["type"] == "SqlStatement" and n["properties"].get("kind") == "CREATE TABLE"
                 and n["path"] == "db/sql/001_schema_sqlite.sql"}
    for table, refs in tables.items():
        db_node = f"src:db:db/runtime-data/taskdesk-demo.sqlite:table:{table}"
        grounds = []
        if refs:
            rpath, idx = refs[0]
            grounds.append(prov_line(f"src:file:{rpath}", rpath, idx, "sql-literal-table-reference"))
        if db_node in source_nodes:
            grounds.append(prov_node(db_node, "sqlite-schema-table"))
        if table in ddl_nodes:
            grounds.append(prov_node(ddl_nodes[table], "sql-ddl-create-table"))
        if grounds:
            add(f"sem:datastore:table:{table.lower()}", "DataStore", table, 0.98, grounds,
                {"table": table, "reference_count": len(refs), "schema_verified": db_node in source_nodes})
            edge(f"sem:datastore:table:{table.lower()}", "sem:datastore:sqlite", "part-of", 0.9)

    # Class → table `references` edges: every table-name literal found above
    # becomes evidence linking the class's semantic node (Action/Component/
    # DataObject) to the table DataStore. Heuristic (literal match, no SQL
    # parsing), so confidence < 1 and every edge carries its line evidence.
    class_path_to_sem: dict[str, set[str]] = {}
    for sn in sem_nodes.values():
        if sn["type"] in ("Action", "Component", "DataObject"):
            for g in sn["grounded_in"]:
                if (g.get("source_node") or "").startswith("src:class:"):
                    class_path_to_sem.setdefault(g["file"], set()).add(sn["id"])
    for table, refs in tables.items():
        table_sem = f"sem:datastore:table:{table.lower()}"
        if table_sem not in sem_nodes:
            continue
        by_class: dict[str, list[tuple[str, int]]] = {}
        for rpath, idx in refs:
            for sid in class_path_to_sem.get(rpath, ()):
                by_class.setdefault(sid, []).append((rpath, idx))
        for sid, lines in sorted(by_class.items()):
            grounds = [prov_line(f"src:file:{p}", p, i, "sql-literal-table-reference")
                       for p, i in lines[:5]]
            edge(sid, table_sem, "references", 0.85, grounds,
                 {"reference_lines": [i for _, i in lines],
                  "heuristic": "word-boundary table-name literal match in class source; SQL is not parsed"})

    # Rules / security / configuration — spans located from source, not assumed.
    login_action = "taskdesk-legacy/src/main/java/com/example/taskdesk/action/LoginAction.java"
    assign_action = "taskdesk-legacy/src/main/java/com/example/taskdesk/action/TaskAssignAction.java"
    report_action = "taskdesk-legacy/src/main/java/com/example/taskdesk/action/TaskReportAction.java"
    add("sem:security:session-login", "SecurityElement", "Session login state", 0.93, [
        prov_node("src:class:com.example.taskdesk.util.SecurityUtils", "session-security-utility"),
        prov_line("src:class:com.example.taskdesk.action.LoginAction", login_action,
                  first_line_containing(login_action, "setAttribute"), "session-attribute-write"),
    ])
    add("sem:rule:manager-role-checks", "Rule", "Manager-only role checks", 0.9, [
        prov_line("src:class:com.example.taskdesk.action.TaskAssignAction", assign_action,
                  first_line_containing(assign_action, "MANAGER"), "role-check"),
        prov_line("src:class:com.example.taskdesk.action.TaskReportAction", report_action,
                  first_line_containing(report_action, "MANAGER"), "role-check"),
    ])
    validator_grounds = [prov_node("src:validation-field:loginForm:username", "commons-validator-field")]
    plugin_node = next((n for n in source["nodes"]
                        if n["properties"].get("kind") == "plug-in" and "Validator" in (n["properties"].get("class_name") or "")), None)
    if plugin_node:
        validator_grounds.append(prov_node(plugin_node["id"], "validator-plugin"))
    add("sem:rule:validator-required-fields", "Rule", "Struts required field validation", 0.96, validator_grounds)
    check_grounds = [prov_node(ddl_nodes[t], f"{t.lower()}-check-constraints") for t in ("APP_USER", "TASK") if t in ddl_nodes]
    check_grounds.append(prov_node("src:db:db/runtime-data/taskdesk-demo.sqlite:table:TASK", "sqlite-create-sql"))
    add("sem:rule:database-check-constraints", "Rule", "Database enum/check constraints", 0.95, check_grounds,
        {"constraints": ["ROLE in OPERATOR/MANAGER", "ACTIVE in 0/1", "STATUS enum", "PRIORITY enum"]})
    add("sem:configuration:taskdesk-db-url", "Configuration", "taskdesk.db.url", 1.0, [
        prov_node("src:config:taskdesk-legacy/src/main/resources/taskdesk.properties:taskdesk.db.url", "properties-entry")
    ])
    add("sem:unknown:runtime-row-semantics", "UnknownSemanticConstruct", "Runtime seed row semantics", 0.7, [
        prov_node("src:file:db/runtime-data/README.md", "documented-row-counts")
    ], unknowns=["The SQLite schema is analyzed, but row contents and business meaning of seed records were not read by the schema parser."])

    for sid in ["sem:security:session-login", "sem:rule:manager-role-checks", "sem:rule:validator-required-fields", "sem:rule:database-check-constraints", "sem:configuration:taskdesk-db-url"]:
        edge(sid, "sem:application:taskdesk-legacy", "part-of", 0.9)
    edge("sem:security:session-login", "sem:rule:manager-role-checks", "secured-by", 0.8)

    return {"repo_fingerprint": HEAD, "nodes": list(sem_nodes.values()), "edges": sem_edges}


def assumptions() -> dict:
    return {"assumptions": [
        {"id": "assumption:scope", "statement": "The requested analysis scope is taskdesk-legacy plus db after user permission to incorporate db.", "reason": "User first requested taskdesk-legacy scope, then explicitly allowed DB incorporation.", "confidence": 1.0, "status": "accepted"},
        {"id": "assumption:java-package-modules", "statement": "Immediate Java package directories action/service/dao/form/model/util represent source modules.", "reason": "Directory names and package declarations align across source files.", "confidence": 0.9, "status": "accepted"},
        {"id": "assumption:do-suffix", "statement": "Struts action paths map to .do URLs through the web.xml url-pattern.", "reason": "The parsed web.xml url-pattern element maps ActionServlet to *.do and struts-config declares action paths without suffix.", "confidence": 1.0, "status": "accepted"},
    ]}


def run_verifier(iteration: int) -> tuple[dict, int]:
    proc = subprocess.run(
        ["python3", str(VERIFIER), "--work", str(WORK), "--iteration", str(iteration)],
        cwd=ROOT, text=True, capture_output=True)
    print(proc.stdout, end="")
    if proc.returncode == 2:
        print(proc.stderr, file=sys.stderr, end="")
        raise RuntimeError("verifier could not produce a verdict")
    return json.loads((WORK / "verification.json").read_text(encoding="utf-8")), proc.returncode


def write_report(inv: dict, src: dict, sem: dict, ver: dict | None) -> None:
    actions = [n for n in sem["nodes"] if n["type"] == "Action"]
    views = [n for n in sem["nodes"] if n["type"] == "View"]
    components = [n for n in sem["nodes"] if n["type"] == "Component"]
    by_id = {n["id"]: n for n in sem["nodes"]}
    table_refs: dict[str, list[str]] = {}
    for e in sem["edges"]:
        if e["type"] == "references" and e["target_id"].startswith("sem:datastore:table:"):
            table_refs.setdefault(by_id[e["target_id"]]["name"], []).append(by_id[e["source_id"]]["name"])
    table_ref_lines = [
        f"- `{t}` is referenced by: {', '.join(sorted(set(cs)))}."
        for t, cs in sorted(table_refs.items())]
    if ver is None:
        status = "Status: PARTIAL - verification pending"
        verification_lines = ["- Verification pending: see verification.json after the verifier runs."]
    elif ver["passed"]:
        status = "Status: FINAL - verification passed (all scores >= 8)"
        verification_lines = None
    else:
        status = "Status: PARTIAL - gate failures: " + ", ".join(ver["gate_failures"])
        verification_lines = None
    if ver is not None:
        st = ver["verifier"].get("self_test") or {}
        verification_lines = [
            f"- Verified by `{ver['verifier']['tool']}` ({ver['verifier'].get('gallery_source')}); "
            f"self-test caught {st.get('mutations_detected', '?')}/{st.get('mutations_applied', '?')} seeded mutations.",
            "- Scores (measured): " + json.dumps({k: v["value"] for k, v in ver["scores"].items()}, sort_keys=True) + ".",
        ]
    lines = [
        "# TaskDesk Legacy Application Structure",
        "",
        status,
        "",
        "## Application overview",
        "TaskDesk Legacy is represented as `sem:application:taskdesk-legacy`, grounded in the Maven WAR module (`taskdesk-legacy/pom.xml`) and the Struts servlet mapping (`taskdesk-legacy/src/main/webapp/WEB-INF/web.xml`).",
        "",
        "## Detected technology stack",
        "- Maven WAR packaging, Struts 1.x, JSP/JSTL, Servlet 2.5, SQLite JDBC, SQL DDL, and a live SQLite demo database are detected from `pom.xml`, `web.xml`, `struts-config.xml`, `taskdesk.properties`, `db/sql/001_schema_sqlite.sql`, and `db/runtime-data/taskdesk-demo.sqlite`.",
        "",
        "## Source inventory summary",
        f"- Scope: `taskdesk-legacy/**` plus `db/**`; files inventoried: {inv['summary']['total_files']}.",
        f"- Language/format counts: {json.dumps(inv['summary']['languages'], sort_keys=True)}.",
        "",
        "## Major modules/components",
        "- Modules: action, service, DAO, form, model, util, view, and configuration modules are represented as `sem:module:*` nodes.",
        f"- Components detected: {', '.join(sorted(n['name'] for n in components))}.",
        "",
        "## Entrypoints",
        "- `sem:entrypoint:struts-action-servlet-do` maps `*.do` URLs to Struts ActionServlet; the suffix is derived from the parsed `url-pattern` element in `web.xml`.",
        "",
        "## Views/screens (if detected)",
        "- Detected JSP views: " + ", ".join(sorted(v["properties"].get("view_path", v["name"]) for v in views)) + ".",
        "- `accessDenied.jsp` and `error.jsp` are reachable only through struts-config `<global-forwards>`, not from a specific action.",
        "",
        "## Controllers/actions/handlers (if detected)",
        "- Detected Struts actions: " + ", ".join(sorted(a["properties"].get("route", a["name"]) for a in actions)) + ".",
        "",
        "## Services/domain logic (if detected)",
        "- Service classes are represented as `Component` nodes where Java classes are under `src/main/java/com/example/taskdesk/service/`, including task, user, and audit services.",
        "",
        "## Data access and persistence (if detected)",
        "- DAO components touch `TASK`, `APP_USER`, `TASK_COMMENT`, and `TASK_AUDIT`; each table is represented as a `DataStore` from Java SQL literals, `db/sql/001_schema_sqlite.sql`, and live SQLite schema introspection.",
        "- `sem:datastore:sqlite` is grounded in the `taskdesk.db.url` configuration entry, `JdbcConnectionManager.java`, and `db/runtime-data/taskdesk-demo.sqlite`.",
        "- Foreign-key and index evidence is present in the source graph from `sqlite-schema-v1`, including TASK to APP_USER, comments/audit to TASK and APP_USER, and indexes on status, priority, owner, due date, comment task, and audit task.",
        "- Class-to-table `references` edges (word-boundary literal match, confidence 0.85, line evidence on every edge):",
        *table_ref_lines,
        "",
        "## External integrations (if detected)",
        "- `sem:integration:sqlite-jdbc` is grounded in the `org.xerial:sqlite-jdbc` Maven dependency (span from the maven-pom parser) and `Class.forName(\"org.sqlite.JDBC\")`.",
        "",
        "## Semantic type registry summary",
        "- The kernel semantic vocabulary is used with accepted status only; no project-specific candidate types were needed.",
        "",
        "## Unresolved unknowns",
        "- `sem:unknown:runtime-row-semantics`: schema and row counts are known, but row contents and business meaning of seed records were not read by the schema parser.",
        "",
        "## Assumptions",
        "- Scope is limited to `taskdesk-legacy/**` plus `db/**`; package directories are treated as modules; Struts paths use the `.do` suffix from the parsed `web.xml` url-pattern.",
        "- A tracked symlink under `taskdesk-legacy/runtime-data/` is recorded as an inventory uncertainty rather than followed.",
        "",
        "## Confidence and evidence notes",
        "- Route/action/view claims are high confidence because the struts-config-v1 parser extracts action paths, action classes, forms, and forwards with element spans.",
        "- Table claims are high confidence because they are grounded in Java SQL literals, SQL DDL, and SQLite schema introspection.",
        "",
        "## Limitations",
        "- JSP extraction is lexical and does not parse scriptlet Java.",
        "- Java parsing is structural and does not do expression-level symbol resolution.",
        "- SQLite parser reads schema only, not row data.",
        "",
        "## Verification",
        *(verification_lines or []),
    ]
    (REPORTS / "application-structure.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_state() -> dict:
    state_path = WORK / "state.json"
    if state_path.exists():
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
            if prev.get("loop_id") == "semantic-source-discovery" and prev.get("status") == "iterating":
                prev["iteration"] = int(prev.get("iteration", 0)) + 1
                prev["status"] = "running"
                return prev
        except (json.JSONDecodeError, ValueError):
            pass
    return {
        "loop_id": "semantic-source-discovery",
        "iteration": 1,
        "max_iterations": 6,
        "status": "running",
        "repo_fingerprint": HEAD,
        "scope": "read-only semantic source discovery limited to taskdesk-legacy plus db after user permission",
        "cache_dir": ".cache/scripts",
        "work_dir": ".work/semantic-loop",
        "last_completed_phase": None,
        "weakest_score": None,
        "next_action": None,
        "history": [],
    }


def main() -> int:
    tracked = subprocess.run(["git", "ls-files", *SCOPE_ROOTS], cwd=ROOT, text=True, capture_output=True, check=True).stdout.splitlines()
    tracked = sorted(t for t in tracked if t)
    files = [f for f in tracked if (ROOT / f).is_file()]
    skipped = [f for f in tracked if not (ROOT / f).is_file()]
    WORK.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    state = load_state()
    state["repo_fingerprint"] = HEAD
    iteration = state["iteration"]
    state["history"].append({"iteration": iteration, "summary": "Started scoped semantic discovery for taskdesk-legacy plus db.", "timestamp": datetime.now(timezone.utc).isoformat()})
    write_json(WORK / "state.json", state)

    inv = inventory(files, skipped)
    write_json(WORK / "inventory.json", inv)
    write_json(WORK / "assumptions.json", assumptions())
    write_json(WORK / "parser-registry.json", parser_registry())
    src = build_source(files)
    write_json(WORK / "source-graph.json", src)
    write_json(WORK / "semantic-types.json", semantic_types())
    sem = build_semantic(src)
    write_json(WORK / "semantic-graph.json", sem)

    # Report first (status pending), then the independent verifier, then the
    # report's status is aligned with the verdict and re-verified so the final
    # verification.json measures the final report.
    write_report(inv, src, sem, None)
    ver, _ = run_verifier(iteration)
    write_report(inv, src, sem, ver)
    ver, rc = run_verifier(iteration)

    state["status"] = "complete" if ver["passed"] else "iterating"
    state["last_completed_phase"] = "report"
    state["weakest_score"] = ver["weakest_score"]
    state["next_action"] = ver["required_next_action"]
    state["history"].append({"iteration": iteration, "summary": f"Verification passed={ver['passed']}; weakest={ver['weakest_score']}.", "timestamp": datetime.now(timezone.utc).isoformat()})
    write_json(WORK / "state.json", state)
    print(json.dumps({"passed": ver["passed"],
                      "scores": {k: v["value"] for k, v in ver["scores"].items()},
                      "self_test": ver["verifier"]["self_test"],
                      "nodes": len(src["nodes"]), "semantic_nodes": len(sem["nodes"])}, indent=2))
    return rc


if __name__ == "__main__":
    sys.exit(main())
