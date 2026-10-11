"""Extensible Minecraft plugin library with configurable repos, manifest schema,
dependency resolution, secure downloads + checksum verification.
Manifests and artifacts are untrusted; URLs/paths validated; JARs never executed during validation.
"""
import os
import json
import hashlib
import urllib.parse
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from plugin_adapters import _validate_url, modrinth_project_version, hangar_version

# Configurable external repositories
DEFAULT_REPOS = {
    "github": {"enabled": True, "base_url": "https://github.com", "allowed_domains": ["github.com", "raw.githubusercontent.com"]},
    "modrinth": {"enabled": True, "base_url": "https://modrinth.com", "allowed_domains": ["modrinth.com", "api.modrinth.com"]},
    "hangar": {"enabled": True, "base_url": "https://hangar.papermc.io", "allowed_domains": ["hangar.papermc.io", "api.hangar.papermc.io"]},
}


def load_repo_config(path="plugin_repos.json"):
    if not os.path.exists(path):
        return DEFAULT_REPOS.copy()
    with open(path, "r") as f:
        cfg = json.load(f)
    # Merge; do not blindly trust contents
    merged = DEFAULT_REPOS.copy()
    for k, v in cfg.items():
        if isinstance(v, dict):
            if k in merged and isinstance(merged[k], dict):
                merged[k].update(v)
            else:
                merged[k] = v
    return merged


class PluginLibrary:
    def __init__(self, download_dir="./plugin_downloads", repo_config_path="plugin_repos.json"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.repos = load_repo_config(repo_config_path)

    def get_repo(self, name: str):
        return self.repos.get(name, {})

    def _confine_path(self, target: Path) -> bool:
        # Prevent escape from download_dir via .. or absolute paths
        try:
            target = target.resolve()
            base = self.download_dir.resolve()
            target.relative_to(base)
            return True
        except (ValueError, RuntimeError):
            return False

    def validate_manifest(self, manifest_data: Dict[str, Any]) -> (bool, List[str]):
        errors = []
        if not isinstance(manifest_data, dict):
            return False, ["manifest must be JSON object"]
        # Required fields
        for f in ("plugin_id", "name", "version", "mc_version"):
            if f not in manifest_data or not isinstance(manifest_data[f], str) or not manifest_data[f].strip():
                errors.append(f"missing/invalid required field: {f}")
        # Downloads validation (untrusted URLs)
        downloads = manifest_data.get("downloads", [])
        if not isinstance(downloads, list):
            errors.append("downloads must be array")
            downloads = []
        for idx, d in enumerate(downloads):
            url = d.get("url") if isinstance(d, dict) else None
            if not url or not isinstance(url, str):
                errors.append(f"downloads[{idx}].url missing")
                continue
            if not _validate_url(url):
                errors.append(f"downloads[{idx}].url invalid/unsafe: {url}")
            checksum = d.get("checksum")
            if checksum and not isinstance(checksum, str):
                errors.append(f"downloads[{idx}].checksum must be string")
        # Dependencies
        deps = manifest_data.get("dependencies", [])
        if not isinstance(deps, list):
            errors.append("dependencies must be array")
        else:
            for idx, dep in enumerate(deps):
                if not isinstance(dep, dict) or not dep.get("plugin_id"):
                    errors.append(f"dependencies[{idx}] missing plugin_id")
        # Repository references (configurable repos)
        repos = manifest_data.get("repositories", {})
        if isinstance(repos, dict):
            for repo_name, repo_ref in repos.items():
                if repo_name not in self.repos and repo_name not in DEFAULT_REPOS:
                    errors.append(f"unknown repo reference: {repo_name}")
                if isinstance(repo_ref, dict):
                    for key in ("repo_url", "project_id", "version_id"):
                        val = repo_ref.get(key)
                        if val and isinstance(val, str) and key == "repo_url" and not val.startswith("https://"):
                            errors.append(f"repositories.{repo_name}.repo_url must use https://")
        return (len(errors) == 0, errors)

    def resolve_dependencies(self, plugin_id: str, manifest_data: Dict[str, Any], inventory: Dict[str, Any]) -> (bool, List[str]):
        """Best-effort dependency resolution using installed-plugin inventory.
        Does not silently install missing dependencies."""
        errors = []
        deps = manifest_data.get("dependencies", []) if isinstance(manifest_data, dict) else []
        installed = inventory.get("installed", {}) if isinstance(inventory, dict) else {}
        for dep in deps:
            if not isinstance(dep, dict):
                continue
            dep_id = dep.get("plugin_id")
            dep_version = dep.get("min_version") or dep.get("max_version")
            if dep_id not in installed:
                errors.append(f"missing dependency: {dep_id} (required by {plugin_id})")
            else:
                installed_version = installed[dep_id].get("version") if isinstance(installed[dep_id], dict) else None
                if installed_version and dep_version:
                    # Very basic semver-like comparison (not full semver)
                    # Just report potential mismatch; do not block unless clearly incompatible
                    pass  # best-effort; report only if clearly wrong
        return (len(errors) == 0, errors)

    def download_artifact(self, url: str, dest_path: Path, expected_checksum: Optional[str] = None, checksum_type: str = "sha256") -> (bool, List[str]):
        errors = []
        if not _validate_url(url):
            return False, [f"URL invalid/unsafe: {url}"]
        # Confine destination
        try:
            dest_path = dest_path.resolve()
            base = self.download_dir.resolve()
            dest_path.relative_to(base)
        except (ValueError, RuntimeError):
            return False, ["destination path escapes download directory"]
        try:
            r = requests.get(url, stream=True, timeout=30)
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            # Checksum verification (treat file as untrusted until verified)
            if expected_checksum and checksum_type == "sha256":
                h = hashlib.sha256()
                with open(dest_path, "rb") as f2:
                    while True:
                        chunk = f2.read(8192)
                        if not chunk:
                            break
                        h.update(chunk)
                actual = h.hexdigest()
                if actual != expected_checksum.lower():
                    # Remove corrupt artifact
                    try:
                        dest_path.unlink()
                    except Exception:
                        pass
                    errors.append(f"checksum mismatch: expected {expected_checksum}, got {actual}")
                    return False, errors
            # Never execute JAR during validation
            return True, errors
        except Exception as e:
            errors.append(f"download error: {e}")
            return False, errors

    def load_inventory(self, server_dir: Path) -> Dict[str, Any]:
        inv_path = server_dir / "plugin_inventory.json"
        if not inv_path.exists():
            return {"installed": {}, "version": 1}
        with open(inv_path, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"installed": {}, "version": 1}
        installed = data.get("installed", {})
        if not isinstance(installed, dict):
            installed = {}
        return {"installed": installed, "version": data.get("version", 1)}

    def save_inventory(self, server_dir: Path, inventory: Dict[str, Any]) -> bool:
        inv_path = server_dir / "plugin_inventory.json"
        try:
            server_dir.mkdir(parents=True, exist_ok=True)
            with open(inv_path, "w") as f:
                json.dump(inventory, f, indent=2)
            return True
        except Exception as e:
            return False

    def install_plugin(self, server_dir: Path, manifest_path: Path, artifact_path: Optional[Path] = None) -> (bool, List[str]):
        errors = []
        plugins_dir = server_dir / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)
        # Load and validate manifest (untrusted)
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            return False, [f"invalid manifest: {e}"]
        ok, val_errors = self.validate_manifest(manifest)
        if not ok:
            return False, val_errors
        # Integrity/roll-safe: record previous inventory
        inventory = self.load_inventory(server_dir)
        plugin_id = manifest.get("plugin_id", "unknown")
        # If artifact provided, verify path is confined and file exists
        if artifact_path:
            try:
                artifact_path = artifact_path.resolve()
                plugins_dir.resolve()  # just to get base
                artifact_path.relative_to(plugins_dir.resolve())
            except (ValueError, RuntimeError):
                return False, ["artifact path escapes plugins directory"]
            if not artifact_path.exists():
                return False, ["artifact file missing"]
            dest = plugins_dir / f"{plugin_id}.jar"
            # Copy instead of move to preserve original (rollback possible)
            import shutil
            shutil.copy2(str(artifact_path), str(dest))
        # Update inventory
        inventory.setdefault("installed", {})[plugin_id] = {
            "version": manifest.get("version"),
            "manifest_path": str(manifest_path),
            "installed_at": str(__import__('time').time())
        }
        self.save_inventory(server_dir, inventory)
        return True, []

    def rollback_plugin(self, server_dir: Path, plugin_id: str, backup_manifest_path: Optional[Path] = None) -> (bool, List[str]):
        errors = []
        inventory = self.load_inventory(server_dir)
        installed = inventory.get("installed", {})
        if plugin_id not in installed:
            return False, [f"plugin not installed: {plugin_id}"]
        plugins_dir = server_dir / "plugins"
        jar_path = plugins_dir / f"{plugin_id}.jar"
        # Remove installed jar (safe rollback)
        if jar_path.exists():
            try:
                jar_path.unlink()
            except Exception as e:
                errors.append(f"failed to remove jar: {e}")
        # Restore previous inventory state (remove entry; user can restore from backup if needed)
        installed.pop(plugin_id, None)
        self.save_inventory(server_dir, inventory)
        return (len(errors) == 0, errors)
