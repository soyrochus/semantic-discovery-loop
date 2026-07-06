# Skill 04 — Source Graph Builder

## Purpose

Create `.work/semantic-loop/source-graph.json` (schema:
`contracts/source-graph.schema.json`) from the inventory and parser results: the
deterministic Layer 1 graph of source-level constructs.

## Rules

- **The source graph is factual.** Every node and edge must be derivable from a file in
  the repository by a registered parser or by direct deterministic inspection. If two
  runs over the same repository state would disagree, it does not belong here.
- **No speculative semantic meaning.** "Class `LoginAction` exists at this path with
  method `execute`" is a source fact. "This is the login feature" is semantic — it
  belongs in Layer 2, not here. Node types stay at the level of File, Directory,
  Package, Class, Method, Function, Annotation, Import, XmlElement, ConfigurationEntry,
  Route, Template, SqlStatement, BuildModule, Dependency, and similar.
- **Every node has a stable ID**: `src:<kind>:<qualified-name-or-path>`, e.g.
  `src:file:src/main/java/com/example/Foo.java`,
  `src:method:com.example.Foo.run`,
  `src:xml:WEB-INF/struts-config.xml:/action[@path='/login']`.
  IDs must be reproducible across runs on the same repository state — never random.
- **Every edge has a type and a confidence.** Deterministic containment/declaration
  edges get confidence 1.0; heuristic references (e.g. a string that looks like a route)
  get lower confidence and an explanatory `properties.reason`.
- **Preserve file path and span where possible.** Every node carries the
  repository-relative `path`; constructs inside files carry a line `span`. Record the
  producing `parser_id` so provenance chains back to the registry.
- **Honest attribution.** `parser_id` must name the registered parser that actually
  emitted the node — never another parser's id on output the builder assembled itself.
  Only plain structural nodes (File, Directory, DocumentationSection) may carry
  `parser_id: null`; anything that required interpreting file *content* (routes,
  dependencies, configuration entries, classes…) must come from a registered parser.
  If the builder needs a construct no parser emits, that is a missing parser — go back
  through skill 02/03, do not regex it inline. The verifier cross-checks every
  `parser_id` against the registry and its input patterns.
- Edge endpoints must reference node ids that exist in the graph (no dangling edges) —
  the verifier checks this.
- Do not include excluded files (generated/vendor/build output, the loop's own folders).
