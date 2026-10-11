import os
import json
import subprocess
import time
import shutil
import psutil
import shlex
import requests
from pathlib import Path
from version_fetcher import download_server_jar
class ServerInstance:
    def __init__(self, name, base_dir):
        self.name = name
        self.base_dir = Path(base_dir) / name
        self.meta_file = self.base_dir / "meta.json"
        self.process = None
        self.console_log_file = self.base_dir / "console.log"
    def _load_meta(self):
        if not self.meta_file.exists():
            return {}
        with open(self.meta_file, "r") as f:
            return json.load(f)
    def _save_meta(self, meta):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with open(self.meta_file, "w") as f:
            json.dump(meta, f, indent=2)
    def _check_java(self):
        try:
            subprocess.run(["java", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    def _download_paper(self, version="latest"):
        api_url = "https://api.papermc.io/v2/projects/paper"
        headers = {"User-Agent": "Minecraft-Server-Automator/1.0"}
        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 410:
                return self._download_paper_fallback(version)
            resp.raise_for_status()
            versions = resp.json()["versions"]
            if version == "latest" or version not in versions:
                version = versions[-1]
            builds_url = f"{api_url}/versions/{version}/builds"
            resp = requests.get(builds_url, headers=headers, timeout=10)
            if resp.status_code == 410:
                return self._download_paper_fallback(version)
            resp.raise_for_status()
            builds = resp.json()["builds"]
            if not builds:
                raise ValueError("No builds found")
            selected_build = None
            for build_obj in reversed(builds):
                build_num = build_obj["build"]
                jar_url = f"{api_url}/versions/{version}/builds/{build_num}/downloads/paper-{version}-{build_num}.jar"
                head_resp = requests.head(jar_url, headers=headers, timeout=5)
                if head_resp.status_code == 200:
                    selected_build = build_num
                    break
                else:
                    print(f"Build {build_num} unavailable (status {head_resp.status_code}), trying older...")
            if selected_build is None:
                raise ValueError(f"No available build found for Paper version {version}")
            jar_url = f"{api_url}/versions/{version}/builds/{selected_build}/downloads/paper-{version}-{selected_build}.jar"
            jar_path = self.base_dir / "server.jar"
            r = requests.get(jar_url, stream=True, headers=headers, timeout=30)
            r.raise_for_status()
            with open(jar_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            return version
        except Exception as e:
            print(f"Paper API error: {e}, trying fallback...")
            return self._download_paper_fallback(version)
    def _download_paper_fallback(self, version="latest"):
        raise RuntimeError(
            "Paper download failed: The PaperMC API returned 410 Gone. "
            "Please manually download the Paper JAR from https://papermc.io/downloads "
            "and upload it via the Settings tab (Upload Custom JAR), or select Vanilla server type."
        )
    def create(self, version, server_type="vanilla", jvm_args="-Xmx1024M -Xms1024M", port=25565):
        if not self._check_java():
            raise RuntimeError("Java is not installed or not in PATH. Please install Java 17+.")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        jar_path = self.base_dir / "server.jar"
        if not jar_path.exists():
            if server_type.lower() == "paper":
                self._download_paper(version)
            else:
                download_server_jar(version, str(jar_path))
            if not jar_path.exists() or jar_path.stat().st_size < 1000:
                raise RuntimeError("Failed to download server.jar – file is missing or corrupt.")
        eula_path = self.base_dir / "eula.txt"
        with open(eula_path, "w") as f:
            f.write("eula=true\n")
        props_path = self.base_dir / "server.properties"
        if not props_path.exists():
            with open(props_path, "w") as f:
                f.write(f"server-port={port}\n")
                f.write("enable-query=false\n")
                f.write("enable-rcon=false\n")
                f.write("online-mode=true\n")
        meta = {
            "version": version,
            "server_type": server_type,
            "jvm_args": jvm_args,
            "port": port,
            "created": time.time()
        }
        self._save_meta(meta)
        return True
    def start(self):
        if not self._check_java():
            raise RuntimeError("Java not found")
        if self.is_running():
            return False
        jar_path = self.base_dir / "server.jar"
        if not jar_path.exists():
            raise FileNotFoundError(f"Server JAR not found in {self.base_dir}")
        meta = self._load_meta()
        jvm_args = shlex.split(meta.get("jvm_args", "-Xmx1024M -Xms1024M"))
        cmd = ["java"] + jvm_args + ["-jar", "server.jar", "nogui"]
        self.console_log_file.touch(exist_ok=True)
        log_fd = open(self.console_log_file, "a", encoding="utf-8")
        log_fd.write(f"\n--- Server started at {time.ctime()} ---\n")
        log_fd.flush()
        self.process = subprocess.Popen(
            cmd,
            cwd=str(self.base_dir),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        meta["pid"] = self.process.pid
        meta["started_at"] = time.time()
        self._save_meta(meta)
        import threading
        def reader():
            for line in iter(self.process.stdout.readline, ''):
                log_fd.write(line)
                log_fd.flush()
            log_fd.close()
        threading.Thread(target=reader, daemon=True).start()
        return True
    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            return True
        meta = self._load_meta()
        pid = meta.get("pid")
        if pid:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                proc.wait(timeout=10)
                meta.pop("pid", None)
                self._save_meta(meta)
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    def restart(self):
        self.stop()
        time.sleep(1)
        return self.start()
    def is_running(self):
        if self.process and self.process.poll() is None:
            return True
        meta = self._load_meta()
        pid = meta.get("pid")
        if pid:
            try:
                proc = psutil.Process(pid)
                if proc.is_running():
                    self.process = proc
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    def get_console_log(self, lines=500):
        if not self.console_log_file.exists():
            return "No console output yet."
        try:
            with open(self.console_log_file, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
                if len(all_lines) <= lines:
                    return "".join(all_lines)
                else:
                    return "".join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log: {e}"
    def get_properties(self):
        props_path = self.base_dir / "server.properties"
        if not props_path.exists():
            return {}
        with open(props_path, "r") as f:
            lines = f.readlines()
        props = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
        return props
    def update_properties(self, properties_dict):
        props_path = self.base_dir / "server.properties"
        if not props_path.exists():
            return False
        with open(props_path, "r") as f:
            lines = f.readlines()
        current = {}
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                current[k.strip()] = v.strip()
        current.update(properties_dict)
        with open(props_path, "w") as f:
            for k, v in current.items():
                f.write(f"{k}={v}\n")
        return True
    def backup_world(self):
        world_path = self.base_dir / "world"
        if not world_path.exists():
            return None
        backup_dir = self.base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"world_{timestamp}.zip"
        shutil.make_archive(str(backup_file.with_suffix("")), 'zip', world_path)
        return str(backup_file)
    def backup_full(self):
        backup_dir = self.base_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"full_{timestamp}.zip"
        shutil.make_archive(str(backup_file.with_suffix("")), 'zip', str(self.base_dir), excludes=["backups", "console.log"])
        return str(backup_file)
    def restore_from_backup(self, backup_path):
        if not Path(backup_path).exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        self.stop()
        time.sleep(1)
        temp_dir = self.base_dir.parent / f"{self.name}_restore_temp"
        if temp_dir.exists():
            shutil.rmtree(str(temp_dir))
        shutil.unpack_archive(backup_path, str(temp_dir))
        extracted = list(temp_dir.iterdir())[0] if temp_dir.exists() else temp_dir
        for item in extracted.iterdir():
            dest = self.base_dir / item.name
            if dest.exists():
                if dest.is_dir():
                    shutil.rmtree(str(dest))
                else:
                    dest.unlink()
            shutil.move(str(item), str(dest))
        shutil.rmtree(str(temp_dir))
        return True
    def list_backups(self):
        backup_dir = self.base_dir / "backups"
        if not backup_dir.exists():
            return []
        backups = []
        for f in backup_dir.glob("*.zip"):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "created": stat.st_mtime
            })
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    def delete_backup(self, backup_path):
        p = Path(backup_path)
        if p.exists():
            p.unlink()
            return True
        return False
    def delete(self):
        if self.is_running():
            self.stop()
        time.sleep(0.5)
        try:
            shutil.rmtree(str(self.base_dir))
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete server directory: {e}")
    def clone(self, new_name, base_dir):
        new_base = Path(base_dir) / new_name
        if new_base.exists():
            raise RuntimeError(f"Server directory already exists: {new_name}")
        shutil.copytree(str(self.base_dir), str(new_base))
        new_meta = self._load_meta()
        new_meta["cloned_from"] = self.name
        new_meta["cloned_at"] = time.time()
        new_instance = ServerInstance(new_name, base_dir)
        new_instance._save_meta(new_meta)
        return new_instance
    def get_info(self):
        meta = self._load_meta()
        uptime = None
        if self.is_running() and meta.get("started_at"):
            uptime = int(time.time() - meta["started_at"])
        return {
            "name": self.name,
            "version": meta.get("version", "unknown"),
            "server_type": meta.get("server_type", "vanilla"),
            "jvm_args": meta.get("jvm_args", ""),
            "port": meta.get("port", 25565),
            "running": self.is_running(),
            "created": meta.get("created", 0),
            "uptime": uptime,
            "pid": meta.get("pid")
        }
    def list_plugins(self):
        plugins_dir = self.base_dir / "plugins"
        if not plugins_dir.exists():
            return []
        return [f.name for f in plugins_dir.glob("*.jar")]
    def upload_plugin(self, file_data, filename):
        plugins_dir = self.base_dir / "plugins"
        plugins_dir.mkdir(exist_ok=True)
        dest = plugins_dir / filename
        with open(dest, "wb") as f:
            f.write(file_data)
        return str(dest)
    def delete_plugin(self, filename):
        plugins_dir = self.base_dir / "plugins"
        file_path = plugins_dir / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    def upload_jar(self, file_data, filename):
        jar_path = self.base_dir / "server.jar"
        with open(jar_path, "wb") as f:
            f.write(file_data)
        return str(jar_path)
    def send_command(self, command):
        if not self.is_running():
            raise RuntimeError("Server is not running")
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            return True
        return False
    def get_player_count(self):
        log = self.get_console_log(100)
        import re
        patterns = [
            r"(\d+) player",
            r"There are (\d+) of a max",
            r"Joined the game",
            r"left the game"
        ]
        return None
    def list_files(self, subpath="."):
        target = (self.base_dir / subpath).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        if not target.exists():
            return []
        items = []
        for item in target.iterdir():
            rel = str(item.relative_to(self.base_dir))
            stat = item.stat()
            items.append({
                "name": item.name,
                "path": rel,
                "is_dir": item.is_dir(),
                "size": stat.st_size if item.is_file() else None,
                "modified": stat.st_mtime
            })
        return sorted(items, key=lambda x: (x["is_dir"], x["name"]))
    def read_file(self, filepath):
        target = (self.base_dir / filepath).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        if not target.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if target.is_dir():
            raise IsADirectoryError(f"Path is a directory: {filepath}")
        with open(target, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    def write_file(self, filepath, content):
        target = (self.base_dir / filepath).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    def create_directory(self, path):
        target = (self.base_dir / path).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        target.mkdir(parents=True, exist_ok=True)
        return True
    def delete_file(self, filepath):
        target = (self.base_dir / filepath).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        if not target.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        if target.is_dir():
            shutil.rmtree(str(target))
        else:
            target.unlink()
        return True
    def move_file(self, src, dst):
        src_target = (self.base_dir / src).resolve()
        dst_target = (self.base_dir / dst).resolve()
        base = self.base_dir.resolve()
        if not str(src_target).startswith(str(base) + os.sep) and src_target != base:
            raise PermissionError("Source outside server directory")
        if not str(dst_target).startswith(str(base) + os.sep) and dst_target != base:
            raise PermissionError("Destination outside server directory")
        dst_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_target), str(dst_target))
        return True
    def download_file(self, filepath):
        target = (self.base_dir / filepath).resolve()
        base = self.base_dir.resolve()
        if not str(target).startswith(str(base) + os.sep) and target != base:
            raise PermissionError("Access outside server directory not allowed")
        if not target.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(target, "rb") as f:
            return f.read()
def list_servers(base_dir):
    base = Path(base_dir)
    if not base.exists():
        return []
    return [d.name for d in base.iterdir() if d.is_dir() and (d / "server.jar").exists()]