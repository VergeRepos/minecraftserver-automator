# Plugin Setup and Run Commands

## Exact commands

```bash
# 1) Install dependencies (existing stack preserved)
pip install -r requirements.md  # flask, psutil, requests already present

# 2) Configure external repositories (optional)
# Create plugin_repos.json with configurable repos (default includes modrinth, hangar, github)
cp plugin_repos.json plugin_repos.json  # if present; else defaults apply

# 3) Run tests (always report honestly)
python -I plugin_tests.py

# 4) Start server (existing workflow preserved)
python app.py
```

## Limitations
- Dependency resolution is best-effort, not full semver resolution.
- Modrinth and Hangar adapters use public APIs; rate limits apply.
- Manifests and artifacts are validated but never executed as JARs; no runtime plugin sandbox beyond file/path validation.
- Rollback removes the installed JAR and updates inventory; restoring a previous version requires the original manifest/artifact.
- Existing server creation workflow is integrated via new `/api/servers/<name>/plugin_*` endpoints; UI updates are minimal and rely on the current index.html template.
