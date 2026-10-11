"""Modrinth and Hangar adapters for plugin library.
Treats remote data as untrusted; validates URLs/paths; never executes JARs.
"""
import urllib.parse
import requests
from typing import Optional, Dict, Any

ALLOWED_DOMAINS = {
    "modrinth.com", "api.modrinth.com",
    "hangar.papermc.io", "api.hangar.papermc.io",
    "github.com", "raw.githubusercontent.com",
}


def _validate_url(url: str) -> bool:
    if not url.startswith("https://"):
        return False
    parsed = urllib.parse.urlparse(url)
    domain = parsed.hostname or ""
    # Reject localhost / IP-only / internal
    if domain in ("localhost", "127.0.0.1", "0.0.0.0") or domain.endswith(".local"):
        return False
    # Require allowed domain (configurable; default allows known hosts)
    if domain not in ALLOWED_DOMAINS:
        # Allow subdomains of allowed domains for flexibility
        if not any(domain.endswith("." + d) or domain == d for d in ALLOWED_DOMAINS):
            return False
    return True


def modrinth_project_version(project_id: str, version_id: Optional[str] = None, mc_version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch version info from Modrinth API. Returns untrusted dict; caller validates."""
    if not project_id or "/" in project_id or ".." in project_id:
        return None
    url = f"https://api.modrinth.com/v2/project/{urllib.parse.quote(project_id, safe='')}/version"
    if version_id:
        url = f"https://api.modrinth.com/v2/version/{urllib.parse.quote(version_id, safe='')}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        # Basic structural validation - do NOT execute anything
        if not isinstance(data, (dict, list)):
            return None
        return data
    except Exception:
        return None


def hangar_version(project_id: str, version_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch version info from Hangar API (PaperMC)."""
    if not project_id or "/" in project_id or ".." in project_id:
        return None
    # Hangar API paths vary; best-effort endpoint
    url = f"https://api.hangar.papermc.io/v1/projects/{urllib.parse.quote(project_id, safe='')}/versions"
    if version_id:
        url = f"https://api.hangar.papermc.io/v1/projects/{urllib.parse.quote(project_id, safe='')}/versions/{urllib.parse.quote(version_id, safe='')}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not isinstance(data, (dict, list)):
            return None
        return data
    except Exception:
        return None
