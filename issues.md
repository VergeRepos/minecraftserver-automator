## Known Issues

### Paper Server Download
**Status: Currently Broken**

Automatic Paper server installation is currently non-functional because the application relies on an decommissioned PaperMC API endpoint. Because PaperMC updated its infrastructure, the legacy endpoint returns an error.

#### Example Error Output
```text
Error creating server:
Paper download failed:
The PaperMC API returned 410 Gone.
```
*Note: This issue only affects the automated downloader module. The Paper software itself remains compatible if loaded manually.*

#### Workaround
Until the downloader module is updated, you can manually install Paper by following these steps:
1. Download your preferred Paper server JAR directly from the official PaperMC website.
2. Open the Minecraft Server Automator control panel.
3. Create a new server instance using the **Vanilla** configuration.
4. Navigate to the **Settings** tab for that server.
5. Click **Upload Custom JAR** and select your downloaded Paper JAR file.
6. Restart the server instance.

Alternatively, you can use the built-in Vanilla server type without modification.

#### Planned Fix
A future release will update the download implementation to map directly to PaperMC's active API infrastructure. 

```text
[Current Flow]
Minecraft Version -> Old PaperMC API -> HTTP 410 Gone -> Download Failed

[Planned Flow]
Minecraft Version -> Current PaperMC API -> Paper Build -> server.jar -> Server Created
```

Paper integration should be considered experimental and incomplete until this API migration is finalized.
