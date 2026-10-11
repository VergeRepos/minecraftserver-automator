let currentServer = null;
let refreshInterval = null;
let logInterval = null;
let currentPath = '.';
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
async function checkJava() {
    const badge = document.getElementById('javaStatus');
    try {
        const data = await apiFetch('/api/java');
        if (data.installed) {
            badge.textContent = 'Java found';
            badge.style.background = '#2e7d32';
        } else {
            badge.textContent = 'Java not found';
            badge.style.background = '#b71c1c';
        }
    } catch {
        badge.textContent = 'Java check failed';
        badge.style.background = '#b71c1c';
    }
}
checkJava();
async function loadServerList() {
    try {
        const servers = await apiFetch('/api/servers');
        serverList.innerHTML = '';
        servers.forEach(s => {
            const li = document.createElement('li');
            li.dataset.name = s.name;
            li.innerHTML = `<span>${s.name}</span><span class="status-dot ${s.running ? 'running' : 'stopped'}"></span>`;
            li.addEventListener('click', () => selectServer(s.name));
            if (currentServer === s.name) li.classList.add('active');
            serverList.appendChild(li);
        });
    } catch (e) {
        console.error('Failed to load servers:', e);
    }
}
async function selectServer(name) {
    currentServer = name;
    localStorage.setItem('lastServer', name);
    try {
        const servers = await apiFetch('/api/servers');
        const s = servers.find(sv => sv.name === name);
        if (!s) return;
        serverDetail.style.display = 'block';
        document.getElementById('noServerSelected').style.display = 'none';
        serverName.textContent = s.name;
        serverStatus.textContent = s.running ? 'Running' : 'Stopped';
        statusDot.className = `status-dot ${s.running ? 'running' : 'stopped'}`;
        infoVersion.textContent = s.version || '—';
        infoType.textContent = s.server_type || '—';
        infoPort.textContent = s.port || '—';
        infoJvm.textContent = s.jvm_args || '—';
        startBtn.disabled = s.running;
        stopBtn.disabled = !s.running;
        restartBtn.disabled = !s.running;
        if (s.running) {
            commandInput.disabled = false;
            sendCommandBtn.disabled = false;
            commandInput.placeholder = 'Type a command...';
        } else {
            commandInput.disabled = true;
            sendCommandBtn.disabled = true;
            commandInput.placeholder = 'Start server to send commands';
        }
        if (refreshInterval) clearInterval(refreshInterval);
        refreshInterval = setInterval(() => fetchServerStats(name), 5000);
        loadServerLogs(name);
        if (logInterval) clearInterval(logInterval);
        logInterval = setInterval(() => loadServerLogs(name), 3000);
        loadServerProperties(name);
        loadPlugins(name);
        loadOps(name);
        loadWhitelist(name);
        loadBans(name);
        loadBackups(name);
        loadFiles(name);
        loadServerList();
    } catch (e) {
        alert('Failed to load server: ' + e.message);
    }
}
async function fetchServerStats(name) {
    try {
        const stats = await apiFetch(`/api/servers/${name}/stats`);
        document.getElementById('perfCpu').textContent = stats.cpu ? stats.cpu.toFixed(1) + '%' : '—';
        document.getElementById('perfMem').textContent = stats.memory_percent ? stats.memory_percent.toFixed(1) + '%' : '—';
        document.getElementById('perfUptime').textContent = stats.uptime || '—';
        document.getElementById('perfDisk').textContent = stats.disk_percent ? stats.disk_percent.toFixed(1) + '%' : '—';
        document.getElementById('serverStatus').textContent = stats.running ? 'Running' : 'Stopped';
        statusDot.className = `status-dot ${stats.running ? 'running' : 'stopped'}`;
        startBtn.disabled = stats.running;
        stopBtn.disabled = !stats.running;
        restartBtn.disabled = !stats.running;
    } catch (e) {
        console.error('Stats error:', e);
    }
}
async function loadServerLogs(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/logs`);
        consoleOutput.innerHTML = data.log.split('\n').map(line => {
            const timeMatch = line.match(/^\[(.+?)\]/);
            const time = timeMatch ? timeMatch[1] : null;
            let content = time ? line.slice(timeMatch[0].length) : line;
            const isError = /error|fail|crash|exception/i.test(content);
            return `<div class="log-line ${isError ? 'error' : ''}"><span class="log-time">${time || ''}</span>${escapeHtml(content)}</div>`;
        }).join('');
        consoleOutput.scrollTop = consoleOutput.scrollHeight;
    } catch (e) {
        console.error('Log error:', e);
    }
}
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
async function loadServerProperties(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/properties`);
        propertiesContainer.innerHTML = Object.entries(data).map(([k, v]) => `
            <div class="prop-item">
                <label for="prop-${k}">${k}</label>
                <input type="text" id="prop-${k}" value="${escapeHtml(String(v))}" data-key="${escapeHtml(k)}">
            </div>
        `).join('');
    } catch (e) {
        propertiesContainer.innerHTML = '<p class="error">Failed to load properties</p>';
    }
}
async function loadPlugins(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/plugins`);
        const list = document.getElementById('pluginList');
        if (data.plugins && data.plugins.length > 0) {
            list.innerHTML = data.plugins.map(p => `<div class="plugin-item"><span>${escapeHtml(p)}</span><button class="action-btn danger" onclick="deletePlugin('${name}', '${escapeHtml(p)}')">Remove</button></div>`).join('');
        } else {
            list.innerHTML = '<p class="empty">No plugins installed</p>';
        }
    } catch (e) {
        document.getElementById('pluginList').innerHTML = '<p class="error">Failed to load plugins</p>';
    }
}
async function loadOps(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/ops`);
        const list = document.getElementById('opList');
        if (data.ops && data.ops.length > 0) {
            list.innerHTML = data.ops.map(op => `<div class="player-item"><span>${escapeHtml(op)}</span><button class="action-btn danger" onclick="removeOp('${name}', '${escapeHtml(op)}')">Remove</button></div>`).join('');
        } else {
            list.innerHTML = '<p class="empty">No operators</p>';
        }
    } catch (e) {
        document.getElementById('opList').innerHTML = '<p class="error">Failed to load operators</p>';
    }
}
async function loadWhitelist(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/whitelist`);
        const list = document.getElementById('whitelistList');
        if (data.whitelist && data.whitelist.length > 0) {
            list.innerHTML = data.whitelist.map(w => `<div class="player-item"><span>${escapeHtml(w.name || w)}</span><button class="action-btn danger" onclick="removeWhitelist('${name}', '${escapeHtml(w.name || w)}')">Remove</button></div>`).join('');
        } else {
            list.innerHTML = '<p class="empty">Whitelist empty</p>';
        }
    } catch (e) {
        document.getElementById('whitelistList').innerHTML = '<p class="error">Failed to load whitelist</p>';
    }
}
async function loadBans(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/bans`);
        const list = document.getElementById('banList');
        if (data.bans && data.bans.length > 0) {
            list.innerHTML = data.bans.map(b => `<div class="player-item"><span>${escapeHtml(b.name || b)}${b.reason ? ' — ' + escapeHtml(b.reason) : ''}</span><button class="action-btn" onclick="pardonPlayer('${name}', '${escapeHtml(b.name || b)}')">Pardon</button></div>`).join('');
        } else {
            list.innerHTML = '<p class="empty">No banned players</p>';
        }
    } catch (e) {
        document.getElementById('banList').innerHTML = '<p class="error">Failed to load bans</p>';
    }
}
async function loadBackups(name) {
    try {
        const data = await apiFetch(`/api/servers/${name}/backups`);
        const list = document.getElementById('backupList');
        if (data.backups && data.backups.length > 0) {
            list.innerHTML = data.backups.map(b => {
                const size = (b.size / 1024 / 1024).toFixed(2);
                const date = new Date(b.created * 1000).toLocaleString();
                return `<div class="backup-item">
                    <span>${escapeHtml(b.name)} — ${size} MB — ${date}</span>
                    <div class="backup-actions">
                        <button class="action-btn" onclick="restoreBackup('${name}', '${escapeHtml(b.name)}')">Restore</button>
                        <a href="/api/servers/${name}/backups/${encodeURIComponent(b.name)}/download" class="action-btn">Download</a>
                        <button class="action-btn danger" onclick="deleteBackup('${name}', '${escapeHtml(b.name)}')">Delete</button>
                    </div>
                </div>`;
            }).join('');
        } else {
            list.innerHTML = '<p class="empty">No backups</p>';
        }
    } catch (e) {
        document.getElementById('backupList').innerHTML = '<p class="error">Failed to load backups</p>';
    }
}
async function loadFiles(name, path = '.') {
    currentPath = path;
    try {
        const data = await apiFetch(`/api/servers/${name}/files?path=${encodeURIComponent(path)}`);
        const breadcrumb = document.getElementById('fileBreadcrumb');
        const parts = path.split('/').filter(p => p && p !== '.');
        let breadcrumbHtml = `<span class="breadcrumb-item" onclick="loadFiles('${name}', '.')">root</span>`;
        let builtPath = '.';
        for (const part of parts) {
            builtPath += '/' + part;
            breadcrumbHtml += ` / <span class="breadcrumb-item" onclick="loadFiles('${name}', '${builtPath}')">${escapeHtml(part)}</span>`;
        }
        breadcrumb.innerHTML = breadcrumbHtml;
        const list = document.getElementById('fileList');
        if (data.files && data.files.length > 0) {
            list.innerHTML = data.files.map(f => {
                const icon = f.is_dir ? '📁' : '📄';
                const clickAction = f.is_dir ? `onclick="loadFiles('${name}', '${path}/${f.name}')"` : `onclick="editFile('${name}', '${path}/${f.name}')"`;
                return `<div class="file-item" ${clickAction}>
                    <span>${icon} ${escapeHtml(f.name)}</span>
                    <span>${f.size ? (f.size / 1024).toFixed(2) + ' KB' : ''}</span>
                    <button class="action-btn danger" onclick="event.stopPropagation(); deleteFile('${name}', '${path}/${f.name}')">Delete</button>
                </div>`;
            }).join('');
        } else {
            list.innerHTML = '<p class="empty">Empty directory</p>';
        }
    } catch (e) {
        document.getElementById('fileList').innerHTML = '<p class="error">Failed to load files</p>';
    }
}
async function startServer(name) {
    try {
        await apiFetch(`/api/servers/${name}/start`, { method: 'POST' });
        selectServer(name);
    } catch (e) {
        alert('Start failed: ' + e.message);
    }
}
async function stopServer(name) {
    try {
        await apiFetch(`/api/servers/${name}/stop`, { method: 'POST' });
        selectServer(name);
    } catch (e) {
        alert('Stop failed: ' + e.message);
    }
}
async function restartServer(name) {
    try {
        await apiFetch(`/api/servers/${name}/restart`, { method: 'POST' });
        selectServer(name);
    } catch (e) {
        alert('Restart failed: ' + e.message);
    }
}
async function backupServer(name, type = 'world') {
    try {
        const data = await apiFetch(`/api/servers/${name}/backup?type=${type}`, { method: 'POST' });
        alert('Backup created: ' + (data.backup || 'success'));
        loadBackups(name);
    } catch (e) {
        alert('Backup failed: ' + e.message);
    }
}
async function deleteServer(name) {
    if (!confirm('Delete server "' + name + '"? This cannot be undone.')) return;
    try {
        await apiFetch(`/api/servers/${name}`, { method: 'DELETE' });
        currentServer = null;
        serverDetail.style.display = 'none';
        document.getElementById('noServerSelected').style.display = 'flex';
        loadServerList();
    } catch (e) {
        alert('Delete failed: ' + e.message);
    }
}
async function saveProperties(name) {
    const inputs = propertiesContainer.querySelectorAll('input');
    const props = {};
    inputs.forEach(input => {
        props[input.dataset.key] = input.value;
    });
    try {
        await apiFetch(`/api/servers/${name}/properties`, {
            method: 'PUT',
            body: JSON.stringify(props)
        });
        alert('Properties saved');
    } catch (e) {
        alert('Save failed: ' + e.message);
    }
}
async function sendCommand(name, cmd) {
    try {
        await apiFetch(`/api/servers/${name}/command`, {
            method: 'POST',
            body: JSON.stringify({ command: cmd })
        });
        commandInput.value = '';
    } catch (e) {
        alert('Command failed: ' + e.message);
    }
}
async function deletePlugin(name, filename) {
    if (!confirm('Delete plugin ' + filename + '?')) return;
    try {
        await apiFetch(`/api/servers/${name}/plugins/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        loadPlugins(name);
    } catch (e) {
        alert('Failed to delete plugin: ' + e.message);
    }
}
async function addOp(name) {
    const input = document.getElementById('opInput');
    const player = input.value.trim();
    if (!player) return;
    try {
        const data = await apiFetch(`/api/servers/${name}/ops`, { method: 'POST', body: JSON.stringify({ ops: [player] }) });
        input.value = '';
        loadOps(name);
    } catch (e) {
        alert('Failed to add operator: ' + e.message);
    }
}
async function removeOp(name, player) {
    try {
        await apiFetch(`/api/servers/${name}/ops`, { method: 'POST', body: JSON.stringify({ action: 'remove', player }) });
        loadOps(name);
    } catch (e) {
        alert('Failed to remove operator: ' + e.message);
    }
}
async function addWhitelist(name) {
    const input = document.getElementById('whitelistInput');
    const player = input.value.trim();
    if (!player) return;
    try {
        await apiFetch(`/api/servers/${name}/whitelist`, { method: 'POST', body: JSON.stringify({ action: 'add', player }) });
        input.value = '';
        loadWhitelist(name);
    } catch (e) {
        alert('Failed to add to whitelist: ' + e.message);
    }
}
async function removeWhitelist(name, player) {
    try {
        await apiFetch(`/api/servers/${name}/whitelist`, { method: 'DELETE', body: JSON.stringify({ player }) });
        loadWhitelist(name);
    } catch (e) {
        alert('Failed to remove from whitelist: ' + e.message);
    }
}
async function banPlayer(name) {
    const input = document.getElementById('banInput');
    const reasonInput = document.getElementById('banReasonInput');
    const player = input.value.trim();
    if (!player) return;
    try {
        await apiFetch(`/api/servers/${name}/bans`, { method: 'POST', body: JSON.stringify({ player, reason: reasonInput.value.trim() }) });
        input.value = '';
        reasonInput.value = '';
        loadBans(name);
    } catch (e) {
        alert('Failed to ban player: ' + e.message);
    }
}
async function pardonPlayer(name, player) {
    try {
        await apiFetch(`/api/servers/${name}/bans`, { method: 'DELETE', body: JSON.stringify({ player }) });
        loadBans(name);
    } catch (e) {
        alert('Failed to pardon player: ' + e.message);
    }
}
async function restoreBackup(name, filename) {
    if (!confirm('Restore backup ' + filename + '? This will overwrite current data.')) return;
    try {
        await apiFetch(`/api/servers/${name}/backups/${encodeURIComponent(filename)}/restore`, { method: 'POST' });
        alert('Backup restored');
    } catch (e) {
        alert('Failed to restore backup: ' + e.message);
    }
}
async function deleteBackup(name, filename) {
    if (!confirm('Delete backup ' + filename + '?')) return;
    try {
        await apiFetch(`/api/servers/${name}/backups/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        loadBackups(name);
    } catch (e) {
        alert('Failed to delete backup: ' + e.message);
    }
}
async function editFile(name, path) {
    try {
        const data = await apiFetch(`/api/servers/${name}/files/read?path=${encodeURIComponent(path)}`);
        document.getElementById('fileEditorContent').value = data.content;
        document.getElementById('fileEditor').style.display = 'block';
        document.getElementById('fileEditor').dataset.path = path;
    } catch (e) {
        alert('Failed to read file: ' + e.message);
    }
}
async function saveFile(name) {
    const editor = document.getElementById('fileEditor');
    const path = editor.dataset.path;
    const content = document.getElementById('fileEditorContent').value;
    try {
        await apiFetch(`/api/servers/${name}/files/write`, {
            method: 'POST',
            body: JSON.stringify({ path, content })
        });
        editor.style.display = 'none';
    } catch (e) {
        alert('Failed to save file: ' + e.message);
    }
}
async function deleteFile(name, path) {
    if (!confirm('Delete ' + path + '?')) return;
    try {
        await apiFetch(`/api/servers/${name}/files/delete`, {
            method: 'POST',
            body: JSON.stringify({ path })
        });
        loadFiles(name, currentPath);
    } catch (e) {
        alert('Failed to delete file: ' + e.message);
    }
}
async function cloneServer(name) {
    const input = document.getElementById('cloneNameInput');
    const newName = input.value.trim();
    if (!newName) {
        alert('Enter a name for the cloned server');
        return;
    }
    try {
        await apiFetch(`/api/servers/${name}/clone`, {
            method: 'POST',
            body: JSON.stringify({ new_name: newName })
        });
        input.value = '';
        loadServerList();
        alert('Server cloned successfully');
    } catch (e) {
        alert('Failed to clone server: ' + e.message);
    }
}
startBtn.addEventListener('click', () => currentServer && startServer(currentServer));
stopBtn.addEventListener('click', () => currentServer && stopServer(currentServer));
restartBtn.addEventListener('click', () => currentServer && restartServer(currentServer));
backupBtn.addEventListener('click', () => currentServer && backupServer(currentServer));
deleteBtn.addEventListener('click', () => currentServer && deleteServer(currentServer));
savePropertiesBtn.addEventListener('click', () => currentServer && saveProperties(currentServer));
sendCommandBtn.addEventListener('click', () => {
    if (currentServer && commandInput.value.trim()) {
        sendCommand(currentServer, commandInput.value.trim());
    }
});
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && currentServer && commandInput.value.trim()) {
        sendCommand(currentServer, commandInput.value.trim());
    }
});
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});
newServerBtn.addEventListener('click', () => {
    modal.style.display = 'block';
    loadVersionOptions();
});
closeModal.addEventListener('click', () => modal.style.display = 'none');
window.addEventListener('click', (e) => {
    if (e.target === modal) modal.style.display = 'none';
});
async function loadVersionOptions() {
    try {
        const versions = await apiFetch('/api/versions');
        versionSelect.innerHTML = versions.map(v => `<option value="${v.id}">${v.id} (${v.type})</option>`).join('');
    } catch (e) {
        versionSelect.innerHTML = '<option>Failed to load versions</option>';
    }
}
newServerForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = serverNameInput.value.trim();
    const version = versionSelect.value;
    const serverType = serverTypeSelect.value;
    const jvmArgs = jvmArgsInput.value;
    const port = parseInt(portInput.value);
    try {
        await apiFetch('/api/servers', {
            method: 'POST',
            body: JSON.stringify({ name, version, server_type: serverType, jvm_args: jvmArgs, port })
        });
        modal.style.display = 'none';
        loadServerList();
        selectServer(name);
    } catch (err) {
        alert('Failed to create server: ' + err.message);
    }
});
document.getElementById('uploadPluginBtn').addEventListener('click', async () => {
    const input = document.getElementById('pluginFileInput');
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append('plugin', input.files[0]);
    try {
        const res = await fetch(`/api/servers/${currentServer}/plugins`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error((await res.json()).error || 'Upload failed');
        loadPlugins(currentServer);
        input.value = '';
    } catch (e) {
        alert('Failed to upload plugin: ' + e.message);
    }
});
document.getElementById('uploadJarBtn').addEventListener('click', async () => {
    const input = document.getElementById('customJarInput');
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append('jar', input.files[0]);
    try {
        const res = await fetch(`/api/servers/${currentServer}/upload_jar`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error((await res.json()).error || 'Upload failed');
        alert('JAR uploaded');
        input.value = '';
    } catch (e) {
        alert('Failed to upload JAR: ' + e.message);
    }
});
document.getElementById('addOpBtn').addEventListener('click', () => currentServer && addOp(currentServer));
document.getElementById('addWhitelistBtn').addEventListener('click', () => currentServer && addWhitelist(currentServer));
document.getElementById('banBtn').addEventListener('click', () => currentServer && banPlayer(currentServer));
document.getElementById('createBackupBtn').addEventListener('click', () => currentServer && backupServer(currentServer, 'world'));
document.getElementById('createFullBackupBtn').addEventListener('click', () => currentServer && backupServer(currentServer, 'full'));
document.getElementById('saveFileBtn').addEventListener('click', () => currentServer && saveFile(currentServer));
document.getElementById('cancelEditBtn').addEventListener('click', () => {
    document.getElementById('fileEditor').style.display = 'none';
});
document.getElementById('cloneServerBtn').addEventListener('click', () => currentServer && cloneServer(currentServer));
const lastServer = localStorage.getItem('lastServer');
loadServerList();
if (lastServer) {
    selectServer(lastServer).catch(() => {});
}