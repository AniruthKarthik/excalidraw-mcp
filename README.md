# Excalidraw MCP

A local, backend-only MCP server for creating and editing importable Excalidraw
version-2 documents. It uses stdio by default and does not run a frontend,
browser, hosted preview, or Wrangler.

## Setup

Requires Python 3.12 or newer and `uv`:

```bash
uv sync --locked
uv run --locked excalidraw-mcp
```

Configure an MCP client to launch `uv run --locked excalidraw-mcp` from this repository.
Set `EXCALIDRAW_SCENE_DIR` to an absolute directory to change persistent storage.
The default is the platform user-data directory (`$XDG_DATA_HOME/excalidraw-mcp/scenes`
or `~/.local/share/excalidraw-mcp/scenes` on Linux, and
`~/Library/Application Support/excalidraw-mcp/scenes` on macOS). Set
`EXCALIDRAW_HISTORY_LIMIT` to a number from 1 through 100 to change the in-memory
undo depth (default: 20).
Persisted scenes are limited to 25 MiB and documents to 10,000 elements by
default. Operators can tune those limits with `EXCALIDRAW_MAX_SCENE_BYTES` and
`EXCALIDRAW_MAX_ELEMENTS`; see [docs/operations.md](docs/operations.md).

## Workflow

Use individual shape tools for manual diagrams, or `draw_graph` for structured
nodes and edges. Inspect the result with `get_scene`, edit elements by returned
IDs, then use `export_scene` for an embedded document or `save` for a server-local
file. Import the resulting `.excalidraw` document into Excalidraw.

`preview` intentionally reports an unsupported-operation error. No scene data is
uploaded. Unsaved state and undo history are process-local and disappear when the
server exits.

See [docs/tools.md](docs/tools.md) for tool contracts and
[docs/graph-generation.md](docs/graph-generation.md) for layouts and examples.
Deployment boundaries, configuration, backups, and release checks are covered in
[docs/operations.md](docs/operations.md). Security reports follow
[SECURITY.md](SECURITY.md).

## Tests

```bash
uv run --locked python -B -m unittest discover -s tests -v
```

The suite covers storage safety, Excalidraw serialization, concurrency,
relationships, MCP schemas, editing, undo, and graph layout. Browser rendering
and pixel-level visual compatibility are outside the backend test scope.
