---
name: repo-architecture-summary
description: Existing repo architecture summary and plugin upgrade plan
type: project
metadata:
  type: project
---

Repo: https://github.com/VergeRepos/minecraftserver-automator (local clone at C:\Users\nyohi\OneDrive\Documents\projects\minecraft-automator\minecraftserver-automator). Stack: Python 3.12, Flask, Jinja2, vanilla JS, JSON config, subprocess/java server management.

Planned file changes for extensible plugin library (manifests/artifacts treated as untrusted; URLs/paths validated; JARs never executed during validation):
- plugin_manifest_schema.md (documented manifest schema)
- plugin_library.py (library + adapters + resolution + checksum verification)
- plugin_adapters.py (Modrinth / Hangar adapters where practical)
- plugin_inventory.py (installed-plugin inventory per server)
- plugin_tests.py (tests; run and report honestly)
- plugin_docs.md / PLUGIN_SETUP.md (setup/run commands + limitations)
- app.py edits (integrate plugin endpoints into existing server creation workflow)
- templates/index.html edits (plugin UI integrated into existing page)
- config.json update (optional external repo config)

Constraints preserved: existing stack, existing functionality, secure/download-only behavior, no JAR execution for validation.
