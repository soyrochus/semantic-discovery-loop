#!/usr/bin/env python3
"""xml-structure — XML structure extractor for the semantic discovery loop.

Uses a real XML parser (xml.sax) — not regexes — so CDATA, comments, entities
and attribute quoting are handled correctly, with line numbers from the SAX
locator. External entity/DTD resolution is disabled.

Each element becomes a node with a stable path-style id
(src:xml:<file>:/root[1]/child[2]) and its attributes as properties.

Usage:
  python3 parser.py <file.xml> [...]   # parse files, JSON to stdout
  python3 parser.py --smoke            # self-test on embedded sample
"""

from __future__ import annotations

import io
import json
import sys
import xml.sax
from pathlib import Path

PARSER_ID = "xml-structure-v1"


class StructureHandler(xml.sax.ContentHandler):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._stack: list[dict] = []  # {"id","child_counts",...}
        self._edge_n = 0
        self._loc = None

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def startElement(self, name, attrs):
        if self._stack:
            parent = self._stack[-1]
            parent["child_counts"][name] = parent["child_counts"].get(name, 0) + 1
            idx = parent["child_counts"][name]
            xpath = f"{parent['xpath']}/{name}[{idx}]"
        else:
            xpath = f"/{name}[1]"
        node = {
            "id": f"src:xml:{self.path}:{xpath}",
            "layer": "source",
            "type": "XmlElement",
            "name": name,
            "path": self.path,
            "span": {"start_line": self._line(), "end_line": self._line()},
            "hash": None,
            "parser_id": PARSER_ID,
            "properties": {"xpath": xpath, "attributes": dict(attrs)},
        }
        self.nodes.append(node)
        if self._stack:
            self._edge_n += 1
            self.edges.append({
                "id": f"edge:{self.path}:{self._edge_n}",
                "source_id": self._stack[-1]["id"],
                "target_id": node["id"],
                "type": "contains",
                "confidence": 1.0,
                "properties": {},
            })
        self._stack.append({"id": node["id"], "xpath": xpath,
                            "child_counts": {}, "node": node})

    def endElement(self, name):
        entry = self._stack.pop()
        entry["node"]["span"]["end_line"] = self._line()

    def characters(self, content):
        if self._stack and content.strip():
            props = self._stack[-1]["node"]["properties"]
            text = (props.get("text", "") + content).strip()
            props["text"] = text[:500]


def parse_xml(path: str, data: bytes) -> dict:
    handler = StructureHandler(path)
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.setFeature(xml.sax.handler.feature_external_pes, False)
    parser.parse(io.BytesIO(data))

    total_lines = max(1, len(data.splitlines()))
    file_node = {
        "id": f"src:file:{path}", "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID, "properties": {"language": "XML"},
    }
    nodes = [file_node] + handler.nodes
    edges = handler.edges
    if handler.nodes:
        edges = [{
            "id": f"edge:{path}:root",
            "source_id": file_node["id"],
            "target_id": handler.nodes[0]["id"],
            "type": "contains",
            "confidence": 1.0,
            "properties": {},
        }] + edges
    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<web-app version="2.5">
  <!-- <servlet><servlet-name>fake</servlet-name></servlet> -->
  <servlet>
    <servlet-name>task</servlet-name>
    <servlet-class>com.example.TaskServlet</servlet-class>
  </servlet>
  <servlet>
    <servlet-name>login</servlet-name>
    <servlet-class><![CDATA[com.example.LoginServlet]]></servlet-class>
  </servlet>
  <servlet-mapping>
    <servlet-name>task</servlet-name>
    <url-pattern>/tasks/*</url-pattern>
  </servlet-mapping>
</web-app>
"""


def smoke() -> None:
    result = parse_xml("web.xml", SMOKE_SAMPLE)
    by_xpath = {n["properties"].get("xpath"): n for n in result["nodes"] if n["type"] == "XmlElement"}

    assert "/web-app[1]" in by_xpath
    assert "/web-app[1]/servlet[1]" in by_xpath
    assert "/web-app[1]/servlet[2]" in by_xpath, "sibling indexing failed"
    names = [n["name"] for n in result["nodes"] if n["type"] == "XmlElement"]
    assert names.count("servlet") == 2, "commented-out element was parsed!"
    cdata = by_xpath["/web-app[1]/servlet[2]/servlet-class[1]"]
    assert cdata["properties"]["text"] == "com.example.LoginServlet"
    root = by_xpath["/web-app[1]"]
    assert root["properties"]["attributes"] == {"version": "2.5"}
    assert root["span"]["end_line"] > root["span"]["start_line"]
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
        result = parse_xml(p.as_posix(), p.read_bytes())
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
