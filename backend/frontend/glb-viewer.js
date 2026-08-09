/**
 * Visualizador GLB mínimo em WebGL, sem dependência externa.
 *
 * As malhas do Hunyuan3D saem só com POSITION — sem normais, sem UV. Uma biblioteca
 * completa renderizaria cinza chapado do mesmo jeito e custaria centenas de KB, então
 * aqui os triângulos são expandidos e a normal de face é calculada no vertex shader
 * de saída, dando sombreado real com o mínimo de código. Tudo local: nenhum CDN.
 */
const GLB_MAGIC = 0x46546c67; // "glTF"
const COMPONENT_READERS = {
  5121: (view, offset) => view.getUint8(offset),
  5123: (view, offset) => view.getUint16(offset, true),
  5125: (view, offset) => view.getUint32(offset, true),
};
const COMPONENT_SIZE = { 5121: 1, 5123: 2, 5125: 4, 5126: 4 };

function parseGlb(buffer) {
  const header = new DataView(buffer, 0, 12);
  if (header.getUint32(0, true) !== GLB_MAGIC) throw new Error("Arquivo não é um GLB válido");
  let offset = 12;
  let gltf = null;
  let bin = null;
  while (offset < buffer.byteLength) {
    const view = new DataView(buffer, offset, 8);
    const length = view.getUint32(0, true);
    const type = view.getUint32(4, true);
    const start = offset + 8;
    if (type === 0x4e4f534a) gltf = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, start, length)));
    if (type === 0x004e4942) bin = buffer.slice(start, start + length);
    offset = start + length + ((4 - (length % 4)) % 4);
  }
  if (!gltf) throw new Error("GLB sem chunk JSON");
  return { gltf, bin };
}

function readAccessor(gltf, bin, index) {
  const accessor = gltf.accessors[index];
  const view = gltf.bufferViews[accessor.bufferView];
  const componentSize = COMPONENT_SIZE[accessor.componentType];
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[accessor.type];
  const base = (view.byteOffset || 0) + (accessor.byteOffset || 0);
  const stride = view.byteStride || componentSize * components;
  const data = new DataView(bin);
  const out = accessor.componentType === 5126
    ? new Float32Array(accessor.count * components)
    : new Uint32Array(accessor.count * components);
  // Assinatura precisa bater com a de COMPONENT_READERS: (view, offset).
  const read = accessor.componentType === 5126
    ? (view, offset) => view.getFloat32(offset, true)
    : COMPONENT_READERS[accessor.componentType];
  if (!read) throw new Error(`componentType não suportado: ${accessor.componentType}`);
  for (let i = 0; i < accessor.count; i += 1) {
    for (let c = 0; c < components; c += 1) {
      out[i * components + c] = read(data, base + i * stride + c * componentSize);
    }
  }
  return out;
}

/** Expande os índices em triângulos independentes e calcula a normal de cada face. */
function buildFlatMesh(positions, indices) {
  const count = indices ? indices.length : positions.length / 3;
  const vertices = new Float32Array(count * 3);
  const normals = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 3) {
    const idx = [0, 1, 2].map(k => (indices ? indices[i + k] : i + k) * 3);
    const p = idx.map(o => [positions[o], positions[o + 1], positions[o + 2]]);
    const u = [p[1][0] - p[0][0], p[1][1] - p[0][1], p[1][2] - p[0][2]];
    const v = [p[2][0] - p[0][0], p[2][1] - p[0][1], p[2][2] - p[0][2]];
    let n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const len = Math.hypot(n[0], n[1], n[2]) || 1;
    n = [n[0] / len, n[1] / len, n[2] / len];
    for (let k = 0; k < 3; k += 1) {
      vertices.set(p[k], (i + k) * 3);
      normals.set(n, (i + k) * 3);
    }
  }
  return { vertices, normals, count };
}

const VERTEX_SHADER = `
attribute vec3 aPosition; attribute vec3 aNormal;
uniform mat4 uProjection; uniform mat4 uView;
varying vec3 vNormal;
void main() { vNormal = aNormal; gl_Position = uProjection * uView * vec4(aPosition, 1.0); }`;

const FRAGMENT_SHADER = `
precision mediump float;
varying vec3 vNormal;
uniform vec3 uColor;
void main() {
  vec3 light = normalize(vec3(0.45, 0.8, 0.6));
  float diffuse = max(dot(normalize(vNormal), light), 0.0);
  float rim = pow(1.0 - abs(normalize(vNormal).z), 2.0) * 0.25;
  gl_FragColor = vec4(uColor * (0.32 + 0.68 * diffuse) + rim, 1.0);
}`;

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
  return shader;
}

function perspective(fov, aspect, near, far) {
  const f = 1 / Math.tan(fov / 2);
  return new Float32Array([
    f / aspect, 0, 0, 0, 0, f, 0, 0,
    0, 0, (far + near) / (near - far), -1,
    0, 0, (2 * far * near) / (near - far), 0,
  ]);
}

const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const normalize = (v) => { const l = Math.hypot(...v) || 1; return [v[0] / l, v[1] / l, v[2] / l]; };

/** lookAt clássico com up = +Y, a partir de uma câmera em órbita esférica. */
function orbitView(distance, yaw, pitch, center) {
  const cp = Math.cos(pitch), sp = Math.sin(pitch), cy = Math.cos(yaw), sy = Math.sin(yaw);
  const eye = [center[0] + distance * cp * sy, center[1] + distance * sp, center[2] + distance * cp * cy];
  const f = normalize([center[0] - eye[0], center[1] - eye[1], center[2] - eye[2]]);
  const s = normalize(cross(f, [0, 1, 0]));
  const u = cross(s, f);
  return new Float32Array([
    s[0], u[0], -f[0], 0, s[1], u[1], -f[1], 0, s[2], u[2], -f[2], 0,
    -(s[0] * eye[0] + s[1] * eye[1] + s[2] * eye[2]),
    -(u[0] * eye[0] + u[1] * eye[1] + u[2] * eye[2]),
    f[0] * eye[0] + f[1] * eye[1] + f[2] * eye[2], 1,
  ]);
}

export async function mountGlbViewer(canvas, url, options = {}) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status} ao carregar a malha`);
  const { gltf, bin } = parseGlb(await response.arrayBuffer());
  const primitive = gltf.meshes?.[0]?.primitives?.[0];
  if (!primitive) throw new Error("GLB sem malha");
  const positions = readAccessor(gltf, bin, primitive.attributes.POSITION);
  const indices = primitive.indices != null ? readAccessor(gltf, bin, primitive.indices) : null;
  const mesh = buildFlatMesh(positions, indices);

  const box = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  for (let i = 0; i < positions.length; i += 3) {
    for (let k = 0; k < 3; k += 1) {
      box.min[k] = Math.min(box.min[k], positions[i + k]);
      box.max[k] = Math.max(box.max[k], positions[i + k]);
    }
  }
  const center = [0, 1, 2].map(k => (box.min[k] + box.max[k]) / 2);
  const radius = Math.max(...[0, 1, 2].map(k => box.max[k] - box.min[k])) || 1;

  const gl = canvas.getContext("webgl", { antialias: true, alpha: true });
  if (!gl) throw new Error("WebGL indisponível neste navegador");
  const program = gl.createProgram();
  gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER));
  gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER));
  gl.linkProgram(program);
  gl.useProgram(program);

  const bind = (data, name) => {
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    const location = gl.getAttribLocation(program, name);
    gl.enableVertexAttribArray(location);
    gl.vertexAttribPointer(location, 3, gl.FLOAT, false, 0, 0);
  };
  bind(mesh.vertices, "aPosition");
  bind(mesh.normals, "aNormal");

  const colour = options.color || [0.55, 0.62, 0.78];
  gl.uniform3fv(gl.getUniformLocation(program, "uColor"), colour);
  gl.enable(gl.DEPTH_TEST);

  const state = { yaw: 0.6, pitch: 0.35, distance: radius * 2.1, spinning: options.autoRotate !== false };
  const render = () => {
    const width = canvas.clientWidth || 240;
    const height = canvas.clientHeight || 180;
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.uniformMatrix4fv(gl.getUniformLocation(program, "uProjection"), false,
      perspective(Math.PI / 4, canvas.width / canvas.height, radius / 100, radius * 12));
    gl.uniformMatrix4fv(gl.getUniformLocation(program, "uView"), false,
      orbitView(state.distance, state.yaw, state.pitch, center));
    gl.drawArrays(gl.TRIANGLES, 0, mesh.count);
  };

  // Renderização sob demanda. Uma malha de centenas de milhares de triângulos
  // redesenhada a 60 fps trava a aba, e o canvas pode ter vários nós com malha ao
  // mesmo tempo. Só desenha quando a câmera muda, e a rotação de apresentação para
  // sozinha depois de uma volta.
  let frame = 0;
  let needsRender = true;
  let visible = true;
  const spinUntil = state.spinning ? performance.now() + 7000 : 0;
  const invalidate = () => { needsRender = true; };

  const loop = () => {
    frame = requestAnimationFrame(loop);
    if (!visible) return;
    if (state.spinning && performance.now() < spinUntil) { state.yaw += 0.008; needsRender = true; }
    else state.spinning = false;
    if (!needsRender) return;
    needsRender = false;
    render();
  };
  loop();

  const observer = typeof IntersectionObserver === "function"
    ? new IntersectionObserver(entries => {
        visible = entries.some(entry => entry.isIntersecting);
        if (visible) invalidate();
      })
    : null;
  observer?.observe(canvas);

  let dragging = false; let lastX = 0; let lastY = 0;
  canvas.addEventListener("pointerdown", event => {
    dragging = true; state.spinning = false; lastX = event.clientX; lastY = event.clientY;
    canvas.setPointerCapture(event.pointerId); event.stopPropagation();
  });
  canvas.addEventListener("pointermove", event => {
    if (!dragging) return;
    state.yaw -= (event.clientX - lastX) * 0.01;
    state.pitch = Math.max(-1.4, Math.min(1.4, state.pitch + (event.clientY - lastY) * 0.01));
    lastX = event.clientX; lastY = event.clientY;
    invalidate();
    event.stopPropagation();
  });
  canvas.addEventListener("pointerup", () => { dragging = false; });
  canvas.addEventListener("wheel", event => {
    event.preventDefault(); event.stopPropagation();
    state.distance = Math.max(radius * 0.6, Math.min(radius * 8, state.distance * (event.deltaY > 0 ? 1.12 : 0.89)));
    invalidate();
  }, { passive: false });
  window.addEventListener("resize", invalidate);

  return {
    stats: { vertices: positions.length / 3, triangles: mesh.count / 3 },
    // Descartar era só cancelar o quadro. Ficavam para trás o listener de
    // `resize` no window — que segura o canvas vivo para sempre — e o contexto
    // WebGL, que o navegador limita a ~16 por aba. `lose_context` devolve o
    // contexto na hora, em vez de esperar a coleta de lixo decidir.
    dispose: () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", invalidate);
      try { gl.getExtension("WEBGL_lose_context")?.loseContext(); } catch { /* já perdido */ }
    },
  };
}
