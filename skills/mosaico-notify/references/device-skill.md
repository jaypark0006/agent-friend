---
name: mosaico-screen
description: ESP-Mosaico desktop companion screen with multi-agent progress dashboard, status messages, screenshots, and sensor telemetry.
---

# Mosaico Screen Companion Skill

This device is an interactive 480x480 companion screen on your local network.
Autonomous agents can report task progress, display alerts, stream images, and query telemetry.

## 1. Multi-Agent Progress Dashboard & Pipeline (POST /api/widget)

Report step-by-step progress for any background agent or task.
The screen automatically pipelines active tasks and pushes completed items up into scrollable history (drag finger down on screen to pull down completed history).

### Request Format (JSON)
```http
POST /api/widget HTTP/1.1
Content-Type: application/json

{
  "id": "coder-turn-3",         // Unique task ID chosen by the agent (not shown)
  "agent": "Codex",             // Agent display name
  "session": "Backend",         // Optional session or project name
  "title": "Compile firmware",  // The task
  "status": "Compiling...",     // Current action / status text
  "progress": 68,               // 0..100 integer (-1 to hide progress bar)
  "badge": "RUNNING",          // Status pill (e.g. IDLE, RUNNING, DONE)
  "color": "#39e69d",          // Theme hex color (green, blue, orange, etc.)
  "action": {                   // Optional: Request physical touch confirmation from user
    "type": "confirm",
    "options": ["Approve", "Cancel"]
  },
  "done": false,                // Set true when task finishes (displays DONE)
  "delete": false,              // Set true to remove agent from dashboard
  "show": true                  // Switch display to widget page immediately
}
```

### Python Example
```python
from urllib.request import Request, urlopen
import json

payload = {
    "id": "coder-turn-3",
    "agent": "Codex",
    "session": "Backend",
    "title": "Compile firmware",
    "status": "Compiling firmware artifacts...",
    "progress": 68,
    "color": "#39e69d",
    "show": True
}
req = Request("http://{{DEVICE_IP}}/api/widget",
              data=json.dumps(payload).encode(),
              headers={"Content-Type": "application/json"})
urlopen(req, timeout=3)
```

### cURL Example
```sh
curl -X POST http://{{DEVICE_IP}}/api/widget \
  -H "Content-Type: application/json" \
  -d '{"id":"test-agent","agent":"Codex","session":"Backend","title":"Run tests","status":"All 42 tests passed","progress":100,"badge":"DONE","color":"#39e69d"}'
```

## 2. Text Message Feed (POST /api/text)

Post messages to the swipeable text message history page:
```sh
curl -X POST http://{{DEVICE_IP}}/api/text \
  -H "Content-Type: application/json" \
  -d '{"text":"Deployment successful!","font_size":32,"align":"left"}'
```

## 3. Screen Capture (GET /api/screenshot)

Fetch the real-time rendered display frame (BMP format, 480x480 RGB565):
```sh
curl -o screen.bmp http://{{DEVICE_IP}}/api/screenshot
```

## 4. Query Dashboard & Device Status
- `GET /api/widget`: Returns active agent list and counts.
- `GET /api/status`: Returns device uptime, Wi-Fi RSSI, memory, and display state.
- `GET /api/sensors`: Returns IMU orientation, battery level, buttons, and peripherals.
