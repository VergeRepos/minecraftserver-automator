import requests

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"

def fetch_versions():
    try:
        resp = requests.get(MANIFEST_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        versions = []
        for v in data["versions"]:
            versions.append({
                "id": v["id"],
                "type": v["type"],
                "url": v["url"],
                "releaseTime": v["releaseTime"]
            })
        versions.sort(key=lambda x: x["releaseTime"], reverse=True)
        return versions
    except Exception as e:
        print(f"Error fetching versions: {e}")
        return []

def download_server_jar(version_id, dest_path):
    versions = fetch_versions()
    detail_url = None
    for v in versions:
        if v["id"] == version_id:
            detail_url = v["url"]
            break
    if not detail_url:
        raise ValueError(f"Version {version_id} not found")
    detail_resp = requests.get(detail_url, timeout=10)
    detail_resp.raise_for_status()
    detail = detail_resp.json()
    server_url = detail["downloads"]["server"]["url"]
    r = requests.get(server_url, stream=True)
    r.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest_path
