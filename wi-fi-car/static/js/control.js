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
