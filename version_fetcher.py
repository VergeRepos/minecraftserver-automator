import requests
MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"
PAPER_API = "https://api.papermc.io/v2/projects/paper"
PURPUR_API = "https://api.purpurmc.org/v2"
def fetch_versions():
    try:
        resp = requests.get(MANIFEST_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        versions = []
        for v in data.get("versions", []):
            versions.append({"id": v["id"], "type": v.get("type","release"), "url": v.get("url"), "releaseTime": v.get("releaseTime")})
        versions.sort(key=lambda x: x.get("releaseTime") or "", reverse=True)
        return versions
    except Exception as e:
        print("Error fetching versions:", e)
        return []
def fetch_paper_builds(version_id):
    try:
        url = f"{PAPER_API}/versions/{version_id}/builds"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("builds", [])
    except Exception as e:
        print("Paper fetch error:", e)
        return []
def fetch_purpur_versions():
    try:
        url = f"{PURPUR_API}/versions"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("versions", [])
    except Exception as e:
        print("Purpur fetch error:", e)
        return []
def fetch_purpur_builds(version_id):
    try:
        url = f"{PURPUR_API}/{version_id}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json().get("builds", [])
    except Exception as e:
        print("Purpur builds fetch error:", e)
        return []
def download_server_jar(version_id, dest_path, server_type="vanilla"):
    if server_type.lower() == "paper":
        builds = fetch_paper_builds(version_id)
        if not builds:
            raise ValueError("No Paper builds for " + version_id)
        latest = builds[-1]
        url = f"{PAPER_API}/versions/{version_id}/builds/{latest.get('build')}/downloads/application"
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        return dest_path
    elif server_type.lower() == "purpur":
        builds = fetch_purpur_builds(version_id)
        if not builds:
            raise ValueError("No Purpur builds for " + version_id)
        latest = builds[-1]
        url = f"{PURPUR_API}/{version_id}/{latest}"
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk: f.write(chunk)
        return dest_path
    versions = fetch_versions()
    detail_url = None
    for v in versions:
        if v.get("id") == version_id:
            detail_url = v.get("url")
            break
    if not detail_url: raise ValueError("Version not found")
    detail_resp = requests.get(detail_url, timeout=10)
    detail_resp.raise_for_status()
    server_url = detail_resp.json().get("downloads",{}).get("server",{}).get("url")
    if not server_url: raise ValueError("No server URL")
    r = requests.get(server_url, stream=True, timeout=30)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk: f.write(chunk)
    return dest_path
def get_server_types():
    return [
        {"id": "vanilla", "name": "Vanilla", "description": "Official Minecraft server by Mojang"},
        {"id": "paper", "name": "Paper", "description": "High-performance Spigot fork with optimizations"},
        {"id": "purpur", "name": "Purpur", "description": "Fork of Paper with more features and options"}
    ]