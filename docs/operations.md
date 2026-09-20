# Operations and production readiness

This server is designed for a local, trusted MCP client over stdio. Each process
owns one in-memory scene and one undo history. Start a separate process for each
independent client or workspace.

## Installation and launch

For a locked source checkout:

```bash
uv sync --locked
uv run --locked excalidraw-mcp
```

The package also exposes an `excalidraw-mcp` console command when installed from
a wheel. MCP configuration must use stdio and must not add shell output to stdout.

## Configuration

| Variable | Default | Allowed | Purpose |
| --- | ---: | ---: | --- |
| `EXCALIDRAW_SCENE_DIR` | platform user data | absolute path | Persistent scene directory |
| `EXCALIDRAW_HISTORY_LIMIT` | `20` | 1–100 | Process-local undo snapshots |
| `EXCALIDRAW_MAX_HISTORY_BYTES` | `104857600` | 1 KiB–500 MiB | Shared undo snapshot budget |
| `EXCALIDRAW_MAX_SCENE_BYTES` | `26214400` | 1 KiB–100 MiB | Maximum persisted scene size |
| `EXCALIDRAW_MAX_EXPORT_BYTES` | `26214400` | 1 KiB–100 MiB | Maximum MCP export/resource size |
| `EXCALIDRAW_MAX_ELEMENTS` | `10000` | 1–100,000 | Maximum active/imported elements |

Configuration is read by the operation that needs it. Invalid values produce an
actionable MCP error instead of silently falling back.

On Linux the default storage root is
`$XDG_DATA_HOME/excalidraw-mcp/scenes`, falling back to
`~/.local/share/excalidraw-mcp/scenes`. On macOS it is
`~/Library/Application Support/excalidraw-mcp/scenes`.

## Storage and recovery

Saves use a private temporary file, atomic publication, and file/directory
`fsync`. New storage directories are private (`0700`) and scene files use `0600`.
Existing files are not replaced unless `overwrite=true`. Scene names are
restricted, and symlinks and non-regular files are rejected. Keep the configured
directory on a local filesystem with normal POSIX descriptor and
atomic-link/rename semantics.

Undo is not a durable backup. History is trimmed by both snapshot count and total
serialized byte budget; a single snapshot larger than the byte budget is not
retained. Back up the scene directory using normal filesystem snapshots or
copies. A server restart starts with an empty active scene; call `load` to restore
a saved one.

## Deployment boundary

Do not expose this process as an unauthenticated network service. A future HTTP
transport would need authentication, authorization, request limits, per-user
scene isolation, lifecycle management, and audit logging. Those controls are not
part of the current stdio server.

## Release checks

Before a release, run:

```bash
uv lock --check
uv run --locked python -B -m unittest discover -s tests -v
uv run --locked python -B -m compileall -q -f main.py excalidraw_mcp tests
uv build
```

CI tests Python 3.12 through 3.14, exercises storage on macOS, builds the release
artifacts, installs the wheel, and verifies MCP tool registration outside the
source tree.
