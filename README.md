# Minecraft Server Automator

> A self‑hosted web‑based control panel for managing multiple Minecraft servers with version selection, plugin management, cracked mode, and real‑time console access.

---

## 📖 Overview

**Minecraft Server Automator** is a lightweight Flask application that lets you create, start, stop, and monitor Minecraft servers directly from your browser. It supports both **Vanilla** (official Mojang releases) and **Paper** server JARs, allows you to toggle offline/cracked mode, upload custom JARs, manage plugins, and send console commands – all through a clean, responsive UI with live log streaming.

It is designed for server administrators, homelab enthusiasts, and educators who need a simple yet powerful tool to provision and manage Minecraft servers without touching the command line.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Multi‑Version Support** | Automatically fetches all official Minecraft versions (including snapshots) from Mojang’s manifest. |
| **Server Type Selection** | Choose between **Vanilla** (official) or **Paper** (performance‑optimised) when creating a server. |
| **Custom JAR Upload** | Upload any server JAR (e.g., Forge, Fabric, Spigot) via the web UI. |
| **Cracked / Offline Mode** | Toggle `online-mode` with one click for offline play or testing. |
| **Plugin Management** | Upload, list, and delete `.jar` plugins – they are stored in the server’s `plugins/` folder. |
| **Console Commands** | Send any command (e.g., `/say Hello`, `stop`, `gamemode creative @a`) to the running server. |
| **Live Console Log** | Real‑time streaming of server output; auto‑scrolls and persists across sessions. |
| **Server Properties Editor** | Modify any `server.properties` setting directly from the UI. |
| **World Backups** | Create a ZIP backup of the `world/` folder with a single click. |
| **Memory‑Aware JVM Tuning** | Automatically adjusts heap size (`-Xmx` / `-Xms`) based on available system RAM to avoid out‑of‑memory errors. |
| **Responsive UI** | Works on desktops, tablets, and mobile devices with a collapsible sidebar. |
| **Java & Memory Health Checks** | Displays Java installation status and free RAM on the sidebar. |
| **Process Management** | Uses Python’s `subprocess` with proper PID tracking; servers can be stopped/restarted gracefully. |

---

## 🧰 Prerequisites

- **Operating System**: Windows, macOS, or Linux (tested on Windows 10/11, Ubuntu 20.04).
- **Java**: **Java 17 or higher** (Minecraft 1.18+ requires Java 17). The tool will warn you if Java is not found.
- **Python**: **Python 3.9 or newer**.
- **RAM**: At least 1 GB of free RAM for the server itself (2 GB recommended). The tool monitors available memory and warns you if it is low.
- **Internet**: Required for downloading server JARs and version manifests (offline mode works after initial download).

---

## 📦 Installation

1. **Clone or download** this repository:
   ```bash
   git clone https://github.com/yourusername/minecraft-automator.git
   cd minecraft-automator
Install Python dependencies:

bash
pip install -r requirements.txt
If requirements.txt is not provided, install manually:

bash
pip install flask psutil requests
Create the required directory structure (if not already present):

text
minecraft-automator/
├── app.py
├── server_manager.py
├── version_fetcher.py
├── config.json
├── requirements.txt      (optional)
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── script.js
Customise config.json (optional):

json
{
    "servers_dir": "./servers",
    "host": "0.0.0.0",
    "port": 5000,
    "debug": true
}
servers_dir: where server instances will be stored.

host / port: bind address and port for the web UI.

debug: enable Flask debug mode (set to false in production).

Run the application:

bash
python app.py
You should see output like:

text
* Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
Open your browser at http://localhost:5000 (or your server’s IP).

🖥️ Usage Guide
Creating a Server
Click the + New Server button in the sidebar.

Fill in:

Server Name (must be unique, no spaces).

Version – choose from the dropdown (fetched from Mojang).

Server Type – Vanilla or Paper (Paper downloads the latest stable build for that version).

JVM Arguments – customise memory and garbage‑collection flags (the tool will automatically cap memory if your system is low).

Port – the port the server will listen on.

Click Create. The server directory and server.jar will be downloaded/created.

Starting / Stopping / Restarting
Select a server from the sidebar.

Use the Start, Stop, or Restart buttons in the header.

Managing Properties
Click the Properties tab.

Edit any property in the key‑value grid.

Click Save Properties to apply changes (you may need to restart the server for some settings).

Toggling Cracked Mode
Click the Settings tab.

Check/uncheck Cracked Mode.

Click Apply Settings – this changes online-mode in server.properties.

Uploading a Custom JAR
In the Settings tab, use the Upload Custom JAR file picker.

Select a .jar file (e.g., Forge installer, Fabric server, or any Minecraft server JAR).

The file will replace server.jar – restart the server to use it.

Managing Plugins (Paper / Spigot)
Click the Plugins tab.

Upload a .jar plugin using the file picker.

Plugins appear in a list with a Delete button.

Note: Plugins are stored in the server’s plugins/ folder; they are loaded when the server starts.

Sending Console Commands
Go to the Console tab.

Type a command (e.g., /say Hello, op username, list) in the input box.

Press Send or hit Enter – the command is sent to the server’s stdin.

Backing Up a World
In the server detail view, click the Backup button.

A ZIP archive of the world/ folder is created inside the server’s backups/ directory.

Deleting a Server
Click the Delete button (danger, red).

Confirm the action – the server process is terminated and the entire folder is removed permanently.

🏗️ Architecture & API
The backend is a Flask REST API; the frontend is vanilla HTML/CSS/JS with fetch() calls.

Endpoint	Method	Description
/api/java	GET	Checks if Java is installed.
/api/memory	GET	Returns system memory info (total, available, free GB).
/api/versions	GET	Returns list of Minecraft versions from Mojang manifest.
/api/servers	GET	Lists all server instances with status.
/api/servers	POST	Creates a new server (JSON: name, version, server_type, jvm_args, port).
/api/servers/<name>/start	POST	Starts the server.
/api/servers/<name>/stop	POST	Stops the server.
/api/servers/<name>/restart	POST	Restarts the server.
/api/servers/<name>/logs	GET	Returns last 200 lines of console log.
/api/servers/<name>/properties	GET/PUT	Get or update server.properties.
/api/servers/<name>/backup	POST	Creates a world backup.
/api/servers/<name>	DELETE	Deletes the server instance.
/api/servers/<name>/plugins	GET/POST/DELETE	List, upload, or delete plugins.
/api/servers/<name>/upload_jar	POST	Replaces server.jar with a custom file.
/api/servers/<name>/command	POST	Sends a command to the running server.
All endpoints return JSON; errors are sent with appropriate HTTP status codes.

🐛 Known Issues
Issue	Description	Workaround / Status
Paper API 410 Gone	PaperMC’s API occasionally changes or returns 410 for old builds.	The tool tries older builds sequentially; if all fail, it prompts you to upload a manual JAR.
Out‑of‑Memory on Low‑RAM Systems	Windows page file may be too small, causing JVM failures even with 256 MB.	Free up system memory, increase page file size, or set even lower -Xmx (e.g., -Xmx128M). The UI shows free RAM.
Windows Path Escaping	On rare occasions, paths with spaces may cause issues.	Use server names without spaces; ensure the installation folder path has no spaces.
Console Log Stops Updating	If the server process is killed externally, the log file may not be updated.	Restart the server; the tool will re‑attach to the new PID.
Plugin Deletion Leaves Empty Folders	Deleting a plugin removes the .jar but empty directories remain.	This does not affect server operation. Future versions may clean empty folders.
Multiple Servers on Same Port	The tool does not prevent port conflicts.	Ensure each server uses a unique port. The UI shows the port for each instance.
🔮 Future Improvements
User Authentication – Add login system (Flask‑Login) for multi‑user environments.

Scheduled Backups – Cron‑like automated world backups with configurable frequency.

Modded Server Support – One‑click installation of Forge, Fabric, or NeoForge (with version selection).

Resource Monitoring – Display CPU, RAM, and player count per server in real time.

Server Templates – Pre‑configured server.properties and world presets (e.g., creative, hardcore).

Docker Deployment – Provide a Dockerfile and docker‑compose.yml for easy containerised setup.

WebSocket Log Streaming – Replace polling with a WebSocket for instant log updates.

Auto‑Start on Boot – Option to automatically start servers when the application launches.

Whitelist / Ops Management – UI for adding/removing players from whitelist.json and ops.json.

Multi‑Instance Clustering – Manage servers across multiple hosts.

Performance Tuning Guide – Built‑in recommendations for JVM flags based on system specs.

🤝 Contributing
Contributions are welcome! Please follow these steps:

Fork the repository.

Create a new branch (git checkout -b feature/your-feature).

Commit your changes (git commit -m 'Add some feature').

Push to the branch (git push origin feature/your-feature).

Open a Pull Request.

Ensure your code follows PEP 8, and update the README if necessary.

📄 License
This project is licensed under the MIT License – see the LICENSE file for details.

🙏 Acknowledgements
Mojang for providing the version manifest and server JARs.

PaperMC for their high‑performance server software.

Flask, psutil, and requests for the excellent libraries.

📬 Contact
For questions, bug reports, or feature requests, please open an issue on GitHub or contact the maintainer at your-email@example.com.

Built with ❤️ for the Minecraft community.
