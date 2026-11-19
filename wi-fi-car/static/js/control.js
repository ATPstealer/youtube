const UI = window.CAR_UI;
const $ = id => document.getElementById(id);

function post(url, body) {
    return fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    }).catch(() => {});
}

// --- Driving ---
const speedRange = $('speed-range');
const speedDisplay = $('speed-display');

const buttons = {
    'btn-up': { action: 'move', direction: 'f' },
    'btn-down': { action: 'move', direction: 'b' },
    'btn-left': { action: 'turn', direction: 'l' },
    'btn-right': { action: 'turn', direction: 'r' },
    'btn-stop': { action: 'stop', direction: '' },
};

// e.code, so it works with any keyboard layout (also Russian)
const keyMap = { KeyW: 'btn-up', KeyS: 'btn-down', KeyA: 'btn-left', KeyD: 'btn-right' };

let activeKeys = [];      // held drive keys, last one wins
let pointerBtn = null;    // d-pad button held with mouse/touch

function sendCommand(action, direction) {
    post('/control', { action, speed: speedRange.value, direction });
}

function activeButton() {
    if (activeKeys.length) return keyMap[activeKeys[activeKeys.length - 1]];
    return pointerBtn;
}

// Re-send the current move so a new speed applies immediately
function resendActive() {
    const id = activeButton();
    if (id) sendCommand(buttons[id].action, buttons[id].direction);
}

function releaseAll() {
    if (activeKeys.length || pointerBtn) sendCommand('stop', '');
    activeKeys = [];
    pointerBtn = null;
    document.querySelectorAll('.btn.active').forEach(b => b.classList.remove('active'));
}

speedRange.oninput = () => { speedDisplay.innerText = speedRange.value; };
speedRange.onchange = resendActive;

function adjustSpeed(delta) {
    speedRange.value = Math.max(0, Math.min(100, parseInt(speedRange.value, 10) + delta));
    speedDisplay.innerText = speedRange.value;
    resendActive();
}

// D-pad: pointer capture guarantees the release event even if the
// finger/cursor slides off the button, so the car never keeps driving.
Object.entries(buttons).forEach(([id, cmd]) => {
    const btn = $(id);
    btn.addEventListener('pointerdown', e => {
        e.preventDefault();
        btn.setPointerCapture(e.pointerId);
        btn.classList.add('active');
        sendCommand(cmd.action, cmd.direction);
        if (cmd.action !== 'stop') pointerBtn = id;
    });
    const release = () => {
        if (!activeKeys.some(k => keyMap[k] === id)) btn.classList.remove('active');
        if (pointerBtn === id) {
            pointerBtn = null;
            if (activeKeys.length) resendActive(); else sendCommand('stop', '');
        }
    };
    btn.addEventListener('pointerup', release);
    btn.addEventListener('pointercancel', release);
    btn.addEventListener('lostpointercapture', release);
    btn.addEventListener('contextmenu', e => e.preventDefault());
});

window.addEventListener('keydown', e => {
    const btnId = keyMap[e.code];
    if (btnId) {
        e.preventDefault();
        if (!activeKeys.includes(e.code)) {
            activeKeys.push(e.code);
            $(btnId).classList.add('active');
            resendActive();
        }
    } else if (e.code === 'Space') {
        e.preventDefault();
        if (!e.repeat) {
            activeKeys = [];
            document.querySelectorAll('.btn.active').forEach(b => b.classList.remove('active'));
            $('btn-stop').classList.add('active');
            sendCommand('stop', '');
        }
    } else if ((e.code === 'BracketLeft' || e.code === 'BracketRight') && !e.repeat) {
        adjustSpeed(e.code === 'BracketRight' ? UI.speed_step : -UI.speed_step);
    } else if (e.code === 'KeyF' && !e.repeat && fsRequest) {
        toggleFullscreen();
    }
});

window.addEventListener('keyup', e => {
    const btnId = keyMap[e.code];
    if (btnId) {
        activeKeys = activeKeys.filter(k => k !== e.code);
        if (pointerBtn !== btnId) $(btnId).classList.remove('active');
        if (activeKeys.length || pointerBtn) resendActive(); else sendCommand('stop', '');
    } else if (e.code === 'Space') {
        e.preventDefault();
        $('btn-stop').classList.remove('active');
    }
});

// Switching tab/window while a key is held never delivers keyup: stop instead
window.addEventListener('blur', releaseAll);
document.addEventListener('visibilitychange', () => { if (document.hidden) releaseAll(); });

// Clicking the top/slider buttons must not leave them focused, or Space would click them
document.querySelectorAll('.icon-btn, .mini').forEach(b =>
    b.addEventListener('pointerdown', e => e.preventDefault()));

// --- Trim (straight-line correction for wheels of different size) ---
const trimRange = $('trim-range');
const trimDisplay = $('trim-display');

function showTrim(value) {
    trimDisplay.innerText = (value > 0 ? '+' : '') + Number(value).toFixed(1);
}

function sendTrim() {
    post('/trim', { trim: parseFloat(trimRange.value) });
}

trimRange.oninput = () => showTrim(trimRange.value);
trimRange.onchange = sendTrim;   // on release; applies immediately, saved on the car
$('trim-reset').onclick = () => {
    trimRange.value = 0;
    showTrim(0);
    sendTrim();
};

// --- Live status ---
const statusChip = $('status-chip');
const statusText = $('status');
let trimLoaded = false;

function updateStatus() {
    fetch('/status')
        .then(r => r.json())
        .then(s => {
            if (!trimLoaded) {
                trimRange.value = s.trim;
                showTrim(s.trim);
                trimLoaded = true;
            }
            statusText.innerText =
                `L ${s.l_ticks} · R ${s.r_ticks} · err ${s.error} · PWM ${s.l_pwm}/${s.r_pwm} · ${s.sync}`;
            const state = s.sync.startsWith('fault') ? 'fault' : s.sync;
            statusChip.className = `glass status ${state}`;
        })
        .catch(() => {
            statusText.innerText = 'car offline';
            statusChip.className = 'glass status fault';
        });
}

updateStatus();
setInterval(updateStatus, UI.status_poll_ms);

// --- Video: reconnect if the stream drops ---
const video = $('video');
const noVideo = $('no-video');
video.addEventListener('load', () => noVideo.classList.add('hidden'));
video.addEventListener('error', () => {
    noVideo.classList.remove('hidden');
    setTimeout(() => { video.src = `${video.dataset.src}?t=${Date.now()}`; }, 2000);
});

// --- Logs ---
const logPanel = $('log-panel');
const logToggle = $('log-toggle');

logToggle.onclick = () => {
    const open = !logPanel.classList.toggle('hidden');
    logToggle.classList.toggle('on', open);
    if (open) updateLogs();
};

function updateLogs() {
    if (logPanel.classList.contains('hidden')) return;
    fetch('/logs')
        .then(r => r.json())
        .then(logs => {
            logPanel.replaceChildren(...logs.map(line => {
                const div = document.createElement('div');
                div.className = 'log-entry';
                div.textContent = line;
                return div;
            }));
            logPanel.scrollTop = logPanel.scrollHeight;
        })
        .catch(() => {});
}

setInterval(updateLogs, UI.log_poll_ms);

// --- Fullscreen: button, F key, double-click on video; Esc exits natively ---
const fsBtn = $('fullscreen-toggle');
const root = document.documentElement;
const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement;
const fsRequest = root.requestFullscreen || root.webkitRequestFullscreen;
const fsExit = document.exitFullscreen || document.webkitExitFullscreen;

function toggleFullscreen() {
    const call = fsElement() ? () => fsExit.call(document) : () => fsRequest.call(root);
    try { Promise.resolve(call()).catch(() => {}); } catch (e) {}
}

function onFullscreenChange() {
    const on = !!fsElement();
    fsBtn.textContent = on ? '\u2715 Exit fullscreen' : '\u26F6';
    fsBtn.title = on ? 'Exit fullscreen (Esc or F)' : 'Fullscreen (F)';
    fsBtn.classList.toggle('on', on);
    releaseAll();   // a key held during the switch can lose its keyup
}

if (fsRequest) {
    fsBtn.onclick = toggleFullscreen;
    video.addEventListener('dblclick', toggleFullscreen);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('webkitfullscreenchange', onFullscreenChange);
    onFullscreenChange();
} else {
    fsBtn.classList.add('hidden');   // e.g. iPhone Safari has no fullscreen API for pages
}
