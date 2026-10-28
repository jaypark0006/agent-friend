import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { DEFAULT_ACTIVITY, parseActivity, visualTarget, approachVisual, insightEnvelope } from './parameters.mjs';

export function createRenderer(canvas, { onError = () => {} } = {}) {
  const screen = canvas.parentElement;
  const settings = { radiance: 0.7 };
  let activity = { ...DEFAULT_ACTIVITY };
  let visual = visualTarget(activity);
  let insightAt = -Infinity;
  const eventIds = new Set();
  const state = { time: 0, spin: 0, paused: matchMedia('(prefers-reduced-motion: reduce)').matches };
  let alive = true, ready = false, visible = true;
  let drawStill = () => {};
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'low-power' });
  renderer.setPixelRatio(1); renderer.setSize(480, 480, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 40);
  camera.position.set(0, 0, 5.4);

  // Broad cool studio reflections, a warm edge, and dark gaps between them.
  const studio = new THREE.Scene(); studio.background = new THREE.Color('#0b101c');
  const lampGeometry = new THREE.PlaneGeometry(1, 1);
  const lampMaterials = [];
  function lamp(position, size, rgb, energy) {
    const color = new THREE.Color(rgb).multiplyScalar(energy);
    const material = new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide });
    lampMaterials.push(material);
    const panel = new THREE.Mesh(lampGeometry, material);
    panel.position.set(...position); panel.scale.set(size[0], size[1], 1); panel.lookAt(0, 0, 0);
    studio.add(panel);
  }
  lamp([-3, 3, 3], [2.2, 6], '#dcefff', 7);
  lamp([4, 0.5, 2], [0.7, 5], '#abc7ff', 6);
  lamp([0, -4, 1], [5, 0.45], '#f1b785', 4);
  lamp([1, 2, -4], [3, 3], '#d2aeed', 5);
  lamp([-4, -0.5, -2], [1, 2.5], '#a4dccf', 2.8);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const environment = pmrem.fromScene(studio, 0.035);
  scene.environment = environment.texture;
  pmrem.dispose(); lampGeometry.dispose(); lampMaterials.forEach(material => material.dispose());
  const keyLight = new THREE.DirectionalLight('#edf3ff', 2.6);
  keyLight.position.set(-3, 4, 5); scene.add(keyLight);
  const warmLight = new THREE.PointLight('#ffc98e', 0, 10, 2);
  warmLight.position.set(0.1, 0.1, 1.5); scene.add(warmLight);

  const uniforms = { uTime: { value: 0 }, uOpen: { value: 0 }, uFinish: { value: 0 }, uFlow: { value: 0 }, uMorph: { value: 0.5 }, uTension: { value: 0.25 }, uSeed: { value: 0 } };
  const surfaceCode = `
    uniform float uTime;
    uniform float uOpen;
    uniform float uFinish;
    uniform float uFlow;
    uniform float uMorph;
    uniform float uTension;
    uniform float uSeed;
    const float TAU = 6.28318530718;
    vec3 spine(float u) {
      float a = u * TAU;
      float phase = uTime * 0.24 + uSeed * TAU;
      float waves = mix(cos(3.0 * a + phase), cos(7.0 * a - phase), uMorph);
      float r = 0.76 + waves * (0.05 + uTension * 0.25);
      vec3 calm = vec3(r * cos(a), r * sin(a), 0.09 * sin(2.0 * a + phase));
      float braidRadius = 0.66 + 0.31 * cos(3.0 * a + phase * 0.4);
      vec3 braid = vec3(braidRadius * cos(2.0 * a), braidRadius * sin(2.0 * a), 0.38 * sin(3.0 * a + phase * 0.4));
      vec3 flower = vec3((0.92 + waves * 0.23) * cos(a), (0.92 + waves * 0.23) * sin(a),
        (0.15 + uTension * 0.24) * sin(5.0 * a + phase));
      float curl = smoothstep(0.06, 0.50, uMorph);
      float unfurl = smoothstep(0.50, 1.0, uMorph);
      vec3 live = mix(mix(calm, braid, curl), flower, unfurl);
      live.z += uFlow * 0.07 * sin(9.0 * a - phase * 2.0);
      vec3 opened = vec3((1.10 + 0.15 * cos(5.0 * a)) * cos(a), (1.10 + 0.15 * cos(5.0 * a)) * sin(a), 0.21 * sin(3.0 * a + phase));
      vec3 sealed = vec3(0.8 * cos(a), 0.8 * sin(a), 0.07 * sin(2.0 * a));
      return mix(mix(live, opened, uOpen), sealed, uFinish);
    }
    vec3 surface(vec2 param) {
      float u = param.x;
      float v = param.y * TAU;
      vec3 c = spine(u);
      vec3 delta = spine(u + 0.0005) - spine(u - 0.0005);
      vec3 t = normalize(delta + vec3(0.000001, 0.0, 0.0));
      vec3 axis = abs(t.z) > 0.98 ? vec3(0.0, 1.0, 0.0) : vec3(0.0, 0.0, 1.0);
      vec3 n = normalize(cross(t, axis));
      vec3 b = cross(t, n);
      float radius = mix(0.23, 0.072, uFlow);
      radius *= 1.0 + 0.22 * sin(3.0 * u * TAU - uTime * 0.7);
      radius = mix(mix(radius, 0.075, uOpen), 0.20, uFinish);
      float twist = v + u * TAU * 3.0 + uTime * 0.12;
      float width = 1.0 + uFlow * 1.30 + uOpen * 0.35;
      float depth = mix(0.92, 0.37, max(uFlow, uOpen));
      return c + n * cos(twist) * radius * width + b * sin(twist) * radius * depth;
    }
  `;
  const surfaceMaterial = new THREE.MeshPhysicalMaterial({
    color: '#aebace', metalness: 0.94, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.13,
    iridescence: 0.55, iridescenceIOR: 1.35, iridescenceThicknessRange: [180, 380], envMapIntensity: 1.15,
    emissive: '#ffae52', emissiveIntensity: 0
  });
  surfaceMaterial.onBeforeCompile = shader => {
    Object.assign(shader.uniforms, uniforms);
    shader.vertexShader = shader.vertexShader.replace('#include <common>', '#include <common>\n' + surfaceCode);
    shader.vertexShader = shader.vertexShader.replace('#include <beginnormal_vertex>', `
      vec3 here = surface(uv);
      vec3 du = surface(uv + vec2(0.0003, 0.0)) - surface(uv - vec2(0.0003, 0.0));
      vec3 dv = surface(uv + vec2(0.0, 0.0003)) - surface(uv - vec2(0.0, 0.0003));
      vec3 objectNormal = normalize(cross(dv, du));
      #ifdef USE_TANGENT
        vec3 objectTangent = normalize(du);
      #endif
    `);
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', 'vec3 transformed = here;');
  };
  surfaceMaterial.customProgramCacheKey = () => 'mosaico-parametric-field-v1';
  function parametricGrid(columns, rows) {
    const positions = [], uv = [], normals = [], indices = [];
    for (let u = 0; u <= columns; u++) for (let v = 0; v <= rows; v++) {
      positions.push(0, 0, 0); normals.push(0, 0, 1); uv.push(u / columns, v / rows);
      if (u < columns && v < rows) {
        const a = u * (rows + 1) + v, b = a + rows + 1;
        indices.push(a, a + 1, b, a + 1, b + 1, b);
      }
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    geometry.setIndex(indices); return geometry;
  }
  const surfaceGeometry = parametricGrid(288, 28);
  const sculpture = new THREE.Mesh(surfaceGeometry, surfaceMaterial); sculpture.frustumCulled = false;
  const body = new THREE.Group(); body.add(sculpture); scene.add(body);
  const beadGeometry = new THREE.SphereGeometry(1, 24, 16);
  const beadMaterial = new THREE.MeshPhysicalMaterial({ color: '#b6c7df', metalness: 0.96,
    roughness: 0.14, clearcoat: 1, iridescence: 0.6, iridescenceIOR: 1.35 });
  const beads = [];
  for (let i = 0; i < 5; i++) { const bead = new THREE.Mesh(beadGeometry, beadMaterial); scene.add(bead); beads.push(bead); }

  // A finite release of sparks, rather than a permanently busy background.
  const seeds = new Float32Array(160 * 3);
  for (let i = 0; i < 160; i++) {
    seeds[i * 3] = ((i * 0.61803398875) % 1) * Math.PI * 2;
    seeds[i * 3 + 1] = ((i * 0.754877666) % 1);
    seeds[i * 3 + 2] = ((i * 0.56984029) % 1);
  }
  const sparkGeometry = new THREE.BufferGeometry();
  sparkGeometry.setAttribute('position', new THREE.BufferAttribute(seeds, 3));
  const sparkMaterial = new THREE.ShaderMaterial({
    uniforms: { uSpread: { value: 0 }, uAlpha: { value: 0 } },
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    vertexShader: `
      uniform float uSpread; varying float vAlpha;
      void main() {
        float a = position.x + uSpread * (0.4 + position.z);
        float r = 0.55 + uSpread * (0.4 + position.y * 0.95);
        vec3 p = vec3(cos(a) * r, sin(a) * r, (position.z - 0.5) * uSpread * 1.2);
        p.y += uSpread * uSpread * 0.20;
        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_Position = projectionMatrix * mv;
        gl_PointSize = (1.5 + position.z * 2.0) * 4.0 / max(1.0, -mv.z);
        vAlpha = 0.25 + position.y * 0.75;
      }
    `,
    fragmentShader: `
      uniform float uAlpha; varying float vAlpha;
      void main() {
        float d = length(gl_PointCoord - 0.5) * 2.0;
        if (d > 1.0) discard;
        gl_FragColor = vec4(vec3(1.8, 0.95, 0.35), (1.0 - smoothstep(0.15, 1.0, d)) * uAlpha * vAlpha);
      }
    `
  });
  const sparks = new THREE.Points(sparkGeometry, sparkMaterial); sparks.frustumCulled = false; scene.add(sparks);
  const atmosphereMaterial = new THREE.ShaderMaterial({
    uniforms: { uBase: { value: new THREE.Color() }, uHaze: { value: new THREE.Color() }, uHeat: { value: 0 } },
    depthWrite: false, depthTest: false,
    vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.9999, 1.0); }`,
    fragmentShader: `
      varying vec2 vUv; uniform vec3 uBase; uniform vec3 uHaze; uniform float uHeat;
      void main() {
        vec2 p = vUv - 0.5;
        float haze = exp(-dot(p * vec2(1.0, 1.2), p * vec2(1.0, 1.2)) * 10.0);
        float center = exp(-dot(p, p) * 32.0);
        vec3 color = mix(uBase, uHaze, haze * 0.32);
        color += vec3(0.25, 0.085, 0.018) * center * uHeat;
        float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898,78.233))) * 43758.5453) - 0.5;
        gl_FragColor = vec4(max(vec3(0.0), color + grain * 0.0015), 1.0);
      }
    `
  });
  const atmosphereGeometry = new THREE.PlaneGeometry(2, 2);
  const atmosphere = new THREE.Mesh(atmosphereGeometry, atmosphereMaterial);
  atmosphere.frustumCulled = false; atmosphere.renderOrder = -100; scene.add(atmosphere);
  function applyTheme() {
    const probe = document.createElement('span'); probe.hidden = true; screen.appendChild(probe);
    probe.style.color = 'var(--ml-bg)'; atmosphereMaterial.uniforms.uBase.value.set(getComputedStyle(probe).color);
    probe.style.color = 'var(--ml-haze)'; atmosphereMaterial.uniforms.uHaze.value.set(getComputedStyle(probe).color);
    probe.remove(); if (ready) drawStill();
  }
  applyTheme();
  const target = new THREE.WebGLRenderTarget(480, 480, { type: THREE.HalfFloatType }); target.samples = 4;
  const composer = new EffectComposer(renderer, target);
  const renderPass = new RenderPass(scene, camera);
  const bloom = new UnrealBloomPass(new THREE.Vector2(480, 480), 0.30, 0.45, 1.15);
  const output = new OutputPass();
  composer.addPass(renderPass); composer.addPass(bloom); composer.addPass(output); composer.setSize(480, 480);
  const silver = new THREE.Color('#aebace'), gold = new THREE.Color('#f1c995');
  const tilt = new THREE.Vector2();
  screen.addEventListener('pointermove', event => {
    const rect = screen.getBoundingClientRect();
    tilt.set(((event.clientX - rect.left) / rect.width - 0.5) * 0.18, ((event.clientY - rect.top) / rect.height - 0.5) * 0.18);
    if (state.paused) drawStill();
  });
  screen.addEventListener('pointerleave', () => { tilt.set(0, 0); if (state.paused) drawStill(); });

  function render(dt, instant = false) {
    const target = visualTarget(activity);
    visual = instant ? target : approachVisual(visual, target, dt);
    const effect = insightEnvelope((performance.now() - insightAt) / 1000);
    const activeEffect = !['done', 'error', 'waiting', 'offline'].includes(activity.phase);
    if (!activeEffect) for (const key of Object.keys(effect)) effect[key] = 0;
    state.time += dt * visual.pace;
    state.spin += dt * visual.pace * 0.13 * (1 - visual.finish);
    uniforms.uTime.value = state.time;
    uniforms.uOpen.value = effect.opening;
    uniforms.uFinish.value = visual.finish;
    uniforms.uFlow.value = visual.flow;
    uniforms.uMorph.value = visual.morphology;
    uniforms.uTension.value = visual.tension;
    uniforms.uSeed.value = visual.seedOffset;
    const warmth = Math.min(1, visual.warmth + effect.light * 0.85);
    surfaceMaterial.color.copy(silver).lerp(gold, warmth);
    surfaceMaterial.roughness = 0.24 - visual.flow * 0.12;
    surfaceMaterial.emissiveIntensity = effect.light * 0.35 * settings.radiance;
    surfaceMaterial.iridescence = 0.35 + visual.flow * 0.5 - effect.light * 0.3;
    surfaceMaterial.envMapIntensity = visual.visibility * 1.15;
    body.scale.setScalar(visual.radius * (1 - effect.charge * 0.26));
    body.rotation.set(0.28 + Math.sin(state.time * 0.23) * 0.20 + tilt.y,
      0.15 + Math.sin(state.time * 0.19) * 0.28 + tilt.x, -0.26 + state.spin);
    body.position.y = Math.sin(state.time * 0.7) * 0.03 * (1 - visual.finish);
    beads.forEach((bead, i) => {
      const a = i * Math.PI * 2 / 5 + state.time * (0.18 + i * 0.012);
      const r = (1.18 + i * 0.06) * (0.75 + visual.spread * 0.38);
      bead.position.set(Math.cos(a) * r, Math.sin(a) * r * 0.75, Math.sin(a + 1) * 0.55 - 0.15);
      const size = (0.018 + (i % 3) * 0.012) * (1 - visual.finish) * visual.visibility;
      bead.scale.set(size, size * (1 + visual.flow * 2), size);
    });
    warmLight.intensity = effect.light * 6 * settings.radiance;
    atmosphereMaterial.uniforms.uHeat.value = effect.light * settings.radiance;
    bloom.strength = 0.19 + visual.flow * 0.15 + effect.light * settings.radiance * 0.6;
    sparkMaterial.uniforms.uSpread.value = effect.spread;
    sparkMaterial.uniforms.uAlpha.value = effect.particles * settings.radiance;
    sparks.visible = effect.particles > 0.001;
    composer.render();
  }
  drawStill = () => { if (ready && alive) render(0, state.paused); };
  const visibility = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; });
  visibility.observe(screen);
  const motionPreference = matchMedia('(prefers-reduced-motion: reduce)');
  function reduceMotion(event) { if (event.matches) { state.paused = true; drawStill(); } }
  motionPreference.addEventListener('change', reduceMotion);
  function dispose() {
    if (!alive) return;
    alive = false; renderer.setAnimationLoop(null); visibility.disconnect();
    motionPreference.removeEventListener('change', reduceMotion);
    [surfaceGeometry, beadGeometry, sparkGeometry, atmosphereGeometry].forEach(item => item.dispose());
    [surfaceMaterial, beadMaterial, sparkMaterial, atmosphereMaterial].forEach(item => item.dispose());
    environment.dispose(); bloom.dispose(); output.dispose(); composer.dispose(); renderer.dispose();
  }
  canvas.addEventListener('webglcontextlost', event => { event.preventDefault(); dispose(); onError('WebGL context lost; reload the page.'); });
  window.addEventListener('pagehide', dispose, { once: true });
  ready = true;
  render(0, true);
  let previous = performance.now();
  renderer.setAnimationLoop(now => {
    if (!canvas.isConnected) { dispose(); return; }
    const dt = Math.min((now - previous) / 1000, 0.05); previous = now;
    if (!alive || document.hidden || !visible || state.paused) return;
    try { render(dt); } catch { dispose(); onError('Rendering stopped; reload the page.'); }
  });
  return {
    update(value) {
      const parsed = parseActivity(value);
      activity = parsed;
      if (parsed.event && !eventIds.has(parsed.event_id)) {
        eventIds.add(parsed.event_id);
        if (eventIds.size > 128) eventIds.delete(eventIds.values().next().value);
        insightAt = performance.now() - (state.paused ? 1450 : 0);
      }
      if (['done', 'waiting', 'error', 'offline'].includes(parsed.phase)) insightAt = -Infinity;
      drawStill();
    },
    setPaused(value) { state.paused = Boolean(value); drawStill(); return state.paused; },
    get paused() { return state.paused; },
    dispose
  };
}
