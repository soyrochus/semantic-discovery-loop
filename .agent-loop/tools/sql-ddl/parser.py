#!/usr/bin/env python3
"""sql-ddl — SQL script extractor for the semantic discovery loop.

Comment- and string-aware: '--' and '/* */' comments and single-quoted string
contents are masked before splitting, so semicolons inside strings or comments
never break statements, and commented-out DDL is never extracted.

Each statement becomes a SqlStatement node with kind, target object and span;
CREATE TABLE additionally gets column names and foreign-key references.

Usage:
  python3 parser.py <file.sql> [...]   # JSON to stdout
  python3 parser.py --smoke            # self-test
"""

from __future__ import annotations

import json
import re
import sys
from bisect import bisect_right
from pathlib import Path

PARSER_ID = "sql-ddl-v1"

KIND_RE = re.compile(
    r"^\s*(?P<kind>CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX|VIEW|TRIGGER)|"
    r"ALTER\s+TABLE|DROP\s+(?:TABLE|INDEX|VIEW|TRIGGER)|"
    r"INSERT\s+INTO|UPDATE|DELETE\s+FROM|SELECT|PRAGMA|"
    r"BEGIN|COMMIT|ROLLBACK)\b",
    re.I | re.S,
)
NAME_RES = {
    "CREATE TABLE": re.compile(r"TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<n>[\w\".]+)", re.I),
    "CREATE INDEX": re.compile(r"INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<n>[\w\".]+)\s+ON\s+(?P<on>[\w\".]+)", re.I),
    "CREATE VIEW": re.compile(r"VIEW\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<n>[\w\".]+)", re.I),
    "CREATE TRIGGER": re.compile(r"TRIGGER\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<n>[\w\".]+)", re.I),
    "ALTER TABLE": re.compile(r"ALTER\s+TABLE\s+(?P<n>[\w\".]+)", re.I),
    "DROP TABLE": re.compile(r"TABLE\s+(?:IF\s+EXISTS\s+)?(?P<n>[\w\".]+)", re.I),
    "INSERT INTO": re.compile(r"INTO\s+(?P<n>[\w\".]+)", re.I),
    "UPDATE": re.compile(r"UPDATE\s+(?P<n>[\w\".]+)", re.I),
    "DELETE FROM": re.compile(r"FROM\s+(?P<n>[\w\".]+)", re.I),
}
CONSTRAINT_STARTERS = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
FK_RE = re.compile(r"REFERENCES\s+(?P<t>[\w\".]+)", re.I)


def mask_sql(text: str) -> str:
    """Blank out comments and single-quoted string contents, keep newlines."""
    out, i, n = [], 0, len(text)
    CODE, LINE, BLOCK, STR = range(4)
    state = CODE
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == CODE:
            if c == "-" and nxt == "-":
                state, i = LINE, i + 2
                out.append("  ")
            elif c == "/" and nxt == "*":
                state, i = BLOCK, i + 2
                out.append("  ")
            elif c == "'":
                state, i = STR, i + 1
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
        elif state == STR:
            if c == "'" and nxt == "'":
                out.append("  ")
                i += 2
            elif c == "'":
                state, i = CODE, i + 1
                out.append("'")
            else:
                out.append("\n" if c == "\n" else " ")
                i += 1
    return "".join(out)


def _unquote(name: str) -> str:
    return name.strip().strip('"')


def _columns_and_fks(mask_body: str) -> tuple[list[str], list[str]]:
    """Column names and referenced tables from a CREATE TABLE (...) body."""
    depth, parts, cur = 0, [], []
    for c in mask_body:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    columns, fks = [], []
    for part in parts:
        tokens = part.split()
        if not tokens:
            continue
        if tokens[0].upper() in CONSTRAINT_STARTERS:
            m = FK_RE.search(part)
            if m:
                fks.append(_unquote(m.group("t")))
        else:
            columns.append(_unquote(tokens[0]))
            m = FK_RE.search(part)  # inline REFERENCES
            if m:
                fks.append(_unquote(m.group("t")))
    return columns, fks


def parse_sql(path: str, text: str) -> dict:
    mask = mask_sql(text)
    starts = [0] + [i + 1 for i, c in enumerate(mask) if c == "\n"]
    line_of = lambda off: bisect_right(starts, off)
    total_lines = max(1, len(mask.splitlines()))

    file_id = f"src:file:{path}"
    nodes = [{
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID, "properties": {"language": "SQL"},
    }]
    edges = []

    # split on ';' in masked text (strings/comments already blanked)
    stmts, pos = [], 0
    while pos < len(mask):
        end = mask.find(";", pos)
        if end == -1:
            end = len(mask)
        chunk = mask[pos:end]
        if chunk.strip():
            stmts.append((pos + (len(chunk) - len(chunk.lstrip())), end, chunk.strip()))
        pos = end + 1

    table_nodes: dict[str, str] = {}
    for n_stmt, (off, end_off, stmt) in enumerate(stmts, 1):
        m = KIND_RE.match(stmt)
        kind = re.sub(r"\s+", " ", m.group("kind").upper()) if m else "UNKNOWN"
        kind = kind.replace("CREATE UNIQUE INDEX", "CREATE INDEX")
        props: dict = {"kind": kind}
        name = None
        name_re = NAME_RES.get(kind)
        if name_re:
            nm = name_re.search(stmt)
            if nm:
                name = _unquote(nm.group("n"))
                props["object"] = name
                if "on" in (name_re.groupindex or {}):
                    try:
                        props["on_table"] = _unquote(nm.group("on"))
                    except IndexError:
                        pass
        if kind == "CREATE TABLE" and name:
            body_open = stmt.find("(")
            if body_open != -1:
                depth, close = 0, -1
                for i in range(body_open, len(stmt)):
                    if stmt[i] == "(":
                        depth += 1
                    elif stmt[i] == ")":
                        depth -= 1
                        if depth == 0:
                            close = i
                            break
                if close != -1:
                    cols, fks = _columns_and_fks(stmt[body_open + 1:close])
                    props["columns"] = cols
                    if fks:
                        props["references_tables"] = sorted(set(fks))
        node_id = f"src:sql:{path}:stmt-{n_stmt}"
        nodes.append({
            "id": node_id, "layer": "source", "type": "SqlStatement",
            "name": f"{kind} {name}" if name else kind, "path": path,
            "span": {"start_line": line_of(off), "end_line": line_of(max(off, end_off - 1))},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        })
        edges.append({
            "id": f"edge:{path}:{len(edges) + 1}",
            "source_id": file_id, "target_id": node_id,
            "type": "contains", "confidence": 1.0, "properties": {},
        })
        if kind == "CREATE TABLE" and name:
            table_nodes[name] = node_id

    # FK edges between CREATE TABLE statements in the same script
    for node in nodes:
        for ref in node.get("properties", {}).get("references_tables", []):
            if ref in table_nodes and node["id"] != table_nodes[ref]:
                edges.append({
                    "id": f"edge:{path}:{len(edges) + 1}",
                    "source_id": node["id"], "target_id": table_nodes[ref],
                    "type": "references", "confidence": 1.0,
                    "properties": {"via": "foreign key"},
                })
    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = """\
-- schema for smoke test
-- CREATE TABLE commented_out (id INTEGER);
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    note TEXT DEFAULT 'semi;colon -- not a comment',
    CONSTRAINT uq_name UNIQUE (name)
);

CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    title TEXT,
    owner_id INTEGER REFERENCES users(id),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

CREATE INDEX idx_tasks_owner ON tasks (owner_id);
INSERT INTO users (id, name) VALUES (1, 'it''s a name; really');
"""


def smoke() -> None:
    result = parse_sql("schema.sql", SMOKE_SAMPLE)
    stmts = [n for n in result["nodes"] if n["type"] == "SqlStatement"]
    by_name = {n["name"]: n for n in stmts}

    assert len(stmts) == 4, f"expected 4 statements, got {[n['name'] for n in stmts]}"
    users = by_name["CREATE TABLE users"]
    assert users["properties"]["columns"] == ["id", "name", "note"], users["properties"]["columns"]
    tasks = by_name["CREATE TABLE tasks"]
    assert tasks["properties"]["references_tables"] == ["users"]
    idx = by_name["CREATE INDEX idx_tasks_owner"]
    assert idx["properties"]["on_table"] == "tasks"
    ins = by_name["INSERT INTO users"]
    assert ins["span"]["start_line"] == ins["span"]["end_line"] == 18
    fk_edges = [e for e in result["edges"] if e["type"] == "references"]
    assert len(fk_edges) == 1 and fk_edges[0]["source_id"] == tasks["id"]
    node_ids = {n["id"] for n in result["nodes"]}
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
        result = parse_sql(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
