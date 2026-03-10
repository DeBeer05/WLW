// index.js - WebSocket client for Smart-IoT-Gateway-Scan card

// Replace with your actual websocket server address/port
const ws = new WebSocket('ws://10.245.13.18:8765');
let wsLines = [];
ws.onmessage = function(event) {
  const output = document.getElementById('websocket-output');
  if (output) {
    // Force width to 560px via JS
    output.style.width = '560px';
    output.style.minWidth = '560px';
    output.style.maxWidth = '560px';
    // Split incoming message into lines and add to array
    wsLines = wsLines.concat(event.data.split(/\r?\n/));
    // Limit to last 200 lines in memory
    if (wsLines.length > 200) {
      wsLines = wsLines.slice(wsLines.length - 200);
    }
    // Always show exactly 11 lines
    const visibleLines = wsLines.slice(-12);
    output.innerHTML = visibleLines.join('<br>');
    output.scrollTop = output.scrollHeight;
  }
};
ws.onerror = function() {
  const output = document.getElementById('websocket-output');
  if (output) {
    output.style.width = '560px';
    output.style.minWidth = '560px';
    output.style.maxWidth = '560px';
    output.innerHTML = 'WebSocket connection error.';
  }
};
