#!/usr/bin/env python3
"""maven-pom — Maven POM extractor for the semantic discovery loop.

Extracts the build module and its declared dependencies from pom.xml using a
real XML parser (xml.sax) with a locator, so every dependency carries the
line span of its actual <dependency> block. External entity/DTD resolution is
disabled.

Usage:
  python3 parser.py <pom.xml> [...]   # parse files, JSON to stdout
  python3 parser.py --smoke           # self-test on embedded sample
"""

from __future__ import annotations

import io
import json
import sys
import xml.sax
from pathlib import Path

PARSER_ID = "maven-pom-v1"

_COORD_TAGS = {"groupId", "artifactId", "version", "packaging", "scope"}


class PomHandler(xml.sax.ContentHandler):
    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.project: dict = {}
        self.dependencies: list[dict] = []
        self._loc = None
        self._stack: list[str] = []
        self._dep: dict | None = None
        self._text = ""

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def startElement(self, name, attrs):
        self._stack.append(name)
        self._text = ""
        # Only direct project dependencies, not dependencyManagement or plugins.
        if self._stack[-3:] == ["project", "dependencies", "dependency"]:
            self._dep = {"start_line": self._line(), "end_line": self._line()}

    def characters(self, content):
        self._text += content

    def endElement(self, name):
        text = self._text.strip()
        if self._dep is not None and name in _COORD_TAGS and self._stack[-2:] == ["dependency", name]:
            self._dep[name] = text
        elif name == "dependency" and self._dep is not None:
            self._dep["end_line"] = self._line()
            if self._dep.get("groupId") and self._dep.get("artifactId"):
                self.dependencies.append(self._dep)
            self._dep = None
        elif self._stack[-2:] == ["project", name] and name in ("groupId", "artifactId", "version", "packaging", "name"):
            self.project[name] = text
        self._stack.pop()
        self._text = ""


def parse_pom(path: str, data: bytes) -> dict:
    handler = PomHandler(path)
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.setFeature(xml.sax.handler.feature_external_pes, False)
    parser.parse(io.BytesIO(data))

    total_lines = max(1, len(data.splitlines()))
    artifact = handler.project.get("artifactId") or Path(path).parent.name or "unknown-module"
    file_node = {
        "id": f"src:file:{path}", "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"language": "XML", "role": "build"},
    }
    module_node = {
        "id": f"src:build-module:{artifact}", "layer": "source", "type": "BuildModule",
        "name": artifact, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"group_id": handler.project.get("groupId"),
                       "version": handler.project.get("version"),
                       "packaging": handler.project.get("packaging")},
    }
    nodes = [file_node, module_node]
    edges = [{
        "id": f"edge:{path}:declares-module",
        "source_id": file_node["id"], "target_id": module_node["id"],
        "type": "declares", "confidence": 1.0, "properties": {},
    }]
    for dep in handler.dependencies:
        did = f"src:dependency:{dep['groupId']}:{dep['artifactId']}"
        nodes.append({
            "id": did, "layer": "source", "type": "Dependency",
            "name": f"{dep['groupId']}:{dep['artifactId']}", "path": path,
            "span": {"start_line": dep["start_line"], "end_line": dep["end_line"]},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"group_id": dep["groupId"], "artifact_id": dep["artifactId"],
                           "version": dep.get("version"), "scope": dep.get("scope")},
        })
        edges.append({
            "id": f"edge:{path}:depends-on:{dep['groupId']}:{dep['artifactId']}",
            "source_id": module_node["id"], "target_id": did,
            "type": "depends-on", "confidence": 1.0, "properties": {},
        })
    return {"nodes": nodes, "edges": edges}


SMOKE_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>demo-app</artifactId>
    <version>1.0.0</version>
    <packaging>war</packaging>
    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>com.example</groupId>
                <artifactId>managed-only</artifactId>
                <version>9.9</version>
            </dependency>
        </dependencies>
    </dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.xerial</groupId>
            <artifactId>sqlite-jdbc</artifactId>
            <version>3.45.3.0</version>
        </dependency>
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>servlet-api</artifactId>
            <version>2.5</version>
            <scope>provided</scope>
        </dependency>
    </dependencies>
</project>
"""


def smoke() -> None:
    result = parse_pom("pom.xml", SMOKE_SAMPLE)
    by_id = {n["id"]: n for n in result["nodes"]}

    module = by_id["src:build-module:demo-app"]
    assert module["properties"]["packaging"] == "war"
    assert module["properties"]["group_id"] == "com.example"
    assert "src:dependency:com.example:managed-only" not in by_id, \
        "dependencyManagement entry leaked into dependencies"
    dep = by_id["src:dependency:org.xerial:sqlite-jdbc"]
    assert dep["properties"]["version"] == "3.45.3.0"
    sample_lines = SMOKE_SAMPLE.decode().splitlines()
    assert "<dependency>" in sample_lines[dep["span"]["start_line"] - 1]
    assert "</dependency>" in sample_lines[dep["span"]["end_line"] - 1]
    assert by_id["src:dependency:javax.servlet:servlet-api"]["properties"]["scope"] == "provided"
    dep_edges = [e for e in result["edges"] if e["type"] == "depends-on"]
    assert len(dep_edges) == 2
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
        result = parse_pom(p.as_posix(), p.read_bytes())
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
