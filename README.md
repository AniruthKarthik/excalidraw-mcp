# Excalidraw MCP

A local, backend-only MCP server for creating and editing importable Excalidraw
version-2 documents. It uses stdio by default and does not run a frontend,
browser, hosted preview, or Wrangler.

## Setup

Requires Python 3.12 or newer and `uv`:

```bash
uv sync --locked
uv run --locked main.py
```

Configure an MCP client to launch `uv run --locked main.py` from this repository.
Set `EXCALIDRAW_SCENE_DIR` to an absolute directory to change persistent storage.
The default is `scenes/` beside `config.py`. Set `EXCALIDRAW_HISTORY_LIMIT` to a
number from 1 through 100 to change the in-memory undo depth (default: 20).

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

## Tests

```bash
uv run --locked python -B -m unittest discover -s tests -v
```

The suite covers storage safety, Excalidraw serialization, concurrency,
relationships, MCP schemas, editing, undo, and graph layout. Browser rendering
and pixel-level visual compatibility are outside the backend test scope.
