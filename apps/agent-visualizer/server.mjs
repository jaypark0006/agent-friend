import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { WebSocket, WebSocketServer } from 'ws';
import { parseActivity } from './src/parameters.mjs';

const port = Number(process.env.AGENT_VISUALIZER_PORT ?? 4318);
if (!Number.isSafeInteger(port) || port < 1024 || port > 65535) throw new Error('AGENT_VISUALIZER_PORT must be 1024..65535');
const origin = `http://127.0.0.1:${port}`;
const root = fileURLToPath(new URL('./dist/', import.meta.url));
const files = new Map([['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']], ['/app.css', ['app.css', 'text/css; charset=utf-8']]]);
const sources = new Map();
const viewers = new Set();
const connections = new Set();
const started = Date.now();
let revision = 0;
let dirty = false;

function validHost(request) { return request.headers.host === `127.0.0.1:${port}`; }
function send(socket, message) {
  if (socket.readyState !== WebSocket.OPEN) return;
  if (socket.bufferedAmount > 65536) { socket.close(1013, 'slow consumer'); return; }
  socket.send(JSON.stringify(message));
}
function snapshot() {
  return { type: 'snapshot', version: 1, revision, sources: [...sources].map(([source, item]) => ({
    source, activity: item.activity, online: Boolean(item.owner), updated_at: item.updatedAt
  })) };
}
function disconnect(socket) {
  viewers.delete(socket); connections.delete(socket);
  for (const item of sources.values()) if (item.owner === socket) {
    item.owner = null; item.activity = { ...item.activity, phase: 'offline', tps: 0 };
    item.updatedAt = Date.now(); revision++; dirty = true;
  }
}
const server = createServer(async (request, response) => {
  if (!validHost(request)) { response.writeHead(403); response.end(); return; }
  const route = files.get(request.url);
  if (request.method !== 'GET' || !route) { response.writeHead(404); response.end(); return; }
  try {
    const body = await readFile(join(root, route[0]));
    response.writeHead(200, {
      'Content-Type': route[1], 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': `default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self' ws://127.0.0.1:${port}; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'`
    });
    response.end(body);
  } catch { response.writeHead(503); response.end('Build first: npm run build'); }
});
const wss = new WebSocketServer({ noServer: true, maxPayload: 2048, perMessageDeflate: false });
server.on('upgrade', (request, socket, head) => {
  if (!validHost(request) || (request.headers.origin && request.headers.origin !== origin) ||
      !['/ws/events', '/ws/view'].includes(request.url) || connections.size >= 32) {
    socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); return;
  }
  wss.handleUpgrade(request, socket, head, ws => {
    connections.add(ws); ws.role = request.url === '/ws/view' ? 'viewer' : 'producer';
    ws.alive = true; ws.on('pong', () => { ws.alive = true; });
    ws.on('error', () => { ws.terminate(); });
    ws.on('close', () => disconnect(ws));
    ws.bucketAt = performance.now(); ws.budget = 40;
    if (ws.role === 'viewer') { viewers.add(ws); send(ws, snapshot()); }
    ws.on('message', (data, binary) => {
      if (ws.role !== 'producer') { ws.close(1008, 'viewer is read-only'); return; }
      const now = performance.now();
      ws.budget = Math.min(40, ws.budget + (now - ws.bucketAt) * 0.04); ws.bucketAt = now;
      if (ws.budget < 1) { ws.close(1008, 'maximum 40 parameter updates per second'); return; }
      ws.budget--;
      try {
        if (binary) throw new Error('send JSON parameters, not images or binary');
        const message = JSON.parse(data.toString('utf8'));
        if (!message || typeof message !== 'object' || Array.isArray(message)) throw new Error('expected an object');
        const source = message.source ?? 'default';
        if (typeof source !== 'string' || !/^[a-zA-Z0-9._:-]{1,64}$/.test(source)) throw new Error('invalid source');
        const { source: ignored, ...parameters } = message;
        const activity = parseActivity(parameters);
        const existing = sources.get(source);
        if (existing?.owner && existing.owner !== ws) throw new Error('source already has a connected producer');
        if (!existing && sources.size >= 16) {
          const obsolete = [...sources].find(([, item]) => !item.owner);
          if (!obsolete) throw new Error('maximum 16 sources');
          sources.delete(obsolete[0]);
        }
        const events = existing?.events ?? new Set();
        const event = activity.event;
        const eventId = activity.event_id;
        delete activity.event; delete activity.event_id;
        sources.set(source, { owner: ws, activity, updatedAt: Date.now(), events });
        revision++; dirty = true;
        // A reconnect snapshot never replays an old transient effect.
        if (event && !events.has(eventId)) {
          events.add(eventId);
          if (events.size > 128) events.delete(events.values().next().value);
          for (const viewer of viewers) send(viewer, { type: 'effect', source, event, event_id: eventId, activity });
        }
        send(ws, { type: 'accepted', source, revision });
      } catch (error) { send(ws, { type: 'error', error: error.message }); }
    });
  });
});
const publish = setInterval(() => {
  const now = Date.now();
  for (const item of sources.values()) if (item.owner && now - item.updatedAt > 10000 && item.activity.phase !== 'offline') {
    item.activity = { ...item.activity, phase: 'offline', tps: 0 }; revision++; dirty = true;
  }
  if (dirty) { dirty = false; const value = snapshot(); for (const viewer of viewers) send(viewer, value); }
}, 100);
const heartbeat = setInterval(() => {
  for (const ws of connections) { if (!ws.alive) ws.terminate(); else { ws.alive = false; ws.ping(); } }
}, 10000);
function shutdown() {
  clearInterval(publish); clearInterval(heartbeat);
  for (const ws of connections) ws.terminate();
  wss.close(); server.close();
}
process.once('SIGINT', shutdown); process.once('SIGTERM', shutdown);
server.on('error', error => { console.error(error.message); shutdown(); process.exitCode = 1; });
server.listen(port, '127.0.0.1', () => console.log(JSON.stringify({ app: 'agent-visualizer', version: '0.1.0', started, url: origin,
  events: `ws://127.0.0.1:${port}/ws/events`, note: 'Parameters only. No agent is started and no device frame is sent.' })));
