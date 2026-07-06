#!/usr/bin/env python3
"""java-structure — structural Java parser for the semantic discovery loop.

Tokenizer-based, not line-regex-based: comments and string/char literals are
masked out before any structural matching, and spans come from brace matching,
so `class Fake` inside a comment or string is never picked up.

Extracts: package, imports, type declarations (class/interface/enum, incl.
nested), methods/constructors with line spans and annotations.

Emits a source-graph fragment (see .agent-loop/contracts/source-graph.schema.json):
  {"parser_id": ..., "nodes": [...], "edges": [...]}

Usage:
  python3 parser.py <File.java> [...]   # parse files, JSON to stdout
  python3 parser.py --smoke             # self-test on embedded sample
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "java-structure-v1"

MODIFIERS = {
    "public", "protected", "private", "static", "final", "abstract",
    "synchronized", "native", "default", "strictfp", "transient", "volatile",
}
CONSTRAINT_KEYWORDS = {"if", "while", "for", "switch", "catch", "return", "new", "throw", "else", "do", "try"}

TYPE_RE = re.compile(r"(?<![.\w$])(?P<kind>class|interface|enum)\s+(?P<name>[\w$]+)")
PACKAGE_RE = re.compile(r"^[ \t]*package\s+([\w.]+)\s*;", re.M)
IMPORT_RE = re.compile(r"^[ \t]*import\s+(static\s+)?([\w.]+(?:\.\*)?)\s*;", re.M)
METHOD_RE = re.compile(
    r"^[ \t]*(?P<mods>(?:(?:public|protected|private|static|final|abstract|"
    r"synchronized|native|default|strictfp)\s+)*)"
    r"(?P<ret>[\w$.]+(?:<[^={};]*>)?(?:\[\s*\])*\s+)?"
    r"(?P<name>[\w$]+)\s*\(",
    re.M,
)


def mask_code(text: str) -> str:
    """Replace comment and string/char literal contents with spaces.

    Newlines are preserved so offsets and line numbers stay identical to the
    original text.
    """
    out = []
    i, n = 0, len(text)
    CODE, LINE, BLOCK, STR, CHR = range(5)
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
                state, i = STR, i + 1
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
    """Index of the char closing the open_ch at `start`, or -1."""
    d = 0
    for i in range(start, len(mask)):
        if mask[i] == open_ch:
            d += 1
        elif mask[i] == close_ch:
            d -= 1
            if d == 0:
                return i
    return -1


def annotations_above(mask_lines: list[str], decl_line: int) -> list[str]:
    """Annotation names on the lines directly above a declaration (1-based line)."""
    result = []
    ln = decl_line - 1
    while ln >= 1:
        stripped = mask_lines[ln - 1].strip()
        m = re.match(r"^@([\w$.]+)", stripped)
        if m:
            result.insert(0, m.group(1))
            ln -= 1
        else:
            break
    return result


def parse_generic_suffix(mask: str, pos: int) -> int:
    """If mask[pos] starts a <...> generic section, return index after it."""
    if pos < len(mask) and mask[pos] == "<":
        end = match_forward(mask, pos, "<", ">")
        if end != -1:
            return end + 1
    return pos


def split_extends_implements(rest: str) -> tuple[list[str], list[str]]:
    rest = re.sub(r"\s+", " ", rest).strip()
    extends, implements = [], []
    m_impl = re.search(r"\bimplements\b(.*)$", rest)
    if m_impl:
        implements = [t.strip() for t in m_impl.group(1).split(",") if t.strip()]
        rest = rest[: m_impl.start()]
    m_ext = re.search(r"\bextends\b(.*)$", rest)
    if m_ext:
        extends = [t.strip() for t in m_ext.group(1).split(",") if t.strip()]
    return extends, implements


def parse_java(path: str, text: str) -> dict:
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
            "source_id": src,
            "target_id": dst,
            "type": etype,
            "confidence": confidence,
            "properties": props or {},
        })

    file_id = f"src:file:{path}"
    nodes.append({
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID, "properties": {"language": "Java"},
    })

    pkg = None
    m = PACKAGE_RE.search(mask)
    if m:
        pkg = m.group(1)
        ln = line_of(starts, m.start())
        pkg_id = f"src:package:{pkg}"
        nodes.append({
            "id": pkg_id, "layer": "source", "type": "Package",
            "name": pkg, "path": path,
            "span": {"start_line": ln, "end_line": ln},
            "hash": None, "parser_id": PARSER_ID, "properties": {},
        })
        add_edge(pkg_id, file_id, "contains")

    for m in IMPORT_RE.finditer(mask):
        target = m.group(2)
        ln = line_of(starts, m.start())
        imp_id = f"src:import:{path}:{target}"
        nodes.append({
            "id": imp_id, "layer": "source", "type": "Import",
            "name": target, "path": path,
            "span": {"start_line": ln, "end_line": ln},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"static": bool(m.group(1))},
        })
        add_edge(file_id, imp_id, "imports")

    # --- type declarations ---
    types = []  # {"name","kind","fqn","id","decl","body_open","body_close","depth"}
    for m in TYPE_RE.finditer(mask):
        name_end = m.end()
        pos = parse_generic_suffix(mask, _skip_ws(mask, name_end))
        # find the body '{' — everything between name and '{' is extends/implements
        brace = mask.find("{", pos)
        semi = mask.find(";", pos)
        if brace == -1 or (semi != -1 and semi < brace):
            continue  # no body (shouldn't happen for real type decls)
        body_close = match_forward(mask, brace, "{", "}")
        if body_close == -1:
            body_close = len(mask) - 1
        extends, implements = split_extends_implements(mask[pos:brace])
        types.append({
            "kind": m.group("kind"), "name": m.group("name"),
            "decl": m.start(), "body_open": brace, "body_close": body_close,
            "depth": depth[m.start()],
            "extends": extends, "implements": implements,
        })

    # nesting: innermost enclosing registered type determines the FQN
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
        t["fqn"] = (pkg + "." if pkg else "") + ".".join(chain)
        t["id"] = f"src:{t['kind']}:{t['fqn']}"

    for t in types:
        decl_line = line_of(starts, t["decl"])
        end_line = line_of(starts, t["body_close"])
        node_type = {"class": "Class", "interface": "Interface", "enum": "Enum"}[t["kind"]]
        props: dict = {"qualified_name": t["fqn"]}
        if t["extends"]:
            props["extends"] = t["extends"]
        if t["implements"]:
            props["implements"] = t["implements"]
        anns = annotations_above(mask_lines, decl_line)
        if anns:
            props["annotations"] = anns
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
        # innermost registered type whose body contains this offset
        owner = None
        for t in types:
            if t["body_open"] < o < t["body_close"]:
                if owner is None or t["body_open"] > owner["body_open"]:
                    owner = t
        if owner is None:
            continue
        if depth[o] != depth[owner["body_open"]] + 1:
            continue  # not directly in the type body (statement, anonymous class, …)
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
        # after params: optional throws, then '{' (body) or ';' (abstract/interface)
        rest = mask[paren_close + 1:]
        m_after = re.match(r"\s*(throws\s+[\w$.,\s]+?)?\s*([;{])", rest)
        if not m_after:
            continue
        decl_line = line_of(starts, m.start())
        if m_after.group(2) == "{":
            body_open = paren_close + 1 + m_after.end() - 1
            body_close = match_forward(mask, body_open, "{", "}")
            end_line = line_of(starts, body_close if body_close != -1 else body_open)
        else:
            end_line = line_of(starts, paren_close + 1 + m_after.end() - 1)
        params = re.sub(r"\s+", " ", mask[paren_open + 1:paren_close]).strip()
        arity = 0 if not params else params.count(",") + 1
        method_id = f"src:method:{owner['fqn']}#{name}:{decl_line}"
        props = {
            "signature": f"{name}({params})",
            "modifiers": m.group("mods").split(),
            "arity": arity,
            "kind": "constructor" if is_ctor else "method",
        }
        if ret:
            props["return_type"] = ret
        anns = annotations_above(mask_lines, decl_line)
        if anns:
            props["annotations"] = anns
        nodes.append({
            "id": method_id, "layer": "source", "type": "Method",
            "name": name, "path": path,
            "span": {"start_line": decl_line, "end_line": end_line},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        })
        add_edge(owner["id"], method_id, "declares")

    return {"nodes": nodes, "edges": edges}


def _skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


SMOKE_SAMPLE = '''\
package com.example.demo;

import java.util.List;
import static java.util.Collections.emptyList;

// class FakeInComment { void nope() {} }
/* class AlsoFake { } */

public class TaskService extends BaseService implements Runnable, AutoCloseable {

    private String q = "class FakeInString { int x; }";

    public TaskService() {
        this.q = q + "run(";
    }

    @Override
    public void run() {
        if (q.length() > 0) {
            helper(1);
        }
    }

    public List<String> helper(int count) throws IllegalStateException {
        Runnable r = new Runnable() { public void run() { } };
        return emptyList();
    }

    public List<String> helper(int count, String label) {
        return emptyList();
    }

    static class Inner {
        void innerMethod() { }
    }
}

interface Notifier {
    void notifyUser(String msg);
}
'''


def smoke() -> None:
    result = parse_java("Sample.java", SMOKE_SAMPLE)
    by_id = {n["id"]: n for n in result["nodes"]}
    names = {(n["type"], n["name"]) for n in result["nodes"]}

    assert ("Class", "TaskService") in names
    assert ("Class", "Inner") in names
    assert ("Interface", "Notifier") in names
    assert ("Class", "FakeInComment") not in names, "parsed a comment!"
    assert ("Class", "AlsoFake") not in names, "parsed a block comment!"
    assert ("Class", "FakeInString") not in names, "parsed a string literal!"

    svc = by_id["src:class:com.example.demo.TaskService"]
    assert svc["properties"]["extends"] == ["BaseService"]
    assert svc["properties"]["implements"] == ["Runnable", "AutoCloseable"]

    inner = by_id["src:class:com.example.demo.TaskService.Inner"]
    assert inner["properties"]["qualified_name"].endswith("TaskService.Inner")

    methods = [n for n in result["nodes"] if n["type"] == "Method"]
    method_names = [n["name"] for n in methods]
    assert method_names.count("helper") == 2, f"overloads: {method_names}"
    assert "run" in method_names
    assert "innerMethod" in method_names
    assert "notifyUser" in method_names
    ctor = [n for n in methods if n["properties"]["kind"] == "constructor"]
    assert len(ctor) == 1 and ctor[0]["name"] == "TaskService"
    run = next(n for n in methods if n["name"] == "run" and "Override" in n["properties"].get("annotations", []))
    assert run["span"]["end_line"] > run["span"]["start_line"]
    # anonymous class run() must not be attributed to TaskService directly
    runs = [n for n in methods if n["name"] == "run"]
    assert len(runs) == 1, "anonymous class method leaked into type body"

    imports = [n for n in result["nodes"] if n["type"] == "Import"]
    assert {i["name"] for i in imports} == {"java.util.List", "java.util.Collections.emptyList"}

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
        result = parse_java(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
