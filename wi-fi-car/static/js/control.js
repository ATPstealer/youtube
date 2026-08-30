const speedRange = document.getElementById('speed-range');
const speedDisplay = document.getElementById('speed-display');

speedRange.oninput = function() {
    speedDisplay.innerText = this.value;
}

function sendCommand(action, direction) {
    const speed = speedRange.value;
    fetch('/control', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action, speed, direction }),
    });
}

const buttons = {
    'btn-up': { action: 'move', direction: 'f' },
    'btn-down': { action: 'move', direction: 'b' },
    'btn-left': { action: 'turn', direction: 'l' },
    'btn-right': { action: 'turn', direction: 'r' },
    'btn-stop': { action: 'stop', direction: '' }
};

Object.keys(buttons).forEach(id => {
    const btn = document.getElementById(id);
    const config = buttons[id];
    
    // Support both mouse and touch events
    ['mousedown', 'touchstart'].forEach(evt => {
        btn.addEventListener(evt, (e) => {
            e.preventDefault();
            sendCommand(config.action, config.direction);
        });
    });
    
    // Stop when released
    if (id !== 'btn-stop') {
        ['mouseup', 'touchend'].forEach(evt => {
            btn.addEventListener(evt, (e) => {
                e.preventDefault();
                sendCommand('stop', '');
            });
        });
    }
});

// --- WASD Control Logic ---
const keyMap = {
    'w': 'btn-up',
    's': 'btn-down',
    'a': 'btn-left',
    'd': 'btn-right',
    'W': 'btn-up',
    'S': 'btn-down',
    'A': 'btn-left',
    'D': 'btn-right'
};

let activeKeyStack = [];

// --- Speed adjustment via [ and ] ---
const activeSpeedKeys = new Set();

function adjustSpeed(delta) {
    const newValue = Math.max(0, Math.min(100, parseInt(speedRange.value, 10) + delta));
    speedRange.value = newValue;
    speedDisplay.innerText = newValue;

    // If currently moving/turning, re-send the active command so the new speed applies immediately
    if (activeKeyStack.length > 0) {
        const lastKey = activeKeyStack[activeKeyStack.length - 1];
        const lastBtnId = keyMap[lastKey];
        const config = buttons[lastBtnId];
        sendCommand(config.action, config.direction);
    }
}

window.addEventListener('keydown', (e) => {
    const key = e.key.toLowerCase();
    const btnId = keyMap[e.key];
    if (btnId && !activeKeyStack.includes(key)) {
        activeKeyStack.push(key);
        const config = buttons[btnId];
        document.getElementById(btnId).classList.add('active');
        sendCommand(config.action, config.direction);
    }
    if (e.key === ' ') { // Space for stop
        sendCommand('stop', '');
        document.getElementById('btn-stop').classList.add('active');
    }
    if ((e.key === '[' || e.key === ']') && !activeSpeedKeys.has(e.key)) {
        activeSpeedKeys.add(e.key);
        adjustSpeed(e.key === ']' ? 10 : -10);
    }
});

window.addEventListener('keyup', (e) => {
    const key = e.key.toLowerCase();
    const btnId = keyMap[e.key];
    if (btnId) {
        activeKeyStack = activeKeyStack.filter(k => k !== key);
        document.getElementById(btnId).classList.remove('active');
        
        if (activeKeyStack.length > 0) {
            // Re-send command for the last pressed key that is still held
            const lastKey = activeKeyStack[activeKeyStack.length - 1];
            const lastBtnId = keyMap[lastKey];
            const config = buttons[lastBtnId];
            sendCommand(config.action, config.direction);
        } else {
            sendCommand('stop', '');
        }
    }
    if (e.key === ' ') {
        document.getElementById('btn-stop').classList.remove('active');
    }
    if (e.key === '[' || e.key === ']') {
        activeSpeedKeys.delete(e.key);
    }
});

// --- Log Panel Logic ---
const logBox = document.getElementById('log-box');
const logToggle = document.getElementById('log-toggle');
const logIndicator = document.getElementById('log-indicator');

logToggle.addEventListener('click', () => {
    const isHidden = logBox.classList.toggle('hidden');
    logIndicator.innerText = isHidden ? '▼' : '▲';
    if (!isHidden) {
        updateLogs();
    }
});

function updateLogs() {
    if (logBox.classList.contains('hidden')) return;

    fetch('/logs')
        .then(response => response.json())
        .then(logs => {
            logBox.innerHTML = logs.map(line => `<div class="log-entry">${line}</div>`).join('');
            logBox.scrollTop = logBox.scrollHeight;
        })
        .catch(err => console.error('Error fetching logs:', err));
}

// Update logs every 2 seconds if the panel is open
setInterval(updateLogs, 2000);
