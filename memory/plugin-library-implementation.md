---
name: plugin-library-implementation
description: Plugin library feature implemented with manifest schema, adapters, secure downloads, tests, docs; limitations documented.
type: project
metadata:
  type: project
---

Implemented extensible plugin library:
- plugin_manifest_schema.md (documented schema; untrusted validation rules)
- plugin_library.py (library + adapters integration + dependency resolution + checksum verification)
- plugin_adapters.py (Modrinth / Hangar best-effort adapters with URL validation)
- plugin_inventory.py (installed-plugin inventory per server)
- plugin_tests.py (13/13 passed; no false claims; python -I isolation; JARs never executed)
- plugin_docs.md / PLUGIN_SETUP.md (setup/run commands + limitations)
- app.py modifications (new /plugin_inventory, /plugin_install, /plugin_rollback endpoints; integrates with existing server creation workflow via manifest_path parameter)
- config/repo support: plugin_repos.json load with DEFAULT_REPOS

Safety preserved: URLs/paths validated (urllib.parse + confine_path + allowlist domain checks); artifacts treated as untrusted; no subprocess execution of downloaded JARs during validation; rollback uses inventory backups; rollback updates inventory and deletes jar.

Limitations: dependency resolution best-effort (not full semver); adapter APIs subject to rate limits; manifest validation structural (not deep semantics); tests cover validation/download/inventory/dependency flows, not full network downloads (best-effort).
