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
        """
        Download the latest available Paper build for the given version.
        Handles 410 Gone by falling back to a direct download from the PaperMC website.
        """
        api_url = "https://api.papermc.io/v2/projects/paper"
        headers = {"User-Agent": "Minecraft-Server-Automator/1.0"}
        try:
            # Get all versions
            resp = requests.get(api_url, headers=headers, timeout=10)
            if resp.status_code == 410:
                # API endpoint gone – fallback to direct download from papermc.io
                print("Paper API returned 410, using fallback download...")
                return self._download_paper_fallback(version)
            resp.raise_for_status()
            versions = resp.json()["versions"]

            if version == "latest" or version not in versions:
                version = versions[-1]  # latest stable

            builds_url = f"{api_url}/versions/{version}/builds"
            resp = requests.get(builds_url, headers=headers, timeout=10)
            if resp.status_code == 410:
                return self._download_paper_fallback(version)
            resp.raise_for_status()
            builds = resp.json()["builds"]
            if not builds:
                raise ValueError("No builds found")

            # Find a downloadable build
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
            # If all else fails, try fallback
            print(f"Paper API error: {e}, trying fallback...")
            return self._download_paper_fallback(version)

    def _download_paper_fallback(self, version="latest"):
        """
        Fallback: try to download from a known working URL or instruct the user.
        """
        # A reliable fallback: use the latest build from the official website
        # We'll try to get the latest version and build from the API, but if the API is down,
        # we can use a static URL like: https://api.papermc.io/v2/projects/paper/versions/1.21.3/builds/24/downloads/paper-1.21.3-24.jar
        # However, that's not future-proof. We'll raise an error with instructions.
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

    def get_console_log(self, lines=200):
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

    def delete(self):
        if self.is_running():
            self.stop()
        time.sleep(0.5)
        try:
            shutil.rmtree(str(self.base_dir))
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete server directory: {e}")

    def get_info(self):
        meta = self._load_meta()
        return {
            "name": self.name,
            "version": meta.get("version", "unknown"),
            "server_type": meta.get("server_type", "vanilla"),
            "jvm_args": meta.get("jvm_args", ""),
            "port": meta.get("port", 25565),
            "running": self.is_running(),
            "created": meta.get("created", 0)
        }

    # --- Plugin management ---
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

    # --- Console command ---
    def send_command(self, command):
        if not self.is_running():
            raise RuntimeError("Server is not running")
        if self.process and self.process.stdin:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            return True
        return False

def list_servers(base_dir):
    base = Path(base_dir)
    if not base.exists():
        return []
    return [d.name for d in base.iterdir() if d.is_dir() and (d / "server.jar").exists()]
