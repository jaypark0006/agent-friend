/** The visual contract is independent of agents, transports and renderers. */
export const PHASES = Object.freeze(['idle', 'generating', 'tool', 'waiting', 'done', 'error', 'offline']);
export const DEFAULT_ACTIVITY = Object.freeze({ phase: 'idle', tps: 0, shape: 0.5, seed: 1 });
export const clamp = (value, low = 0, high = 1) => Math.min(high, Math.max(low, value));
const smooth = value => { const x = clamp(value); return x * x * (3 - 2 * x); };

/** Strict snapshots: unknown fields/invalid values do not partially update state. */
export function parseActivity(message) {
  if (!message || typeof message !== 'object' || Array.isArray(message)) throw new Error('expected an object');
  const keys = ['phase', 'tps', 'shape', 'seed', 'event', 'event_id'];
  if (Object.keys(message).some(key => !keys.includes(key))) throw new Error('unknown activity field');
  if (!PHASES.includes(message.phase)) throw new Error('invalid phase');
  const tps = message.tps ?? 0;
  const shape = message.shape ?? 0.5;
  const seed = message.seed ?? 1;
  if (!Number.isFinite(tps) || tps < 0 || tps > 10000) throw new Error('tps must be 0..10000');
  if (!Number.isFinite(shape) || shape < 0 || shape > 1) throw new Error('shape must be 0..1');
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > 65535) throw new Error('seed must be an integer 0..65535');
  if (message.event !== undefined && message.event !== 'insight') throw new Error('unsupported event');
  if (message.event !== undefined && (typeof message.event_id !== 'string' || !/^[a-zA-Z0-9._:-]{1,64}$/.test(message.event_id))) {
    throw new Error('insight requires a unique event_id of 1..64 safe characters');
  }
  if (message.event === undefined && message.event_id !== undefined) throw new Error('event_id requires an event');
  return { phase: message.phase, tps, shape, seed,
    ...(message.event ? { event: message.event, event_id: message.event_id } : {}) };
}

/** Pure, deterministic mapping. Zero throughput never invents a task state. */
export function visualTarget(activity) {
  const flow = activity.phase === 'generating' ? clamp(Math.log1p(activity.tps) / Math.log1p(140)) : 0;
  const seedOffset = ((activity.seed * 0.618033988749895) % 1);
  const morphology = clamp(activity.shape * 0.62 + flow * 0.38);
  let pace = 0.12 + flow * 1.65;
  let radius = 0.74 + flow * 0.26;
  let spread = flow;
  let tension = 0.25 + flow * 0.7;
  let warmth = flow * 0.35;
  let finish = 0;
  let visibility = 1;
  if (activity.phase === 'tool') { pace = 0.72; spread = 0.45; tension = 0.65; }
  if (activity.phase === 'waiting') { pace = 0.06; radius = 0.83; tension = 0.08; }
  if (activity.phase === 'idle') { pace = 0.09; radius = 0.70; tension = 0.08; }
  if (activity.phase === 'done') { pace = 0; radius = 0.83; tension = 0.03; finish = 1; warmth = 0.45; }
  if (activity.phase === 'error') { pace = 0.08; radius = 0.72; tension = 0.9; warmth = 1; }
  if (activity.phase === 'offline') { pace = 0.035; radius = 0.65; tension = 0.03; visibility = 0.3; }
  return { flow, morphology, pace, radius, spread, tension, warmth, finish, visibility, seedOffset };
}

export function insightEnvelope(ageSeconds, duration = 3.2) {
  if (ageSeconds < 0 || ageSeconds >= duration) return { charge: 0, opening: 0, light: 0, particles: 0, spread: 0 };
  const p = ageSeconds / duration;
  return {
    charge: smooth(p / 0.19) * (1 - smooth((p - 0.19) / 0.17)),
    opening: smooth((p - 0.18) / 0.27) * (1 - smooth((p - 0.72) / 0.28)),
    light: smooth((p - 0.16) / 0.17) * (1 - smooth((p - 0.61) / 0.39)),
    particles: Math.sin(Math.PI * smooth((p - 0.29) / 0.7)),
    spread: smooth((p - 0.3) / 0.65)
  };
}

/** Continuous, frame-rate-independent response; do not reset the animation clock. */
export function approachVisual(current, target, dtSeconds) {
  const dt = clamp(dtSeconds, 0, 0.1);
  return Object.fromEntries(Object.entries(target).map(([key, value]) => {
    const previous = current[key] ?? value;
    const seconds = value > previous ? 0.32 : 0.80;
    return [key, previous + (value - previous) * (1 - Math.exp(-dt / seconds))];
  }));
}

/** Sliding observation window over actual token counts, not text chunks. */
export class OutputRate {
  constructor(windowMs = 2000) {
    if (!Number.isFinite(windowMs) || windowMs < 250 || windowMs > 10000) throw new Error('windowMs must be 250..10000');
    this.windowMs = windowMs;
    this.samples = [];
    this.startedAt = null;
    this.lastAt = null;
  }
  add(tokenCount, nowMs) {
    if (!Number.isSafeInteger(tokenCount) || tokenCount < 0 || tokenCount > 1000000 || !Number.isFinite(nowMs)) throw new Error('invalid token sample');
    if (this.lastAt !== null && nowMs < this.lastAt) throw new Error('timestamps must be monotonic');
    this.startedAt ??= nowMs;
    this.lastAt = nowMs;
    const bucket = Math.floor(nowMs / 50) * 50;
    const tail = this.samples.at(-1);
    if (tail?.time === bucket) tail.tokens += tokenCount;
    else this.samples.push({ time: bucket, tokens: tokenCount });
    return this.read(nowMs);
  }
  read(nowMs) {
    if (!Number.isFinite(nowMs) || (this.lastAt !== null && nowMs < this.lastAt)) throw new Error('invalid observation time');
    this.samples = this.samples.filter(sample => nowMs - sample.time < this.windowMs);
    if (this.startedAt === null) return 0;
    const seconds = Math.max(0.25, Math.min(this.windowMs, nowMs - this.startedAt) / 1000);
    return this.samples.reduce((sum, sample) => sum + sample.tokens, 0) / seconds;
  }
  reset() { this.samples.length = 0; this.startedAt = null; this.lastAt = null; }
}
