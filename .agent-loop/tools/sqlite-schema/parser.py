#!/usr/bin/env python3
"""sqlite-schema — SQLite database introspector for the semantic discovery loop.

A fully proper parser: it does not parse SQL text at all, it asks SQLite itself
(stdlib sqlite3, opened read-only via URI) for the schema — tables, columns,
indexes, views, and foreign keys. Deterministic output, sorted by name.

Usage:
  python3 parser.py <db.sqlite> [...]   # JSON to stdout
  python3 parser.py --smoke             # self-test on a temp database
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

PARSER_ID = "sqlite-schema-v1"


def parse_sqlite(path: str) -> dict:
    uri = f"file:{path}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    try:
        file_id = f"src:file:{path}"
        nodes = [{
            "id": file_id, "layer": "source", "type": "File",
            "name": Path(path).name, "path": path, "span": None,
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"format": "SQLite database"},
        }]
        edges = []

        def add_edge(src, dst, etype, props=None):
            edges.append({
                "id": f"edge:{path}:{len(edges) + 1}",
                "source_id": src, "target_id": dst, "type": etype,
                "confidence": 1.0, "properties": props or {},
            })

        rows = con.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()

        table_ids = {}
        for obj_type, name, tbl_name, sql in rows:
            if obj_type == "table":
                cols = con.execute(f'PRAGMA table_info("{name}")').fetchall()
                node_id = f"src:db:{path}:table:{name}"
                table_ids[name] = node_id
                nodes.append({
                    "id": node_id, "layer": "source", "type": "DatabaseTable",
                    "name": name, "path": path, "span": None,
                    "hash": None, "parser_id": PARSER_ID,
                    "properties": {
                        "columns": [
                            {"name": c[1], "type": c[2], "notnull": bool(c[3]),
                             "primary_key": bool(c[5])}
                            for c in cols
                        ],
                        "create_sql": (sql or "")[:1000],
                    },
                })
                add_edge(file_id, node_id, "contains")
        for obj_type, name, tbl_name, sql in rows:
            if obj_type == "table":
                continue
            node_id = f"src:db:{path}:{obj_type}:{name}"
            nodes.append({
                "id": node_id, "layer": "source",
                "type": {"index": "DatabaseIndex", "view": "DatabaseView",
                         "trigger": "DatabaseTrigger"}.get(obj_type, "DatabaseObject"),
                "name": name, "path": path, "span": None,
                "hash": None, "parser_id": PARSER_ID,
                "properties": {"on_table": tbl_name, "create_sql": (sql or "")[:1000]},
            })
            add_edge(file_id, node_id, "contains")
            if tbl_name in table_ids:
                add_edge(node_id, table_ids[tbl_name], "configures")

        for name, node_id in sorted(table_ids.items()):
            for fk in con.execute(f'PRAGMA foreign_key_list("{name}")').fetchall():
                target = fk[2]
                if target in table_ids:
                    add_edge(node_id, table_ids[target], "references",
                             {"via": "foreign key", "from_column": fk[3], "to_column": fk[4]})

        return {"nodes": nodes, "edges": edges}
    finally:
        con.close()


def smoke() -> None:
    import tempfile, os
    fd, tmp = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        con = sqlite3.connect(tmp)
        con.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT,
                                owner_id INTEGER REFERENCES users(id));
            CREATE INDEX idx_tasks_owner ON tasks (owner_id);
            CREATE VIEW open_tasks AS SELECT * FROM tasks;
        """)
        con.commit()
        con.close()

        result = parse_sqlite(tmp)
        by_type = {}
        for n in result["nodes"]:
            by_type.setdefault(n["type"], []).append(n)
        tables = {n["name"]: n for n in by_type["DatabaseTable"]}
        assert set(tables) == {"users", "tasks"}
        cols = {c["name"]: c for c in tables["users"]["properties"]["columns"]}
        assert cols["id"]["primary_key"] and cols["name"]["notnull"]
        assert by_type["DatabaseIndex"][0]["properties"]["on_table"] == "tasks"
        assert by_type["DatabaseView"][0]["name"] == "open_tasks"
        fk = [e for e in result["edges"] if e["type"] == "references"]
        assert len(fk) == 1 and fk[0]["properties"]["from_column"] == "owner_id"
        node_ids = {n["id"] for n in result["nodes"]}
        for e in result["edges"]:
            assert e["source_id"] in node_ids and e["target_id"] in node_ids
        print("SMOKE PASS")
    finally:
        os.unlink(tmp)


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "--smoke":
        smoke()
        return 0
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    all_nodes, all_edges = [], []
    for arg in argv[1:]:
        result = parse_sqlite(Path(arg).as_posix())
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
