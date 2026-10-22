# MCP tools and resources

All domain failures are MCP tool errors. Numeric inputs and style values have
JSON Schema bounds/enums, structured dictionary results have output schemas, and
tools advertise read-only, destructive, idempotent, and open-world hints where
applicable. Those annotations describe intent; clients still decide how to show
or approve calls.

## Create and edit

- `add_rectangle`, `add_circle`, `add_diamond`: add a shape and optional label;
  supports `roundness` ("adaptive", "round", "sharp") and `frame_id`; returns the shape ID and `label_id`.
- `add_arrow`: add a coordinate-based arrow (supports `elbowed=True/False`) and optional bound label.
- `add_text`: add standalone text with optional `frame_id`.
- `add_frame`: create an Excalidraw frame container (`name`, `x`, `y`, `w`, `h`) and optionally parent
  initial elements inside it.
- `connect`: connect two existing shapes by ID (supports `elbowed=True/False`). The arrow starts and ends at
  approximate shape boundaries and follows later shape moves/resizes.
- `move`: move a container with its label and connector endpoints. Moving a frame automatically moves all
  contained children. Moving bound text independently is rejected. Moving an arrow directly detaches its endpoints.
- `resize`: resize rectangles, ellipses, diamonds, and frames, recenter labels, and reroute fully bound connectors.
- `update_element`: update an element's label, styling, `roundness`, `elbowed` connector mode, or `frame_id` parent.
  Passing an empty label removes a container label. Standalone text cannot be empty; delete it. Setting `frame_id=""`
  unparents an element.
- `delete`: delete an element and its owned label, cleaning reverse bindings. Deleting a frame unparents its children
  without deleting them.
- `batch_mutate`: execute multiple creation, movement, connection, styling, and resizing operations atomically in a single
  revision step. Supports dynamic `client_id` reference resolution across operations and rolls back 100% on any failure.
- `clear`: reset elements, app state, and embedded files.
- `undo`: restore the snapshot before the latest successful mutation. History is
  bounded by `EXCALIDRAW_HISTORY_LIMIT` and `EXCALIDRAW_MAX_HISTORY_BYTES`;
  failed operations and reads add no entry or consume existing history.

## Inspect and persist

- `find_elements(query=None, type=None, frame_id=None, element_id=None, connected_to=None, include_bound_labels=False, limit=50)`:
  flexible query tool filtering active elements by text search, element type, frame membership, ID, or graph connectivity.
- `get_scene(offset=0, limit=50)`: returns up to 200 active elements per page,
  total count, current revision, and `has_more`.
- `get_element(element_id)`: returns one active element and scene revision.
- `list_saved_scenes`: returns validated regular-file names in configured storage.
- `save(name, overwrite=false)`: atomically writes a complete server-local file.
- `load(name)`: validates and replaces the active scene. A concurrent edit makes
  the operation fail instead of being overwritten. Persisted byte and document
  element limits are enforced before the active scene changes.
- `export_scene`: embeds a complete `.excalidraw` snapshot in the result without
  writing to disk, subject to `EXCALIDRAW_MAX_EXPORT_BYTES`.
- `draw_architecture`: compatibility shorthand for comma/newline components such
  as `box: API, circle: Database`. It is a list DSL, not natural-language parsing.
- `draw_graph`: structured graph generation supporting layered/horizontal/vertical layouts, subgraph clusters (frames),
  elbowed edge routing, and adaptive corner roundness. Described in `graph-generation.md`.

Saved documents are also readable without changing the active scene through the
resource template `excalidraw://scenes/{name}.excalidraw`. The same name rules and
storage confinement as `load` apply.

Tools that remove or replace content (`delete`, `clear`, `load`,
`draw_architecture`, and `draw_graph`) are marked destructive. File operations
are marked open-world because they access configured server storage. Scene
inspection and export are read-only. `save(overwrite=true)` can replace a file
and is marked destructive.

The server is process-local. Creating multiple server instances through
`create_server()` gives each its own scene, but enabling a shared HTTP transport
would still require authentication and per-user lifecycle design.
