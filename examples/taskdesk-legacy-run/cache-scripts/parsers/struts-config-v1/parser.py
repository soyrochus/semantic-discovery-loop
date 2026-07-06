#!/usr/bin/env python3
"""struts-config — Struts 1.x configuration extractor for the semantic discovery loop.

Interprets Struts framework XML (struts-config.xml and commons-validator
validation.xml) into factual source constructs: Route nodes for action
mappings (with their forwards recorded as properties), ConfigurationEntry
nodes for form-beans, global-forwards, plug-ins, message-resources, and
validator fields. Uses a real XML parser (xml.sax) with a locator for line
spans; external entity/DTD resolution is disabled.

This tool records what the configuration *says* (paths, types, forwards).
Deriving URL suffixes (e.g. `.do` from web.xml) or application meaning is the
graph builders' job.

Usage:
  python3 parser.py <struts-config.xml|validation.xml> [...]   # JSON to stdout
  python3 parser.py --smoke                                    # self-test
"""

from __future__ import annotations

import io
import json
import sys
import xml.sax
from pathlib import Path

PARSER_ID = "struts-config-v1"


class StrutsHandler(xml.sax.ContentHandler):
    """Extracts Struts constructs from struts-config.xml."""

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._loc = None
        self._action: dict | None = None
        self._in_global_forwards = False
        self._plugin: dict | None = None
        self._edge_n = 0

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def _node(self, id_: str, type_: str, name: str, start: int, props: dict) -> dict:
        node = {
            "id": id_, "layer": "source", "type": type_, "name": name,
            "path": self.path,
            "span": {"start_line": start, "end_line": start},
            "hash": None, "parser_id": PARSER_ID, "properties": props,
        }
        self.nodes.append(node)
        return node

    def startElement(self, name, attrs):
        a = dict(attrs)
        line = self._line()
        if name == "action":
            route_path = a.get("path", "")
            self._action = self._node(
                f"src:route:{self.path}:{route_path}", "Route", route_path, line,
                {"framework": "Struts", "path": route_path,
                 "action_class": a.get("type"), "form_bean": a.get("name"),
                 "scope": a.get("scope"), "input": a.get("input"),
                 "forwards": []})
        elif name == "forward" and self._action is not None:
            self._action["properties"]["forwards"].append(
                {"name": a.get("name"), "path": a.get("path"),
                 "redirect": a.get("redirect"), "line": line})
        elif name == "global-forwards":
            self._in_global_forwards = True
        elif name == "forward" and self._in_global_forwards:
            fid = f"src:struts:global-forward:{self.path}:{a.get('name')}"
            self._node(fid, "ConfigurationEntry", a.get("name", ""), line,
                       {"kind": "global-forward", "forward_path": a.get("path")})
        elif name == "form-bean":
            self._node(f"src:struts:form-bean:{self.path}:{a.get('name')}",
                       "ConfigurationEntry", a.get("name", ""), line,
                       {"kind": "form-bean", "form_class": a.get("type")})
        elif name == "message-resources":
            self._node(f"src:struts:message-resources:{self.path}:{a.get('parameter')}",
                       "ConfigurationEntry", a.get("parameter", ""), line,
                       {"kind": "message-resources"})
        elif name == "plug-in":
            self._plugin = self._node(
                f"src:struts:plug-in:{self.path}:{a.get('className')}",
                "ConfigurationEntry", a.get("className", ""), line,
                {"kind": "plug-in", "class_name": a.get("className"), "set_properties": {}})
        elif name == "set-property" and self._plugin is not None:
            self._plugin["properties"]["set_properties"][a.get("property", "")] = a.get("value")

    def endElement(self, name):
        line = self._line()
        if name == "action" and self._action is not None:
            self._action["span"]["end_line"] = line
            self._action = None
        elif name == "global-forwards":
            self._in_global_forwards = False
        elif name == "plug-in" and self._plugin is not None:
            self._plugin["span"]["end_line"] = line
            self._plugin = None


class ValidationHandler(xml.sax.ContentHandler):
    """Extracts validator field constructs from commons-validator validation.xml."""

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self.nodes: list[dict] = []
        self._loc = None
        self._form: str | None = None
        self._field: dict | None = None

    def setDocumentLocator(self, locator):
        self._loc = locator

    def _line(self) -> int:
        return max(1, self._loc.getLineNumber()) if self._loc else 1

    def startElement(self, name, attrs):
        a = dict(attrs)
        if name == "form":
            self._form = a.get("name")
        elif name == "field" and self._form:
            prop = a.get("property", "")
            self._field = {
                "id": f"src:validation-field:{self._form}:{prop}",
                "layer": "source", "type": "ConfigurationEntry",
                "name": f"{self._form}.{prop}", "path": self.path,
                "span": {"start_line": self._line(), "end_line": self._line()},
                "hash": None, "parser_id": PARSER_ID,
                "properties": {"kind": "validator-field", "form": self._form,
                               "property": prop, "depends": a.get("depends")},
            }
            self.nodes.append(self._field)

    def endElement(self, name):
        if name == "field" and self._field is not None:
            self._field["span"]["end_line"] = self._line()
            self._field = None
        elif name == "form":
            self._form = None


def _root_element(data: bytes) -> str:
    for chunk in data.split(b"<"):
        text = chunk.strip()
        if not text or text.startswith((b"?", b"!", b"--")):
            continue
        return text.split()[0].rstrip(b">").decode("ascii", "replace")
    return ""


def parse_struts(path: str, data: bytes) -> dict:
    root = _root_element(data)
    if root == "form-validation":
        handler: xml.sax.ContentHandler = ValidationHandler(path)
    elif root == "struts-config":
        handler = StrutsHandler(path)
    else:
        raise ValueError(f"{path}: root element <{root}> is not Struts configuration")
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
        "hash": None, "parser_id": PARSER_ID,
        "properties": {"language": "XML", "framework": "Struts"},
    }
    nodes = [file_node] + handler.nodes
    edges = [{
        "id": f"edge:{path}:declares:{n['id']}",
        "source_id": file_node["id"], "target_id": n["id"],
        "type": "declares", "confidence": 1.0, "properties": {},
    } for n in handler.nodes]
    edges.extend(getattr(handler, "edges", []))
    return {"nodes": nodes, "edges": edges}


SMOKE_CONFIG = b"""<?xml version="1.0" encoding="UTF-8"?>
<struts-config>
    <form-beans>
        <form-bean name="loginForm" type="com.example.form.LoginForm"/>
    </form-beans>
    <global-forwards>
        <forward name="error" path="/jsp/error.jsp"/>
    </global-forwards>
    <action-mappings>
        <action path="/login"
                type="com.example.action.LoginAction"
                name="loginForm"
                input="/jsp/login.jsp">
            <forward name="success" path="/tasks.do" redirect="true"/>
        </action>
        <action path="/logout" type="com.example.action.LogoutAction"/>
    </action-mappings>
    <plug-in className="org.apache.struts.validator.ValidatorPlugIn">
        <set-property property="pathnames" value="/WEB-INF/validation.xml"/>
    </plug-in>
</struts-config>
"""

SMOKE_VALIDATION = b"""<?xml version="1.0" encoding="UTF-8"?>
<form-validation>
    <formset>
        <form name="loginForm">
            <field property="username" depends="required">
                <arg key="login.username"/>
            </field>
        </form>
    </formset>
</form-validation>
"""


def smoke() -> None:
    result = parse_struts("struts-config.xml", SMOKE_CONFIG)
    by_id = {n["id"]: n for n in result["nodes"]}

    login = by_id["src:route:struts-config.xml:/login"]
    assert login["type"] == "Route"
    assert login["properties"]["action_class"] == "com.example.action.LoginAction"
    assert login["properties"]["input"] == "/jsp/login.jsp"
    assert login["properties"]["forwards"] == [
        {"name": "success", "path": "/tasks.do", "redirect": "true",
         "line": login["properties"]["forwards"][0]["line"]}]
    assert login["span"]["end_line"] > login["span"]["start_line"], "action span not closed"
    assert "src:route:struts-config.xml:/logout" in by_id, "self-closing action missed"
    gf = by_id["src:struts:global-forward:struts-config.xml:error"]
    assert gf["properties"]["forward_path"] == "/jsp/error.jsp"
    assert by_id["src:struts:form-bean:struts-config.xml:loginForm"]["properties"]["form_class"] == "com.example.form.LoginForm"
    plugin = by_id["src:struts:plug-in:struts-config.xml:org.apache.struts.validator.ValidatorPlugIn"]
    assert plugin["properties"]["set_properties"] == {"pathnames": "/WEB-INF/validation.xml"}

    vresult = parse_struts("validation.xml", SMOKE_VALIDATION)
    vby_id = {n["id"]: n for n in vresult["nodes"]}
    field = vby_id["src:validation-field:loginForm:username"]
    assert field["properties"]["depends"] == "required"

    for res in (result, vresult):
        node_ids = {n["id"] for n in res["nodes"]}
        for e in res["edges"]:
            assert e["source_id"] in node_ids and e["target_id"] in node_ids

    try:
        parse_struts("web.xml", b"<web-app/>")
        raise AssertionError("non-Struts XML was accepted")
    except ValueError:
        pass
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
        result = parse_struts(p.as_posix(), p.read_bytes())
        all_nodes.extend(result["nodes"])
        all_edges.extend(result["edges"])
    json.dump({"parser_id": PARSER_ID, "nodes": all_nodes, "edges": all_edges},
              sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
