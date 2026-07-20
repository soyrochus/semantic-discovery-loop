#!/usr/bin/env python3
"""aspnet-directive — ASP.NET directive-file extractor for the semantic discovery loop.

Targets the small family of ASP.NET Framework files that open with a
`<%@ ... %>` directive and are not well-formed XML: `.asax` (Application),
`.svc` (ServiceHost), `.asmx` (WebService), `.ashx` (WebHandler), and the
`.aspx`/`.ascx`/`.master` WebForms family (Page/Control/Master), should any
of those appear. These are the ASP.NET entry-point files that `xml-structure`
cannot parse correctly.

Extracts every `<%@ ... %>` directive with its attributes, and turns
CodeBehind/CodeFile and Inherits/Class/Service attribute values into
unresolved reference nodes (the semantic-graph builder is responsible for
resolving these against actual C# constructs, e.g. from csharp-structure
output). Also records any inline `<script runat="server">` blocks by
presence and span, without parsing their C# contents.

Usage:
  python3 parser.py <file.asax|.svc|.asmx|.ashx> [...]   # JSON to stdout
  python3 parser.py --smoke                              # self-test
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "aspnet-directive-v1"

DIRECTIVE_RE = re.compile(r"<%@\s*(?P<kind>\w+)\b(?P<attrs>.*?)%>", re.S)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.S)
SERVER_SCRIPT_RE = re.compile(r"<script\b(?P<attrs>[^>]*\brunat\s*=\s*[\"']server[\"'][^>]*)>(?P<body>.*?)</script>", re.S | re.I)

CODE_REF_ATTRS = {"codebehind", "codefile"}
TYPE_REF_ATTRS = {"inherits", "class", "service"}


def attrs_of(chunk: str) -> dict:
    return {m.group(1).lower(): m.group(3) for m in ATTR_RE.finditer(chunk)}


def parse_directive_file(path: str, text: str) -> dict:
    starts = [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]
    line_of = lambda off: bisect_right(starts, off)
    total_lines = max(1, len(text.splitlines()))

    nodes: list[dict] = []
    edges: list[dict] = []
    counter = {"edge": 0, "node": 0}

    file_id = f"src:file:{path}"
    file_node = {
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"language": "ASP.NET-directive"},
    }
    nodes.append(file_node)

    def add(node_type: str, name: str, offset: int, end_offset: int,
            props: dict, edge_source: str, edge_type: str = "contains") -> dict:
        counter["node"] += 1
        node = {
            "id": f"src:aspnet:{path}:{counter['node']}:{node_type.lower()}:{name}",
            "layer": "source", "type": node_type, "name": name, "path": path,
            "span": {"start_line": line_of(offset), "end_line": line_of(max(offset, end_offset - 1))},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        }
        nodes.append(node)
        counter["edge"] += 1
        edges.append({
            "id": f"edge:{path}:{counter['edge']}",
            "source_id": edge_source, "target_id": node["id"],
            "type": edge_type, "confidence": 1.0, "properties": {},
        })
        return node

    first_kind = None
    for m in DIRECTIVE_RE.finditer(text):
        kind, attrs = m.group("kind"), attrs_of(m.group("attrs"))
        if first_kind is None:
            first_kind = kind
            file_node["properties"]["entry_kind"] = kind
            if "language" in attrs:
                file_node["properties"]["code_language"] = attrs["language"]
        props = {"directive": kind, **{f"attr_{k}": v for k, v in attrs.items()}}
        directive = add("Directive", kind, m.start(), m.end(), props, file_id)

        for key in CODE_REF_ATTRS:
            if attrs.get(key):
                add("FileReference", attrs[key], m.start(), m.end(),
                    {"target_path": attrs[key], "via_attr": key}, directive["id"], "references")
        for key in TYPE_REF_ATTRS:
            if attrs.get(key):
                add("TypeReference", attrs[key], m.start(), m.end(),
                    {"qualified_name": attrs[key], "via_attr": key}, directive["id"], "references")

    for m in SERVER_SCRIPT_RE.finditer(text):
        attrs = attrs_of(m.group("attrs"))
        add("ServerScript", "(inline)", m.start(), m.end(),
            {"language": attrs.get("language"), "has_src": "src" in attrs}, file_id)

    return {"nodes": nodes, "edges": edges}


SMOKE_ASAX = (
    '<%@ Application Codebehind="Global.asax.cs" Inherits="Curriculums.MvcApplication" '
    'Language="C#" %>\n'
)

SMOKE_SVC = (
    '<%@ ServiceHost Language="C#" Debug="true" '
    'Service="Curriculums.Services.WSCurriculums" CodeBehind="WSCurriculums.svc.cs" %>\n'
)

SMOKE_ASHX = (
    '<%@ WebHandler Language="C#" Class="Curriculums.Handlers.Upload" %>\n'
    '<script language="C#" runat="server">\n'
    '  // inline handler code, intentionally not parsed\n'
    '</script>\n'
)


def smoke() -> None:
    result = parse_directive_file("Global.asax", SMOKE_ASAX)
    by_type = {}
    for n in result["nodes"]:
        by_type.setdefault(n["type"], []).append(n)
    assert by_type["File"][0]["properties"]["entry_kind"] == "Application"
    assert by_type["File"][0]["properties"]["code_language"] == "C#"
    file_refs = {n["name"] for n in by_type["FileReference"]}
    assert file_refs == {"Global.asax.cs"}
    type_refs = {n["name"] for n in by_type["TypeReference"]}
    assert type_refs == {"Curriculums.MvcApplication"}
    node_ids = {n["id"] for n in result["nodes"]}
    for e in result["edges"]:
        assert e["source_id"] in node_ids and e["target_id"] in node_ids

    svc_result = parse_directive_file("Services/WSCurriculums.svc", SMOKE_SVC)
    svc_by_type = {}
    for n in svc_result["nodes"]:
        svc_by_type.setdefault(n["type"], []).append(n)
    assert svc_by_type["File"][0]["properties"]["entry_kind"] == "ServiceHost"
    assert {n["name"] for n in svc_by_type["TypeReference"]} == {"Curriculums.Services.WSCurriculums"}
    assert {n["name"] for n in svc_by_type["FileReference"]} == {"WSCurriculums.svc.cs"}

    ashx_result = parse_directive_file("Handlers/Upload.ashx", SMOKE_ASHX)
    ashx_by_type = {}
    for n in ashx_result["nodes"]:
        ashx_by_type.setdefault(n["type"], []).append(n)
    assert ashx_by_type["File"][0]["properties"]["entry_kind"] == "WebHandler"
    assert {n["name"] for n in ashx_by_type["TypeReference"]} == {"Curriculums.Handlers.Upload"}
    assert len(ashx_by_type.get("ServerScript", [])) == 1
    assert ashx_by_type["ServerScript"][0]["properties"]["language"] == "C#"

    print("SMOKE PASS")


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--smoke":
        smoke()
        return 0
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    all_nodes, all_edges = [], []
    for arg in argv[1:]:
        p = Path(arg)
        result = parse_directive_file(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
