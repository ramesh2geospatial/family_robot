/* FamilyRobot Companion PWA — JavaScript */

const API = '';  // Same origin

// ── Tab Navigation ──────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');

        if (btn.dataset.tab === 'members') loadMembers();
    });
});

// ── Toast ───────────────────────────────────────────────────────

function showToast(msg, duration = 2500) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), duration);
}

// ── Device Control ──────────────────────────────────────────────

async function sendCommand(deviceId, action) {
    try {
        const res = await fetch(API + '/api/device/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_id: deviceId, action: action}),
        });
        const data = await res.json();
        if (res.ok) {
            updateDeviceState(deviceId, data.state);
            showToast(`${deviceId}: ${action.toUpperCase()}`);
        } else {
            showToast('Error: ' + (data.detail || 'Unknown'));
        }
    } catch (e) {
        showToast('Connection error');
    }
}

async function sendLevel(deviceId, value) {
    try {
        const res = await fetch(API + '/api/device/command', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_id: deviceId, action: 'set_level', value: parseInt(value)}),
        });
        const data = await res.json();
        if (res.ok) {
            updateDeviceState(deviceId, data.state);
        }
    } catch (e) { /* silent */ }
}

function updateDeviceState(deviceId, state) {
    const el = document.getElementById('state-' + deviceId);
    if (el) {
        if (state.on !== undefined) {
            el.textContent = state.on ? '🟢 ON' : '🔴 OFF';
        } else if (state.pct !== undefined) {
            el.textContent = `⚡ ${state.pct}%`;
        } else {
            el.textContent = JSON.stringify(state);
        }
    }
}

// ── Family Members ──────────────────────────────────────────────

async function loadMembers() {
    try {
        const res = await fetch(API + '/api/members');
        const data = await res.json();
        const list = document.getElementById('membersList');
        if (!data.members || data.members.length === 0) {
            list.innerHTML = '<p style="color:var(--text-secondary);font-size:0.9rem">No members enrolled yet.</p>';
            return;
        }
        list.innerHTML = data.members.map(m => `
            <div class="member-card">
                <div class="member-avatar">${m.name.charAt(0).toUpperCase()}</div>
                <div class="member-info">
                    <div class="name">${m.name}</div>
                    <div class="role">${m.role} · ${m.language}</div>
                </div>
            </div>
        `).join('');
    } catch (e) {
        showToast('Failed to load members');
    }
}

async function enrollMember() {
    const name = document.getElementById('enrollName').value.trim();
    const role = document.getElementById('enrollRole').value;
    const language = document.getElementById('enrollLang').value;
    if (!name) { showToast('Please enter a name'); return; }

    try {
        const res = await fetch(API + '/api/enroll', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, role, language}),
        });
        if (res.ok) {
            showToast(`Enrolled ${name}!`);
            document.getElementById('enrollName').value = '';
            loadMembers();
        } else {
            const data = await res.json();
            showToast('Error: ' + (data.detail || 'Unknown'));
        }
    } catch (e) {
        showToast('Connection error');
    }
}

// ── Memory ──────────────────────────────────────────────────────

async function searchMemory() {
    const query = document.getElementById('memoryQuery').value.trim();
    if (!query) return;

    try {
        const res = await fetch(API + '/api/memory/search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query, k: 5}),
        });
        const data = await res.json();
        const container = document.getElementById('memoryResults');
        if (!data.results || data.results.length === 0) {
            container.innerHTML = '<p style="color:var(--text-secondary)">No memories found.</p>';
            return;
        }
        container.innerHTML = data.results.map(r => `
            <div class="memory-item">
                ${r.text}
                <div class="score">Score: ${(r.score || 0).toFixed(3)}</div>
            </div>
        `).join('');
    } catch (e) {
        showToast('Search failed');
    }
}

async function storeMemory() {
    const text = document.getElementById('memoryText').value.trim();
    if (!text) { showToast('Please enter something to remember'); return; }

    try {
        const res = await fetch(API + '/api/memory/store', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text, meta: {source: 'pwa'}}),
        });
        if (res.ok) {
            showToast('Memory saved!');
            document.getElementById('memoryText').value = '';
        }
    } catch (e) {
        showToast('Failed to save');
    }
}

// ── Status Polling ──────────────────────────────────────────────

async function pollStatus() {
    try {
        const res = await fetch(API + '/api/status');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('statusText').textContent = data.status;
            document.getElementById('statusBadge').classList.add('connected');
        }
    } catch (e) {
        document.getElementById('statusText').textContent = 'Offline';
        document.getElementById('statusBadge').classList.remove('connected');
    }
}

// Poll every 10s
setInterval(pollStatus, 10000);
pollStatus();

// ── PWA Service Worker ──────────────────────────────────────────

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
