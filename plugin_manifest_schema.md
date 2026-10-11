# Plugin Manifest Schema (v1.0)

This document defines the manifest schema used by the extensible plugin library. All manifests and downloaded artifacts are treated as untrusted data.

## Schema

```json
{
  "plugin_id": "string (required, unique identifier)",
  "name": "string (required, display name)",
  "version": "string (required, semver preferred)",
  "author": "string (optional)",
  "description": "string (optional)",
  "mc_version": "string (required, Minecraft version compatibility)",
  "loader": "string (optional, e.g. 'fabric', 'forge', 'paper', 'vanilla')",
  "repositories": {
    "modrinth": {
      "project_id": "string (optional)",
      "version_id": "string (optional)"
    },
    "hangar": {
      "project_id": "string (optional)",
      "version_id": "string (optional)"
    },
    "github": {
      "repo_url": "string (optional, HTTPS only, validated)"
    }
  },
  "downloads": [
    {
      "url": "string (required, HTTPS only, validated against allowlist/domain)",
      "checksum": "sha256 (optional but strongly recommended)",
      "checksum_type": "sha256"
    }
  ],
  "dependencies": [
    {
      "plugin_id": "string",
      "min_version": "string (optional)",
      "max_version": "string (optional)"
    }
  ],
  "manifest_version": "1.0"
}
```

## Validation rules
- `repositories.*.github.repo_url` must use `https://`; no `file://`, no `localhost`, no IP-only URLs.
- `downloads[].url` must use `https://`. URLs are resolved with `urllib.parse.urlparse` and cross-checked against a configurable domain allowlist (default: `modrinth.com`, `hangar.papermc.io`, `github.com`, `raw.githubusercontent.com`).
- Paths derived from manifest fields are normalized with `os.path.abspath` and confined within the configured plugin download directory; `..` sequences that escape the base are rejected.
- Downloaded JAR artifacts are never executed (`subprocess`, `exec`) during validation. Only `hashlib.sha256` checksum verification and basic ZIP/JAR structural checks run.
- Dependency resolution is best-effort: it checks `plugin_inventory` for installed plugin IDs and versions, reports conflicts/failures, and does not silently install missing dependencies.
