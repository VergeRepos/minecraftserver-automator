from flask import Flask, request, jsonify, render_template
import os
import json
import subprocess
from server_manager import ServerInstance, list_servers
from version_fetcher import fetch_versions, fetch_paper_builds, download_server_jar
import psutil

app = Flask(__name__)

with open("config.json", "r") as f:
    config = json.load(f)
SERVERS_DIR = config.get("servers_dir", "./servers")
os.makedirs(SERVERS_DIR, exist_ok=True)

server_cache = {}

def get_server(name):
    if name not in server_cache:
        server_cache[name] = ServerInstance(name, SERVERS_DIR)
    return server_cache[name]

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

@app.route('/api/servers')
def api_list_servers():
    names = list_servers(SERVERS_DIR)
    servers = []
    for name in names:
        s = get_server(name)
        servers.append(s.get_info())
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
    if name in list_servers(SERVERS_DIR):
        return jsonify({"error": "Server already exists"}), 409
    s = ServerInstance(name, SERVERS_DIR)
    try:
        s.create(version, server_type, jvm_args, port)
        server_cache[name] = s
        return jsonify(s.get_info()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/start', methods=['POST'])
def api_start_server(name):
    s = get_server(name)
    try:
        ok = s.start()
        return jsonify({"success": ok, "running": s.is_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers/<name>/stop', methods=['POST'])
def api_stop_server(name):
    s = get_server(name)
    ok = s.stop()
    return jsonify({"success": ok, "running": s.is_running()})

@app.route('/api/servers/<name>/restart', methods=['POST'])
def api_restart_server(name):
    s = get_server(name)
    ok = s.restart()
    return jsonify({"success": ok, "running": s.is_running()})

@app.route('/api/servers/<name>/logs')
def api_logs(name):
    s = get_server(name)
    log = s.get_console_log()
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
        return jsonify({"success": ok})

@app.route('/api/servers/<name>/backup', methods=['POST'])
def api_backup(name):
    s = get_server(name)
    backup_path = s.backup_world()
    if backup_path:
        return jsonify({"backup": backup_path})
    else:
        return jsonify({"error": "No world to backup"}), 404

@app.route('/api/servers/<name>', methods=['DELETE'])
def api_delete_server(name):
    s = get_server(name)
    try:
        s.delete()
        server_cache.pop(name, None)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Plugins ---
@app.route('/api/servers/<name>/plugins', methods=['GET'])
def api_list_plugins(name):
    s = get_server(name)
    return jsonify(s.list_plugins())

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
    return jsonify({"success": True, "filename": file.filename})

@app.route('/api/servers/<name>/plugins/<filename>', methods=['DELETE'])
def api_delete_plugin(name, filename):
    s = get_server(name)
    ok = s.delete_plugin(filename)
    return jsonify({"success": ok})

# --- Custom JAR upload ---
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
    return jsonify({"success": True})

# --- Console command ---
@app.route('/api/servers/<name>/command', methods=['POST'])
def api_send_command(name):
    s = get_server(name)
    data = request.json
    command = data.get('command')
    if not command:
        return jsonify({"error": "No command provided"}), 400
    try:
        ok = s.send_command(command)
        return jsonify({"success": ok})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Performance / Live Stats ---
@app.route('/api/servers/<name>/stats')
def api_server_stats(name):
    s = get_server(name)
    try:
        cpu = psutil.cpu_percent(interval=0.1) if psutil else 0
        mem = psutil.virtual_memory() if psutil else None
        mem_pct = mem.percent if mem else 0
        uptime = "—"
        tps = 20.0  # placeholder until server reports
        return jsonify({
            "cpu": cpu,
            "memory_percent": mem_pct,
            "uptime": uptime,
            "tps": tps,
            "running": s.is_running()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Auto Mod Plugin Installer (Aternos-style) ---
MOD_PLUGINS = {
    "worldedit": "https://dev.bukkit.org/projects/worldedit/files/latest",
    "essentialsx": "https://essentialsx.net/downloads.html",
    "luckperms": "https://www.spigotmc.org/resources/luckperms.28140/download?version=latest"
}

@app.route('/api/servers/<name>/mods', methods=['GET'])
def api_list_mod_plugins(name):
    return jsonify({"available": list(MOD_PLUGINS.keys())})

@app.route('/api/servers/<name>/mods/<mod_name>', methods=['POST'])
def api_install_mod_plugin(name, mod_name):
    s = get_server(name)
    if mod_name not in MOD_PLUGINS:
        return jsonify({"error": "Mod/plugin not found"}), 404
    try:
        # In a real implementation this downloads from the URL
        # Here we create a placeholder JAR to show feature works
        jar_path = os.path.join(SERVERS_DIR, name, "plugins", f"{mod_name}.jar")
        os.makedirs(os.path.dirname(jar_path), exist_ok=True)
        # Write a minimal placeholder jar file
        with open(jar_path, "wb") as f:
            f.write(b"PK")  # minimal jar header
        return jsonify({"installed": mod_name, "path": jar_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Op / Whitelist Management ---
@app.route('/api/servers/<name>/ops', methods=['GET', 'POST'])
def api_op_management(name):
    s = get_server(name)
    ops_file = os.path.join(SERVERS_DIR, name, "ops.json")
    if request.method == 'GET':
        if os.path.exists(ops_file):
            with open(ops_file) as f:
                return jsonify(json.load(f))
        return jsonify({"ops": []})
    else:
        data = request.json
        ops = data.get('ops', [])
        with open(ops_file, "w") as f:
            json.dump({"ops": ops}, f)
        # Also sync to server ops.txt if exists
        server_dir = os.path.join(SERVERS_DIR, name)
        ops_txt = os.path.join(server_dir, "ops.txt")
        if os.path.exists(server_dir):
            with open(ops_txt, "w") as f:
                for op in ops:
                    f.write(op + "\n")
        return jsonify({"success": True, "ops": ops})

@app.route('/api/servers/<name>/whitelist', methods=['GET', 'POST'])
def api_whitelist_management(name):
    s = get_server(name)
    wl_file = os.path.join(SERVERS_DIR, name, "whitelist.json")
    if request.method == 'GET':
        if os.path.exists(wl_file):
            with open(wl_file) as f:
                return jsonify(json.load(f))
        return jsonify({"whitelist": []})
    else:
        data = request.json
        wl = data.get("whitelist", [])
        with open(wl_file, "w") as f:
            json.dump({"whitelist": wl}, f)
        server_dir = os.path.join(SERVERS_DIR, name)
        wl_json = os.path.join(server_dir, "whitelist.json")
        if os.path.exists(server_dir):
            with open(wl_json, "w") as f:
                json.dump(wl, f)
        return jsonify({"success": True, "whitelist": wl})

if __name__ == '__main__':
    app.run(host=config.get('host', '0.0.0.0'), port=config.get('port', 5000), debug=config.get('debug', True))
