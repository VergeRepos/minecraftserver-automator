##  Usage Guide

### Creating a New Server
Follow these steps to deploy a new Minecraft instance from the web interface:

1. **Open the control panel** in your web browser (usually `http://localhost:5000`).
2. Click the **"New Server"** button on the dashboard.
3. Enter a unique **Server Name** (e.g., `survival`).
4. Select your desired **Minecraft Version** and **Server Type** (Vanilla, Paper, etc.).
5. Configure the **Server Port** (ensure this port is open on your firewall if playing with friends).
6. Configure **JVM Arguments** if your instance requires custom RAM allocations or optimization flags.
7. Click **"Create"**.

>  **What happens next?**  
> The application will automatically generate a dedicated directory for your server, fetch the requested server software binaries, and handle the initial setup.

#### Example Resulting Directory Structure
Once created, your new instance will populate under the `servers/` directory like this:

```text
servers/
└── survival/
    ├── server.jar            # Downloaded server software binary
    ├── server.properties     # Core Minecraft configuration file
    ├── plugins/              # Folder for custom plugins/mods
    ├── world/                # Main world save data
    └── backups/              # Automated backup storage directory
```
