## Roadmap

The current core milestone focuses on stabilizing existing features (**Vanilla installation** and **Custom JAR uploads** are fully operational) before expanding into automated modding and infrastructure features.

### Short-Term Milestones (High Priority)

#### Fix Paper Support
* **Objective:** Migrate the internal downloader tool from the legacy API to the current PaperMC API endpoint.
* **Target Lifecycle:** Minecraft Version → Check Availability → Find Latest Stable Build → Download Server JAR → Verify Download → Install Server → Start Server.

#### Authentication & Role-Based Access Control
* **Objective:** Add user authentication to secure the panel.
* **Planned Roles:** Administrator, Moderator, and Viewer.

---

### Medium-Term Milestones (Feature Expansion)

#### Automated Scheduled Backups
* **Objective:** Implement configurable cron-style schedules for automated instance backups.

#### Modded Server Support
* **Objective:** Introduce automated downloader engines for modern modding toolchains:
  * Fabric
  * Forge
  * NeoForge

#### Enhanced Resource Monitoring
* **Objective:** Expose real-time host and instance performance metrics:
  * System metrics: CPU, RAM, Disk, and Network usage.
  * Game metrics: TPS, MSPT, and Active Player Count.

#### WebSocket Web Console
* **Objective:** Migrate the server log stream from HTTP polling to WebSockets to achieve low-latency console feedback.

---

### Long-Term Milestones (Scale & Deployment)

#### Reusable Server Templates
* **Objective:** Enable administrators to save pre-configured plugins, properties, and worlds as standard base templates for rapid new deployment.

#### Native Docker Support
* **Objective:** Provide official `Dockerfile` and `docker-compose.yml` assets for streamlined, containerized project deployments.

#### Process Auto-Start
* **Objective:** Add configuration options to flag specific Minecraft server instances to auto-boot instantly when the host script initializes.

#### Game State Player Management
* **Objective:** Build dedicated UI wrapper control panels to directly manage:
  * Server Operators (OP)
  * Whitelists
  * Ban/Kick commands
  * Live player details and statistics

#### Multi-Host Node Management
* **Objective:** Extend the control panel architecture to securely monitor and orchestrate Minecraft server instances distributed across multiple remote machines.
