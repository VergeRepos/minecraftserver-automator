## Installation & Setup

Follow these steps to get the Minecraft Automator up and running on your system.

### 1. Clone the Repository
Clone the project to your local machine and navigate into the project directory:
```bash
git clone https://github.com/yourusername/minecraft-automator.git
cd minecraft-automator
```
*(Note: Replace the URL above with your actual repository URL).*

---

### 2. Create a Virtual Environment
Using a virtual environment is highly recommended to keep dependencies isolated.

#### Windows
```powershell
python -m venv .venv
.venv\Scripts\activate
```

#### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install Dependencies
Install the required packages using `pip`:
```bash
pip install -r requirements.txt
```

If a `requirements.txt` file is not available in your project, install them manually:
```bash
pip install flask psutil requests
```

---

### 4. Configure the Application
Create a file named `config.json` in the root project directory and paste the following configuration:

```json
{
    "servers_dir": "./servers",
    "host": "0.0.0.0",
    "port": 5000,
    "debug": false
}
```

#### Configuration Options

| Option | Description |
| :--- | :--- |
| `servers_dir` | Directory where Minecraft server instances are stored. |
| `host` | Network address used by the web server. |
| `port` | HTTP port used by the control panel. |
| `debug` | Enables Flask debug mode. **Disable this in production.** |

---

### 5. Start the Application
Run the main script to start the web panel:
```bash
python app.py
```

Upon a successful startup, you should see output similar to:
```text
* Running on http://0.0.0.0:5000/
```

#### Accessing the Web Panel
* **Local Machine:** Open [http://localhost:5000](http://localhost:5000) in your web browser.
* **Remote Server:** Open `http://SERVER_IP:5000` (replace `SERVER_IP` with your actual server IP address).
