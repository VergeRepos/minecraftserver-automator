from flask import Flask, request, jsonify, render_template, send_file
import os
import json
import subprocess
import time
from pathlib import Path
from server_manager import ServerInstance, list_servers
from version_fetcher import fetch_versions, fetch_paper_builds, fetch_purpur_versions, fetch_purpur_builds, download_server_jar, get_server_types
import psutil
from plugin_library import PluginLibrary
from plugin_inventory import list_server_plugins

app = Flask(__name__)

with open("config.json", "r") as f:
    config = json.load(f)

SERVERS_DIR = config.get("servers_dir", "./servers")
DATA_DIR = config.get("data_dir", "./data")
os.makedirs(SERVERS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

server_cache = {}

def get_server(name):
    if name not in server_cache:
        server_cache[name] = ServerInstance(name, SERVERS_DIR)
    return server_cache[name]

def load_data(file_name, default=None):
    path = Path(DATA_DIR) / file_name
    if path.exists():
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}

def save_data(file_name, data):
    path = Path(DATA_DIR) / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/java')
def api_java_check():
    try:
        subprocess.run(["java", "-version"], capture_output=True, check=True)
        return jsonify({"installed": True})
    except:
        return jsonify({"installed": False}), 503

@app.route('/api/versions')
def api_versions():
    versions = fetch_versions()
    return jsonify(versions)

@app.route('/api/server_types')
def api_server_types():
    return jsonify(get_server_types())

@app.route('/api/servers')
def api_list_servers():
    names = list_servers(SERVERS_DIR)
    servers = []
    for name in names:
        s = get_server(name)
        info = s.get_info()
        servers.append(info)
    return jsonify(servers)

@app.route('/api/servers', methods=['POST'])
def api_create_server():
    data = request.json
    name = data.get('name')
    version = data.get('version')
    server_type = data.get('server_type', 'vanilla')
    jvm_args = data.get('jvm_args', '-Xmx1024M -Xms1024M')
    port = data.get('port', 25565)
    if not name or not version:
        return jsonify({"error": "name and version required"}), 400
    if not name.isalnum() and not all(c in '-_' for c in name.replace(name.replace('-', '').replace('_', ''), '')):
        return jsonify({"error": "Server name must be alphanumeric with dashes or underscores only"}), 400
    if name in list_servers(SERVERS_DIR):
        return jsonify({"error": "Server already exists"}), 409
    s = ServerInstance(name, SERVERS_DIR)
    try:
        s.create(version, server_type, jvm_args, port)
        server_cache[name] = s
        log_activity("server_create", {"name": name, "version": version, "type": server_type})
        return jsonify(s.get_info()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/clone', methods=['POST'])
def api_clone_server(name):
    data = request.json or {}
    new_name = data.get('new_name')
    if not new_name:
        return jsonify({"error": "new_name required"}), 400
    if not new_name.isalnum() and not all(c in '-_' for c in new_name.replace(new_name.replace('-', '').replace('_', ''), '')):
        return jsonify({"error": "Server name must be alphanumeric with dashes or underscores only"}), 400
    s = get_server(name)
    try:
        new_instance = s.clone(new_name, SERVERS_DIR)
        server_cache[new_name] = new_instance
        log_activity("server_clone", {"original": name, "clone": new_name})
        return jsonify(new_instance.get_info()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/start', methods=['POST'])
def api_start_server(name):
    s = get_server(name)
    try:
        ok = s.start()
        log_activity("server_start", {"name": name, "success": ok})
        return jsonify({"success": ok, "running": s.is_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/stop', methods=['POST'])
def api_stop_server(name):
    s = get_server(name)
    try:
        ok = s.stop()
        log_activity("server_stop", {"name": name, "success": ok})
        return jsonify({"success": ok, "running": s.is_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/restart', methods=['POST'])
def api_restart_server(name):
    s = get_server(name)
    try:
        ok = s.restart()
        log_activity("server_restart", {"name": name, "success": ok})
        return jsonify({"success": ok, "running": s.is_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/graceful_stop', methods=['POST'])
def api_graceful_stop(name):
    s = get_server(name)
    try:
        if s.is_running():
            s.send_command("save-all")
            time.sleep(2)
            s.send_command("stop")
            s.stop()
        log_activity("server_graceful_stop", {"name": name})
        return jsonify({"success": True, "running": s.is_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/logs')
def api_logs(name):
    s = get_server(name)
    lines = request.args.get('lines', 500, type=int)
    log = s.get_console_log(lines=lines)
    return jsonify({"log": log})

@app.route('/api/servers/<name>/properties', methods=['GET', 'PUT'])
def api_properties(name):
    s = get_server(name)
    if request.method == 'GET':
        props = s.get_properties()
        return jsonify(props)
    else:
        data = request.json
        ok = s.update_properties(data)
        log_activity("properties_update", {"name": name, "keys": list(data.keys())})
        return jsonify({"success": ok})

@app.route('/api/servers/<name>/backup', methods=['POST'])
def api_backup(name):
    s = get_server(name)
    backup_type = request.args.get('type', 'world')
    try:
        if backup_type == 'full':
            backup_path = s.backup_full()
        else:
            backup_path = s.backup_world()
        if backup_path:
            log_activity("backup_create", {"name": name, "type": backup_type, "path": backup_path})
            return jsonify({"backup": backup_path})
        else:
            return jsonify({"error": "No content to backup"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/backups', methods=['GET'])
def api_list_backups(name):
    s = get_server(name)
    backups = s.list_backups()
    return jsonify({"backups": backups})

@app.route('/api/servers/<name>/backups//restore', methods=['POST'])
def api_restore_backup(name, filename):
    s = get_server(name)
    backup_path = Path(SERVERS_DIR) / name / "backups" / filename
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404
    try:
        s.restore_from_backup(str(backup_path))
        log_activity("backup_restore", {"name": name, "backup": filename})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/backups/', methods=['DELETE'])
def api_delete_backup(name, filename):
    s = get_server(name)
    backup_path = Path(SERVERS_DIR) / name / "backups" / filename
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404
    try:
        s.delete_backup(str(backup_path))
        log_activity("backup_delete", {"name": name, "backup": filename})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/backups//download')
def api_download_backup(name, filename):
    s = get_server(name)
    backup_path = Path(SERVERS_DIR) / name / "backups" / filename
    if not backup_path.exists():
        return jsonify({"error": "Backup not found"}), 404
    return send_file(str(backup_path), as_attachment=True, download_name=filename)

@app.route('/api/servers/<name>', methods=['DELETE'])
def api_delete_server(name):
    s = get_server(name)
    try:
        s.delete()
        server_cache.pop(name, None)
        log_activity("server_delete", {"name": name})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/plugins', methods=['GET'])
def api_list_plugins(name):
    s = get_server(name)
    return jsonify({"plugins": s.list_plugins()})

@app.route('/api/servers/<name>/plugins', methods=['POST'])
def api_upload_plugin(name):
    s = get_server(name)
    if 'plugin' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['plugin']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    if not file.filename.endswith('.jar'):
        return jsonify({"error": "File must be .jar"}), 400
    data = file.read()
    s.upload_plugin(data, file.filename)
    log_activity("plugin_upload", {"server": name, "plugin": file.filename})
    return jsonify({"success": True, "filename": file.filename})

@app.route('/api/servers/<name>/plugins/', methods=['DELETE'])
def api_delete_plugin(name, filename):
    s = get_server(name)
    ok = s.delete_plugin(filename)
    if ok:
        log_activity("plugin_delete", {"server": name, "plugin": filename})
    return jsonify({"success": ok})

@app.route('/api/servers/<name>/plugin_inventory', methods=['GET'])
def api_plugin_inventory(name):
    inventory = list_server_plugins(os.path.join(SERVERS_DIR, name))
    return jsonify({"installed": inventory})

@app.route('/api/servers/<name>/plugin_install', methods=['POST'])
def api_plugin_install(name):
    data = request.json or {}
    manifest_path = data.get("manifest_path")
    if not manifest_path or not os.path.exists(manifest_path):
        return jsonify({"error": "manifest_path required and must exist"}), 400
    lib = PluginLibrary()
    ok, errs = lib.install_plugin(Path(SERVERS_DIR) / name, Path(manifest_path))
    if not ok:
        return jsonify({"error": errs}), 400
    log_activity("plugin_install", {"server": name, "manifest": manifest_path})
    return jsonify({"success": True})

@app.route('/api/servers/<name>/plugin_rollback', methods=['POST'])
def api_plugin_rollback(name):
    data = request.json or {}
    plugin_id = data.get("plugin_id")
    if not plugin_id:
        return jsonify({"error": "plugin_id required"}), 400
    lib = PluginLibrary()
    ok, errs = lib.rollback_plugin(Path(SERVERS_DIR) / name, plugin_id)
    log_activity("plugin_rollback", {"server": name, "plugin": plugin_id})
    return jsonify({"success": ok, "errors": errs})

@app.route('/api/servers/<name>/upload_jar', methods=['POST'])
def api_upload_jar(name):
    s = get_server(name)
    if 'jar' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['jar']
    if not file.filename.endswith('.jar'):
        return jsonify({"error": "Must be .jar"}), 400
    data = file.read()
    s.upload_jar(data, file.filename)
    log_activity("jar_upload", {"server": name, "filename": file.filename})
    return jsonify({"success": True})

@app.route('/api/servers/<name>/command', methods=['POST'])
def api_send_command(name):
    s = get_server(name)
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    if not s.is_running():
        return jsonify({"error": "Server is not running"}), 400
    try:
        ok = s.send_command(command)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/stats')
def api_server_stats(name):
    s = get_server(name)
    try:
        cpu = psutil.cpu_percent(interval=0.1) if psutil else 0
        mem = psutil.virtual_memory() if psutil else None
        mem_pct = mem.percent if mem else 0
        disk = psutil.disk_usage(str(Path(SERVERS_DIR) / name)) if psutil else None
        disk_pct = disk.percent if disk else 0
        info = s.get_info()
        uptime = info.get("uptime")
        if uptime is not None:
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m"
        else:
            uptime_str = None
        return jsonify({
            "cpu": cpu,
            "memory_percent": mem_pct,
            "disk_percent": disk_pct,
            "uptime": uptime_str,
            "uptime_seconds": uptime,
            "running": s.is_running()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files', methods=['GET'])
def api_list_files(name):
    s = get_server(name)
    subpath = request.args.get('path', '.')
    try:
        files = s.list_files(subpath)
        return jsonify({"path": subpath, "files": files})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/read', methods=['GET'])
def api_read_file(name):
    s = get_server(name)
    filepath = request.args.get('path')
    if not filepath:
        return jsonify({"error": "path required"}), 400
    try:
        content = s.read_file(filepath)
        return jsonify({"content": content})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/write', methods=['POST'])
def api_write_file(name):
    s = get_server(name)
    data = request.json or {}
    filepath = data.get('path')
    content = data.get('content', '')
    if not filepath:
        return jsonify({"error": "path required"}), 400
    try:
        s.write_file(filepath, content)
        log_activity("file_write", {"server": name, "path": filepath})
        return jsonify({"success": True})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/create_dir', methods=['POST'])
def api_create_directory(name):
    s = get_server(name)
    data = request.json or {}
    path = data.get('path')
    if not path:
        return jsonify({"error": "path required"}), 400
    try:
        s.create_directory(path)
        log_activity("dir_create", {"server": name, "path": path})
        return jsonify({"success": True})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/delete', methods=['POST'])
def api_delete_file(name):
    s = get_server(name)
    data = request.json or {}
    filepath = data.get('path')
    if not filepath:
        return jsonify({"error": "path required"}), 400
    try:
        s.delete_file(filepath)
        log_activity("file_delete", {"server": name, "path": filepath})
        return jsonify({"success": True})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/move', methods=['POST'])
def api_move_file(name):
    s = get_server(name)
    data = request.json or {}
    src = data.get('src')
    dst = data.get('dst')
    if not src or not dst:
        return jsonify({"error": "src and dst required"}), 400
    try:
        s.move_file(src, dst)
        log_activity("file_move", {"server": name, "src": src, "dst": dst})
        return jsonify({"success": True})
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/files/download')
def api_download_file(name):
    s = get_server(name)
    filepath = request.args.get('path')
    if not filepath:
        return jsonify({"error": "path required"}), 400
    try:
        data = s.download_file(filepath)
        filename = Path(filepath).name
        from io import BytesIO
        return send_file(BytesIO(data), as_attachment=True, download_name=filename)
    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/ops', methods=['GET', 'POST'])
def api_op_management(name):
    s = get_server(name)
    ops_file = Path(SERVERS_DIR) / name / "ops.json"
    if request.method == 'GET':
        if ops_file.exists():
            try:
                data = json.load(open(ops_file))
                return jsonify({"ops": data.get("ops", [])})
            except Exception:
                pass
        return jsonify({"ops": []})
    else:
        data = request.json or {}
        ops = data.get('ops', [])
        with open(ops_file, "w") as f:
            json.dump({"ops": ops}, f)
        ops_txt = Path(SERVERS_DIR) / name / "ops.txt"
        with open(ops_txt, "w") as f:
            for op in ops:
                f.write(op + "\n")
        if s.is_running():
            for op in ops:
                s.send_command(f"op {op}")
        log_activity("ops_update", {"server": name, "ops_count": len(ops)})
        return jsonify({"success": True, "ops": ops})

@app.route('/api/servers/<name>/whitelist', methods=['GET', 'POST', 'DELETE'])
def api_whitelist_management(name):
    s = get_server(name)
    wl_file = Path(SERVERS_DIR) / name / "whitelist.json"
    if request.method == 'GET':
        if wl_file.exists():
            try:
                data = json.load(open(wl_file))
                return jsonify({"whitelist": data.get("whitelist", [])})
            except Exception:
                pass
        return jsonify({"whitelist": []})
    elif request.method == 'DELETE':
        data = request.json or {}
        player = data.get('player')
        if not player:
            return jsonify({"error": "player required"}), 400
        if wl_file.exists():
            try:
                content = json.load(open(wl_file))
                wl = content.get("whitelist", [])
                new_wl = [w for w in wl if w.get("name") != player and w.get("uuid") != player]
                with open(wl_file, "w") as f:
                    json.dump({"whitelist": new_wl}, f)
                if s.is_running():
                    s.send_command(f"whitelist remove {player}")
                log_activity("whitelist_remove", {"server": name, "player": player})
                return jsonify({"success": True, "whitelist": new_wl})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({"error": "whitelist not found"}), 404
    else:
        data = request.json or {}
        action = data.get('action')
        player = data.get('player')
        if not action or not player:
            return jsonify({"error": "action and player required"}), 400
        wl = []
        if wl_file.exists():
            try:
                content = json.load(open(wl_file))
                wl = content.get("whitelist", [])
            except Exception:
                pass
        if action == 'add':
            new_entry = {"name": player, "uuid": data.get('uuid', '')}
            if not any(w.get("name") == player for w in wl):
                wl.append(new_entry)
                with open(wl_file, "w") as f:
                    json.dump({"whitelist": wl}, f)
                if s.is_running():
                    s.send_command(f"whitelist add {player}")
                log_activity("whitelist_add", {"server": name, "player": player})
                return jsonify({"success": True, "whitelist": wl})
        return jsonify({"success": False})

@app.route('/api/servers/<name>/bans', methods=['GET', 'POST', 'DELETE'])
def api_ban_management(name):
    s = get_server(name)
    bans_file = Path(SERVERS_DIR) / name / "banned-players.json"
    if request.method == 'GET':
        if bans_file.exists():
            try:
                data = json.load(open(bans_file))
                return jsonify({"bans": data.get("players", [])})
            except Exception:
                pass
        return jsonify({"bans": []})
    elif request.method == 'DELETE':
        data = request.json or {}
        player = data.get('player')
        if not player:
            return jsonify({"error": "player required"}), 400
        if bans_file.exists():
            try:
                content = json.load(open(bans_file))
                bans = content.get("players", [])
                new_bans = [b for b in bans if b.get("name") != player and b.get("uuid") != player]
                with open(bans_file, "w") as f:
                    json.dump({"players": new_bans}, f)
                if s.is_running():
                    s.send_command(f"pardon {player}")
                log_activity("ban_pardon", {"server": name, "player": player})
                return jsonify({"success": True, "bans": new_bans})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        return jsonify({"error": "bans file not found"}), 404
    else:
        data = request.json or {}
        player = data.get('player')
        reason = data.get('reason', '')
        if not player:
            return jsonify({"error": "player required"}), 400
        bans = []
        if bans_file.exists():
            try:
                content = json.load(open(bans_file))
                bans = content.get("players", [])
            except Exception:
                pass
        new_ban = {"name": player, "uuid": data.get('uuid', ''), "reason": reason, "source": "server", "created": time.time()}
        if not any(b.get("name") == player for b in bans):
            bans.append(new_ban)
            with open(bans_file, "w") as f:
                json.dump({"players": bans}, f)
            if s.is_running():
                cmd = f"ban {player}" + (f" {reason}" if reason else "")
                s.send_command(cmd)
            log_activity("ban_player", {"server": name, "player": player, "reason": reason})
            return jsonify({"success": True, "bans": bans})
        return jsonify({"success": False, "error": "Player already banned"})

@app.route('/api/servers/<name>/kick', methods=['POST'])
def api_kick_player(name):
    s = get_server(name)
    data = request.json or {}
    player = data.get('player')
    reason = data.get('reason', '')
    if not player:
        return jsonify({"error": "player required"}), 400
    if not s.is_running():
        return jsonify({"error": "Server not running"}), 400
    try:
        cmd = f"kick {player}" + (f" {reason}" if reason else "")
        s.send_command(cmd)
        log_activity("kick_player", {"server": name, "player": player, "reason": reason})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def log_activity(action, details):
    log_entry = {
        "timestamp": time.time(),
        "action": action,
        "details": details
    }
    logs = load_data("activity_log.json", [])
    logs.append(log_entry)
    if len(logs) > 1000:
        logs = logs[-1000:]
    save_data("activity_log.json", logs)

@app.route('/api/activity')
def api_activity_log():
    logs = load_data("activity_log.json", [])
    logs.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    limit = request.args.get('limit', 100, type=int)
    return jsonify({"logs": logs[:limit]})

@app.route('/api/catalog/repositories', methods=['GET', 'POST'])
def api_catalog_repos():
    if request.method == 'POST':
        data = request.json or {}
        repos = load_data("catalog_repos.json", [])
        new_repo = {
            "id": data.get("id") or data.get("name", "").lower().replace(" ", "-"),
            "name": data.get("name"),
            "type": data.get("type", "github"),
            "url": data.get("url"),
            "enabled": data.get("enabled", True)
        }
        repos.append(new_repo)
        save_data("catalog_repos.json", repos)
        return jsonify({"success": True, "repository": new_repo}), 201
    else:
        repos = load_data("catalog_repos.json", [])
        return jsonify({"repositories": repos})

@app.route('/api/catalog/repositories/<repo_id>', methods=['PUT', 'DELETE'])
def api_manage_repo(repo_id):
    repos = load_data("catalog_repos.json", [])
    idx = next((i for i, r in enumerate(repos) if r.get("id") == repo_id), None)
    if idx is None:
        return jsonify({"error": "Repository not found"}), 404
    if request.method == 'DELETE':
        repos.pop(idx)
        save_data("catalog_repos.json", repos)
        return jsonify({"success": True})
    else:
        data = request.json or {}
        repos[idx].update(data)
        save_data("catalog_repos.json", repos)
        return jsonify({"success": True, "repository": repos[idx]})

@app.route('/api/catalog/plugins')
def api_catalog_plugins():
    repos = load_data("catalog_repos.json", [])
    all_plugins = []
    for repo in repos:
        if not repo.get("enabled", True):
            continue
        repo_plugins = load_data(f"catalog_{repo['id']}.json", [])
        for p in repo_plugins:
            p["source"] = repo["name"]
            all_plugins.append(p)
    return jsonify({"plugins": all_plugins})

@app.route('/api/catalog/refresh', methods=['POST'])
def api_refresh_catalog():
    data = request.json or {}
    repo_id = data.get("repository_id")
    repos = load_data("catalog_repos.json", [])
    if repo_id:
        repos = [r for r in repos if r.get("id") == repo_id]
    for repo in repos:
        if not repo.get("enabled", True):
            continue
        if repo.get("type") == "github":
            try:
                url = repo.get("url", "").rstrip("/")
                manifest_url = f"{url}/raw/main/plugins.json"
                resp = requests.get(manifest_url, timeout=10)
                if resp.status_code == 200:
                    plugins = resp.json()
                    save_data(f"catalog_{repo['id']}.json", plugins)
            except Exception as e:
                print(f"Failed to sync catalog {repo['id']}: {e}")
    log_activity("catalog_refresh", {"repository": repo_id})
    return jsonify({"success": True})

@app.route('/api/schedules', methods=['GET', 'POST'])
def api_schedules():
    if request.method == 'POST':
        data = request.json or {}
        schedules = load_data("schedules.json", [])
        new_schedule = {
            "id": f"sched_{int(time.time())}",
            "name": data.get("name"),
            "server": data.get("server"),
            "action": data.get("action"),
            "cron": data.get("cron"),
            "enabled": data.get("enabled", True),
            "last_run": None,
            "next_run": None
        }
        schedules.append(new_schedule)
        save_data("schedules.json", schedules)
        return jsonify({"success": True, "schedule": new_schedule}), 201
    else:
        schedules = load_data("schedules.json", [])
        return jsonify({"schedules": schedules})

@app.route('/api/schedules/<schedule_id>', methods=['PUT', 'DELETE'])
def api_manage_schedule(schedule_id):
    schedules = load_data("schedules.json", [])
    idx = next((i for i, s in enumerate(schedules) if s.get("id") == schedule_id), None)
    if idx is None:
        return jsonify({"error": "Schedule not found"}), 404
    if request.method == 'DELETE':
        schedules.pop(idx)
        save_data("schedules.json", schedules)
        return jsonify({"success": True})
    else:
        data = request.json or {}
        schedules[idx].update(data)
        save_data("schedules.json", schedules)
        return jsonify({"success": True, "schedule": schedules[idx]})

@app.route('/api/notifications', methods=['GET', 'POST'])
def api_notifications():
    if request.method == 'POST':
        data = request.json or {}
        integrations = load_data("notifications.json", [])
        new_integration = {
            "id": f"notif_{int(time.time())}",
            "name": data.get("name"),
            "type": data.get("type"),
            "webhook_url": data.get("webhook_url"),
            "events": data.get("events", []),
            "enabled": data.get("enabled", True)
        }
        integrations.append(new_integration)
        save_data("notifications.json", integrations)
        return jsonify({"success": True, "integration": new_integration}), 201
    else:
        integrations = load_data("notifications.json", [])
        return jsonify({"integrations": integrations})

@app.route('/api/notifications/<int_id>', methods=['PUT', 'DELETE'])
def api_manage_notification(int_id):
    integrations = load_data("notifications.json", [])
    idx = next((i for i, n in enumerate(integrations) if n.get("id") == int_id), None)
    if idx is None:
        return jsonify({"error": "Integration not found"}), 404
    if request.method == 'DELETE':
        integrations.pop(idx)
        save_data("notifications.json", integrations)
        return jsonify({"success": True})
    else:
        data = request.json or {}
        integrations[idx].update(data)
        save_data("notifications.json", integrations)
        return jsonify({"success": True, "integration": integrations[idx]})

@app.route('/api/notifications/test/<int_id>', methods=['POST'])
def api_test_notification(int_id):
    integrations = load_data("notifications.json", [])
    integration = next((n for n in integrations if n.get("id") == int_id), None)
    if not integration:
        return jsonify({"error": "Integration not found"}), 404
    if integration.get("type") == "discord":
        try:
            payload = {"content": "Test notification from Minecraft Server Automator"}
            resp = requests.post(integration["webhook_url"], json=payload, timeout=10)
            return jsonify({"success": resp.status_code in (200, 204)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host=config.get('host', '0.0.0.0'), port=config.get('port', 5000), debug=config.get('debug', True))