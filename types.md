## Server Types

### Vanilla
Vanilla server support is fully functional and uses the official Minecraft server JAR.

```text
Server Type: Vanilla
Status: Supported
```

### Paper
Automatic Paper server support is currently not functional. The internal download system uses an outdated PaperMC API endpoint, which returns an `HTTP 410 Gone` error. 

When attempting to create a Paper server through the web panel, the application will display the following message:

```text
Error creating server:
Paper download failed:
The PaperMC API returned 410 Gone.
```

#### Current Support Status
* **Vanilla Support:** Working
* **Custom JAR Upload:** Working
* **Paper Support:** Currently Broken

#### Planned Fix & Workaround
Paper support will be restored in a future update by migrating the downloader module to the current, active PaperMC API. 

Until this update is released, you can manually use Paper by following these steps:
1. Select **Vanilla** when creating the server inside the control panel.
2. Download your desired Paper server JAR file manually from the official PaperMC website.
3. Upload the file to your server instance using **Settings** -> **Upload Custom JAR**.

*Note: Automated Paper installation is under active development. Do not rely on the automated installer at this time.*
