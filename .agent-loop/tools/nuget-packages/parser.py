#!/usr/bin/env python3
"""nuget-packages — .NET package-dependency extractor for the semantic discovery loop.

The maven-pom analogue for .NET: extracts declared NuGet package dependencies
using a real XML parser (xml.sax) with a locator, so every dependency carries
the line span of its actual declaration. External entity/DTD resolution is
disabled. Dispatches on the file's root element:

  - <packages>  (packages.config, classic non-SDK-style projects)
      -> Dependency node per <package id version targetFramework>.
  - <Project>   (.csproj, SDK-style)
      -> BuildModule node (from <TargetFramework(s)>) plus a Dependency node
         per <PackageReference Include Version> and a ProjectReference edge
         per <ProjectReference Include>.

Usage:
  python3 parser.py <packages.config|*.csproj> [...]   # parse files, JSON to stdout
  python3 parser.py --smoke                             # self-test
"""

from __future__ import annotations

import io
import json
import sys
import xml.sax
from pathlib import Path

PARSER_ID = "nuget-packages-v1"


class RootSniffHandler(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.root: str | None = None

    def startElement(self, name, attrs):
        if self.root is None:
            self.root = name
        raise _StopAfterRoot()


class _StopAfterRoot(Exception):
    pass


def sniff_root(data: bytes) -> str | None:
    handler = RootSniffHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.setFeature(xml.sax.handler.feature_external_pes, False)
    try:
        parser.parse(io.BytesIO(data))
    except _StopAfterRoot:
        pass
    return handler.root


class PackagesConfigHandler(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.packages: list[dict] = []
        self._loc = None

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def startElement(self, name, attrs):
        if name == "package" and attrs.get("id"):
            ln = self._line()
            self.packages.append({
                "id": attrs.get("id"), "version": attrs.get("version"),
                "target_framework": attrs.get("targetFramework"),
                "start_line": ln, "end_line": ln,
            })


class CsprojHandler(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.target_frameworks: list[str] = []
        self.package_refs: list[dict] = []
        self.project_refs: list[dict] = []
        self._loc = None
        self._stack: list[str] = []
        self._text = ""

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def startElement(self, name, attrs):
        self._stack.append(name)
        self._text = ""
        if name == "PackageReference" and attrs.get("Include"):
            ln = self._line()
            self.package_refs.append({
                "id": attrs.get("Include"),
                "version": attrs.get("Version"),
                "start_line": ln, "end_line": ln,
            })
        elif name == "ProjectReference" and attrs.get("Include"):
            ln = self._line()
            self.project_refs.append({"path": attrs.get("Include"), "start_line": ln, "end_line": ln})

    def characters(self, content):
        self._text += content

    def endElement(self, name):
        if name in ("TargetFramework", "TargetFrameworkVersion") and self._text.strip():
            self.target_frameworks.append(self._text.strip())
        elif name == "TargetFrameworks" and self._text.strip():
            self.target_frameworks.extend(t.strip() for t in self._text.split(";") if t.strip())
        self._stack.pop()
        self._text = ""


def _module_name(path: str) -> str:
    stem = Path(path).stem
    return stem if stem else Path(path).parent.name or "unknown-module"


def parse_packages_config(path: str, data: bytes) -> dict:
    handler = PackagesConfigHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.setFeature(xml.sax.handler.feature_external_pes, False)
    parser.parse(io.BytesIO(data))

    total_lines = max(1, len(data.splitlines()))
    file_id = f"src:file:{path}"
    nodes = [{
        "id": file_id, "layer": "source", "type": "File",
        "name": Path(path).name, "path": path,
        "span": {"start_line": 1, "end_line": total_lines},
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"language": "XML", "role": "nuget-manifest", "format": "packages.config"},
    }]
    edges = []
    for pkg in handler.packages:
        did = f"src:dependency:{pkg['id']}"
        nodes.append({
            "id": did, "layer": "source", "type": "Dependency",
            "name": pkg["id"], "path": path,
            "span": {"start_line": pkg["start_line"], "end_line": pkg["end_line"]},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"package_id": pkg["id"], "version": pkg["version"],
                           "target_framework": pkg["target_framework"]},
        })
        edges.append({
            "id": f"edge:{path}:depends-on:{pkg['id']}",
            "source_id": file_id, "target_id": did,
            "type": "depends-on", "confidence": 1.0, "properties": {},
        })
    return {"nodes": nodes, "edges": edges}


def parse_csproj(path: str, data: bytes) -> dict:
    handler = CsprojHandler()
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.setFeature(xml.sax.handler.feature_external_ges, False)
    parser.setFeature(xml.sax.handler.feature_external_pes, False)
    parser.parse(io.BytesIO(data))

    total_lines = max(1, len(data.splitlines()))
    file_id = f"src:file:{path}"
    module_name = _module_name(path)
    module_id = f"src:build-module:{module_name}"
    nodes = [
        {
            "id": file_id, "layer": "source", "type": "File",
            "name": Path(path).name, "path": path,
            "span": {"start_line": 1, "end_line": total_lines},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"language": "XML", "role": "build"},
        },
        {
            "id": module_id, "layer": "source", "type": "BuildModule",
            "name": module_name, "path": path,
            "span": {"start_line": 1, "end_line": total_lines},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"target_frameworks": handler.target_frameworks},
        },
    ]
    edges = [{
        "id": f"edge:{path}:declares-module",
        "source_id": file_id, "target_id": module_id,
        "type": "declares", "confidence": 1.0, "properties": {},
    }]
    for pkg in handler.package_refs:
        did = f"src:dependency:{pkg['id']}"
        nodes.append({
            "id": did, "layer": "source", "type": "Dependency",
            "name": pkg["id"], "path": path,
            "span": {"start_line": pkg["start_line"], "end_line": pkg["end_line"]},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"package_id": pkg["id"], "version": pkg.get("version")},
        })
        edges.append({
            "id": f"edge:{path}:depends-on:{pkg['id']}",
            "source_id": module_id, "target_id": did,
            "type": "depends-on", "confidence": 1.0, "properties": {},
        })
    for ref in handler.project_refs:
        rid = f"src:project-reference:{path}:{ref['path']}"
        nodes.append({
            "id": rid, "layer": "source", "type": "ProjectReference",
            "name": ref["path"], "path": path,
            "span": {"start_line": ref["start_line"], "end_line": ref["end_line"]},
            "hash": None, "parser_id": PARSER_ID,
            "properties": {"target_path": ref["path"]},
        })
        edges.append({
            "id": f"edge:{path}:references-project:{ref['path']}",
            "source_id": module_id, "target_id": rid,
            "type": "references", "confidence": 1.0, "properties": {},
        })
    return {"nodes": nodes, "edges": edges}


def parse_file(path: str, data: bytes) -> dict:
    root = sniff_root(data)
    if root == "packages":
        return parse_packages_config(path, data)
    if root == "Project":
        return parse_csproj(path, data)
    return {"nodes": [], "edges": []}


SMOKE_PACKAGES_CONFIG = b"""<?xml version="1.0" encoding="utf-8"?>
<packages>
  <package id="Newtonsoft.Json" version="12.0.3" targetFramework="net461" />
  <package id="EntityFramework" version="6.4.4" targetFramework="net461" />
</packages>
"""

SMOKE_CSPROJ = b"""<?xml version="1.0" encoding="utf-8"?>
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <ProjectReference Include="..\\Domain.Models\\Domain.Models.csproj" />
  </ItemGroup>
</Project>
"""

SMOKE_LEGACY_CSPROJ = b"""<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" DefaultTargets="Build"
         xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <TargetFrameworkVersion>v4.6.2</TargetFrameworkVersion>
  </PropertyGroup>
</Project>
"""


def smoke() -> None:
    result = parse_file("packages.config", SMOKE_PACKAGES_CONFIG)
    by_id = {n["id"]: n for n in result["nodes"]}
    dep = by_id["src:dependency:Newtonsoft.Json"]
    assert dep["properties"]["version"] == "12.0.3"
    assert dep["properties"]["target_framework"] == "net461"
    sample_lines = SMOKE_PACKAGES_CONFIG.decode().splitlines()
    assert "Newtonsoft.Json" in sample_lines[dep["span"]["start_line"] - 1]
    assert len([n for n in result["nodes"] if n["type"] == "Dependency"]) == 2
    node_ids = {n["id"] for n in result["nodes"]}
    for e in result["edges"]:
        assert e["source_id"] in node_ids and e["target_id"] in node_ids

    result2 = parse_file("Curriculums.csproj", SMOKE_CSPROJ)
    by_id2 = {n["id"]: n for n in result2["nodes"]}
    module = by_id2["src:build-module:Curriculums"]
    assert module["properties"]["target_frameworks"] == ["net8.0"]
    dep2 = by_id2["src:dependency:Newtonsoft.Json"]
    assert dep2["properties"]["version"] == "13.0.3"
    proj_refs = [n for n in result2["nodes"] if n["type"] == "ProjectReference"]
    assert len(proj_refs) == 1 and proj_refs[0]["name"].endswith("Domain.Models.csproj")
    node_ids2 = {n["id"] for n in result2["nodes"]}
    for e in result2["edges"]:
        assert e["source_id"] in node_ids2 and e["target_id"] in node_ids2

    result3 = parse_file("Domain.Layer.csproj", SMOKE_LEGACY_CSPROJ)
    by_id3 = {n["id"]: n for n in result3["nodes"]}
    module3 = by_id3["src:build-module:Domain.Layer"]
    assert module3["properties"]["target_frameworks"] == ["v4.6.2"]
    assert not any(n["type"] == "Dependency" for n in result3["nodes"]), \
        "legacy csproj has no PackageReference entries and must yield zero Dependency nodes"

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
        result = parse_file(p.as_posix(), p.read_bytes())
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
