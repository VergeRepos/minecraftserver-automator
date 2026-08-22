# Minecraft Server Automator

A self-hosted, web-based control panel designed to deploy, configure, and manage multiple Minecraft server instances simultaneously from a browser.

Minecraft Server Automator eliminates the need for command-line management by providing a clean graphical interface to handle everything from vanilla installations to heavily modded instances.

---

## Quick Links

**[Installation Guide](install.md)** | **[System Requirements](requirements.md)** | **[How to Use](usage.md)** | **[Project Structure](structure.md)**

**[Supported Server Types](types.md)** | **[Known Issues](issues.md)** | **[Development Roadmap](roadmap.md)**

---

## Screenshots

| Creating a New Server | Configuring Server Properties |
| :---: | :---: |
| <img src="https://github.com" width="250" alt="Creating a new server"> | <img src="https://github.com" width="550" alt="Configuring the server"> |

---

## Key Features

### Lifecycle and Process Management
* **Multi-Instance Support:** Deploy and run multiple independent servers simultaneously.
* **Process Controls:** Start, stop, and restart instances safely with tracked background processes.
* **Automated JVM Allocation:** Memory parameters auto-adjust dynamically based on available system RAM.

### Engine and Mod Support
* **Automated Downloads:** Fetches official Vanilla manifests and Paper builds dynamically.
* **Custom JAR Uploads:** Deploy Forge, Fabric, Spigot, or NeoForge server files seamlessly.
* **Plugin Manager:** Upload, list, and delete `.jar` plugins directly via the user interface.

### Server Administration
* **Interactive Live Console:** Read real-time stdout logs and execute terminal commands instantly.
* **Visual Configuration Editor:** Adjust `server.properties` fields without manual file modification.
* **Authentication Toggle:** Switch between Online and Cracked/Offline modes via the interface.
* **Automated Backups:** Package server worlds into compressed `.zip` archives on demand.

### Dashboard and Monitoring
* **System Metrics:** Monitor local Java states and host machine memory overhead.
* **Responsive Layout:** Interface layouts optimized for desktops, tablets, and mobile devices.

---

## Quick Start

1. **Verify Prerequisites:** Ensure Java (matching your required Minecraft versions) and necessary system runtimes are installed. Refer to the **[System Requirements](requirements.md)**.
2. **Clone the Repository:**
   ```bash
   git clone https://github.com
   cd minecraft-server-automator
   ```
3. **Run the Installer:** Follow the setup steps detailed in the **[Installation Guide](install.md)** to build and launch the application.
4. **Access the Web Interface:** Open your browser and navigate to the configured host port to begin creating servers.
