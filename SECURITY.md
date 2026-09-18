# Security policy

## Supported versions

Security fixes are applied to the latest revision of the default branch. This
project has not yet declared a stable 1.x compatibility line.

## Reporting a vulnerability

Use GitHub's private security-advisory reporting for this repository. Do not put
unpatched vulnerability details, scene contents, filesystem paths, or other
sensitive data in a public issue.

Include the affected revision, operating system, reproduction steps, impact, and
whether the issue crosses the local trusted-client boundary. Maintainers should
acknowledge a report before requesting additional sensitive artifacts.

## Security boundary

The supported deployment is a local stdio process launched by a trusted MCP
client. Saved scenes may contain sensitive text and embedded image data. They are
stored unencrypted in `EXCALIDRAW_SCENE_DIR`; access control and backups are the
operator's responsibility.

Scene names are confined to the configured directory, symlinks are rejected,
writes are atomic, and configurable byte/element limits bound common resource
exhaustion paths. The server does not provide authentication or multi-user
isolation and must not be exposed directly as a public network service.
