# Structured graph generation

`draw_graph(nodes, edges, layout="layered", direction="horizontal")` replaces the
current scene atomically. Caller IDs are stable logical identifiers; the result's
`node_map` and `edge_map` map them to generated Excalidraw element and label IDs.

Example arguments:

```json
{
  "nodes": [
    {"id": "client", "label": "Client", "shape": "rectangle"},
    {"id": "api", "label": "API", "shape": "diamond"},
    {"id": "db", "label": "Database", "shape": "ellipse"},
    {"id": "cache", "label": "Cache", "shape": "rectangle"}
  ],
  "edges": [
    {"id": "request", "source": "client", "target": "api", "label": "HTTP"},
    {"id": "persist", "source": "api", "target": "db"},
    {"id": "lookup", "source": "api", "target": "cache", "label": "read"}
  ],
  "layout": "layered",
  "direction": "horizontal"
}
```

`layered` assigns longest-path ranks and supports branches and isolated nodes. It
requires an acyclic graph. `horizontal` and `vertical` place nodes linearly in
input order and support cyclic edge sets. Layout is deterministic.

Spacing accumulates actual node dimensions, preventing the fixed-gap overlap of
the earlier implementation. Labels wrap at 24 characters, and dimensions account
for line count and shape padding. Arrow endpoints use rectangle/diamond bounding
boxes or the ellipse equation rather than shape centers. This is intentionally a
small deterministic layout engine: it does not minimize crossings or route around
unrelated nodes.

Limits are 200 nodes, 500 edges, 2,000 characters per label, and 200 characters
per logical ID. Node IDs and explicit edge IDs must be unique; endpoints must
exist; self-loops are rejected. Invalid input and layout failures preserve the
previous scene.
