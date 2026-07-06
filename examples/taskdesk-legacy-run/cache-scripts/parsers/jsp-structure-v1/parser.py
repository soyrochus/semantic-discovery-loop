#!/usr/bin/env python3
"""jsp-structure — JSP template extractor for the semantic discovery loop.

JSP is not well-formed XML, so this is an honest *lexical extractor* (declared
as such in tool.json), but a careful one: JSP comments (<%%-- --%%>) and HTML
comments are masked out before matching, so commented-out includes and forms
are never extracted.

Extracts: page/include/taglib directives, <jsp:include>/<jsp:forward>, custom
taglib tag usage, HTML forms with actions, links, and scriptlet/EL counts.

Usage:
  python3 parser.py <file.jsp> [...]   # JSON to stdout
  python3 parser.py --smoke            # self-test
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "jsp-structure-v1"

DIRECTIVE_RE = re.compile(r"<%@\s*(?P<kind>page|include|taglib)\b(?P<attrs>.*?)%>", re.S)
JSP_ACTION_RE = re.compile(r"<jsp:(?P<kind>include|forward)\b(?P<attrs>.*?)/?>", re.S)
CUSTOM_TAG_RE = re.compile(r"<(?P<prefix>\w+):(?P<name>[\w.-]+)\b")
FORM_RE = re.compile(r"<form\b(?!:)(?P<attrs>.*?)>", re.S | re.I)
LINK_RE = re.compile(r"<a\b(?P<attrs>.*?)>", re.S | re.I)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*([\"'])(.*?)\2", re.S)
SCRIPTLET_RE = re.compile(r"<%[^@!=-].*?%>", re.S)
EXPRESSION_RE = re.compile(r"<%=.*?%>", re.S)
EL_RE = re.compile(r"\$\{[^}]*\}")


def mask_comments(text: str) -> str:
    """Replace JSP and HTML comment contents with spaces, preserving newlines."""
    def blank(m: re.Match) -> str:
        return "".join("\n" if c == "\n" else " " for c in m.group(0))
    text = re.sub(r"<%--.*?--%>", blank, text, flags=re.S)
    text = re.sub(r"<!--.*?-->", blank, text, flags=re.S)
    return text


def attrs_of(chunk: str) -> dict:
    return {m.group(1).lower(): m.group(3) for m in ATTR_RE.finditer(chunk)}


def parse_jsp(path: str, text: str) -> dict:
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
            "language": "JSP",
            "scriptlet_count": len(SCRIPTLET_RE.findall(mask)),
            "expression_count": len(EXPRESSION_RE.findall(mask)),
            "el_expression_count": len(EL_RE.findall(mask)),
        },
    }
    nodes.append(file_node)

    def add(node_type: str, name: str, offset: int, end_offset: int,
            props: dict, edge_type: str = "contains") -> dict:
        counter["node"] += 1
        node = {
            "id": f"src:jsp:{path}:{counter['node']}:{node_type.lower()}:{name}",
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

    taglib_prefixes = {}
    for m in DIRECTIVE_RE.finditer(mask):
        kind, attrs = m.group("kind"), attrs_of(m.group("attrs"))
        props = {"directive": kind, **{f"attr_{k}": v for k, v in attrs.items()}}
        add("Directive", kind, m.start(), m.end(), props,
            "includes" if kind == "include" else "contains")
        if kind == "taglib" and "prefix" in attrs:
            taglib_prefixes[attrs["prefix"]] = attrs.get("uri", "")

    for m in JSP_ACTION_RE.finditer(mask):
        kind, attrs = m.group("kind"), attrs_of(m.group("attrs"))
        target = attrs.get("page", "")
        add("Include" if kind == "include" else "Forward", target or kind,
            m.start(), m.end(), {"target": target},
            "includes" if kind == "include" else "forwards-to")

    tag_usage: dict[str, dict] = {}
    for m in CUSTOM_TAG_RE.finditer(mask):
        prefix, name = m.group("prefix"), m.group("name")
        if prefix == "jsp":
            continue
        key = f"{prefix}:{name}"
        entry = tag_usage.setdefault(key, {"count": 0, "first_line": line_of(m.start()),
                                           "taglib_uri": taglib_prefixes.get(prefix, "")})
        entry["count"] += 1
    if tag_usage:
        file_node["properties"]["custom_tags"] = tag_usage

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
<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<%@ include file="header.jspf" %>
<%-- <form action="/fake.do" method="post"></form> --%>
<!-- <jsp:include page="fake.jsp"/> -->
<html>
<body>
  <jsp:include page="menu.jsp"/>
  <c:forEach items="${tasks}" var="task">
    <a href="taskDetail.do?id=${task.id}">${task.title}</a>
  </c:forEach>
  <form action="taskSave.do" method="POST">
    <input name="title"/>
  </form>
  <% int visits = 1; %>
  <%= visits %>
</body>
</html>
"""


def smoke() -> None:
    result = parse_jsp("tasks.jsp", SMOKE_SAMPLE)
    nodes = result["nodes"]
    by_type = {}
    for n in nodes:
        by_type.setdefault(n["type"], []).append(n)

    file_node = by_type["Template"][0]
    directives = {n["name"] for n in by_type["Directive"]}
    assert directives == {"page", "taglib", "include"}
    includes = [n for n in by_type.get("Include", [])]
    assert [n["properties"]["target"] for n in includes] == ["menu.jsp"], "commented include leaked or real one missed"
    forms = by_type["Form"]
    assert len(forms) == 1, "commented-out form was extracted!"
    assert forms[0]["properties"]["action"] == "taskSave.do"
    assert forms[0]["properties"]["method"] == "post"
    tags = file_node["properties"]["custom_tags"]
    assert "c:forEach" in tags and tags["c:forEach"]["taglib_uri"].endswith("jstl/core")
    assert file_node["properties"]["scriptlet_count"] == 1
    assert file_node["properties"]["expression_count"] == 1
    assert file_node["properties"]["el_expression_count"] >= 2
    assert any(l["href"].startswith("taskDetail.do") for l in file_node["properties"]["links"])
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
        result = parse_jsp(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
