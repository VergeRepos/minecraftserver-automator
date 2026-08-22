let currentServer = null;
let refreshInterval = null;
let logInterval = null;

const serverList = document.getElementById('serverList');
const serverDetail = document.getElementById('serverDetail');
const noServerSelected = document.getElementById('noServerSelected');
const serverName = document.getElementById('serverName');
const serverStatus = document.getElementById('serverStatus');
const statusDot = document.getElementById('statusDot');
const infoVersion = document.getElementById('infoVersion');
const infoType = document.getElementById('infoType');
const infoPort = document.getElementById('infoPort');
const infoJvm = document.getElementById('infoJvm');
const consoleOutput = document.getElementById('consoleOutput');
const propertiesContainer = document.getElementById('propertiesContainer');

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const restartBtn = document.getElementById('restartBtn');
const backupBtn = document.getElementById('backupBtn');
const deleteBtn = document.getElementById('deleteBtn');
const savePropertiesBtn = document.getElementById('savePropertiesBtn');

const modal = document.getElementById('newServerModal');
const newServerBtn = document.getElementById('newServerBtn');
const closeModal = document.querySelector('.close');
const newServerForm = document.getElementById('newServerForm');
const versionSelect = document.getElementById('versionSelect');
const serverNameInput = document.getElementById('serverNameInput');
const jvmArgsInput = document.getElementById('jvmArgsInput');
const portInput = document.getElementById('portInput');
const serverTypeSelect = document.getElementById('serverTypeSelect');

const menuToggle = document.getElementById('menuToggle');
const sidebar = document.getElementById('sidebar');

const commandInput = document.getElementById('commandInput');
const sendCommandBtn = document.getElementById('sendCommandBtn');

menuToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && e.target !== menuToggle) {
            sidebar.classList.remove('open');
        }
    }
});

// --- API helper ---
async function apiFetch(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    if (!res.ok) {
        let errMsg;
        try {
            const data = await res.json();
            errMsg = data.error || res.statusText;
        } catch {
            errMsg = res.statusText;
        }
        throw new Error(errMsg);
    }
    return res.json();
}

// --- Check Java ---
async function checkJava() {
    const badge = document.getElementById('javaStatus');
    try {
        const data = await apiFetch('/api/java');
        if (data.installed) {
            badge.textContent = '✅ Java found';
            badge.style.background = '#2e7d32';
        } else {
            badge.textContent = '❌ Java not found';
            badge.style.background = '#b71c1c';
        }
    } catch {
        badge.textContent = '❌ Java check failed';
        badge.style.background = '#b71c1c';
    }
}
checkJava();

// --- Load server list ---
async function loadServerList() {
    try {
        const servers = await apiFetch('/api/servers');
        serverList.innerHTML = '';
        servers.forEach(s => {
            const li = document.createElement('li');
            li.dataset.name = s.name;
            li.innerHTML = `
                <span>${s.name}</span>
                <span class="status-dot ${s.running ? 'running' : 'stopped'}"></span>
            `;
            li.addEventListener('click', () => selectServer(s.name));
            if (currentServer === s.name) li.classList.add('active');
            serverList.appendChild(li);
        });
        if (currentServer && !servers.find(s => s.name === currentServer)) {
            currentServer = null;
            serverDetail.style.display = 'none';
            noServerSelected.style.display = 'flex';
        }
        if (servers.length === 0) {
            serverDetail.style.display = 'none';
            noServerSelected.style.display = 'flex';
        }
    } catch (err) {
        console.error('Failed to load servers:', err);
    }
}

// --- Select server ---
async function selectServer(name) {
    currentServer = name;
    document.querySelectorAll('#serverList li').forEach(li => {
        li.classList.toggle('active', li.dataset.name === name);
    });
    serverDetail.style.display = 'block';
    noServerSelected.style.display = 'none';
    sidebar.classList.remove('open');
    await refreshServerInfo();
    startLogPolling();
}

// --- Refresh server info ---
async function refreshServerInfo() {
    if (!currentServer) return;
    try {
        const servers = await apiFetch('/api/servers');
        const s = servers.find(s => s.name === currentServer);
        if (!s) {
            currentServer = null;
            serverDetail.style.display = 'none';
            noServerSelected.style.display = 'flex';
            loadServerList();
            return;
        }
        serverName.textContent = s.name;
        const statusText = s.running ? 'Running' : 'Stopped';
        serverStatus.textContent = statusText;
        statusDot.className = `status-dot ${s.running ? 'running' : 'stopped'}`;
        infoVersion.textContent = s.version;
        infoType.textContent = s.server_type || 'vanilla';
        infoPort.textContent = s.port;
        infoJvm.textContent = s.jvm_args;
        // Update command UI
        commandInput.disabled = !s.running;
        sendCommandBtn.disabled = !s.running;
        // Update sidebar dot
        const li = document.querySelector(`#serverList li[data-name="${s.name}"]`);
        if (li) {
            const dot = li.querySelector('.status-dot');
            dot.className = `status-dot ${s.running ? 'running' : 'stopped'}`;
        }
        await loadProperties();
        // Reload settings/plugins if those tabs are active
        if (document.getElementById('tab-settings').classList.contains('active')) {
            loadSettings();
        }
        if (document.getElementById('tab-plugins').classList.contains('active')) {
            loadPlugins();
        }
    } catch (err) {
        console.error('Error refreshing server info:', err);
    }
}

// --- Load properties ---
async function loadProperties() {
    if (!currentServer) return;
    try {
        const props = await apiFetch(`/api/servers/${currentServer}/properties`);
        propertiesContainer.innerHTML = '';
        for (const [key, value] of Object.entries(props)) {
            const div = document.createElement('div');
            div.className = 'prop-item';
            div.innerHTML = `
                <label>${key}</label>
                <input type="text" data-key="${key}" value="${value}">
            `;
            propertiesContainer.appendChild(div);
        }
    } catch (err) {
        console.error('Failed to load properties:', err);
    }
}

// --- Save properties ---
async function saveProperties() {
    if (!currentServer) return;
    const inputs = propertiesContainer.querySelectorAll('input[data-key]');
    const props = {};
    inputs.forEach(inp => { props[inp.dataset.key] = inp.value; });
    try {
        await apiFetch(`/api/servers/${currentServer}/properties`, {
            method: 'PUT',
            body: JSON.stringify(props)
        });
        alert('Properties saved!');
    } catch (err) {
        alert('Error saving properties: ' + err.message);
    }
}

// --- Console log polling ---
function startLogPolling() {
    if (logInterval) clearInterval(logInterval);
    fetchLogs();
    logInterval = setInterval(fetchLogs, 2000);
}

async function fetchLogs() {
    if (!currentServer) return;
    try {
        const data = await apiFetch(`/api/servers/${currentServer}/logs`);
        consoleOutput.textContent = data.log || 'No logs yet.';
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    } catch (err) {
        // ignore
    }
}

// --- Server actions ---
async function serverAction(action) {
    if (!currentServer) return;
    const btn = document.getElementById(`${action}Btn`);
    const originalText = btn.textContent;
    btn.textContent = '...';
    btn.disabled = true;
    try {
        await apiFetch(`/api/servers/${currentServer}/${action}`, { method: 'POST' });
        await refreshServerInfo();
        loadServerList();
    } catch (err) {
        alert(`Error ${action}: ${err.message}`);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

startBtn.addEventListener('click', () => serverAction('start'));
stopBtn.addEventListener('click', () => serverAction('stop'));
restartBtn.addEventListener('click', () => serverAction('restart'));

backupBtn.addEventListener('click', async () => {
    if (!currentServer) return;
    try {
        const data = await apiFetch(`/api/servers/${currentServer}/backup`, { method: 'POST' });
        alert(`Backup created: ${data.backup}`);
    } catch (err) {
        alert('Backup failed: ' + err.message);
    }
});

deleteBtn.addEventListener('click', async () => {
    if (!currentServer) return;
    if (!confirm(`Delete server "${currentServer}"? This is permanent.`)) return;
    try {
        await apiFetch(`/api/servers/${currentServer}`, { method: 'DELETE' });
        currentServer = null;
        serverDetail.style.display = 'none';
        noServerSelected.style.display = 'flex';
        loadServerList();
        if (logInterval) clearInterval(logInterval);
    } catch (err) {
        alert('Delete failed: ' + err.message);
    }
});

savePropertiesBtn.addEventListener('click', saveProperties);

// --- Tab switching ---
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        const tabId = 'tab-' + this.dataset.tab;
        document.getElementById(tabId).classList.add('active');
        if (this.dataset.tab === 'plugins') loadPlugins();
        if (this.dataset.tab === 'settings') loadSettings();
    });
});

// --- Settings ---
async function loadSettings() {
    if (!currentServer) return;
    try {
        const props = await apiFetch(`/api/servers/${currentServer}/properties`);
        const onlineMode = props['online-mode'] !== undefined ? props['online-mode'] : 'true';
        const isCracked = onlineMode === 'false';
        document.getElementById('crackedToggle').checked = isCracked;
        document.getElementById('crackedStatus').textContent = isCracked ? 'Enabled' : 'Disabled';
        const servers = await apiFetch('/api/servers');
        const s = servers.find(s => s.name === currentServer);
        document.getElementById('serverTypeDisplay').textContent = s ? s.server_type : 'unknown';
    } catch (err) {
        console.error('Failed to load settings:', err);
    }
}

document.getElementById('applySettingsBtn').addEventListener('click', async () => {
    if (!currentServer) return;
    const cracked = document.getElementById('crackedToggle').checked;
    try {
        await apiFetch(`/api/servers/${currentServer}/properties`, {
            method: 'PUT',
            body: JSON.stringify({ 'online-mode': cracked ? 'false' : 'true' })
        });
        document.getElementById('crackedStatus').textContent = cracked ? 'Enabled' : 'Disabled';
        alert('Settings applied!');
    } catch (err) {
        alert('Error: ' + err.message);
    }
});

document.getElementById('uploadJarBtn').addEventListener('click', async () => {
    if (!currentServer) return;
    const input = document.getElementById('customJarInput');
    if (!input.files.length) return alert('Select a JAR file');
    const file = input.files[0];
    if (!file.name.endsWith('.jar')) return alert('Must be a .jar file');
    const formData = new FormData();
    formData.append('jar', file);
    try {
        const res = await fetch(`/api/servers/${currentServer}/upload_jar`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        alert('JAR uploaded successfully! Restart the server to apply.');
    } catch (err) {
        alert('Upload failed: ' + err.message);
    }
});

// --- Plugins ---
async function loadPlugins() {
    if (!currentServer) return;
    try {
        const plugins = await apiFetch(`/api/servers/${currentServer}/plugins`);
        const container = document.getElementById('pluginList');
        container.innerHTML = '';
        if (plugins.length === 0) {
            container.innerHTML = '<p>No plugins installed.</p>';
        } else {
            plugins.forEach(name => {
                const div = document.createElement('div');
                div.className = 'plugin-item';
                div.innerHTML = `
                    <span>${name}</span>
                    <button data-plugin="${name}" class="delete-plugin-btn">Delete</button>
                `;
                container.appendChild(div);
            });
            document.querySelectorAll('.delete-plugin-btn').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const filename = btn.dataset.plugin;
                    if (!confirm(`Delete plugin "${filename}"?`)) return;
                    try {
                        await apiFetch(`/api/servers/${currentServer}/plugins/${filename}`, { method: 'DELETE' });
                        loadPlugins();
                    } catch (err) {
                        alert('Delete failed: ' + err.message);
                    }
                });
            });
        }
    } catch (err) {
        console.error('Failed to load plugins:', err);
    }
}

document.getElementById('uploadPluginBtn').addEventListener('click', async () => {
    if (!currentServer) return;
    const input = document.getElementById('pluginFileInput');
    if (!input.files.length) return alert('Select a plugin .jar');
    const file = input.files[0];
    if (!file.name.endsWith('.jar')) return alert('Must be .jar');
    const formData = new FormData();
    formData.append('plugin', file);
    try {
        const res = await fetch(`/api/servers/${currentServer}/plugins`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error(await res.text());
        alert('Plugin uploaded!');
        loadPlugins();
    } catch (err) {
        alert('Upload failed: ' + err.message);
    }
});

// --- Send command ---
sendCommandBtn.addEventListener('click', async () => {
    if (!currentServer) return;
    const command = commandInput.value.trim();
    if (!command) return;
    try {
        await apiFetch(`/api/servers/${currentServer}/command`, {
            method: 'POST',
            body: JSON.stringify({ command })
        });
        commandInput.value = '';
    } catch (err) {
        alert('Failed to send command: ' + err.message);
    }
});
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendCommandBtn.click();
    }
});

// --- Modal: New Server ---
newServerBtn.addEventListener('click', async () => {
    modal.style.display = 'flex';
    try {
        const versions = await apiFetch('/api/versions');
        versionSelect.innerHTML = '';
        versions.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = `${v.id} (${v.type})`;
            versionSelect.appendChild(opt);
        });
    } catch (err) {
        alert('Failed to load versions: ' + err.message);
    }
});

closeModal.addEventListener('click', () => modal.style.display = 'none');
window.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
});

newServerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = serverNameInput.value.trim();
    const version = versionSelect.value;
    const server_type = serverTypeSelect.value;
    const jvm_args = jvmArgsInput.value.trim();
    const port = parseInt(portInput.value);
    if (!name) return alert('Server name required');
    const btn = newServerForm.querySelector('button[type="submit"]');
    btn.textContent = 'Creating...';
    btn.disabled = true;
    try {
        await apiFetch('/api/servers', {
            method: 'POST',
            body: JSON.stringify({ name, version, server_type, jvm_args, port })
        });
        modal.style.display = 'none';
        loadServerList();
        currentServer = name;
        selectServer(name);
    } catch (err) {
        alert('Error creating server: ' + err.message);
    } finally {
        btn.textContent = 'Create';
        btn.disabled = false;
    }
});

// --- Initial load ---
loadServerList();

setInterval(() => {
    loadServerList();
    if (currentServer) refreshServerInfo();
}, 5000);