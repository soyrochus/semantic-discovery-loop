#!/usr/bin/env python3
"""properties-config — .properties extractor for the semantic discovery loop.

Follows java.util.Properties line rules: '#'/'!' comments, '='/':'/' '
separators, backslash line continuations, and key escapes — so multi-line
values and commented-out keys are handled correctly.

Each key becomes a ConfigurationEntry node with the full line span of its
(possibly continued) definition.

Usage:
  python3 parser.py <file.properties> [...]   # JSON to stdout
  python3 parser.py --smoke                   # self-test
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PARSER_ID = "properties-config-v1"


def _logical_lines(text: str):
    """Yield (start_line, end_line, content) with continuations joined."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        start = i
        raw = lines[i]
        stripped = raw.lstrip()
        if not stripped or stripped[0] in "#!":
            i += 1
            continue
        content = raw
        while _ends_with_odd_backslashes(content) and i + 1 < len(lines):
            content = content[:-1].rstrip("\r")
            i += 1
            content += lines[i].lstrip()
        yield (start + 1, i + 1, content.strip())
        i += 1


def _ends_with_odd_backslashes(s: str) -> bool:
    s = s.rstrip("\r")
    n = 0
    for c in reversed(s):
        if c == "\\":
            n += 1
        else:
            break
    return n % 2 == 1


def _split_key_value(content: str) -> tuple[str, str]:
    key_chars = []
    i = 0
    while i < len(content):
        c = content[i]
        if c == "\\" and i + 1 < len(content):
            key_chars.append(content[i:i + 2])
            i += 2
            continue
        if c in "=:" or c.isspace():
            break
        key_chars.append(c)
        i += 1
    rest = content[i:].lstrip()
    if rest[:1] in ("=", ":"):
        rest = rest[1:].lstrip()
    key = "".join(key_chars).replace("\\ ", " ").replace("\\=", "=").replace("\\:", ":")
    return key, rest


def parse_properties(path: str, text: str) -> dict:
    total_lines = max(1, len(text.splitlines()))
    file_id = f"src:file:{path}"
    nodes = [{
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"language": "Properties"},
    }]
    edges = []
    for n_edge, (start, end, content) in enumerate(_logical_lines(text), 1):
        key, value = _split_key_value(content)
        if not key:
            continue
        node_id = f"src:config:{path}:{key}"
        nodes.append({
            "id": node_id, "layer": "source", "type": "ConfigurationEntry",
            "name": key, "path": path,
            "span": {"start_line": start, "end_line": end},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"value": value[:500]},
        })
        edges.append({
            "id": f"edge:{path}:{n_edge}",
            "source_id": file_id, "target_id": node_id,
            "type": "contains", "confidence": 1.0, "properties": {},
        })
    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = """\
# database settings
db.url=jdbc:sqlite:taskdesk.sqlite
db.user: admin
# disabled.key=should-not-appear
! also a comment
mail.recipients=alice@example.com,\\
    bob@example.com,\\
    carol@example.com
key\\ with\\ spaces = spaced
trailing.slash=ends\\\\
plain value-without-separator
"""


def smoke() -> None:
    result = parse_properties("app.properties", SMOKE_SAMPLE)
    entries = {n["name"]: n for n in result["nodes"] if n["type"] == "ConfigurationEntry"}

    assert entries["db.url"]["properties"]["value"] == "jdbc:sqlite:taskdesk.sqlite"
    assert entries["db.user"]["properties"]["value"] == "admin"
    assert "disabled.key" not in entries, "commented-out key parsed!"
    mail = entries["mail.recipients"]
    assert mail["properties"]["value"] == "alice@example.com,bob@example.com,carol@example.com"
    assert mail["span"] == {"start_line": 6, "end_line": 8}, mail["span"]
    assert "key with spaces" in entries
    assert entries["trailing.slash"]["properties"]["value"] == "ends\\\\", "even backslashes are not a continuation"
    assert entries["plain"]["properties"]["value"] == "value-without-separator"
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
        result = parse_properties(p.as_posix(), p.read_text(encoding="utf-8", errors="replace"))
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
