#!/usr/bin/env python3
"""csharp-structure — structural C# parser for the semantic discovery loop.

Modeled directly on the java-structure gallery tool: a masking pass removes
comments and string/char literal contents (including C# verbatim `@"..."`
and interpolated `$"..."` strings) before any structural matching, and spans
come from brace matching, so `class Fake` inside a comment or string is
never picked up.

Extracts: namespace (block- or file-scoped), using directives (incl. static
and alias), type declarations (class/interface/struct/enum/record, incl.
nested, with unresolved base-list names and attributes), methods/
constructors with line spans and attributes, and simple auto-properties.

Emits a source-graph fragment (see .agent-loop/contracts/source-graph.schema.json):
  {"parser_id": ..., "nodes": [...], "edges": [...]}

Usage:
  python3 parser.py <File.cs> [...]   # parse files, JSON to stdout
  python3 parser.py --smoke           # self-test on embedded sample
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "csharp-structure-v1"

MODIFIERS = {
    "public", "protected", "private", "internal", "static", "final", "sealed",
    "abstract", "virtual", "override", "async", "extern", "partial", "new",
    "unsafe", "readonly",
}
CONSTRAINT_KEYWORDS = {"if", "while", "for", "foreach", "switch", "catch", "return",
                        "new", "throw", "else", "do", "try", "using", "lock", "fixed",
                        "in", "is", "as", "out", "ref", "when"}

TYPE_RE = re.compile(
    r"(?<![.\w$])(?P<kind>class|interface|struct|enum|record)\s+"
    r"(?:(?P<recordkind>class|struct)\s+)?(?P<name>[\w$]+)"
)
NAMESPACE_RE = re.compile(r"^[ \t]*namespace\s+([\w.]+)\s*(;|\{)", re.M)
USING_RE = re.compile(
    r"^[ \t]*using\s+(?!\()(static\s+)?(?:(\w+)\s*=\s*)?([\w.]+)\s*;", re.M
)
METHOD_RE = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:public|protected|private|internal|static|sealed|"
    r"abstract|virtual|override|async|extern|partial|new|unsafe)\s+)*)"
    r"(?P<ret>[\w$.]+(?:<[^={};]*>)?\??(?:\[\s*\])*\s+)?"
    r"(?P<name>[\w$]+)\s*(?:<[^(){};]*>)?\s*\(",
    re.M,
)
PROPERTY_RE = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:public|protected|private|internal|static|sealed|"
    r"abstract|virtual|override|new|readonly)\s+)*)"
    r"(?P<type>[\w$.]+(?:<[^={};]*>)?\??(?:\[\s*\])*)\s+"
    r"(?P<name>[\w$]+)\s*\{\s*(?P<accessors>[^{}]*)\}",
    re.M,
)
ATTR_LINE_RE = re.compile(r"^\s*\[(.*)\]\s*$")


def mask_code(text: str) -> str:
    """Replace comment and string/char literal contents with spaces.

    Handles C#-specific literal forms: verbatim strings (`@"..."`, closing
    quote escaped as `""`, no backslash escaping, embedded newlines allowed)
    and interpolated strings (`$"..."`, `$@"..."`/`@$"..."`) which follow the
    escaping rules of their non-interpolated counterpart. Triple-quoted raw
    string literals (C# 11+) are not handled — see known_limitations.

    Newlines are preserved so offsets and line numbers stay identical to the
    original text.
    """
    out = []
    i, n = 0, len(text)
    CODE, LINE, BLOCK, STR, VERBATIM, CHR = range(6)
    state = CODE
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == CODE:
            if c == "/" and nxt == "/":
                state, i = LINE, i + 2
                out.append("  ")
            elif c == "/" and nxt == "*":
                state, i = BLOCK, i + 2
                out.append("  ")
            elif c == '"':
                prev1 = text[i - 1] if i >= 1 else ""
                prev2 = text[i - 2] if i >= 2 else ""
                is_verbatim = prev1 == "@" or (prev1 == "$" and prev2 == "@")
                state, i = (VERBATIM if is_verbatim else STR), i + 1
                out.append('"')
            elif c == "'":
                state, i = CHR, i + 1
                out.append("'")
            else:
                out.append(c)
                i += 1
        elif state == LINE:
            out.append("\n" if c == "\n" else " ")
            if c == "\n":
                state = CODE
            i += 1
        elif state == BLOCK:
            if c == "*" and nxt == "/":
                state, i = CODE, i + 2
                out.append("  ")
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
        elif state == VERBATIM:
            if c == '"' and nxt == '"':
                out.append("  ")
                i += 2
            elif c == '"':
                state, i = CODE, i + 1
                out.append('"')
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
        elif state in (STR, CHR):
            quote = '"' if state == STR else "'"
            if c == "\\":
                out.append("  ")
                i += 2
            elif c == quote:
                state, i = CODE, i + 1
                out.append(quote)
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
    return "".join(out)


def line_starts(text: str) -> list[int]:
    starts = [0]
    for i, c in enumerate(text):
        if c == "\n":
            starts.append(i + 1)
    return starts


def line_of(starts: list[int], offset: int) -> int:
    return bisect_right(starts, offset)


def depth_array(mask: str) -> list[int]:
    """depth[i] = brace depth *before* character i."""
    depth = [0] * (len(mask) + 1)
    d = 0
    for i, c in enumerate(mask):
        depth[i] = d
        if c == "{":
            d += 1
        elif c == "}":
            d = max(0, d - 1)
    depth[len(mask)] = d
    return depth


def match_forward(mask: str, start: int, open_ch: str, close_ch: str) -> int:
    d = 0
    for i in range(start, len(mask)):
        if mask[i] == open_ch:
            d += 1
        elif mask[i] == close_ch:
            d -= 1
            if d == 0:
                return i
    return -1


def split_top_level_commas(s: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


def attributes_above(mask_lines: list[str], decl_line: int) -> list[str]:
    """Attribute type names on the lines directly above a declaration (1-based line)."""
    result: list[str] = []
    ln = decl_line - 1
    while ln >= 1:
        stripped = mask_lines[ln - 1].strip()
        m = ATTR_LINE_RE.match(stripped)
        if m:
            names = []
            for seg in split_top_level_commas(m.group(1)):
                name_m = re.match(r"\s*([\w.]+)", seg)
                if name_m:
                    names.append(name_m.group(1))
            result = names + result
            ln -= 1
        else:
            break
    return result


def parse_generic_suffix(mask: str, pos: int) -> int:
    if pos < len(mask) and mask[pos] == "<":
        end = match_forward(mask, pos, "<", ">")
        if end != -1:
            return end + 1
    return pos


def parse_base_list(rest: str) -> list[str]:
    rest = re.sub(r"\bwhere\b.*", "", rest, flags=re.S).strip()
    if rest.startswith(":"):
        return [t.strip() for t in rest[1:].split(",") if t.strip()]
    return []


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def parse_csharp(path: str, text: str) -> dict:
    mask = mask_code(text)
    starts = line_starts(mask)
    depth = depth_array(mask)
    mask_lines = mask.splitlines()
    total_lines = max(1, len(mask_lines))

    nodes: list[dict] = []
    edges: list[dict] = []
    edge_n = 0

    def add_edge(src: str, dst: str, etype: str, confidence: float = 1.0, props: dict | None = None):
        nonlocal edge_n
        edge_n += 1
        edges.append({
            "id": f"edge:{path}:{edge_n}",
            "source_id": src, "target_id": dst, "type": etype,
            "confidence": confidence, "properties": props or {},
        })

    file_id = f"src:file:{path}"
    nodes.append({
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID, "properties": {"language": "C#"},
    })

    ns = None
    m = NAMESPACE_RE.search(mask)
    if m:
        ns = m.group(1)
        ln = line_of(starts, m.start())
        ns_id = f"src:namespace:{ns}"
        nodes.append({
            "id": ns_id, "layer": "source", "type": "Namespace",
            "name": ns, "path": path,
            "span": {"start_line": ln, "end_line": ln},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"file_scoped": m.group(2) == ";"},
        })
        add_edge(ns_id, file_id, "contains")

    for m in USING_RE.finditer(mask):
        is_static, alias, target = bool(m.group(1)), m.group(2), m.group(3)
        ln = line_of(starts, m.start())
        using_id = f"src:using:{path}:{target}:{ln}"
        nodes.append({
            "id": using_id, "layer": "source", "type": "Import",
            "name": alias or target, "path": path,
            "span": {"start_line": ln, "end_line": ln},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"static": is_static, "target": target, "alias": alias},
        })
        add_edge(file_id, using_id, "imports")

    # --- type declarations ---
    types = []
    for m in TYPE_RE.finditer(mask):
        if m.group("name") in CONSTRAINT_KEYWORDS or m.group("name") in MODIFIERS:
            continue  # e.g. `foreach (Foo record in list)` — "record" as a variable name
        name_end = m.end()
        pos = parse_generic_suffix(mask, _skip_ws(mask, name_end))
        brace = mask.find("{", pos)
        semi = mask.find(";", pos)
        if brace == -1 or (semi != -1 and semi < brace):
            continue
        body_close = match_forward(mask, brace, "{", "}")
        if body_close == -1:
            body_close = len(mask) - 1
        base_list = parse_base_list(mask[pos:brace])
        types.append({
            "kind": m.group("kind"), "record_kind": m.group("recordkind"),
            "name": m.group("name"),
            "decl": m.start(), "body_open": brace, "body_close": body_close,
            "depth": depth[m.start()], "base_list": base_list,
        })

    for t in types:
        enclosing = None
        for other in types:
            if other is t:
                continue
            if other["body_open"] < t["decl"] < other["body_close"]:
                if enclosing is None or other["body_open"] > enclosing["body_open"]:
                    enclosing = other
        t["enclosing"] = enclosing
    for t in types:
        chain = [t["name"]]
        e = t["enclosing"]
        while e:
            chain.insert(0, e["name"])
            e = e["enclosing"]
        t["fqn"] = (ns + "." if ns else "") + ".".join(chain)
        t["id"] = f"src:{t['kind']}:{t['fqn']}"

    node_type_map = {"class": "Class", "interface": "Interface", "struct": "Struct",
                      "enum": "Enum", "record": "Record"}
    for t in types:
        decl_line = line_of(starts, t["decl"])
        end_line = line_of(starts, t["body_close"])
        node_type = node_type_map[t["kind"]]
        props: dict = {"qualified_name": t["fqn"]}
        if t["record_kind"]:
            props["record_kind"] = t["record_kind"]
        if t["base_list"]:
            props["base_list"] = t["base_list"]
        anns = attributes_above(mask_lines, decl_line)
        if anns:
            props["attributes"] = anns
        nodes.append({
            "id": t["id"], "layer": "source", "type": node_type,
            "name": t["name"], "path": path,
            "span": {"start_line": decl_line, "end_line": end_line},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        })
        parent_id = t["enclosing"]["id"] if t["enclosing"] else file_id
        add_edge(parent_id, t["id"], "declares" if t["enclosing"] else "contains")

    # --- methods / constructors ---
    for m in METHOD_RE.finditer(mask):
        o = m.start("name")
        owner = None
        for t in types:
            if t["body_open"] < o < t["body_close"]:
                if owner is None or t["body_open"] > owner["body_open"]:
                    owner = t
        if owner is None:
            continue
        if depth[o] != depth[owner["body_open"]] + 1:
            continue
        name = m.group("name")
        if name in CONSTRAINT_KEYWORDS or name in MODIFIERS:
            continue
        ret = (m.group("ret") or "").strip()
        if ret in CONSTRAINT_KEYWORDS:
            continue
        is_ctor = not ret and name == owner["name"]
        if not ret and not is_ctor:
            continue
        paren_open = mask.find("(", m.end("name"))
        paren_close = match_forward(mask, paren_open, "(", ")")
        if paren_close == -1:
            continue
        rest = mask[paren_close + 1:]
        term = re.search(r"(=>|[;{])", rest)
        if not term:
            continue
        decl_line = line_of(starts, m.start())
        if term.group(1) == "{":
            body_open = paren_close + 1 + term.start()
            body_close = match_forward(mask, body_open, "{", "}")
            end_line = line_of(starts, body_close if body_close != -1 else body_open)
            kind_suffix = "body"
        elif term.group(1) == "=>":
            semi = rest.find(";", term.end())
            end_line = line_of(starts, paren_close + 1 + (semi if semi != -1 else term.end()))
            kind_suffix = "expression"
        else:
            end_line = line_of(starts, paren_close + 1 + term.start())
            kind_suffix = "abstract"
        params = re.sub(r"\s+", " ", mask[paren_open + 1:paren_close]).strip()
        arity = 0 if not params else params.count(",") + 1
        method_id = f"src:method:{owner['fqn']}#{name}:{decl_line}"
        props = {
            "signature": f"{name}({params})",
            "modifiers": m.group("mods").split(),
            "arity": arity,
            "kind": "constructor" if is_ctor else "method",
            "body_form": kind_suffix,
        }
        if ret:
            props["return_type"] = ret
        anns = attributes_above(mask_lines, decl_line)
        if anns:
            props["attributes"] = anns
        nodes.append({
            "id": method_id, "layer": "source", "type": "Method",
            "name": name, "path": path,
            "span": {"start_line": decl_line, "end_line": end_line},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        })
        add_edge(owner["id"], method_id, "declares")

    # --- simple auto-properties ---
    for m in PROPERTY_RE.finditer(mask):
        o = m.start("name")
        owner = None
        for t in types:
            if t["body_open"] < o < t["body_close"]:
                if owner is None or t["body_open"] > owner["body_open"]:
                    owner = t
        if owner is None or depth[o] != depth[owner["body_open"]] + 1:
            continue
        name = m.group("name")
        if name in CONSTRAINT_KEYWORDS:
            continue
        accessors = re.sub(r"\s+", " ", m.group("accessors")).strip()
        if not re.fullmatch(r"(?:(?:public|private|protected|internal)?\s*(?:get|set|init)\s*;\s*)+", accessors + " " if accessors else "", re.I) and accessors:
            # not a plain auto-property accessor list (e.g. stray field-like braces) — skip defensively
            if not re.fullmatch(r"(get|set|init)\s*;?", accessors.split(";")[0].strip(), re.I):
                continue
        decl_line = line_of(starts, m.start())
        end_line = line_of(starts, m.end() - 1)
        prop_id = f"src:property:{owner['fqn']}#{name}:{decl_line}"
        props = {
            "type": m.group("type").strip(),
            "modifiers": m.group("mods").split(),
            "accessors": accessors,
        }
        anns = attributes_above(mask_lines, decl_line)
        if anns:
            props["attributes"] = anns
        nodes.append({
            "id": prop_id, "layer": "source", "type": "Property",
            "name": name, "path": path,
            "span": {"start_line": decl_line, "end_line": end_line},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        })
        add_edge(owner["id"], prop_id, "declares")

    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = '''\
using System;
using System.Collections.Generic;
using System.ServiceModel;
using static System.Console;
using Json = Newtonsoft.Json.JsonConvert;

// class FakeInComment { void nope() {} }
/* class AlsoFake { } */

namespace Curriculums.Services
{
    [ServiceContract]
    public interface IWSCurriculums
    {
        [OperationContract]
        List<string> obtenerProvincias();
    }

    [Authorize]
    [AuthorizationHelper(MessageError = "denegado, con \\"comillas\\"")]
    public class WSCurriculums : IWSCurriculums, IDisposable
    {
        private string q = @"verbatim ""quoted"" text with { fake brace }";

        public string Name { get; set; }
        public int Count { get; private set; }

        public WSCurriculums()
        {
            this.q = q + "run(";
        }

        public List<string> obtenerProvincias()
        {
            if (q.Length > 0)
            {
                Helper(1);
            }
            return new List<string>();
        }

        public int Square(int n) => n * n;

        private void Helper(int count) { }

        private void RemoveOld(List<string> oldRecords)
        {
            foreach (string record in oldRecords)
            {
                DeleteOne(record);
            }
        }

        public string FileExtension
        {
            get
            {
                return q.Split('.').Last();
            }
        }

        public void Dispose() { }
    }
}
'''


def smoke() -> None:
    result = parse_csharp("Sample.cs", SMOKE_SAMPLE)
    by_id = {n["id"]: n for n in result["nodes"]}
    names = {(n["type"], n["name"]) for n in result["nodes"]}

    assert ("Interface", "IWSCurriculums") in names
    assert ("Class", "WSCurriculums") in names
    assert ("Class", "FakeInComment") not in names, "parsed a comment!"
    assert ("Class", "AlsoFake") not in names, "parsed a block comment!"
    assert not any(t == "Record" for t, _ in names), \
        "foreach (Type record in ...) misparsed as a record-type declaration named 'in'"

    svc = by_id["src:class:Curriculums.Services.WSCurriculums"]
    assert set(svc["properties"]["base_list"]) == {"IWSCurriculums", "IDisposable"}
    assert svc["properties"]["attributes"] == ["Authorize", "AuthorizationHelper"]

    iface = by_id["src:interface:Curriculums.Services.IWSCurriculums"]
    assert iface["properties"]["attributes"] == ["ServiceContract"]

    methods = [n for n in result["nodes"] if n["type"] == "Method"]
    method_names = {n["name"] for n in methods}
    assert {"obtenerProvincias", "Square", "Helper", "Dispose", "WSCurriculums"} <= method_names
    ctor = [n for n in methods if n["properties"]["kind"] == "constructor"]
    assert len(ctor) == 1 and ctor[0]["name"] == "WSCurriculums"
    square = next(n for n in methods if n["name"] == "Square")
    assert square["properties"]["body_form"] == "expression"
    op_contract_method = next(n for n in methods if n["name"] == "obtenerProvincias" and n["path"] == "Sample.cs"
                               and n["properties"].get("attributes"))
    assert op_contract_method["properties"]["attributes"] == ["OperationContract"], \
        "interface method attribute not attached (or wrong method matched)"

    props = [n for n in result["nodes"] if n["type"] == "Property"]
    prop_names = {n["name"] for n in props}
    assert prop_names == {"Name", "Count"}, f"got {prop_names} (FileExtension has a body and must be excluded)"

    usings = {n["name"]: n["properties"] for n in result["nodes"] if n["type"] == "Import"}
    assert usings["System"]["target"] == "System"
    assert usings["System.Console"]["static"] is True
    assert usings["Json"]["alias"] == "Json" and usings["Json"]["target"] == "Newtonsoft.Json.JsonConvert"

    ns_nodes = [n for n in result["nodes"] if n["type"] == "Namespace"]
    assert ns_nodes[0]["name"] == "Curriculums.Services" and ns_nodes[0]["properties"]["file_scoped"] is False

    node_ids = {n["id"] for n in result["nodes"]}
    for e in result["edges"]:
        assert e["source_id"] in node_ids and e["target_id"] in node_ids, "dangling edge"

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
        result = parse_csharp(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
