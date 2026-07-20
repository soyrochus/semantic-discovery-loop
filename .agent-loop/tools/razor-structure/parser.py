#!/usr/bin/env python3
"""razor-structure — Razor view (.cshtml) extractor for the semantic discovery loop.

Razor is not well-formed HTML or XML (it interleaves C# with markup), so this
is an honest *lexical extractor* (declared as such in tool.json), but a
careful one: Razor comments (@* *@) and HTML comments are masked out before
matching, so commented-out includes/forms/links are never extracted.

Extracts: @model/@using/@inherits/Layout directives, partial-view and
child-action includes (Html.Partial/RenderPartial/Action/RenderAction),
route references (Html.ActionLink/Url.Action/Html.BeginForm),
@section declarations, @RenderSection/@RenderBody slots, plain HTML
forms/links, and code-block/expression counts.

Usage:
  python3 parser.py <file.cshtml> [...]   # JSON to stdout
  python3 parser.py --smoke               # self-test
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "razor-structure-v1"

MODEL_RE = re.compile(r"^[ \t]*@model\s+([^\r\n]+)", re.M)
USING_RE = re.compile(r"^[ \t]*@using\s+(?!\()([\w.]+)\s*;?", re.M)
INHERITS_RE = re.compile(r"^[ \t]*@inherits\s+([^\r\n]+)", re.M)
LAYOUT_RE = re.compile(r"\bLayout\s*=\s*(null|\"[^\"]*\")\s*;")
PARTIAL_RE = re.compile(r"Html\.(?:Partial|RenderPartial)(?:Async)?\s*\(\s*\"([^\"]+)\"")
ACTION_HELPER_RE = re.compile(
    r"Html\.(?:Action(?!Link)|RenderAction)(?:Async)?\s*\(\s*\"(?P<action>[^\"]+)\"\s*"
    r"(?:,\s*\"(?P<controller>[^\"]+)\")?"
)
ACTIONLINK_RE = re.compile(
    r"Html\.ActionLink\s*\(\s*\"(?P<text>[^\"]*)\"\s*,\s*\"(?P<action>[^\"]+)\"\s*"
    r"(?:,\s*\"(?P<controller>[^\"]+)\")?"
)
URLACTION_RE = re.compile(
    r"Url\.Action\s*\(\s*\"(?P<action>[^\"]+)\"\s*(?:,\s*\"(?P<controller>[^\"]+)\")?"
)
BEGINFORM_RE = re.compile(
    r"Html\.BeginForm\s*\(\s*\"(?P<action>[^\"]+)\"\s*(?:,\s*\"(?P<controller>[^\"]+)\")?"
)
SECTION_DEF_RE = re.compile(r"@section\s+(\w+)\b")
RENDER_SECTION_RE = re.compile(r"@?RenderSection\s*\(\s*\"([^\"]+)\"")
RENDERBODY_RE = re.compile(r"@RenderBody\s*\(")
CODEBLOCK_RE = re.compile(r"@\{")
EXPRESSION_RE = re.compile(r"@\(")
FORM_RE = re.compile(r"<form\b(?P<attrs>.*?)>", re.S | re.I)
LINK_RE = re.compile(r"<a\b(?P<attrs>.*?)>", re.S | re.I)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.S)


def mask_comments(text: str) -> str:
    """Replace Razor and HTML comment contents with spaces, preserving newlines."""
    def blank(m: re.Match) -> str:
        return "".join("\n" if c == "\n" else " " for c in m.group(0))
    text = re.sub(r"@\*.*?\*@", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    return text


def attrs_of(chunk: str) -> dict:
    return {m.group(1).lower(): m.group(3) for m in ATTR_RE.finditer(chunk)}


def parse_razor(path: str, text: str) -> dict:
    mask = mask_comments(text)
    starts = [0] + [i + 1 for i, c in enumerate(mask) if c == "\n"]
    line_of = lambda off: bisect_right(starts, off)
    total_lines = max(1, len(mask.splitlines()))

    nodes: list[dict] = []
    edges: list[dict] = []
    counter = {"edge": 0, "node": 0}

    file_id = f"src:template:{path}"
    file_node = {
        "id": file_id, "layer": "source", "type": "Template",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {
            "language": "Razor",
            "code_block_count": len(CODEBLOCK_RE.findall(mask)),
            "expression_count": len(EXPRESSION_RE.findall(mask)),
        },
    }
    nodes.append(file_node)

    def add(node_type: str, name: str, offset: int, end_offset: int,
            props: dict, edge_type: str = "contains") -> dict:
        counter["node"] += 1
        node = {
            "id": f"src:razor:{path}:{counter['node']}:{node_type.lower()}:{name}",
            "layer": "source", "type": node_type, "name": name, "path": path,
            "span": {"start_line": line_of(offset), "end_line": line_of(max(offset, end_offset - 1))},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        }
        nodes.append(node)
        counter["edge"] += 1
        edges.append({
            "id": f"edge:{path}:{counter['edge']}",
            "source_id": file_id, "target_id": node["id"],
            "type": edge_type, "confidence": 1.0, "properties": {},
        })
        return node

    for m in MODEL_RE.finditer(mask):
        value = m.group(1).strip()
        add("Directive", "model", m.start(), m.end(), {"directive": "model", "value": value})

    for m in USING_RE.finditer(mask):
        value = m.group(1).strip()
        add("Directive", "using", m.start(), m.end(), {"directive": "using", "value": value})

    for m in INHERITS_RE.finditer(mask):
        value = m.group(1).strip()
        add("Directive", "inherits", m.start(), m.end(), {"directive": "inherits", "value": value})

    for m in LAYOUT_RE.finditer(mask):
        raw = m.group(1)
        value = None if raw == "null" else raw.strip('"')
        add("Directive", "layout", m.start(), m.end(), {"directive": "layout", "value": value},
            "extends" if value else "contains")

    for m in PARTIAL_RE.finditer(mask):
        target = m.group(1)
        add("Include", target, m.start(), m.end(), {"kind": "partial", "target": target}, "includes")

    for m in ACTION_HELPER_RE.finditer(mask):
        action, controller = m.group("action"), m.group("controller")
        name = f"{controller}/{action}" if controller else action
        add("Include", name, m.start(), m.end(),
            {"kind": "child-action", "action": action, "controller": controller}, "includes")

    for m in ACTIONLINK_RE.finditer(mask):
        action, controller = m.group("action"), m.group("controller")
        name = f"{controller}/{action}" if controller else action
        add("RouteReference", name, m.start(), m.end(),
            {"source": "ActionLink", "action": action, "controller": controller,
             "link_text": m.group("text")}, "references")

    for m in URLACTION_RE.finditer(mask):
        action, controller = m.group("action"), m.group("controller")
        name = f"{controller}/{action}" if controller else action
        add("RouteReference", name, m.start(), m.end(),
            {"source": "Url.Action", "action": action, "controller": controller}, "references")

    for m in BEGINFORM_RE.finditer(mask):
        action, controller = m.group("action"), m.group("controller")
        name = f"{controller}/{action}" if controller else action
        add("RouteReference", name, m.start(), m.end(),
            {"source": "Html.BeginForm", "action": action, "controller": controller}, "references")

    for m in SECTION_DEF_RE.finditer(mask):
        add("Section", m.group(1), m.start(), m.end(), {"name": m.group(1)}, "declares")

    for m in RENDER_SECTION_RE.finditer(mask):
        add("SectionSlot", m.group(1), m.start(), m.end(), {"kind": "section-slot", "name": m.group(1)}, "includes")

    for m in RENDERBODY_RE.finditer(mask):
        add("SectionSlot", "(body)", m.start(), m.end(), {"kind": "body-slot"}, "includes")

    for m in FORM_RE.finditer(mask):
        attrs = attrs_of(m.group("attrs"))
        add("Form", attrs.get("action", "(no action)"), m.start(), m.end(),
            {"action": attrs.get("action", ""), "method": attrs.get("method", "get").lower()})

    hrefs = []
    for m in LINK_RE.finditer(mask):
        href = attrs_of(m.group("attrs")).get("href", "")
        if href and not href.startswith(("#", "javascript:")):
            hrefs.append({"href": href, "line": line_of(m.start())})
    if hrefs:
        file_node["properties"]["links"] = hrefs[:100]

    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = """\
@model Curriculums.Models.HomeViewModel
@using System.Linq
@{
    Layout = "~/Views/Shared/_Layout.cshtml";
}
@* <div>@Html.Partial("_fake") commented out</div> *@
<!-- <a href="/fake">fake</a> -->
<html>
<body>
    @Html.Partial("_summary")
    @Html.RenderAction("Widget", "Dashboard")
    @Html.ActionLink("Ver todos", "Index", "Curriculums")
    <a href="@(Url.Action("Details", "Curriculums"))">Detalle</a>
    @using (Html.BeginForm("Save", "Curriculums"))
    {
        <input name="title" />
    }
    <form action="/Curriculums/Legacy" method="post">
        <input name="x" />
    </form>
    @section AddToHead {
        <script src="extra.js"></script>
    }
    @if (IsSectionDefined("AddToHead"))
    {
        @RenderSection("AddToHead", required: false)
    }
    @RenderBody()
</body>
</html>
"""


def smoke() -> None:
    result = parse_razor("Views/Home/Index.cshtml", SMOKE_SAMPLE)
    nodes = result["nodes"]
    by_type: dict[str, list[dict]] = {}
    for n in nodes:
        by_type.setdefault(n["type"], []).append(n)

    file_node = by_type["Template"][0]
    directives = {n["name"]: n["properties"]["value"] for n in by_type["Directive"]}
    assert directives["model"] == "Curriculums.Models.HomeViewModel"
    assert directives["using"] == "System.Linq"
    assert directives["layout"] == "~/Views/Shared/_Layout.cshtml"

    includes = by_type["Include"]
    assert {n["name"] for n in includes} == {"_summary", "Dashboard/Widget"}, \
        "commented-out partial leaked or real includes missed"

    refs = {(n["properties"]["source"], n["name"]) for n in by_type["RouteReference"]}
    assert ("ActionLink", "Curriculums/Index") in refs
    assert ("Url.Action", "Curriculums/Details") in refs
    assert ("Html.BeginForm", "Curriculums/Save") in refs

    forms = by_type["Form"]
    assert len(forms) == 1, "commented-out / fake form handling wrong"
    assert forms[0]["properties"]["action"] == "/Curriculums/Legacy"

    sections = {n["name"] for n in by_type["Section"]}
    assert sections == {"AddToHead"}

    slots = {(n["properties"]["kind"], n["name"]) for n in by_type["SectionSlot"]}
    assert ("section-slot", "AddToHead") in slots
    assert ("body-slot", "(body)") in slots

    assert file_node["properties"]["code_block_count"] >= 1
    assert file_node["properties"]["expression_count"] >= 1
    assert not any(l["href"] == "/fake" for l in file_node["properties"].get("links", [])), \
        "commented-out link leaked"

    node_ids = {n["id"] for n in nodes}
    for e in result["edges"]:
        assert e["source_id"] in node_ids and e["target_id"] in node_ids
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
        result = parse_razor(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
