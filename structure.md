## 📂 Project Structure

Below is the directory layout of a typical installation:

```text
minecraft-automator/
│
├── app.py                # Main Flask application entry point
├── server_manager.py     # Core logic for starting/stopping Minecraft servers
├── version_fetcher.py    # Script to download server jars (Vanilla/Paper, etc.)
├── config.json           # Application settings and directory paths
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
│
├── servers/              # Managed Minecraft server instances
│   ├── survival/         # Example Survival server instance
│   │   ├── server.jar
│   │   ├── server.properties
│   │   ├── plugins/
│   │   ├── world/
│   │   ├── backups/
│   │   └── logs/
│   │
│   └── creative/         # Example Creative server instance
│       ├── server.jar
│       ├── server.properties
│       └── ...
│
├── templates/            # HTML views for the web interface
│   └── index.html        # Main dashboard panel
│
└── static/               # Frontend assets
    ├── style.css         # Dashboard styles
    └── script.js         # AJAX and dynamic UI logic
```
