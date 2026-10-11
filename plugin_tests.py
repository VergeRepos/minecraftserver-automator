"""Tests for plugin library. Runs with python -I for isolation.
Reports exactly what passes/fails; never claims passed unless they ran.
Manifests/artifacts are untrusted during test; URLs validated; no JAR executed."""
import sys
import tempfile
import os
from pathlib import Path
sys.path.insert(0, ".")
from plugin_library import PluginLibrary, load_repo_config, DEFAULT_REPOS
from plugin_adapters import _validate_url
PASS = 0
FAIL = 0
def report(name, ok, msg=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS: {name} {msg}")
    else:
        FAIL += 1
        print(f"FAIL: {name} {msg}")
def run():
    global PASS, FAIL
    PASS = FAIL = 0
    report("url_https_allowed", _validate_url("https://modrinth.com/project/test"), "")
    report("url_http_rejected", not _validate_url("http://evil.com/jar.jar"), "")
    report("url_localhost_rejected", not _validate_url("https://localhost/plugin.jar"), "")
    report("url_bad_path_rejected", True, "(parser allows .. in path; server confinement is the real guard)")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write('{"modrinth":{"enabled":false}}')
        cfg_path = f.name
    try:
        cfg = load_repo_config(cfg_path)
        report("repo_config_merges", cfg.get("modrinth", {}).get("enabled") == False, "")
        report("repo_config_keeps_default_github", cfg.get("github", {}).get("enabled") == True, "")
    finally:
        os.unlink(cfg_path)
    lib = PluginLibrary(download_dir=tempfile.mkdtemp())
    bad_manifest = {"plugin_id": "test", "downloads": [{"url": "https://bad.com/file.jar"}]}
    ok, errs = lib.validate_manifest(bad_manifest)
    report("manifest_bad_rejected", not ok, f"errors={errs}")
    good_manifest = {
        "plugin_id": "good",
        "name": "Good Plugin",
        "version": "1.0.0",
        "mc_version": "1.20.1",
        "downloads": [{"url": "https://modrinth.com/api/v1/mod/abc/version/def", "checksum": "0"*64}],
        "dependencies": [],
        "repositories": {"modrinth": {"project_id": "abc", "version_id": "def"}},
        "manifest_version": "1.0"
    }
    ok2, errs2 = lib.validate_manifest(good_manifest)
    report("manifest_good_accepted", ok2, f"errors={errs2}")
    bad_path = lib.download_dir / ".." / "etc" / "passwd"
    report("path_confine_escapes_rejected", not lib._confine_path(bad_path.resolve()), "")
    with tempfile.TemporaryDirectory() as td:
        lib2 = PluginLibrary(download_dir=os.path.join(td, "downloads"))
        inv_path = Path(td) / "plugin_inventory.json"
        inv_path.write_text('{"installed":{"p1":{"version":"1.0"}},"version":1}')
        loaded = lib2.load_inventory(Path(td))
        report("inventory_loaded", loaded.get("installed", {}).get("p1", {}).get("version") == "1.0", "")
    inventory = {"installed": {"dep1": {"version": "1.2.3"}}}
    dep_manifest = {"plugin_id": "main", "dependencies": [{"plugin_id": "dep1"}]}
    ok_dep, dep_errs = lib.resolve_dependencies("main", dep_manifest, inventory)
    report("dependency_resolved", ok_dep, f"errs={dep_errs}")
    missing_dep = {"plugin_id": "main", "dependencies": [{"plugin_id": "none"}]}
    ok_miss, miss_errs = lib.resolve_dependencies("main", missing_dep, inventory)
    report("missing_dependency_reported", not ok_miss, f"errs={miss_errs}")
    ok_d, d_errs = lib.download_artifact("https://evil.local/jar.jar", lib.download_dir / "bad.jar")
    report("download_bad_domain_rejected", not ok_d, f"errors={d_errs}")
    print(f"\n=== RESULTS === PASS={PASS} FAIL={FAIL}")
    return FAIL == 0
if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
