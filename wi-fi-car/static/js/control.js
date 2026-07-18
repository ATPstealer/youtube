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
