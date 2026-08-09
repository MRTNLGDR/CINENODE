const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const app = $("#app");
const modalRoot = $("#modal-root");
const toastRoot = $("#toast-root");
const uploadInput = $("#asset-upload-input");

const NAV = [
  ["dashboard", "dashboard", "Visão geral"],
  ["projects", "projects", "Projetos"],
  ["workflow", "workflow", "Workflow nodal"],
  ["jobs", "jobs", "Fila e jobs"],
  ["gallery", "gallery", "Galeria"],
  ["engines", "engines", "Engines e modelos"],
  ["governance", "governance", "Governança"],
  ["settings", "settings", "Configurações"],
];

const state = {
  route: location.hash.slice(1) || "dashboard",
  loading: true,
  fatalError: null,
  online: false,
  bootstrap: null,
  projects: [],
  currentProject: null,
  graph: { version: 1, nodes: [], edges: [], metadata: {} },
  selectedNodeId: null,
  history: [],
  future: [],
  jobs: [],
  assets: [],
  engines: [],
  gpu: null,
  profiles: {},
  governance: null,
  governanceError: null,
  governanceCheckedAt: null,
  settings: null,
  paletteQuery: "",
  dirty: false,
  busy: new Set(),
  eventSource: null,
  timers: [],
  view: { x: 0, y: 0, zoom: 1 },
  collapsedCategories: new Set(),
  theme: localStorage.getItem("cinenode.theme") || "dark",
  paletteOpen: false,
  tool: "select",
  promptDraft: { text: "", kind: "video", profile: "" },
  expandedNodes: new Set(),
  uploadTarget: null,
  linking: null,
  snapshots: [],
  snapshotsOpen: false,
  collections: [],
  galleryFilter: { kind: "", search: "", deleted: false, collection: "" },
  chat: { open: false, busy: false, messages: [], proposal: null, summary: "", tools: [], draft: "" },
  openPicker: null,
  expandedPreviews: new Set(),
  modules: null,
  preflight: null,
  library: null,
  dock: {
    open: false,
    tab: "navegador",
    width: 420,
    // A última URL fica no localStorage: reabrir o painel não deve perder o lugar.
    url: localStorage.getItem("cinenode.dock.url") || "https://duckduckgo.com/?q=comfyui+workflow",
    input: "",
    page: null,
    loading: false,
    targets: [],
    active: null,
    catalog: null,
    error: null,
  },
};

function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  localStorage.setItem("cinenode.theme", state.theme);
}

function toggleTheme() {
  state.theme = state.theme === "light" ? "dark" : "light";
  applyTheme();
  renderTopbar();
}

// ---------- Ícones (SVG traço, 16px, herdam currentColor) ----------
const ICON_PATHS = {
  dashboard: '<rect x="2.5" y="2.5" width="5.5" height="11" rx="1.2"/><rect x="10" y="2.5" width="5.5" height="5" rx="1.2"/><rect x="10" y="9.5" width="5.5" height="4" rx="1.2"/>',
  projects: '<rect x="2" y="4" width="14" height="10" rx="1.6"/><path d="M2 7.5h14M6.5 4v10"/>',
  workflow: '<rect x="1.8" y="5.5" width="5" height="5" rx="1.3"/><rect x="11.2" y="2.2" width="5" height="4.6" rx="1.3"/><rect x="11.2" y="11.2" width="5" height="4.6" rx="1.3"/><path d="M6.8 8h2.2a1.4 1.4 0 0 0 1.4-1.4V4.5M6.8 8.6h2.2a1.4 1.4 0 0 1 1.4 1.4v3.5"/>',
  jobs: '<circle cx="9" cy="9" r="6.6"/><path d="M9 5.2V9l2.6 1.6"/>',
  gallery: '<rect x="2" y="3.5" width="14" height="11" rx="1.6"/><circle cx="6.4" cy="7.4" r="1.3"/><path d="M2.6 12.4 6.6 9l3 2.6L12 9.4l3.4 3"/>',
  engines: '<circle cx="9" cy="9" r="2.4"/><path d="M9 1.8v2.3M9 13.9v2.3M16.2 9h-2.3M4.1 9H1.8M14.1 3.9l-1.6 1.6M5.5 12.5l-1.6 1.6M14.1 14.1l-1.6-1.6M5.5 5.5 3.9 3.9"/>',
  governance: '<path d="M9 1.8 15.4 4v4.6c0 3.6-2.6 6.5-6.4 7.6C5.2 15.1 2.6 12.2 2.6 8.6V4z"/><path d="M6.4 8.9 8.2 10.7 11.8 7.1"/>',
  settings: '<circle cx="9" cy="9" r="2.6"/><path d="M14.6 11.1a1.3 1.3 0 0 0 .26 1.43l.05.05a1.55 1.55 0 1 1-2.2 2.2l-.04-.05a1.3 1.3 0 0 0-1.44-.26 1.3 1.3 0 0 0-.79 1.19v.13a1.55 1.55 0 1 1-3.1 0v-.07a1.3 1.3 0 0 0-.85-1.19 1.3 1.3 0 0 0-1.43.26l-.05.05a1.55 1.55 0 1 1-2.2-2.2l.05-.04a1.3 1.3 0 0 0 .26-1.44 1.3 1.3 0 0 0-1.19-.79H1.8a1.55 1.55 0 1 1 0-3.1h.07a1.3 1.3 0 0 0 1.19-.85 1.3 1.3 0 0 0-.26-1.43l-.05-.05a1.55 1.55 0 1 1 2.2-2.2l.04.05a1.3 1.3 0 0 0 1.44.26h.06a1.3 1.3 0 0 0 .79-1.19V1.8a1.55 1.55 0 1 1 3.1 0v.07a1.3 1.3 0 0 0 .79 1.19 1.3 1.3 0 0 0 1.43-.26l.05-.05a1.55 1.55 0 1 1 2.2 2.2l-.05.04a1.3 1.3 0 0 0-.26 1.44v.06a1.3 1.3 0 0 0 1.19.79h.13a1.55 1.55 0 1 1 0 3.1h-.07a1.3 1.3 0 0 0-1.19.79z"/>',

  entrada: '<path d="M10.5 3.5h3.2a1.6 1.6 0 0 1 1.6 1.6v7.8a1.6 1.6 0 0 1-1.6 1.6h-3.2"/><path d="M7 12 10.2 9 7 6M10.2 9H2.4"/>',
  llm: '<path d="M9 2.2 10.6 6.4 15 8l-4.4 1.6L9 13.8 7.4 9.6 3 8l4.4-1.6z"/><path d="M13.6 12.4l.6 1.6 1.6.6-1.6.6-.6 1.6-.6-1.6-1.6-.6 1.6-.6z"/>',
  imagem: '<rect x="2" y="3.5" width="14" height="11" rx="1.6"/><circle cx="6.2" cy="7.2" r="1.2"/><path d="M2.6 12.6 6.4 9l2.9 2.5L11.9 9.5l3.5 3.1"/>',
  video: '<rect x="1.8" y="4" width="10.4" height="10" rx="1.6"/><path d="M12.2 8.2 16.2 5.6v6.8l-4-2.6z"/>',
  audio: '<path d="M2 9h1.8M5.4 5.6v6.8M8.6 3v12M11.8 6.4v5.2M15 8.2v1.6"/>',
  pos: '<path d="M9 1.8 11 6.6l4.8 1.6-4.8 1.6L9 14.6 7 9.8 2.2 8.2 7 6.6z"/>',
  utilidades: '<path d="M4 2.8v3.4a2.4 2.4 0 0 0 2.4 2.4h5.2a2.4 2.4 0 0 1 2.4 2.4v3.4"/><circle cx="4" cy="2.8" r="1.5"/><circle cx="14" cy="15.2" r="1.5"/><path d="M14 2.8v3.4a2.4 2.4 0 0 1-2.4 2.4"/><circle cx="14" cy="2.8" r="1.5"/>',
  saida: '<path d="M7.5 3.5H4.3a1.6 1.6 0 0 0-1.6 1.6v7.8a1.6 1.6 0 0 0 1.6 1.6h3.2"/><path d="M12.4 12 15.6 9l-3.2-3M15.6 9H7.8"/>',

  undo: '<path d="M3.2 8.4h7.4a3.8 3.8 0 1 1 0 7.6H7.4"/><path d="M6.2 4.8 2.9 8.1l3.3 3.3"/>',
  redo: '<path d="M14.8 8.4H7.4a3.8 3.8 0 1 0 0 7.6h3.2"/><path d="M11.8 4.8l3.3 3.3-3.3 3.3"/>',
  check: '<path d="M3.4 9.4 7 13l7.6-8"/>',
  fit: '<path d="M6.4 2.4H3.2a.8.8 0 0 0-.8.8v3.2M11.6 2.4h3.2a.8.8 0 0 1 .8.8v3.2M15.6 11.6v3.2a.8.8 0 0 1-.8.8h-3.2M2.4 11.6v3.2a.8.8 0 0 0 .8.8h3.2"/>',
  select: '<path d="M3.4 2.6 8 15l1.9-4.9L15 8.5z"/>',
  hand: '<path d="M6.2 8.4V4.2a1.4 1.4 0 0 1 2.8 0v3.6M9 7.6V3.4a1.4 1.4 0 0 1 2.8 0v4.4M11.8 8V5.4a1.4 1.4 0 0 1 2.8 0v5.2c0 3-2.2 5.2-5.2 5.2-2.6 0-4-1-5.2-2.9L2.6 10a1.3 1.3 0 0 1 2.1-1.5l1.5 1.9"/>',
  plus: '<path d="M9 3.4v11.2M3.4 9h11.2"/>',
  minus: '<path d="M3.4 9h11.2"/>',
  close: '<path d="M4.4 4.4 13.6 13.6M13.6 4.4 4.4 13.6"/>',
  play: '<path d="M5.6 3.6 14 9l-8.4 5.4z"/>',
  copy: '<rect x="6" y="6" width="9" height="9" rx="1.4"/><path d="M12 6V4.4A1.4 1.4 0 0 0 10.6 3H4.4A1.4 1.4 0 0 0 3 4.4v6.2A1.4 1.4 0 0 0 4.4 12H6"/>',
  rename: '<path d="M11.4 2.9 15.1 6.6M2.6 15.4l.9-3.3 8.2-8.2 3.7 3.7-8.2 8.2z"/>',
  unlink: '<path d="M7.6 10.4 5.2 12.8a2.9 2.9 0 0 1-4.1-4.1L3.5 6.4M10.4 7.6l2.4-2.4a2.9 2.9 0 0 1 4.1 4.1l-2.4 2.4"/><path d="M2.4 2.4l13.2 13.2"/>',
  download: '<path d="M9 2.6v8.6M5.6 8.2 9 11.6l3.4-3.4M2.8 14.4h12.4"/>',
  trash: '<path d="M2.8 4.6h12.4M6.6 4.6V3.2a1.2 1.2 0 0 1 1.2-1.2h2.4a1.2 1.2 0 0 1 1.2 1.2v1.4M13.4 4.6l-.6 9.6a1.3 1.3 0 0 1-1.3 1.2H6.5a1.3 1.3 0 0 1-1.3-1.2l-.6-9.6"/>',
  moon: '<path d="M15.2 10.4A6.6 6.6 0 0 1 7.6 2.8a6.6 6.6 0 1 0 7.6 7.6z"/>',
  sun: '<circle cx="9" cy="9" r="3.4"/><path d="M9 1.6v1.8M9 14.6v1.8M16.4 9h-1.8M3.4 9H1.6M14.2 3.8l-1.3 1.3M5.1 12.9l-1.3 1.3M14.2 14.2l-1.3-1.3M5.1 5.1 3.8 3.8"/>',
  search: '<circle cx="8" cy="8" r="5.2"/><path d="M11.8 11.8 15.6 15.6"/>',
  upload: '<path d="M9 12.4V3.8M5.6 7.2 9 3.8l3.4 3.4M2.8 14.4h12.4"/>',
  chevron: '<path d="M6.4 3.6 11.8 9l-5.4 5.4"/>',
  chat: '<path d="M15.4 11.4a1.6 1.6 0 0 1-1.6 1.6H5.4L2.6 15.8V4.2a1.6 1.6 0 0 1 1.6-1.6h9.6a1.6 1.6 0 0 1 1.6 1.6z"/>',
  spark: '<path d="M9 2.4 10.5 6.9 15 8.4l-4.5 1.5L9 14.4 7.5 9.9 3 8.4l4.5-1.5z"/>',
  dice: '<rect x="2.6" y="2.6" width="12.8" height="12.8" rx="2.6"/><circle cx="6.4" cy="6.4" r=".9" fill="currentColor"/><circle cx="11.6" cy="11.6" r=".9" fill="currentColor"/><circle cx="9" cy="9" r=".9" fill="currentColor"/>',
  text: '<path d="M3.6 4.2h10.8M9 4.2v9.6M6.6 13.8h4.8"/>',
  media: '<path d="M9 2.4 15.4 6v6L9 15.6 2.6 12V6z"/>',
};

function icon(name, size = 16) {
  const path = ICON_PATHS[name];
  if (!path) return "";
  return `<svg class="ico" viewBox="0 0 18 18" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${path}</svg>`;
}

const CATEGORY_ICONS = {
  "Entrada": "entrada",
  "LLM": "llm",
  "Imagem": "imagem",
  "Vídeo": "video",
  "Áudio": "audio",
  "Pós": "pos",
  "Utilidades": "utilidades",
  "Saída": "saida",
};

// ---------- Portas tipadas ----------
// Cada tipo tem cor e glifo próprios. A cor é a mesma no ponto, na linha e no menu
// de conexão, para que a leitura do grafo seja imediata.
const PORT_TYPES = {
  text:  { label: "Texto",  color: "#7a5af8", icon: "text" },
  image: { label: "Imagem", color: "#1d6bf3", icon: "imagem" },
  video: { label: "Vídeo",  color: "#f2762e", icon: "video" },
  audio: { label: "Áudio",  color: "#0aa06e", icon: "audio" },
  media: { label: "Mídia",  color: "#8a93a6", icon: "media" },
};

function portMeta(type) {
  return PORT_TYPES[type] || PORT_TYPES.media;
}

/** "image?" → opcional, "text*" → aceita várias conexões. */
/** Rótulo de cada porta nomeada. Espelha PORT_LABELS do backend. */
const PORT_LABELS = {
  text: "Prompt", image: "Imagem", video: "Vídeo", audio: "Áudio",
  media: "Mídia", model3d: "Modelo 3D", data: "Dados",
  prompt: "Prompt", negativo: "Negativo",
  inicio: "Início", fim: "Fim", ref: "Referência",
  logo: "Logo", mascara: "Máscara", estilo: "Estilo",
  dna: "Structure DNA", controle: "Controle", trilha: "Trilha",
};

function parsePorts(list) {
  return (list || []).map(spec => {
    const raw = String(spec);
    const optional = raw.endsWith("?");
    const multi = raw.endsWith("*");
    const corpo = raw.replace(/[?*]$/, "");
    const [a, b] = corpo.split(":");
    const type = b || a;
    const name = b ? a : type;
    return { name, type, optional, multi, label: PORT_LABELS[name] || PORT_LABELS[type] || name };
  });
}

/** `media` é o tipo curinga: preview aceita tudo e asset genérico serve a todos. */
function portsCompatible(outType, inType) {
  return outType === inType || inType === "media" || outType === "media";
}

function nodeAcceptsType(item, type) {
  return parsePorts(item.inputs).some(port => portsCompatible(type, port.type));
}


const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2.5;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  const units = ["B", "KB", "MB", "GB", "TB"];
  if (!value) return "0 B";
  const index = Math.min(units.length - 1, Math.floor(Math.log(value) / Math.log(1024)));
  return `${(value / 1024 ** index).toFixed(index > 1 ? 2 : 1)} ${units[index]}`;
}

function formatDate(value) {
  if (!value) return "—";
  try { return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" }).format(new Date(value)); }
  catch { return value; }
}

function toast(message, type = "info", timeout = 5000) {
  const element = document.createElement("div");
  element.className = `toast ${type}`;
  element.textContent = message;
  toastRoot.append(element);
  setTimeout(() => element.remove(), timeout);
}

async function api(path, options = {}) {
  const config = { ...options, headers: { ...(options.headers || {}) } };
  if (options.body && !(options.body instanceof FormData) && typeof options.body !== "string") {
    config.headers["Content-Type"] = "application/json";
    config.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, config);
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = payload?.error?.message || payload?.detail?.message || payload?.detail || payload?.message || `HTTP ${response.status}`;
    const message = typeof detail === "string" ? detail : JSON.stringify(detail);
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function setBusy(key, enabled) {
  if (enabled) state.busy.add(key); else state.busy.delete(key);
  renderTopbar();
}

function deepCopy(value) { return JSON.parse(JSON.stringify(value)); }

function pushHistory() {
  state.history.push(deepCopy(state.graph));
  if (state.history.length > 80) state.history.shift();
  state.future = [];
  state.dirty = true;
}

function undo() {
  const previous = state.history.pop();
  if (!previous) return;
  state.future.push(deepCopy(state.graph));
  state.graph = previous;
  state.selectedNodeId = null;
  state.dirty = true;
  renderWorkflow();
}

function redo() {
  const next = state.future.pop();
  if (!next) return;
  state.history.push(deepCopy(state.graph));
  state.graph = next;
  state.selectedNodeId = null;
  state.dirty = true;
  renderWorkflow();
}

function catalogItem(type) { return state.bootstrap?.node_catalog?.find(item => item.type === type); }
function currentNode() { return state.graph.nodes.find(node => node.id === state.selectedNodeId) || null; }

function defaultConfig(item) {
  const config = {};
  for (const field of item.fields || []) config[field.key] = deepCopy(field.default ?? "");
  return config;
}

function newNodeId(type) {
  const stem = type.replaceAll(".", "-");
  let index = 1;
  while (state.graph.nodes.some(node => node.id === `${stem}-${index}`)) index += 1;
  return `${stem}-${index}`;
}

function projectJobs() {
  if (!state.currentProject) return [];
  return state.jobs.filter(job => job.project_id === state.currentProject.id);
}

/** Último asset produzido por cada nó do projeto atual. Base do preview dentro do card. */
function assetsByNode() {
  const map = new Map();
  if (!state.currentProject) return map;
  for (const asset of state.assets) {
    if (asset.project_id !== state.currentProject.id) continue;
    const nodeId = asset.metadata?.node_id;
    if (!nodeId || map.has(nodeId)) continue;
    map.set(nodeId, asset);
  }
  return map;
}

/** Estado de execução por nó, derivado do job mais recente do projeto. */
function nodeRunStates() {
  const map = new Map();
  const job = projectJobs()[0];
  if (!job) return map;
  if (job.status === "RUNNING" && job.current_node_id) map.set(job.current_node_id, "RUNNING");
  if (job.status === "FAILED" && job.current_node_id) map.set(job.current_node_id, "FAILED");
  for (const nodeId of Object.keys(job.result?.node_results || {})) {
    if (!map.has(nodeId)) map.set(nodeId, "SUCCEEDED");
  }
  return map;
}

/** Subgrafo com o nó alvo e todos os seus ancestrais — usado por "executar até aqui". */
function ancestorSubgraph(nodeId) {
  const keep = new Set([nodeId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const edge of state.graph.edges) {
      if (keep.has(edge.target) && !keep.has(edge.source)) { keep.add(edge.source); changed = true; }
    }
  }
  return {
    version: state.graph.version || 1,
    nodes: state.graph.nodes.filter(node => keep.has(node.id)).map(deepCopy),
    edges: state.graph.edges.filter(edge => keep.has(edge.source) && keep.has(edge.target)).map(deepCopy),
    metadata: { ...(state.graph.metadata || {}), partial_target: nodeId },
  };
}

function assetPreviewHtml(asset, { controls = false } = {}) {
  const mime = asset.mime_type || "";
  const src = `/media/${asset.id}`;
  if (asset.kind === "model3d" || /\.(glb|gltf)$/i.test(asset.original_name || asset.path || "")) {
    // Canvas WebGL local; o viewer é montado depois que o elemento entra no DOM.
    return `<canvas class="glb-canvas" data-glb-src="${src}" title="Arraste para girar, role para aproximar"></canvas>`;
  }
  if (mime.startsWith("image/")) return `<img src="${src}" alt="${escapeHtml(asset.original_name || asset.id)}" loading="lazy">`;
  if (mime.startsWith("video/")) return `<video src="${src}" ${controls ? "controls" : "muted loop playsinline"} preload="metadata"></video>`;
  if (mime.startsWith("audio/")) return `<audio src="${src}" controls preload="metadata"></audio>`;
  return `<span class="mono muted">${escapeHtml(asset.kind || "arquivo")}</span>`;
}


/** Monta os visualizadores GLB que entraram no DOM. Import dinâmico: quem nunca
 *  gera 3D não paga o custo do módulo. */
// Map, não WeakMap: para descartar um visualizador é preciso ITERAR os montados,
// e WeakMap não é iterável. O WeakMap parecia a escolha certa — some sozinho
// quando o canvas é coletado — e escondia o vazamento: `render()` faz
// `app.innerHTML = ...`, o que destrói todo canvas e cria outro. O canvas novo
// não estava no mapa, então montava um visualizador NOVO, com contexto WebGL
// novo e laço de `requestAnimationFrame` novo, sem nunca chamar `dispose()` do
// anterior. O navegador limita os contextos WebGL (tipicamente 16): na galeria
// com um GLB, `refreshAssets` a cada 15 s consumia um por vez até a aba morrer,
// e os laços órfãos continuavam desenhando em canvas fora do documento.
const mountedViewers = new Map();

function descartarVisualizadoresOrfaos() {
  for (const [canvas, viewer] of mountedViewers) {
    if (canvas.isConnected) continue;
    try { viewer?.dispose?.(); } catch { /* já descartado */ }
    mountedViewers.delete(canvas);
  }
}
async function mountGlbCanvases() {
  // Descarta antes de montar: o `render()` que acabou de rodar já trocou os
  // canvas, e os antigos estão fora do documento segurando contexto e laço.
  descartarVisualizadoresOrfaos();

  const canvases = $$(".glb-canvas[data-glb-src]").filter(item => !mountedViewers.has(item));
  if (!canvases.length) return;
  let mount;
  try {
    ({ mountGlbViewer: mount } = await import("./glb-viewer.js"));
  } catch (error) {
    toast(`Visualizador 3D indisponível: ${error.message}`, "error");
    return;
  }
  for (const canvas of canvases) {
    // Reserva a vaga antes do await: sem isto, dois `render()` seguidos entram
    // no laço com o mesmo canvas e montam dois visualizadores nele.
    mountedViewers.set(canvas, null);
    try {
      const viewer = await mount(canvas, canvas.dataset.glbSrc);
      // Guarda o visualizador, não `true`: `dispose()` está nele.
      mountedViewers.set(canvas, viewer);
      canvas.title = `${viewer.stats.triangles.toLocaleString("pt-BR")} triângulos · arraste para girar`;
    } catch (error) {
      mountedViewers.delete(canvas);
      canvas.replaceWith(Object.assign(document.createElement("div"), {
        className: "glb-error mono", textContent: error.message,
      }));
    }
  }
}

function canvasPoint(clientX, clientY) {
  const wrap = $("#canvas-wrap");
  if (!wrap) return { x: 0, y: 0 };
  const rect = wrap.getBoundingClientRect();
  return {
    x: (clientX - rect.left - state.view.x) / state.view.zoom,
    y: (clientY - rect.top - state.view.y) / state.view.zoom,
  };
}

function applyView() {
  const canvas = $("#node-canvas");
  if (canvas) canvas.style.transform = `translate(${state.view.x}px, ${state.view.y}px) scale(${state.view.zoom})`;
  const label = $("#zoom-label");
  if (label) label.textContent = `${Math.round(state.view.zoom * 100)}%`;
  drawMinimap();
}

function setZoom(zoom, anchor) {
  const wrap = $("#canvas-wrap");
  const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
  if (wrap && anchor) {
    const rect = wrap.getBoundingClientRect();
    const px = anchor.x - rect.left;
    const py = anchor.y - rect.top;
    state.view.x = px - (px - state.view.x) * (next / state.view.zoom);
    state.view.y = py - (py - state.view.y) * (next / state.view.zoom);
  }
  state.view.zoom = next;
  applyView();
}

async function initialize() {
  mountDock();
  applyTheme();
  try {
    const [bootstrap, projectData, jobsData, assetsData, governance, profileData] = await Promise.all([
      api("/api/bootstrap"),
      api("/api/projects"),
      api("/api/jobs?limit=100"),
      api("/api/assets?limit=200"),
      api("/api/governance/snapshot"),
      // Os perfis alimentam o campo "Perfil" do inspector; sem eles o select abre vazio.
      api("/api/model-profiles"),
    ]);
    state.profiles = profileData.items;
    state.bootstrap = bootstrap;
    state.projects = projectData.items;
    state.jobs = jobsData.items;
    state.assets = assetsData.items;
    state.governance = governance;
    state.online = true;
    const savedProjectId = localStorage.getItem("cinenode.currentProjectId");
    state.currentProject = state.projects.find(project => project.id === savedProjectId) || state.projects[0] || null;
    if (state.currentProject) state.graph = deepCopy(state.currentProject.graph);
    state.loading = false;
    render();
    connectEvents();
    startPolling();
  } catch (error) {
    state.loading = false;
    state.fatalError = error;
    render();
  }
}

function shell(content) {
  const profile = state.bootstrap?.app?.profile || {};
  return `
    <div class="app-shell">
      <header class="topbar" id="topbar">${topbarHtml()}</header>
      <aside class="sidebar">
        <div class="nav-group-title">Produção</div>
        ${NAV.slice(0, 6).map(navButton).join("")}
        <div class="nav-group-title">Administração local</div>
        ${NAV.slice(6).map(navButton).join("")}
        <div class="profile-card"><strong>${escapeHtml(profile.display_name || "Administrador local")}</strong><span>${escapeHtml(profile.role || "super_admin")}</span></div>
      </aside>
      <main class="main" id="main">${content}</main>
    </div>`;
}

function navButton([route, iconName, label]) {
  return `<button class="nav-button ${state.route === route ? "active" : ""}" data-route="${route}">${icon(iconName)}${escapeHtml(label)}</button>`;
}

function topbarHtml() {
  const busy = state.busy.size > 0;
  return `
    <div class="brand"><span class="brand-mark"></span><span class="brand-copy"><strong>CineNode Local</strong><span>Avangard · v${escapeHtml(state.bootstrap?.app?.version || "0.1.0")}</span></span></div>
    ${state.projects.length ? `<select id="top-project-select" class="select project-selector" aria-label="Projeto atual">${state.projects.map(project => `<option value="${project.id}" ${project.id === state.currentProject?.id ? "selected" : ""}>${escapeHtml(project.name)}</option>`).join("")}</select>` : ""}
    <div class="topbar-spacer"></div>
    <span class="status-pill"><span class="status-dot ${state.online ? "online" : ""}"></span>${state.online ? "Local ativo" : "Bridge offline"}</span>
    <button class="btn icon-button" id="theme-toggle" title="Alternar tema claro/escuro" aria-label="Alternar tema">${icon(state.theme === "light" ? "moon" : "sun")}</button>
    ${state.route === "workflow" ? `<button class="btn" id="save-project" ${!state.currentProject || busy ? "disabled" : ""}>${state.dirty ? '<span class="dirty-dot"></span>' : ""}Salvar</button><button class="btn primary" id="run-project" ${!state.currentProject || busy ? "disabled" : ""}>${icon("play")} Executar</button>` : ""}
  `;
}

function renderTopbar() {
  const topbar = $("#topbar");
  if (topbar) topbar.innerHTML = topbarHtml();
  bindTopbar();
}

function render() {
  if (state.loading) {
    app.innerHTML = `<div class="empty-state" style="height:100vh"><div><span class="spinner"></span><strong>Inicializando o núcleo local</strong><div>Banco, fila, governança e interface.</div></div></div>`;
    return;
  }
  if (state.fatalError) {
    app.innerHTML = `<div class="empty-state" style="height:100vh"><div><strong>Não foi possível iniciar</strong><div class="error-state mono">${escapeHtml(state.fatalError.message)}</div><br><button class="btn primary" onclick="location.reload()">Tentar novamente</button></div></div>`;
    return;
  }
  let content = "";
  if (state.route === "dashboard") content = dashboardHtml();
  if (state.route === "projects") content = projectsHtml();
  if (state.route === "workflow") content = workflowHtml();
  if (state.route === "jobs") content = jobsHtml();
  if (state.route === "gallery") content = galleryHtml();
  if (state.route === "engines") content = enginesHtml();
  if (state.route === "governance") content = governanceHtml();
  // Os módulos são avaliados sob demanda: entrar na tela dispara a leitura da
  // evidência já gravada (barato); reavaliar roda os comandos (caro, sob clique).
  if (state.route === "governance" && !state.modules) loadModules().then(render);
  if (state.route === "settings") content = settingsHtml();
  app.innerHTML = shell(content);
  bindShell();
  bindRoute();
  mountGlbCanvases();
}

function bindShell() {
  $$("[data-route]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.route)));
  bindTopbar();
}

function bindTopbar() {
  $("#top-project-select")?.addEventListener("change", event => selectProject(event.target.value));
  $("#theme-toggle")?.addEventListener("click", toggleTheme);
  $("#save-project")?.addEventListener("click", saveCurrentProject);
  $("#run-project")?.addEventListener("click", runCurrentProject);
}

function navigate(route) {
  state.route = route;
  location.hash = route;
  render();
}

window.addEventListener("hashchange", () => {
  const route = location.hash.slice(1);
  if (NAV.some(item => item[0] === route)) { state.route = route; render(); }
});

function dashboardHtml() {
  const summary = state.governance?.summary || {};
  const running = state.jobs.filter(job => job.status === "RUNNING").length;
  const failed = state.jobs.filter(job => job.status === "FAILED").length;
  return `<section class="page" id="conteudo" role="main">
    <div class="page-header"><div><h1 class="page-title">Centro de produção local</h1><p class="page-subtitle">Imagem, vídeo, LLM, pós-processamento 4K/8K e governança no mesmo runtime local.</p></div><div class="actions"><button class="btn" data-action="new-project">${icon("plus")} Novo projeto</button><button class="btn primary" data-route="workflow">Abrir editor</button></div></div>
    <div class="grid cols-4">
      ${metric("Projetos", state.projects.length, "Persistidos em SQLite")}
      ${metric("Jobs ativos", running, `${state.jobs.length} execuções registradas`)}
      ${metric("Assets", state.assets.length, "Galeria local")}
      ${metric("Governança", `${Number(summary.progressPercent || 0).toFixed(0)}%`, `${summary.pendingTasks || 0} tarefas pendentes`)}
    </div>
    <div class="grid cols-2" style="margin-top:14px">
      <article class="card"><div class="card-header"><h2>Execuções recentes</h2><button class="btn small" data-route="jobs">Ver fila</button></div><div class="card-body">${recentJobsHtml()}</div></article>
      <article class="card"><div class="card-header"><h2>Estado estrutural</h2><span class="badge ${state.governance?.state}">${escapeHtml(state.governance?.state || "EMPTY")}</span></div><div class="card-body">
        <div class="module-row"><strong>Banco e migrations</strong><span class="muted">SQLite WAL</span><span class="badge DONE">OK</span></div>
        <div class="module-row"><strong>Fila GPU</strong><span class="muted">1 job por vez</span><span class="badge ${running ? "RUNNING" : "DONE"}">${running ? "ATIVA" : "PRONTA"}</span></div>
        <div class="module-row"><strong>Falhas abertas</strong><span class="muted">Jobs + alertas</span><span class="badge ${failed ? "FAILED" : "DONE"}">${failed}</span></div>
        <div class="module-row"><strong>Modelos locais</strong><span class="muted">Validar arquivos</span><button class="btn small" data-route="engines">Verificar</button></div>
      </div></article>
    </div>
    <article class="card" style="margin-top:14px"><div class="card-header"><h2>Roadmap e alertas reais</h2><button class="btn small" data-route="governance">Abrir governança</button></div><div class="card-body">${alertsCompactHtml()}</div></article>
  </section>`;
}

function metric(label, value, detail) { return `<article class="card metric"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-value">${escapeHtml(value)}</div><div class="metric-detail">${escapeHtml(detail)}</div></article>`; }

function recentJobsHtml() {
  if (!state.jobs.length) return `<div class="empty-state"><div><strong>Nenhuma execução</strong>Crie um workflow e execute.</div></div>`;
  return state.jobs.slice(0, 6).map(job => `<div class="module-row"><span><strong class="mono">${escapeHtml(job.id.slice(-10))}</strong><br><small class="muted">${formatDate(job.created_at)}</small></span><div><div class="progress"><span style="width:${Number(job.progress || 0)}%"></span></div></div><span class="badge ${job.status}">${job.status}</span></div>`).join("");
}

function alertsCompactHtml() {
  const alerts = (state.governance?.alerts || []).filter(item => item.status === "OPEN").slice(0, 4);
  if (!alerts.length) return `<span class="badge DONE">Sem alertas abertos</span>`;
  return alerts.map(alert => `<div class="alert ${alert.severity}"><h4>${escapeHtml(alert.id)} · ${escapeHtml(alert.severity)} · ${escapeHtml(alert.kind)}</h4><p>${escapeHtml(alert.fact)}</p><p><strong>Ação:</strong> ${escapeHtml(alert.action)}</p></div>`).join("");
}

function projectsHtml() {
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Projetos</h1><p class="page-subtitle">Cada projeto preserva o grafo, histórico de jobs e assets.</p></div><button class="btn primary" data-action="new-project">${icon("plus")} Novo projeto</button></div>
  <article class="card"><div class="table-wrap"><table><thead><tr><th>Projeto</th><th>Nós</th><th>Atualização</th><th></th></tr></thead><tbody>
    ${state.projects.length ? state.projects.map(project => `<tr><td><strong>${escapeHtml(project.name)}</strong><br><small class="muted">${escapeHtml(project.description || "Sem descrição")}</small></td><td>${project.graph?.nodes?.length || 0}</td><td>${formatDate(project.updated_at)}</td><td><div class="actions"><button class="btn small" data-open-project="${project.id}">Abrir</button><button class="btn small danger" data-delete-project="${project.id}">Excluir</button></div></td></tr>`).join("") : `<tr><td colspan="4"><div class="empty-state"><div><strong>Nenhum projeto</strong>Crie o primeiro projeto para iniciar.</div></div></td></tr>`}
  </tbody></table></div></article></section>`;
}

function workflowHtml() {
  if (!state.currentProject) return `<section class="page" role="main"><div class="empty-state"><div><strong>Nenhum projeto selecionado</strong><p>Crie um projeto antes de montar o workflow.</p><button class="btn primary" data-action="new-project">Criar projeto</button></div></div></section>`;
  const groups = {};
  for (const item of state.bootstrap.node_catalog) {
    if (state.paletteQuery && !`${item.label} ${item.type} ${item.description}`.toLowerCase().includes(state.paletteQuery.toLowerCase())) continue;
    (groups[item.category] ||= []).push(item);
  }
  const assets = assetsByNode();
  const runStates = nodeRunStates();
  const selected = state.graph.nodes.find(node => node.id === state.selectedNodeId) || null;
  return `<section class="workflow-page ${state.chat.open ? "with-chat" : ""}">
    <div class="canvas-wrap tool-${state.tool}" id="canvas-wrap">
      <div class="node-canvas" id="node-canvas" style="transform:translate(${state.view.x}px, ${state.view.y}px) scale(${state.view.zoom})">
        <svg class="edge-layer" id="edge-layer"></svg>
        ${state.graph.nodes.map(node => nodeHtml(node, assets.get(node.id), runStates.get(node.id))).join("")}
      </div>

      <div class="float-pill canvas-topbar">
        <button class="pill-btn" data-workflow="undo" ${!state.history.length ? "disabled" : ""} title="Desfazer" aria-label="Desfazer">${icon("undo")}</button>
        <button class="pill-btn" data-workflow="redo" ${!state.future.length ? "disabled" : ""} title="Refazer" aria-label="Refazer">${icon("redo")}</button>
        <span class="pill-divider"></span>
        <button class="pill-btn wide" data-workflow="validate">${icon("check")} Validar</button>
        <span class="pill-divider"></span>
        <button class="pill-btn wide ${state.snapshotsOpen ? "active" : ""}" data-snapshots-toggle title="Versões do projeto" aria-label="Versões do projeto">${icon("copy")} Versões${state.snapshots.length ? ` <span class="pill-count">${state.snapshots.length}</span>` : ""}</button>
        <span class="pill-meta">${state.graph.nodes.length} nós · ${state.graph.edges.length} conexões</span>
      </div>
      ${state.snapshotsOpen ? snapshotsPanelHtml() : ""}

      <div class="float-pill canvas-tools">
        <button class="pill-btn ${state.tool === "select" ? "active" : ""}" data-tool="select" title="Selecionar (V)" aria-label="Selecionar (V)">${icon("select")}</button>
        <button class="pill-btn ${state.tool === "pan" ? "active" : ""}" data-tool="pan" title="Mover canvas (H ou espaço)" aria-label="Mover canvas (H ou espaço)">${icon("hand")}</button>
        <span class="pill-divider horizontal"></span>
        <button class="pill-btn ${state.paletteOpen ? "active" : ""}" data-palette-toggle title="Adicionar nó (N)" aria-label="Adicionar nó (N)">${icon("plus")}</button>
        <button class="pill-btn ${state.chat.open ? "active" : ""}" data-workflow="chat" title="Worker (C)" aria-label="Worker (C)">${icon("chat")}</button>
        <button class="pill-btn" data-workflow="preview" title="Conectar previews nos resultados soltos (P)" aria-label="Conectar previews nos resultados soltos (P)">${icon("gallery")}</button>
        <button class="pill-btn" data-workflow="layout" title="Organizar grafo (L)" aria-label="Organizar grafo (L)">${icon("workflow")}</button>
        <button class="pill-btn" data-workflow="fit" title="Enquadrar tudo (F)" aria-label="Enquadrar tudo (F)">${icon("fit")}</button>
      </div>

      <div class="float-pill zoom-pill">
        <button class="pill-btn" data-workflow="zoom-out" title="Reduzir" aria-label="Reduzir">${icon("minus")}</button>
        <button class="pill-btn zoom-value" id="zoom-label" data-workflow="zoom-reset" title="Voltar a 100%" aria-label="Voltar a 100%">${Math.round(state.view.zoom * 100)}%</button>
        <button class="pill-btn" data-workflow="zoom-in" title="Ampliar" aria-label="Ampliar">${icon("plus")}</button>
      </div>

      ${state.paletteOpen ? palettePopoverHtml(groups) : ""}
      ${selected ? nodeToolbarHtml(selected, assets.get(selected.id)) : ""}
      ${promptBarHtml()}
      ${chatPanelHtml()}
      <div class="minimap"><svg id="minimap-svg" viewBox="0 0 200 130" preserveAspectRatio="none"></svg></div>
    </div>
  </section>`;
}

function snapshotsPanelHtml() {
  return `<div class="snapshots-panel" id="snapshots-panel">
    <div class="snapshots-head">
      <strong>Versões do projeto</strong>
      <button class="pill-btn" data-snapshots-toggle aria-label="Fechar">${icon("close")}</button>
    </div>
    <button class="btn primary small snapshots-new" data-snapshot-create>${icon("plus")} Salvar versão atual</button>
    <div class="snapshots-list">
      ${state.snapshots.length
        ? state.snapshots.map(item => `<div class="snapshot-row">
            <div class="snapshot-info">
              <strong>${escapeHtml(item.label)}</strong>
              <small>${item.node_count} nós · ${item.edge_count} conexões · ${formatDate(item.created_at)}</small>
              ${item.origin !== "manual" ? `<span class="snapshot-origin">${escapeHtml(item.origin)}</span>` : ""}
            </div>
            <div class="snapshot-actions">
              <button class="pill-btn" data-snapshot-restore="${item.id}" title="Restaurar esta versão" aria-label="Restaurar esta versão">${icon("undo")}</button>
              <button class="pill-btn danger" data-snapshot-delete="${item.id}" title="Excluir versão" aria-label="Excluir versão">${icon("trash")}</button>
            </div>
          </div>`).join("")
        : `<div class="snapshots-empty muted">Nenhuma versão salva. Salve uma antes de mudanças grandes — restaurar nunca apaga o estado atual.</div>`}
    </div>
  </div>`;
}


/** Diferença entre o grafo atual e o proposto, em linguagem de nó, não de JSON. */
function graphDiff(current, proposal) {
  const before = new Map((current?.nodes || []).map(node => [node.id, node]));
  const after = new Map((proposal?.nodes || []).map(node => [node.id, node]));
  const added = [...after.values()].filter(node => !before.has(node.id));
  const removed = [...before.values()].filter(node => !after.has(node.id));
  const changed = [...after.values()].filter(node => {
    const old = before.get(node.id);
    return old && JSON.stringify(old.config || {}) !== JSON.stringify(node.config || {});
  });
  const edgeKey = edge => `${edge.source}->${edge.target}`;
  const beforeEdges = new Set((current?.edges || []).map(edgeKey));
  const afterEdges = new Set((proposal?.edges || []).map(edgeKey));
  return {
    added, removed, changed,
    edgesAdded: [...afterEdges].filter(key => !beforeEdges.has(key)),
    edgesRemoved: [...beforeEdges].filter(key => !afterEdges.has(key)),
  };
}

function chatPanelHtml() {
  const chat = state.chat;
  if (!chat.open) return "";
  const diff = chat.proposal ? graphDiff(state.graph, chat.proposal) : null;
  const nodeLine = (node, mark) => {
    const item = catalogItem(node.type);
    return `<li class="${mark}"><span>${icon(CATEGORY_ICONS[item?.category] || "utilidades", 12)}</span>
      <strong>${escapeHtml(item?.label || node.type)}</strong><code>${escapeHtml(node.id)}</code></li>`;
  };
  return `<aside class="chat-panel" id="chat-panel">
    <div class="chat-head">
      ${icon("spark", 15)}<strong>Worker</strong>
      <span class="chat-provider">${escapeHtml(state.bootstrap?.agent?.provider || "local")}</span>
      <button class="pill-btn" data-chat-close aria-label="Fechar">${icon("close")}</button>
    </div>
    <div class="chat-body" id="chat-body">
      ${chat.messages.length ? "" : `<div class="chat-hint">
        <p>Peça um workflow em português. O worker lê o catálogo real de nós e valida antes de propor.</p>
        <button class="chat-example" data-chat-example="Monte um workflow que gera um take de vídeo de uma cidade neon na chuva com dolly in e termina num preview.">Gerar um take de vídeo</button>
        <button class="chat-example" data-chat-example="Quero uma imagem 21:9 em 4K, qualidade cinema, com look anamórfico, e depois um upscale 4x.">Imagem cinematográfica com upscale</button>
        <button class="chat-example" data-chat-example="Pegue o último vídeo e me mostre a falsa cor e o waveform dele.">Analisar um vídeo</button>
      </div>`}
      ${chat.messages.map(message => `<div class="chat-msg ${message.role}">${escapeHtml(message.content)}</div>`).join("")}
      ${chat.busy ? `<div class="chat-msg assistant busy"><span class="spinner"></span>pensando e consultando o catálogo…</div>` : ""}
      ${chat.tools.length && !chat.busy ? `<div class="chat-tools">${chat.tools.map(tool =>
        `<span title="${escapeHtml(tool.resultado_resumo)}">${escapeHtml(tool.ferramenta)}</span>`).join("")}</div>` : ""}
      ${diff ? `<div class="chat-proposal">
        <div class="chat-proposal-head">${icon("workflow", 13)} Proposta${chat.summary ? ` · ${escapeHtml(chat.summary)}` : ""}</div>
        <ul class="chat-diff">
          ${diff.added.map(node => nodeLine(node, "add")).join("")}
          ${diff.changed.map(node => nodeLine(node, "mod")).join("")}
          ${diff.removed.map(node => nodeLine(node, "del")).join("")}
        </ul>
        <div class="chat-diff-edges">${diff.edgesAdded.length} conexão(ões) nova(s)${diff.edgesRemoved.length ? ` · ${diff.edgesRemoved.length} removida(s)` : ""}</div>
        <div class="chat-proposal-actions">
          <button class="btn primary small" data-chat-apply>Aplicar no canvas</button>
          <button class="btn small" data-chat-discard>Descartar</button>
        </div>
      </div>` : ""}
    </div>
    <form class="chat-input" id="chat-form">
      <textarea id="chat-draft" rows="2" placeholder="O que você quer montar?" ${chat.busy ? "disabled" : ""}>${escapeHtml(chat.draft)}</textarea>
      <button class="btn primary" type="submit" ${chat.busy ? "disabled" : ""}>${icon("play", 14)}</button>
    </form>
  </aside>`;
}


/** Executa o que o worker pediu no painel. Ele decide abrir; o usuário vê por quê. */
async function aplicarAcoesDePainel(acoes) {
  for (const acao of acoes || []) {
    state.dock.open = true;
    if (acao.tipo === "navegador") {
      state.dock.tab = "navegador";
      renderDock();
      await dockNavigate(acao.alvo);
    } else if (acao.tipo === "software") {
      state.dock.tab = "software";
      state.dock.active = acao.alvo;
      renderDock();
      await loadDockTab("software");
    }
    if (acao.motivo) toast(`Worker abriu o painel: ${acao.motivo}`);
  }
}

async function sendChat(text) {
  const content = String(text || "").trim();
  if (!content || state.chat.busy) return;
  state.chat.messages.push({ role: "user", content });
  state.chat.draft = "";
  state.chat.busy = true;
  state.chat.proposal = null;
  state.chat.tools = [];
  renderWorkflow();
  try {
    const answer = await api("/api/agent/chat", {
      method: "POST",
      body: { messages: state.chat.messages.slice(-20), graph: state.graph },
    });
    state.chat.messages.push({ role: "assistant", content: answer.reply || "" });
    state.chat.proposal = answer.proposal || null;
    state.chat.summary = answer.summary || "";
    state.chat.tools = answer.tools || [];
    // O worker pode ter pedido o painel: navegador para pesquisar, software para operar.
    if (answer.painel_acoes?.length) aplicarAcoesDePainel(answer.painel_acoes);
  } catch (error) {
    state.chat.messages.push({ role: "assistant", content: `Falhou: ${error.message}` });
  } finally {
    state.chat.busy = false;
    renderWorkflow();
    const body = $("#chat-body");
    if (body) body.scrollTop = body.scrollHeight;
  }
}

function applyProposal() {
  const proposal = state.chat.proposal;
  if (!proposal) return;
  pushHistory();
  state.graph = deepCopy(proposal);
  state.chat.proposal = null;
  state.dirty = true;
  renderWorkflow();
  autoLayout();
  toast("Proposta aplicada no canvas");
}

function bindChat() {
  $("[data-chat-close]")?.addEventListener("click", () => { state.chat.open = false; renderWorkflow(); });
  $("[data-chat-apply]")?.addEventListener("click", applyProposal);
  $("[data-chat-discard]")?.addEventListener("click", () => { state.chat.proposal = null; renderWorkflow(); });
  $$("[data-chat-example]").forEach(button => button.addEventListener("click", () => sendChat(button.dataset.chatExample)));
  const draft = $("#chat-draft");
  draft?.addEventListener("input", event => { state.chat.draft = event.target.value; });
  draft?.addEventListener("keydown", event => {
    event.stopPropagation();
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendChat(state.chat.draft); }
  });
  $("#chat-form")?.addEventListener("submit", event => { event.preventDefault(); sendChat(state.chat.draft); });
  $("#chat-panel")?.addEventListener("pointerdown", event => event.stopPropagation());
}


/** Miniatura gerada do próprio nó: ícone da categoria e as portas com suas cores.
 *  Escala para qualquer quantidade de nós sem alguém desenhar arte para cada um. */
function paletteItemHtml(item) {
  const inputs = parsePorts(item.inputs).slice(0, 4);
  const outputs = parsePorts(item.outputs).slice(0, 4);
  const dots = ports => ports.map(port =>
    `<i style="background:${portMeta(port.type).color}" title="${escapeHtml(portMeta(port.type).label)}"></i>`).join("");
  return `<button class="palette-node" draggable="true" data-add-node="${item.type}" title="${escapeHtml(item.description)}" aria-label="${escapeHtml(item.description)}">
    <span class="palette-thumb" data-cat="${escapeHtml(item.category)}">
      <span class="thumb-in">${dots(inputs)}</span>
      ${icon(CATEGORY_ICONS[item.category] || "utilidades", 15)}
      <span class="thumb-out">${dots(outputs)}</span>
    </span>
    <span class="palette-copy"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></span>
  </button>`;
}

function palettePopoverHtml(groups) {
  return `<div class="palette-popover" id="palette-popover">
    <div class="palette-popover-head">
      <input class="input palette-search" id="palette-search" placeholder="Buscar nó…" value="${escapeHtml(state.paletteQuery)}" autofocus>
      <button class="pill-btn" data-palette-toggle aria-label="Fechar">${icon("close")}</button>
    </div>
    <div class="palette-popover-body">
      ${Object.entries(groups).map(([category, items]) => {
        const collapsed = state.collapsedCategories.has(category);
        return `<div class="palette-group ${collapsed ? "collapsed" : ""}">
          <h3 data-toggle-category="${escapeHtml(category)}"><span class="palette-icon">${icon(CATEGORY_ICONS[category] || "utilidades", 13)}</span>${escapeHtml(category)}<span class="palette-count">${items.length}</span></h3>
          ${items.map(item => paletteItemHtml(item)).join("")}
        </div>`;
      }).join("") || `<div class="palette-empty muted">Nenhum nó corresponde à busca.</div>`}
    </div>
  </div>`;
}

function nodeToolbarHtml(node, asset) {
  return `<div class="node-toolbar float-pill" id="node-toolbar" data-toolbar-node="${escapeHtml(node.id)}">
    <button class="pill-btn wide accent" data-node-action="run" title="Executa este nó e tudo que ele depende" aria-label="Executa este nó e tudo que ele depende">${icon("play", 14)} Executar até aqui</button>
    <span class="pill-divider"></span>
    <button class="pill-btn" data-node-action="duplicate" title="Duplicar" aria-label="Duplicar">${icon("copy")}</button>
    <button class="pill-btn" data-node-action="rename" title="Renomear" aria-label="Renomear">${icon("rename")}</button>
    <button class="pill-btn" data-node-action="disconnect" title="Remover conexões" aria-label="Remover conexões">${icon("unlink")}</button>
    ${asset ? `<a class="pill-btn" href="/media/${asset.id}" target="_blank" rel="noopener" title="Abrir resultado">${icon("download")}</a>` : ""}
    <button class="pill-btn danger" data-node-action="delete" title="Excluir" aria-label="Excluir">${icon("trash")}</button>
  </div>`;
}

function promptBarHtml() {
  const kind = state.promptDraft.kind;
  const profiles = Object.entries(state.profiles).filter(([, profile]) => profile.kind === kind);
  const busy = state.busy.has("run-node");
  return `<form class="prompt-bar" id="prompt-bar">
    <div class="prompt-kind">
      <button type="button" class="kind-btn ${kind === "image" ? "active" : ""}" data-prompt-kind="image">${icon("imagem", 14)} Imagem</button>
      <button type="button" class="kind-btn ${kind === "video" ? "active" : ""}" data-prompt-kind="video">${icon("video", 14)} Vídeo</button>
    </div>
    <input class="prompt-input" id="prompt-input" placeholder="Descreva a cena e gere direto no canvas…" value="${escapeHtml(state.promptDraft.text)}" autocomplete="off">
    <select class="prompt-profile" id="prompt-profile" aria-label="Perfil de modelo">
      ${profiles.length
        ? profiles.map(([id, profile]) => `<option value="${id}" ${id === state.promptDraft.profile ? "selected" : ""}>${escapeHtml(profile.label || id)}${profile.ready ? "" : " · faltam arquivos"}</option>`).join("")
        : `<option value="">nenhum perfil ${escapeHtml(kind)}</option>`}
    </select>
    <button class="prompt-go" type="submit" ${busy ? "disabled" : ""}>${busy ? "…" : "Gerar"}</button>
  </form>`;
}

/** Campos que ficam sempre à vista no card; o resto vai para "Ajustes". */
function isPrimaryField(field) {
  return field.type === "textarea" || field.type === "asset" || field.type === "model_profile";
}


/** Regra de visibilidade declarada no catálogo: {"engine":"comfyui"} ou {"any":[...]}. */
function fieldVisible(field, config) {
  const rule = field.show_if;
  if (!rule) return true;
  const matches = clause => Object.entries(clause).every(([key, value]) => String(config?.[key]) === String(value));
  if (Array.isArray(rule.any)) return rule.any.some(matches);
  if (Array.isArray(rule.all)) return rule.all.every(matches);
  return matches(rule);
}

const RATIO_VALUES = {
  "1:1": 1, "4:5": 0.8, "9:16": 0.5625, "2:3": 0.6667, "3:2": 1.5,
  "4:3": 1.3333, "16:9": 1.7778, "1.85:1": 1.85, "2:1": 2, "2.39:1": 2.39, "21:9": 2.3333,
};

/** Proporção como retângulo desenhado: a forma é a informação. */
function ratioPickerHtml(node, field, value) {
  const options = (field.options || []).filter(option => option !== "manual");
  return `<div class="nf nf-wide"><span>${escapeHtml(field.label)}</span>
    <div class="ratio-grid" data-ratio-node="${escapeHtml(node.id)}" data-ratio-field="${escapeHtml(field.key)}">
      ${options.map(option => {
        const ratio = RATIO_VALUES[option] || 1;
        const width = ratio >= 1 ? 26 : Math.round(26 * ratio);
        const height = ratio >= 1 ? Math.round(26 / ratio) : 26;
        return `<button type="button" class="ratio-chip ${String(value) === option ? "active" : ""}" data-ratio-value="${escapeHtml(option)}" title="${escapeHtml(option)}" aria-label="${escapeHtml(option)}">
          <i style="width:${width}px;height:${height}px"></i><b>${escapeHtml(option)}</b></button>`;
      }).join("")}
      <button type="button" class="ratio-chip ${String(value) === "manual" ? "active" : ""}" data-ratio-value="manual" title="Largura e altura manuais" aria-label="Largura e altura manuais">
        <i class="manual"></i><b>manual</b></button>
    </div></div>`;
}

/** Poucas opções viram botões lado a lado; ninguém deve abrir menu para escolher entre três. */
function chipsHtml(node, field, value) {
  const options = field.options || [];
  return `<div class="nf nf-wide"><span>${escapeHtml(field.label)}</span>
    <div class="chip-row" data-chips-node="${escapeHtml(node.id)}" data-chips-field="${escapeHtml(field.key)}">
      ${options.map(option => `<button type="button" class="chip ${String(option) === String(value) ? "active" : ""}" data-chip-value="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join("")}
    </div></div>`;
}

function seedHtml(node, field, value) {
  const current = value ?? field.default ?? -1;
  const aleatoria = String(current) === "-1";
  return `<div class="nf"><span>${escapeHtml(field.label)}</span>
    <div class="seed-wrap">
      <input class="nf-input" type="number" value="${escapeHtml(current)}" data-inline-node="${escapeHtml(node.id)}" data-inline-field="${escapeHtml(field.key)}">
      <button type="button" class="seed-btn ${aleatoria ? "active" : ""}" data-seed-node="${escapeHtml(node.id)}" data-seed-field="${escapeHtml(field.key)}" title="${aleatoria ? "Aleatória a cada execução" : "Sortear uma seed"}" aria-label="${aleatoria ? "Aleatória a cada execução" : "Sortear uma seed"}">${icon("dice", 14)}</button>
    </div></div>`;
}


/** Lista longa não cabe em chips: vira um campo com busca e grade de opções. */
function pickerHtml(node, field, value) {
  const key = escapeHtml(field.key);
  const open = state.openPicker?.node === node.id && state.openPicker?.field === field.key;
  const query = (open ? state.openPicker.query : "") || "";
  const options = (field.options || []).filter(option =>
    !query || String(option).toLowerCase().includes(query.toLowerCase()));
  return `<div class="nf nf-wide nf-picker"><span>${escapeHtml(field.label)}</span>
    <button type="button" class="picker-value ${open ? "open" : ""}" data-picker-node="${escapeHtml(node.id)}" data-picker-field="${key}">
      <strong>${escapeHtml(value ?? field.default ?? "—")}</strong>${icon("chevron", 12)}
    </button>
    ${open ? `<div class="picker-pop">
      <input class="picker-search" placeholder="Buscar…" value="${escapeHtml(query)}" data-picker-search autofocus>
      <div class="picker-grid">
        ${options.length ? options.map(option => `<button type="button" class="picker-item ${String(option) === String(value) ? "active" : ""}" data-picker-pick="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join("")
          : `<div class="picker-empty">nada encontrado</div>`}
      </div>
    </div>` : ""}
  </div>`;
}

function inlineFieldHtml(node, field, value) {
  const key = escapeHtml(field.key);
  const label = escapeHtml(field.label);
  const attrs = `data-inline-node="${escapeHtml(node.id)}" data-inline-field="${key}"`;

  if (field.ui === "ratio") return ratioPickerHtml(node, field, value);
  if (field.ui === "chips") return chipsHtml(node, field, value);
  if (field.ui === "picker") return pickerHtml(node, field, value);
  if (field.ui === "seed") return seedHtml(node, field, value);

  if (field.type === "textarea") {
    return `<label class="nf nf-wide"><span>${label}</span><textarea class="nf-textarea" rows="3" ${attrs} placeholder="${label}">${escapeHtml(value ?? "")}</textarea></label>`;
  }
  if (field.type === "json") {
    return `<label class="nf nf-wide"><span>${label}</span><textarea class="nf-textarea mono" rows="2" ${attrs} data-json-field>${escapeHtml(JSON.stringify(value ?? {}, null, 1))}</textarea></label>`;
  }
  if (field.type === "select") {
    return `<label class="nf"><span>${label}</span><select class="nf-input" ${attrs}>${(field.options || []).map(option => `<option value="${escapeHtml(option)}" ${String(option) === String(value) ? "selected" : ""}>${escapeHtml(option)}</option>`).join("")}</select></label>`;
  }
  if (field.type === "model_profile") {
    // Perfil não é só um nome: o que importa é se os pesos estão no disco.
    // Cada opção mostra o próprio estado, para o erro aparecer antes de executar.
    const profiles = Object.entries(state.profiles).filter(([, profile]) => !field.kind || profile.kind === field.kind);
    if (!profiles.length) {
      return `<div class="nf nf-wide"><span>${label}</span><div class="profile-empty">nenhum perfil ${escapeHtml(field.kind || "")} instalado</div></div>`;
    }
    return `<div class="nf nf-wide"><span>${label}</span>
      <div class="profile-grid" data-profile-node="${escapeHtml(node.id)}" data-profile-field="${key}">
        ${profiles.map(([id, profile]) => `<button type="button" class="profile-card ${id === value ? "active" : ""} ${profile.ready ? "pronto" : "faltando"}" data-profile-value="${escapeHtml(id)}" title="${profile.ready ? "Pesos presentes" : `${(profile.missing_files || []).length} arquivo(s) ausente(s)`}" aria-label="${profile.ready ? "Pesos presentes" : `${(profile.missing_files || []).length} arquivo(s) ausente(s)`}">
          <i></i><strong>${escapeHtml(profile.label || id)}</strong>
          <small>${profile.ready ? "pronto" : `faltam ${(profile.missing_files || []).length}`}</small>
        </button>`).join("")}
      </div></div>`;
  }
  if (field.type === "asset") {
    const asset = state.assets.find(item => item.id === value);
    return `<div class="nf nf-wide"><span>${label}</span>
      <div class="nf-drop ${asset ? "filled" : ""}" data-drop-node="${escapeHtml(node.id)}" data-drop-field="${key}">
        ${asset
          ? `<div class="nf-drop-thumb">${assetPreviewHtml(asset)}</div><div class="nf-drop-meta"><strong>${escapeHtml(asset.original_name || asset.id)}</strong><small>${formatBytes(asset.size_bytes)}</small></div>`
          : `<div class="nf-drop-empty">${icon("upload", 15)}Arraste um arquivo aqui<small>ou clique para escolher</small></div>`}
      </div>
      <select class="nf-input" ${attrs}><option value="">— nenhum —</option>${state.assets.map(item => `<option value="${item.id}" ${item.id === value ? "selected" : ""}>${escapeHtml(item.original_name || item.id)}</option>`).join("")}</select>
    </div>`;
  }
  if (field.type === "number") {
    const hasRange = field.min != null && field.max != null;
    const step = field.step ?? 1;
    const current = Number(value ?? field.default ?? field.min ?? 0);
    // Faixa curta e fracionária vira knob; faixa longa vira slider. Os dois com leitura editável.
    const isKnob = hasRange && step < 1 && (field.max - field.min) <= 8;
    if (isKnob) {
      const turn = (((current - field.min) / (field.max - field.min)) * 270 - 135).toFixed(1);
      return `<div class="nf nf-knob"><span>${label}</span>
        <div class="knob-wrap">
          <div class="knob" data-knob style="--knob-turn:${turn}deg"><i></i></div>
          <input class="nf-input knob-value" type="number" value="${escapeHtml(current)}" min="${field.min}" max="${field.max}" step="${step}" ${attrs}>
        </div></div>`;
    }
    if (hasRange) {
      const fill = (((current - field.min) / (field.max - field.min)) * 100).toFixed(1);
      return `<div class="nf nf-slider"><span>${label}</span>
        <div class="slider-wrap">
          <input class="nf-range" type="range" min="${field.min}" max="${field.max}" step="${step}" value="${escapeHtml(current)}" style="--fill:${fill}%">
          <input class="nf-input slider-value" type="number" value="${escapeHtml(current)}" min="${field.min}" max="${field.max}" step="${step}" ${attrs}>
        </div></div>`;
    }
    return `<label class="nf"><span>${label}</span><input class="nf-input" type="number" value="${escapeHtml(value ?? "")}" ${attrs}></label>`;
  }
  return `<label class="nf"><span>${label}</span><input class="nf-input" type="text" value="${escapeHtml(value ?? "")}" ${attrs}></label>`;
}


/** Ícone por natureza do campo. O usuário reconhece o tipo antes de abrir o painel. */
const FIELD_ICON = {
  select: "lote", number: "escopo", text: "texto", textarea: "texto",
  json: "codigo", path: "entrada", asset: "imagem", model_profile: "processador",
  boolean: "concluido",
};
const FIELD_ICON_BY_KEY = {
  seed: "cache", steps: "escopo", fps: "video", frames: "video",
  width: "lente", height: "lente", aspect_ratio: "lente", resolution: "lente",
  quality: "evidencia", engine: "processador", camera_motion: "camera",
  camera_look: "luz", negative_prompt: "erro", workflow_path: "entrada",
};

/** Resumo iconizado: mostra o que existe no avançado sem precisar abrir. */
function advGlanceHtml(node, advanced) {
  const alterados = advanced.filter(field => {
    const atual = node.config?.[field.key];
    return atual !== undefined && atual !== null && atual !== "" && String(atual) !== String(field.default ?? "");
  });
  const mostrados = advanced.slice(0, 7);
  return `<span class="adv-glance">
    ${mostrados.map(field => {
      const preenchido = alterados.some(other => other.key === field.key);
      const nome = FIELD_ICON_BY_KEY[field.key] || FIELD_ICON[field.type] || "avancado";
      return `<i data-set="${preenchido ? 1 : 0}" title="${escapeHtml(field.label)}">${icon(nome, 11)}</i>`;
    }).join("")}
    ${advanced.length > mostrados.length ? `<i title="mais ${advanced.length - mostrados.length}">+${advanced.length - mostrados.length}</i>` : ""}
  </span>
  <span class="adv-count" data-changed="${alterados.length ? 1 : 0}" title="${alterados.length} de ${advanced.length} alterados">${alterados.length}/${advanced.length}</span>`;
}

/** Largura do cartão sai da natureza do nó, não de um número fixo por tipo. */
function nodeSizeClass(item, fields) {
  if ((item.outputs || []).length === 0 && (item.inputs || []).length <= 1) return "compacto";
  if (fields.some(field => field.type === "textarea" || field.type === "json")) return "largo";
  return "normal";
}

function nodeHtml(node, asset, runState) {
  const item = catalogItem(node.type) || { label: node.type, category: "", fields: [] };
  const fields = (item.fields || []).filter(field => fieldVisible(field, node.config));
  const primary = fields.filter(isPrimaryField);
  const advanced = fields.filter(field => !isPrimaryField(field));
  const statusClass = runState ? ` state-${runState.toLowerCase()}` : "";
  const failure = runState === "FAILED" ? nodeFailure(node.id) : null;
  const ehPreview = Boolean(asset) || node.type === "output.preview" || node.type === "media.scopes";
  const expandido = state.expandedPreviews.has(node.id);
  return `<article class="workflow-node${statusClass} ${state.selectedNodeId === node.id ? "selected" : ""}"
    data-node-id="${node.id}" data-size="${nodeSizeClass(item, fields)}"
    data-preview="${ehPreview ? 1 : 0}" data-expandido="${expandido ? 1 : 0}"
    style="left:${Number(node.position?.x || 0)}px;top:${Number(node.position?.y || 0)}px">
    ${portsHtml(node, item)}
    <div class="node-head" data-drag-handle="${node.id}">
      <span class="node-type-dot" title="${escapeHtml(item.category || "")}">${icon(CATEGORY_ICONS[item.category] || "utilidades", 13)}</span>
      <span class="node-title">${escapeHtml(item.label)}</span>
      ${runState ? `<span class="node-state ${runState}">${runState === "RUNNING" ? "…" : runState === "FAILED" ? "erro" : "ok"}</span>` : ""}
    </div>
    ${ehPreview ? `<button class="node-expand" data-expand-node="${escapeHtml(node.id)}"
      title="${expandido ? "Recolher" : "Expandir"} visualização" aria-label="${expandido ? "Recolher" : "Expandir"} visualização">${icon(expandido ? "bloqueado" : "avancado", 12)}</button>` : ""}
    ${runState === "RUNNING" ? `<div class="node-progress"><span></span></div>` : ""}
    ${asset ? `<div class="node-preview" data-node-preview="${escapeHtml(asset.id)}" title="Clique para ampliar">${assetPreviewHtml(asset)}</div>` : ""}
    ${failure ? `<div class="node-error"><strong>${escapeHtml(failure.code || "ERRO")}</strong>${escapeHtml((failure.message || "").slice(0, 180))}</div>` : ""}
    ${preflightDoNo(node.id).map(problema => `<div class="node-preflight">${icon("atencao", 12)}
      <span><strong>${escapeHtml(problema.mensagem)}</strong>${escapeHtml(problema.como_corrigir)}</span></div>`).join("")}
    <div class="node-body">
      ${primary.map(field => inlineFieldHtml(node, field, node.config?.[field.key])).join("")}
      ${advanced.length ? `<details class="node-advanced" ${state.expandedNodes.has(node.id) ? "open" : ""} data-advanced-node="${escapeHtml(node.id)}">
        <summary><span class="chev">${icon("chevron", 11)}</span>${advGlanceHtml(node, advanced)}</summary>
        <div class="nf-grid">${advanced.map(field => inlineFieldHtml(node, field, node.config?.[field.key])).join("")}</div>
      </details>` : ""}
      ${!fields.length ? `<div class="node-summary">${escapeHtml(item.description || node.type)}</div>` : ""}
      <div class="node-footer">
        <span class="node-id">${escapeHtml(node.id)}</span>
        <button class="node-run" data-node-run="${node.id}" title="Executar este nó e tudo que ele depende" aria-label="Executar este nó e tudo que ele depende">${icon("play", 12)} Rodar</button>
      </div>
    </div>
  </article>`;
}

/** Mensagem de erro do último job, associada ao nó que falhou. */
function nodeFailure(nodeId) {
  const job = projectJobs().find(item => item.status === "FAILED");
  if (!job || job.current_node_id !== nodeId) return null;
  return { code: job.error_code, message: job.error_message };
}

function jobsHtml() {
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Fila e jobs</h1><p class="page-subtitle">Fila GPU sequencial, cancelamento, retry, progresso e causa real das falhas.</p></div><button class="btn" data-action="refresh-jobs">↻ Atualizar</button></div>
  <article class="card"><div class="table-wrap"><table><thead><tr><th>ID / projeto</th><th>Status</th><th>Progresso</th><th>Início / fim</th><th>Resultado</th><th></th></tr></thead><tbody>${state.jobs.length ? state.jobs.map(job => `<tr><td><strong class="mono">${escapeHtml(job.id)}</strong><br><small class="muted">${escapeHtml(job.project_id || "workflow avulso")}</small></td><td><span class="badge ${job.status}">${job.status}</span>${job.current_node_id ? `<br><small class="muted mono">${escapeHtml(job.current_node_id)}</small>` : ""}</td><td style="min-width:170px"><div class="progress"><span style="width:${Number(job.progress || 0)}%"></span></div><small>${Number(job.progress || 0).toFixed(1)}%</small></td><td><small>${formatDate(job.started_at)}<br>${formatDate(job.finished_at)}</small></td><td>${job.error_message ? `<div class="error-state"><strong>${escapeHtml(job.error_code)}</strong><br>${escapeHtml(job.error_message)}</div>` : job.result ? `${job.result.assets?.length || 0} assets` : "—"}</td><td><div class="actions">${["QUEUED","RUNNING"].includes(job.status) ? `<button class="btn small danger" data-cancel-job="${job.id}">Cancelar</button>` : ""}${["FAILED","CANCELLED"].includes(job.status) ? `<button class="btn small" data-retry-job="${job.id}">Retry</button>` : ""}</div></td></tr>`).join("") : `<tr><td colspan="6"><div class="empty-state"><div><strong>Fila vazia</strong>Nenhum job foi criado.</div></div></td></tr>`}</tbody></table></div></article></section>`;
}

function galleryHtml() {
  const filter = state.galleryFilter;
  const collection = state.collections.find(item => item.id === filter.collection);
  const visible = collection ? (collection.items || []) : state.assets;
  const kinds = ["", "image", "video", "audio", "model3d", "file"];
  const labels = { "": "Tudo", image: "Imagens", video: "Vídeos", audio: "Áudio", model3d: "Malhas 3D", file: "Arquivos" };
  return `<section class="page" role="main">
    <div class="page-header">
      <div>
        <h1 class="page-title">${filter.deleted ? "Lixeira" : collection ? escapeHtml(collection.name) : "Galeria local"}</h1>
        <p class="page-subtitle">${filter.deleted
          ? "Assets marcados como excluídos. Restaurar traz de volta; purgar apaga o arquivo do disco."
          : "Arquivos produzidos e importados, com checksum e vínculo ao job."}</p>
      </div>
      <div class="actions">
        <button class="btn" data-upload-asset>${icon("upload")} Importar</button>
        <button class="btn ${filter.deleted ? "primary" : ""}" data-gallery-trash>${icon("trash")} Lixeira</button>
        ${filter.deleted ? `<button class="btn danger" data-gallery-empty>Esvaziar lixeira</button>` : ""}
        <button class="btn" data-action="refresh-assets">↻ Atualizar</button>
      </div>
    </div>

    <div class="gallery-toolbar">
      <label class="gallery-search">${icon("search")}<input class="input" id="gallery-search" placeholder="Buscar por nome ou ID…" value="${escapeHtml(filter.search)}"></label>
      <div class="gallery-kinds">${kinds.map(kind => `<button class="chip ${filter.kind === kind && !filter.collection ? "active" : ""}" data-gallery-kind="${kind}">${labels[kind]}</button>`).join("")}</div>
      <span class="spacer"></span>
      <div class="gallery-collections">
        ${state.collections.map(item => `<button class="chip ${filter.collection === item.id ? "active" : ""}" data-gallery-collection="${item.id}" title="${escapeHtml(item.kind)}" aria-label="${escapeHtml(item.kind)}">${escapeHtml(item.name)} <span class="chip-count">${item.item_count}</span></button>`).join("")}
        <button class="chip ghost" data-collection-create>${icon("plus")} Coleção</button>
        ${collection ? `<button class="chip danger" data-collection-delete="${collection.id}">${icon("trash")}</button>` : ""}
      </div>
    </div>

    ${visible.length ? `<div class="gallery">${visible.map(asset => `<article class="card asset-card ${asset.deleted_at ? "deleted" : ""}">
      <div class="asset-preview">${assetPreviewHtml(asset, { controls: true })}</div>
      <div class="asset-meta">
        <div class="asset-name"><strong>${escapeHtml(asset.original_name || asset.id)}</strong></div>
        <small class="muted">${escapeHtml(asset.kind)} · ${formatBytes(asset.size_bytes)} · ${formatDate(asset.created_at)}</small><br>
        <small class="mono subtle">${escapeHtml(asset.metadata?.sha256?.slice(0, 16) || "sem hash")}</small>
        <div class="actions" style="margin-top:8px">
          <a class="btn small" href="/media/${asset.id}" target="_blank" rel="noopener">Abrir</a>
          <button class="btn small" data-copy="${escapeHtml(asset.id)}">Copiar ID</button>
          ${collection
            ? `<button class="btn small danger" data-collection-remove="${collection.id}" data-asset="${asset.id}">Tirar</button>`
            : asset.deleted_at
              ? `<button class="btn small" data-asset-restore="${asset.id}">Restaurar</button><button class="btn small danger" data-asset-purge="${asset.id}">Apagar</button>`
              : `<button class="btn small" data-asset-collect="${asset.id}">＋ Coleção</button><button class="btn small danger" data-asset-delete="${asset.id}">Excluir</button>`}
        </div>
      </div></article>`).join("")}</div>`
      : `<div class="empty-state"><div><strong>${filter.deleted ? "Lixeira vazia" : collection ? "Coleção vazia" : "Nada encontrado"}</strong><p>${filter.search || filter.kind ? "Nenhum asset corresponde ao filtro." : "Execute um workflow ou importe um arquivo."}</p></div></div>`}
  </section>`;
}

function enginesHtml() {
  const statuses = state.engines;
  const profileEntries = Object.entries(state.profiles);
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Engines e modelos</h1><p class="page-subtitle">Detecção local real. Ausências não são convertidas em saídas simuladas.</p></div><button class="btn primary" data-action="check-engines">Verificar agora</button></div>
  <div class="grid cols-3">${statuses.length ? statuses.map(item => `<article class="card metric"><div class="metric-label">${escapeHtml(item.engine_id)}</div><div class="metric-value" style="font-size:18px"><span class="badge ${item.available ? "DONE" : "FAILED"}">${item.available ? "DISPONÍVEL" : "AUSENTE"}</span></div><div class="metric-detail mono">${escapeHtml(item.version || item.detail || "")}</div><div class="metric-detail">${escapeHtml(item.detail || "")}</div></article>`).join("") : `<article class="card metric"><div class="loading"><span class="spinner"></span>Execute a verificação.</div></article>`}</div>
  <article class="card" style="margin-top:14px"><div class="card-header"><h2>Perfis de inferência</h2><span class="muted">${escapeHtml(state.gpu?.available ? state.gpu.label : (state.gpu?.detail || "GPU não verificada"))}</span></div><div class="table-wrap"><table><thead><tr><th>Perfil</th><th>Tipo / engine</th><th>Base</th><th>Arquivos</th></tr></thead><tbody>${profileEntries.map(([id, profile]) => `<tr><td><strong>${escapeHtml(profile.label || id)}</strong><br><small class="mono muted">${escapeHtml(id)}</small></td><td>${escapeHtml(profile.kind)} · ${escapeHtml(profile.engine)}</td><td><span class="mono">${profile.defaults?.width || "?"}×${profile.defaults?.height || "?"}</span><br><small>${profile.defaults?.steps || "?"} steps</small></td><td>${profile.ready ? `<span class="badge DONE">PRONTO</span>` : `<span class="badge FAILED">${profile.missing_files?.length || 0} AUSENTES</span><details><summary>caminhos</summary><div class="mono">${(profile.missing_files || []).map(file => `<div>${escapeHtml(file.field)}: ${escapeHtml(file.path)}</div>`).join("")}</div></details>`}</td></tr>`).join("")}</tbody></table></div></article>
  <div class="error-state" style="margin-top:14px"><strong>4K/8K:</strong> gere na resolução-base eficiente do modelo e finalize por upscale em tiles. O sistema não mascara pós-processamento como geração nativa.</div>
  </section>`;
}

function governanceHtml() {
  const data = state.governance;

  // Três estados distintos, porque as três causas pedem ações diferentes: a ponte
  // caiu, a ponte respondeu vazio, ou ainda não respondeu. Antes, qualquer um dos
  // três mostrava o mesmo spinner girando para sempre.
  if (state.governanceError) return governanceErroHtml(state.governanceError);
  if (!data) return `<section class="page" role="main"><div class="loading"><span class="spinner"></span>Carregando governança…</div></section>`;
  if (data.state === "EMPTY") return governanceVaziaHtml(data);

  const pending = data.tasks.filter(task => task.status === "PENDING");
  const alerts = data.alerts.filter(alert => alert.status === "OPEN");
  const resolvidos = data.alerts.filter(alert => alert.status === "RESOLVED");

  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Governança</h1><p class="page-subtitle">Fonte única: <span class="mono">/api/governance/snapshot</span> · gerado em ${formatDate(data.generatedAt)}${state.governanceCheckedAt ? ` · lido em ${formatDate(state.governanceCheckedAt)}` : ""}</p></div><div class="actions"><span class="badge ${data.state}">${data.state}</span><button class="btn" data-action="sync-governance">Sincronizar componentes</button><button class="btn" data-action="refresh-governance">↻ Atualizar</button></div></div>
    <div class="grid cols-4">${metric("Tarefas", data.summary.totalTasks, `${data.summary.doneTasks} concluídas`)}${metric("Pendentes", data.summary.pendingTasks, "Roadmap aberto")}${metric("Alertas", data.summary.openAlerts, "Bugs, gaps e riscos")}${metric("Progresso", `${data.summary.progressPercent.toFixed(2)}%`, `${data.summary.documents} documentos`)}</div>
    <div class="grid cols-4" style="margin-top:14px">${metric("Decisões", data.summary.decisions ?? 0, "ADRs registrados")}${metric("Open source", data.summary.opensource ?? 0, `${data.summary.opensourcePendentes ?? 0} sem licença conferida`)}${metric("Auditorias", data.summary.audits ?? 0, data.summary.lastAudit ? `última: ${data.summary.lastAudit}` : "nenhuma registrada")}${metric("Alertas fechados", resolvidos.length, "histórico preservado")}</div>
    ${modulesPanelHtml()}
    <div class="split" style="margin-top:14px"><article class="card"><div class="card-header"><h2>Tarefas por módulo</h2></div><div class="card-body">${data.modules.map(module => `<div class="module-row"><span><strong>${escapeHtml(module.module_id)}</strong> · ${escapeHtml(module.module_title)}</span><div class="progress"><span style="width:${module.total ? module.done/module.total*100 : 0}%"></span></div><span>${module.done}/${module.total}</span></div>`).join("")}</div></article>
    <article class="card"><div class="card-header"><h2>Alertas abertos</h2><span class="badge ${alerts.length ? "HIGH" : "DONE"}">${alerts.length}</span></div><div class="card-body">${alerts.length ? alerts.map(alertaHtml).join("") : `<span class="badge DONE">Nenhum alerta aberto</span>`}</div></article></div>
    <article class="card" style="margin-top:14px"><div class="card-header"><h2>Todo task e roadmap</h2><span class="muted">${pending.length} pendentes</span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Módulo</th><th>Camada</th><th>Prioridade</th><th>Tarefa</th><th>Fonte</th><th>Status</th></tr></thead><tbody>${data.tasks.map(task => `<tr><td class="mono">${escapeHtml(task.id)}</td><td>${escapeHtml(task.category)}</td><td>${escapeHtml(task.camada || "—")}</td><td><span class="badge ${escapeHtml(task.priority || "MEDIUM")}">${escapeHtml(task.priority || "MEDIUM")}</span></td><td>${escapeHtml(task.title)}</td><td class="mono">${escapeHtml(task.source_path)}:${task.source_line}</td><td><button class="badge ${task.status}" data-toggle-task="${task.id}" data-task-status="${task.status}">${task.status}</button></td></tr>`).join("")}</tbody></table></div></article>
    ${decisoesHtml(data.decisions || [])}
    ${opensourceHtml(data.opensource || [])}
    ${auditoriasHtml(data.audits || [])}
    <div class="grid cols-2" style="margin-top:14px"><article class="card"><div class="card-header"><h2>Changelog</h2></div><div class="card-body">${data.changelog.map(change => `<div class="module-row"><strong>v${escapeHtml(change.release)}</strong><span>${escapeHtml(change.category)} · ${escapeHtml(change.description)}</span><span class="mono">L${change.source_line}</span></div>`).join("")}</div></article>
    <article class="card"><div class="card-header"><h2>Logs de governança</h2></div><div class="card-body log-list">${data.logs.slice(0,60).map(log => `<div class="log-row ${log.level}"><strong>${escapeHtml(log.level)} · ${escapeHtml(log.event)}</strong><br><small class="muted">${formatDate(log.created_at)}</small><div class="mono subtle">${escapeHtml(JSON.stringify(log.detail))}</div></div>`).join("")}</div></article></div>
    ${resolvidos.length ? `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Alertas resolvidos</h2><span class="badge DONE">${resolvidos.length}</span></div><div class="card-body">${resolvidos.map(alertaHtml).join("")}</div></article>` : ""}
    <article class="card" style="margin-top:14px"><div class="card-header"><h2>Documentação sincronizada</h2></div><div class="card-body actions">${data.documents.map(doc => `<a class="btn" href="${escapeHtml(doc.link.replace('/docs/','/docs-files/'))}" target="_blank" rel="noopener">${escapeHtml(doc.name)}</a>`).join("")}</div></article>
  </section>`;
}

function governanceErroHtml(mensagem) {
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Governança</h1><p class="page-subtitle">A ponte de governança não respondeu</p></div><div class="actions"><span class="badge CRITICAL">INDISPONÍVEL</span><button class="btn primary" data-action="refresh-governance">↻ Tentar de novo</button></div></div>
    <article class="card"><div class="card-header"><h2>O que aconteceu</h2></div><div class="card-body">
      <p class="mono">${escapeHtml(mensagem)}</p>
      <p class="muted" style="margin-top:10px">A tela não mostra dado antigo enquanto a fonte está fora. Um painel de governança que exibe número velho como se fosse atual é pior do que um painel vazio.</p>
      <div class="actions" style="margin-top:12px"><span class="mono subtle">GET /api/governance/snapshot</span>${state.governanceCheckedAt ? `<span class="muted">última tentativa ${formatDate(state.governanceCheckedAt)}</span>` : ""}</div>
    </div></article></section>`;
}

function governanceVaziaHtml(data) {
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Governança</h1><p class="page-subtitle">A fonte respondeu, e não há nada registrado</p></div><div class="actions"><span class="badge EMPTY">VAZIA</span><button class="btn primary" data-action="sync-governance">Sincronizar componentes</button><button class="btn" data-action="refresh-governance">↻ Atualizar</button></div></div>
    <article class="card"><div class="card-header"><h2>Nenhuma tarefa registrada</h2></div><div class="card-body">
      <p class="muted">O banco está acessível e a semente de governança não rodou, ou foi apagada. Sincronizar registra os componentes que o sistema carrega e abre alerta para cada licença pendente.</p>
      <p class="mono subtle" style="margin-top:10px">gerado em ${formatDate(data.generatedAt)}</p>
    </div></article></section>`;
}

function alertaHtml(alert) {
  const aberto = alert.status === "OPEN";
  const detalhe = [
    alert.origem ? `<div><span class="muted">Origem:</span> <span class="mono">${escapeHtml(alert.origem)}</span></div>` : "",
    alert.causa ? `<div><span class="muted">Causa:</span> ${escapeHtml(alert.causa)}</div>` : "",
    alert.impacto ? `<div><span class="muted">Impacto:</span> ${escapeHtml(alert.impacto)}</div>` : "",
    alert.task_id ? `<div><span class="muted">Tarefa:</span> <span class="mono">${escapeHtml(alert.task_id)}</span></div>` : "",
    alert.teste ? `<div><span class="muted">Teste:</span> <span class="mono">${escapeHtml(alert.teste)}</span></div>` : "",
    (alert.arquivos || []).length ? `<div><span class="muted">Arquivos:</span> <span class="mono">${escapeHtml(alert.arquivos.join(", "))}</span></div>` : "",
    alert.resultado ? `<div><span class="muted">Resultado:</span> ${escapeHtml(alert.resultado)}</div>` : "",
  ].filter(Boolean).join("");
  return `<div class="alert ${escapeHtml(alert.severity)}"><h4>${escapeHtml(alert.id)} · ${escapeHtml(alert.severity)} · ${escapeHtml(alert.kind)}</h4>
    <p>${escapeHtml(alert.fact)}</p>
    <p><strong>Ação:</strong> ${escapeHtml(alert.action)}</p>
    ${detalhe ? `<div class="subtle" style="margin-top:8px">${detalhe}</div>` : ""}
    <div class="actions" style="margin-top:10px"><button class="btn small" data-alert="${escapeHtml(alert.id)}" data-alert-status="${aberto ? "RESOLVED" : "OPEN"}">${aberto ? "Marcar como resolvido" : "Reabrir"}</button></div></div>`;
}

function decisoesHtml(decisoes) {
  if (!decisoes.length) return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Decisões técnicas</h2><span class="badge EMPTY">0</span></div><div class="card-body"><p class="muted">Nenhuma decisão registrada. Uma arquitetura sem decisão registrada é uma arquitetura que ninguém consegue questionar nem defender.</p></div></article>`;
  return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Decisões técnicas</h2><span class="badge DONE">${decisoes.length}</span></div><div class="table-wrap"><table><thead><tr><th>ID</th><th>Título</th><th>Estado</th><th>Módulos</th><th>Documento</th></tr></thead><tbody>${decisoes.map(item => `<tr><td class="mono">${escapeHtml(item.id)}</td><td>${escapeHtml(item.titulo)}</td><td><span class="badge ${escapeHtml(item.estado)}">${escapeHtml(item.estado)}</span></td><td class="mono">${escapeHtml((item.modulos || []).join(", ") || "—")}</td><td class="mono subtle">${escapeHtml(item.documento || "—")}</td></tr>`).join("")}</tbody></table></div></article>`;
}

function opensourceHtml(componentes) {
  if (!componentes.length) return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Open source e licenças</h2><span class="badge EMPTY">0</span></div><div class="card-body"><p class="muted">Nenhum componente registrado. Clique em <strong>Sincronizar componentes</strong> para ler o registro de modelos e gravar origem, licença e uso comercial.</p></div></article>`;
  const semConferir = componentes.filter(item => !item.conferido).length;
  return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Open source e licenças</h2><span class="badge ${semConferir ? "MEDIUM" : "DONE"}">${componentes.length} · ${semConferir} sem conferir</span></div><div class="table-wrap"><table><thead><tr><th>Componente</th><th>Licença</th><th>Comercial</th><th>Integração</th><th>Redistribuído</th><th>Conferido</th></tr></thead><tbody>${componentes.map(item => `<tr><td><strong>${escapeHtml(item.nome)}</strong><br><span class="mono subtle">${escapeHtml(item.origem)}</span></td><td><span class="badge ${item.licenca === "UNKNOWN_BLOCKED" ? "HIGH" : "DONE"}">${escapeHtml(item.spdx || item.licenca)}</span></td><td>${escapeHtml(item.uso_comercial)}</td><td class="mono">${escapeHtml(item.integracao || "—")}</td><td>${item.redistribuido ? `<span class="badge HIGH">sim</span>` : `<span class="badge DONE">não</span>`}</td><td>${item.conferido ? `<span class="badge DONE">no disco</span>` : `<span class="badge MEDIUM">card upstream</span>`}</td></tr>`).join("")}</tbody></table></div></article>`;
}

function auditoriasHtml(auditorias) {
  if (!auditorias.length) return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Histórico de auditorias</h2><span class="badge EMPTY">0</span></div><div class="card-body"><p class="muted">Nenhuma auditoria registrada. Sem histórico, cada rodada recomeça do zero e regressão nenhuma é detectável.</p></div></article>`;
  return `<article class="card" style="margin-top:14px"><div class="card-header"><h2>Histórico de auditorias</h2><span class="badge ${auditorias[0].resultado === "APROVADA" ? "DONE" : "HIGH"}">${auditorias.length}</span></div><div class="table-wrap"><table><thead><tr><th>Quando</th><th>Sessão</th><th>Itens</th><th>Falhas</th><th>Corrigidas</th><th>Testes</th><th>Resultado</th></tr></thead><tbody>${auditorias.map(item => `<tr><td>${formatDate(item.executado_em)}</td><td><strong>${escapeHtml(item.sessao)}</strong><br><span class="subtle">${escapeHtml(item.escopo || "")}</span></td><td>${item.itens_auditados}</td><td>${item.falhas_encontradas}</td><td>${item.falhas_corrigidas}</td><td class="mono">${item.testes_verdes}/${item.testes_total}</td><td><span class="badge ${item.resultado === "APROVADA" ? "DONE" : "HIGH"}">${escapeHtml(item.resultado)}</span></td></tr>`).join("")}</tbody></table></div></article>`;
}

function settingsHtml() {
  if (!state.settings) return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Configurações</h1></div></div><button class="btn primary" data-action="load-settings">Carregar configurações</button></section>`;
  const engines = state.settings.engines || {};
  const profiles = state.settings.model_profiles || {};
  return `<section class="page" role="main"><div class="page-header"><div><h1 class="page-title">Configurações do superadministrador</h1><p class="page-subtitle">Paths locais, providers, modelos, backup e operação. Segredos reais não são exibidos.</p></div><button class="btn primary" data-action="save-settings">Salvar alterações</button></div>
    <div class="grid cols-2"><article class="card"><div class="card-header"><h2>Engines</h2></div><div class="card-body"><label class="field"><span class="field-label">Configuração JSON</span><textarea id="settings-engines" class="textarea code-editor">${escapeHtml(JSON.stringify(engines,null,2))}</textarea></label></div></article>
    <article class="card"><div class="card-header"><h2>Perfis de modelos</h2></div><div class="card-body"><label class="field"><span class="field-label">Configuração JSON</span><textarea id="settings-profiles" class="textarea code-editor">${escapeHtml(JSON.stringify(profiles,null,2))}</textarea></label></div></article></div>
    <div class="grid cols-2" style="margin-top:14px"><article class="card"><div class="card-header"><h2>Dados e recuperação</h2></div><div class="card-body"><div class="actions"><button class="btn" data-action="create-backup">Criar backup completo</button><button class="btn" data-action="list-backups">Listar backups</button></div><div id="backup-results" class="mono muted" style="margin-top:12px"></div></div></article>
    <article class="card"><div class="card-header"><h2>Caminhos locais</h2></div><div class="card-body mono">${Object.entries(state.bootstrap.paths || {}).map(([key,value]) => `<div style="margin-bottom:8px"><strong>${escapeHtml(key)}</strong><br><span class="muted">${escapeHtml(value)}</span></div>`).join("")}</div></article></div>
    <article class="card" style="margin-top:14px"><div class="card-header"><h2>Governança da conta</h2></div><div class="card-body actions"><button class="btn" data-route="governance">Changelog</button><button class="btn" data-route="governance">Roadmap</button><button class="btn" data-route="governance">Tasks</button><button class="btn" data-route="governance">Alertas e logs</button></div></article>
  </section>`;
}

function bindRoute() {
  $$("[data-route]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.route)));
  $$("[data-action='new-project']").forEach(button => button.addEventListener("click", openNewProjectModal));
  $$('[data-open-project]').forEach(button => button.addEventListener("click", () => { selectProject(button.dataset.openProject); navigate("workflow"); }));
  $$('[data-delete-project]').forEach(button => button.addEventListener("click", () => deleteProject(button.dataset.deleteProject)));
  $$('[data-upload-asset]').forEach(button => button.addEventListener("click", () => uploadInput.click()));
  $$('[data-copy]').forEach(button => button.addEventListener("click", () => navigator.clipboard.writeText(button.dataset.copy).then(() => toast("ID copiado"))));
  $("[data-action='refresh-jobs']")?.addEventListener("click", refreshJobs);
  $("[data-action='refresh-assets']")?.addEventListener("click", refreshAssets);
  $("[data-action='check-engines']")?.addEventListener("click", checkEngines);
  $("[data-action='refresh-governance']")?.addEventListener("click", () => refreshGovernance(true));
  $("[data-action='sync-governance']")?.addEventListener("click", sincronizarGovernanca);
  $$("[data-alert]").forEach(btn => btn.addEventListener("click", () => resolverAlerta(btn.dataset.alert, btn.dataset.alertStatus)));
  $("[data-action='load-settings']")?.addEventListener("click", loadSettings);
  $("[data-action='save-settings']")?.addEventListener("click", saveSettings);
  $("[data-action='create-backup']")?.addEventListener("click", createBackup);
  $("[data-action='list-backups']")?.addEventListener("click", listBackups);
  $$('[data-cancel-job]').forEach(button => button.addEventListener("click", () => cancelJob(button.dataset.cancelJob)));
  $$('[data-retry-job]').forEach(button => button.addEventListener("click", () => retryJob(button.dataset.retryJob)));
  $$('[data-toggle-task]').forEach(button => button.addEventListener("click", () => toggleTask(button.dataset.toggleTask, button.dataset.taskStatus)));
  $("#gallery-search")?.addEventListener("input", event => {
    state.galleryFilter.search = event.target.value;
    state.galleryFilter.collection = "";
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(() => refreshAssets(), 250);
  });
  $$('[data-gallery-kind]').forEach(button => button.addEventListener("click", () => {
    state.galleryFilter.kind = button.dataset.galleryKind;
    state.galleryFilter.collection = "";
    refreshAssets();
  }));
  $$('[data-gallery-collection]').forEach(button => button.addEventListener("click", () => {
    state.galleryFilter.collection = state.galleryFilter.collection === button.dataset.galleryCollection ? "" : button.dataset.galleryCollection;
    render();
  }));
  $("[data-gallery-trash]")?.addEventListener("click", () => {
    state.galleryFilter.deleted = !state.galleryFilter.deleted;
    state.galleryFilter.collection = "";
    refreshAssets();
  });
  $("[data-gallery-empty]")?.addEventListener("click", emptyTrash);
  $("[data-collection-create]")?.addEventListener("click", createCollection);
  $("[data-collection-delete]")?.addEventListener("click", event => deleteCollection(event.currentTarget.dataset.collectionDelete));
  $$('[data-collection-remove]').forEach(button => button.addEventListener("click", () => removeFromCollection(button.dataset.collectionRemove, button.dataset.asset)));
  $$('[data-asset-delete]').forEach(button => button.addEventListener("click", () => deleteAsset(button.dataset.assetDelete)));
  $$('[data-asset-restore]').forEach(button => button.addEventListener("click", () => restoreAsset(button.dataset.assetRestore)));
  $$('[data-asset-purge]').forEach(button => button.addEventListener("click", () => purgeAsset(button.dataset.assetPurge)));
  $$('[data-asset-collect]').forEach(button => button.addEventListener("click", () => addAssetToCollection(button.dataset.assetCollect)));
  // Redesenha depois de carregar: sem isso os chips de coleção só apareceriam
  // no próximo render. Não entra em laço porque a lista deixa de estar vazia.
  if (state.route === "gallery" && !state.collections.length) refreshCollections();
  if (state.route === "workflow") bindWorkflow();
  if (state.route === "settings" && !state.settings) loadSettings(false);
  if (state.route === "engines" && (!state.engines.length || !Object.keys(state.profiles).length)) checkEngines(false);
}

function openNewProjectModal() {
  modalRoot.innerHTML = `<div class="modal-backdrop"><form class="modal" id="new-project-form"><div class="modal-head"><h2>Novo projeto</h2><button type="button" class="btn ghost" data-close-modal>${icon("close")}</button></div><div class="modal-body"><label class="field"><span class="field-label">Nome</span><input class="input" name="name" required maxlength="160" autofocus></label><label class="field"><span class="field-label">Descrição</span><textarea class="textarea" name="description" maxlength="4000"></textarea></label></div><div class="modal-actions"><button type="button" class="btn" data-close-modal>Cancelar</button><button class="btn primary">Criar</button></div></form></div>`;
  $$('[data-close-modal]', modalRoot).forEach(button => button.addEventListener("click", closeModal));
  $("#new-project-form").addEventListener("submit", async event => {
    event.preventDefault();
    const data = new FormData(event.target);
    try {
      setBusy("new-project", true);
      const project = await api("/api/projects", { method: "POST", body: { name: data.get("name"), description: data.get("description"), graph: { version: 1, nodes: [], edges: [], metadata: { template: false } } } });
      state.projects.unshift(project); selectProject(project.id); closeModal(); navigate("workflow"); toast("Projeto criado");
    } catch (error) { toast(error.message, "error"); }
    finally { setBusy("new-project", false); }
  });
}
function closeModal() { modalRoot.innerHTML = ""; }

async function selectProject(id) {
  if (state.dirty && state.currentProject && !confirm("Há alterações não salvas. Trocar de projeto mesmo assim?")) { renderTopbar(); return; }
  const project = state.projects.find(item => item.id === id);
  if (!project) return;
  state.currentProject = project;
  state.graph = deepCopy(project.graph);
  state.selectedNodeId = null; state.history = []; state.future = []; state.dirty = false;
  localStorage.setItem("cinenode.currentProjectId", id);
  refreshSnapshots(false);
  render();
}

async function deleteProject(id) {
  const project = state.projects.find(item => item.id === id);
  if (!project || !confirm(`Excluir o projeto “${project.name}”? Os assets permanecem auditáveis.`)) return;
  try { await api(`/api/projects/${id}`, { method: "DELETE" }); state.projects = state.projects.filter(item => item.id !== id); if (state.currentProject?.id === id) { state.currentProject = state.projects[0] || null; state.graph = deepCopy(state.currentProject?.graph || {version:1,nodes:[],edges:[],metadata:{}}); } render(); toast("Projeto excluído"); }
  catch (error) { toast(error.message, "error"); }
}

async function saveCurrentProject() {
  if (!state.currentProject) return;
  try {
    setBusy("save", true);
    const project = await api(`/api/projects/${state.currentProject.id}`, { method: "PUT", body: { graph: state.graph } });
    state.currentProject = project;
    state.projects = state.projects.map(item => item.id === project.id ? project : item);
    state.dirty = false;
    renderTopbar(); toast("Workflow salvo");
  } catch (error) { toast(`Falha ao salvar: ${error.message}`, "error", 8000); }
  finally { setBusy("save", false); }
}

async function runCurrentProject() {
  if (!state.currentProject) return;
  try {
    setBusy("run", true);
    if (ensurePreviewNodes({ silent: true })) renderWorkflow();

    // Pré-voo antes da fila: 10 das 23 falhas medidas eram detectáveis aqui.
    if (!state.preflightIgnorado) {
      const pf = await runPreflight();
      if (!pf.pronto) {
        renderWorkflow();
        const primeiro = pf.problemas[0];
        toast(`${primeiro.mensagem} ${primeiro.como_corrigir}`, "error", 9000);
        setBusy("run", false);
        return;
      }
    }
    state.preflightIgnorado = false;

    await saveCurrentProject();
    const validation = await api("/api/workflows/validate", { method: "POST", body: state.graph });
    if (!validation.valid) throw new Error(validation.errors.map(item => item.message).join("; "));
    const job = await api("/api/jobs", { method: "POST", body: { project_id: state.currentProject.id } });
    state.jobs.unshift(job);
    // Executar não tira o usuário do grafo: o acompanhamento acontece nos próprios
    // nós (barra de progresso, badge de estado) e no contador da barra superior.
    toast(`Job ${job.id.slice(-8)} enfileirado · acompanhe nos nós`);
    renderWorkflow();
  } catch (error) { toast(`Execução não iniciada: ${error.message}`, "error", 10000); }
  finally { setBusy("run", false); }
}

function addNode(type, position = null) {
  const item = catalogItem(type); if (!item) return;
  pushHistory();
  const wrap = $("#canvas-wrap");
  let point = position;
  if (!point) {
    const rect = wrap?.getBoundingClientRect();
    point = rect
      ? canvasPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
      : { x: 240, y: 160 };
  }
  // Sem procurar vão, o terceiro nó já nasce em cima do segundo.
  const vaga = findFreeSpot(point);
  const node = { id: newNodeId(type), type, position: vaga, config: defaultConfig(item) };
  state.graph.nodes.push(node); state.selectedNodeId = node.id; renderWorkflow();
  return node;
}


/* ---------- Painel lateral: navegador, software controlado e roteamento ---------- */

const DOCK_TABS = [
  { id: "navegador", icon: "remoto",        label: "Navegador" },
  { id: "software",  icon: "processador",   label: "Software" },
  { id: "roteamento",icon: "roteador",      label: "Roteamento" },
];

function dockHtml() {
  const dock = state.dock;
  if (!dock.open) {
    return `<button class="dock-handle" data-dock-open title="Abrir painel lateral (Ctrl+B)" aria-label="Abrir painel lateral (Ctrl+B)">
      ${icon("remoto", 16)}<span>PAINEL</span>
    </button>`;
  }
  return `<aside class="side-dock" style="width:${dock.width}px">
    <div class="dock-resizer" data-dock-resize title="Arraste para redimensionar"></div>
    <header class="dock-head">
      <nav class="dock-tabs">
        ${DOCK_TABS.map(tab => `<button class="dock-tab ${dock.tab === tab.id ? "active" : ""}"
           data-dock-tab="${tab.id}" title="${tab.label}" aria-label="${tab.label}">${icon(tab.icon, 15)}<span>${tab.label}</span></button>`).join("")}
      </nav>
      <button class="dock-close" data-dock-close title="Fechar painel (Ctrl+B)" aria-label="Fechar painel (Ctrl+B)">${icon("erro", 15)}</button>
    </header>
    <div class="dock-body">${dockPanelHtml(dock)}</div>
  </aside>`;
}

function dockPanelHtml(dock) {
  if (dock.tab === "navegador") return dockBrowserHtml(dock);
  if (dock.tab === "software") return dockSoftwareHtml(dock);
  return dockRoutingHtml(dock);
}

function dockBrowserHtml(dock) {
  const page = dock.page;
  return `<div class="dock-browser">
    <form class="dock-url" data-dock-go>
      <button type="button" data-dock-back title="Voltar" aria-label="Voltar">${icon("entrada", 14)}</button>
      <button type="button" data-dock-reload title="Recarregar" aria-label="Recarregar">${icon("laco", 14)}</button>
      <input name="url" placeholder="Buscar ou digitar endereço" value="${escapeHtml(dock.input || dock.url)}" autocomplete="off">
      <button type="submit" title="Ir" aria-label="Ir">${icon("saida", 14)}</button>
    </form>
    ${page?.titulo ? `<div class="dock-title" title="${escapeHtml(page.url)}">${escapeHtml(page.titulo)}</div>` : ""}
    ${dock.loading ? `<div class="dock-status">${icon("progresso", 13)} carregando…</div>` : ""}
    ${dock.error ? `<div class="dock-error">${icon("atencao", 14)}<div><strong>${escapeHtml(dock.error.mensagem || "Falhou")}</strong>
        <span>${escapeHtml(dock.error.como_corrigir || "")}</span></div></div>` : ""}
    ${!page
      ? `<div class="dock-empty">${icon("remoto", 22)}<p>Digite um endereço para começar.</p></div>`
      : page.embed_bloqueado
      ? `<div class="dock-reader">
           <div class="dock-reader-note">${icon("bloqueado", 13)} Este site recusa ser embutido. Mostrando o texto lido pelo servidor local.</div>
           <article>${escapeHtml(page.texto || "").slice(0, 12000)}</article>
           <div class="dock-reader-actions">
             <button class="btn small" data-dock-external>Abrir no navegador do sistema</button>
             <button class="btn small" data-dock-to-node>Enviar texto para um nó</button>
           </div>
         </div>`
      : `<iframe class="dock-frame" src="${escapeHtml(dock.url)}" referrerpolicy="no-referrer"
           sandbox="allow-scripts allow-same-origin allow-forms allow-popups"></iframe>`}
  </div>`;
}

function dockSoftwareHtml(dock) {
  if (!dock.targets.length) {
    return `<div class="dock-empty">${icon("processador", 22)}<p>Procurando softwares controláveis…</p></div>`;
  }
  const active = dock.targets.find(t => t.id === dock.active);
  return `<div class="dock-software">
    <ul class="dock-list">
      ${dock.targets.map(target => `<li class="dock-item ${dock.active === target.id ? "active" : ""}" data-target="${escapeHtml(target.id)}">
        <span class="dock-item-icon">${icon(target.icone || "processador", 16)}</span>
        <span class="dock-item-copy">
          <strong>${escapeHtml(target.nome)}</strong>
          <small>${escapeHtml(target.url)}</small>
        </span>
        <span class="dock-state" data-state="${escapeHtml(target.estado)}">${escapeHtml(target.estado)}</span>
      </li>`).join("")}
    </ul>
    ${active && active.estado === "no ar" && active.embed
      ? `<iframe class="dock-frame" src="${escapeHtml(active.url)}"
           sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"></iframe>`
      : active
        ? `<div class="dock-offline">
             ${icon(active.estado === "no ar" ? "atencao" : "bloqueado", 20)}
             <strong>${escapeHtml(active.nome)} — ${escapeHtml(active.estado)}</strong>
             ${active.estado === "no ar"
               ? `<p>Este alvo não aceita ser embutido. Abra em janela própria.</p>
                  <button class="btn small" data-open-external="${escapeHtml(active.url)}">Abrir em janela</button>`
               : `<p>Não está respondendo. Para instalar ou subir:</p>
                  <code>${escapeHtml(active.instalar || "—")}</code>`}
           </div>`
        : `<div class="dock-empty">${icon("processador", 22)}<p>Escolha um software na lista.</p></div>`}
  </div>`;
}

function dockRoutingHtml(dock) {
  const catalog = dock.catalog;
  if (!catalog) return `<div class="dock-empty">${icon("roteador", 22)}<p>Carregando roteamento…</p></div>`;
  const cfg = catalog.configuracao || {};
  return `<div class="dock-routing">
    <section class="route-openrouter">
      <label class="route-switch">
        <input type="checkbox" data-openrouter-toggle ${cfg.openrouter_enabled ? "checked" : ""}>
        <span>${icon("remoto", 14)} OpenRouter — todos os provedores</span>
      </label>
      <div class="route-key">
        <input type="password" data-openrouter-key placeholder="${cfg.openrouter_key_set ? "chave gravada nesta máquina" : "cole a chave sk-or-..."}" autocomplete="off">
        <button class="btn small primary" data-openrouter-save>Salvar</button>
      </div>
      <p class="route-note">${icon("local", 12)} A chave fica só neste computador. Nenhum nó a recebe: o gateway resolve.</p>
      ${catalog.aviso ? `<div class="dock-error">${icon("atencao", 14)}<div><strong>${escapeHtml(catalog.aviso.mensagem)}</strong>
        <span>${escapeHtml(catalog.aviso.como_corrigir || "")}</span></div></div>` : ""}
    </section>

    <section class="route-policy">
      <span class="route-label">Política</span>
      <div class="chips">
        ${["LOCAL_ONLY", "LOCAL_FIRST", "HYBRID"].map(policy => `<button class="chip ${cfg.policy === policy ? "active" : ""}"
          data-policy="${policy}">${policy === "LOCAL_ONLY" ? "só local" : policy === "LOCAL_FIRST" ? "local primeiro" : "híbrido"}</button>`).join("")}
      </div>
    </section>

    <section class="route-slots">
      <span class="route-label">Capacidades — qualquer nó pede por aqui</span>
      ${(catalog.slots || []).map(slot => {
        const r = slot.resolvido;
        const opcoes = [
          ...(catalog.modelos_locais || []).map(m => ({ v: `ollama|${m.id}`, t: `local · ${m.id}` })),
          ...(catalog.modelos_remotos || []).slice(0, 400).map(m => ({ v: `openrouter|${m.id}`, t: `openrouter · ${m.id}` })),
        ];
        const atual = slot.escolhido?.provider ? `${slot.escolhido.provider}|${slot.escolhido.model}` : "";
        return `<div class="route-slot">
          <div class="route-slot-head">
            <strong>${escapeHtml(slot.label)}</strong>
            ${r ? `<span class="route-badge" data-local="${r.local}">${icon(r.local ? "local" : "remoto", 11)}${escapeHtml(r.model)}</span>`
                : `<span class="route-badge" data-local="false">${icon("atencao", 11)}sem modelo</span>`}
          </div>
          <small>${escapeHtml(slot.description)}</small>
          <select class="nf-input" data-slot-bind="${escapeHtml(slot.id)}">
            <option value="">automático${r ? ` — ${escapeHtml(r.reason)}` : ""}</option>
            ${opcoes.map(o => `<option value="${escapeHtml(o.v)}" ${o.v === atual ? "selected" : ""}>${escapeHtml(o.t)}</option>`).join("")}
          </select>
        </div>`;
      }).join("")}
    </section>
  </div>`;
}

async function loadDockTab(tab) {
  const dock = state.dock;
  dock.error = null;
  if (tab === "software") {
    try {
      const data = await api("/api/mcp/targets");
      dock.targets = data.alvos || [];
      if (!dock.active && dock.targets.length) dock.active = dock.targets.find(t => t.estado === "no ar")?.id || dock.targets[0].id;
    } catch (error) { dock.error = { mensagem: "Não consegui listar os softwares.", como_corrigir: String(error).slice(0, 160) }; }
  } else if (tab === "roteamento") {
    try { dock.catalog = await api("/api/ai/catalog"); }
    catch (error) { dock.error = { mensagem: "Não consegui ler o roteamento.", como_corrigir: String(error).slice(0, 160) }; }
  }
  renderDock();
}

async function dockNavigate(raw) {
  const dock = state.dock;
  let target = (raw || "").trim();
  if (!target) return;
  // Sem ponto e sem esquema, o usuário está buscando, não navegando.
  if (!/^https?:\/\//i.test(target)) {
    target = /^[\w-]+(\.[\w-]+)+([\/?#].*)?$/.test(target)
      ? `https://${target}`
      : `https://duckduckgo.com/?q=${encodeURIComponent(target)}`;
  }
  dock.url = target;
  dock.input = target;
  dock.loading = true;
  dock.error = null;
  localStorage.setItem("cinenode.dock.url", target);
  renderDock();
  try {
    dock.page = await api("/api/web/fetch", { method: "POST", body: { url: target, modo: "texto" } });
  } catch (error) {
    dock.error = error?.detail || { mensagem: "Não consegui abrir o endereço.", como_corrigir: String(error).slice(0, 160) };
    dock.page = null;
  }
  dock.loading = false;
  renderDock();
}

function renderDock() {
  const host = $("#side-dock-host");
  if (!host) return;
  host.innerHTML = dockHtml();
  document.body.dataset.dockOpen = state.dock.open ? "1" : "0";
  document.documentElement.style.setProperty("--dock-width", `${state.dock.open ? state.dock.width : 0}px`);
  bindDock();
}

function bindDock() {
  $("[data-dock-open]")?.addEventListener("click", () => {
    state.dock.open = true;
    renderDock();
    loadDockTab(state.dock.tab);
    if (state.dock.tab === "navegador" && !state.dock.page) dockNavigate(state.dock.url);
  });
  $("[data-dock-close]")?.addEventListener("click", () => { state.dock.open = false; renderDock(); });
  $$("[data-dock-tab]").forEach(button => button.addEventListener("click", () => {
    state.dock.tab = button.dataset.dockTab;
    renderDock();
    loadDockTab(state.dock.tab);
  }));

  // Redimensionar arrastando a borda esquerda do painel.
  const resizer = $("[data-dock-resize]");
  if (resizer) {
    resizer.addEventListener("pointerdown", event => {
      event.preventDefault();
      resizer.setPointerCapture(event.pointerId);
      const startX = event.clientX;
      const startWidth = state.dock.width;
      const move = moveEvent => {
        const proposto = startWidth + (startX - moveEvent.clientX);
        state.dock.width = Math.max(300, Math.min(window.innerWidth - 380, proposto));
        const panel = $(".side-dock");
        if (panel) panel.style.width = `${state.dock.width}px`;
        document.documentElement.style.setProperty("--dock-width", `${state.dock.width}px`);
      };
      const up = () => {
        resizer.removeEventListener("pointermove", move);
        resizer.removeEventListener("pointerup", up);
        localStorage.setItem("cinenode.dock.width", String(state.dock.width));
      };
      resizer.addEventListener("pointermove", move);
      resizer.addEventListener("pointerup", up);
    });
  }

  $("[data-dock-go]")?.addEventListener("submit", event => {
    event.preventDefault();
    dockNavigate(new FormData(event.target).get("url"));
  });
  $("[data-dock-reload]")?.addEventListener("click", () => dockNavigate(state.dock.url));
  $("[data-dock-back]")?.addEventListener("click", () => history.back());
  $("[data-dock-external]")?.addEventListener("click", () => window.open(state.dock.url, "_blank", "noopener"));
  $("[data-open-external]")?.addEventListener("click", event =>
    window.open(event.currentTarget.dataset.openExternal, "_blank", "noopener"));
  $("[data-dock-to-node]")?.addEventListener("click", () => {
    const texto = state.dock.page?.texto || "";
    if (!texto) return;
    const node = addNode("input.text");
    if (node) { node.config.text = texto.slice(0, 4000); state.dirty = true; renderWorkflow(); }
    toast("Texto da página virou um nó de prompt");
  });

  $$("[data-target]").forEach(item => item.addEventListener("click", () => {
    state.dock.active = item.dataset.target;
    renderDock();
  }));

  $("[data-openrouter-save]")?.addEventListener("click", async () => {
    const campo = $("[data-openrouter-key]");
    const patch = { openrouter_enabled: $("[data-openrouter-toggle]")?.checked ?? false };
    if (campo?.value.trim()) patch.openrouter_key = campo.value.trim();
    try {
      await api("/api/ai/settings", { method: "PUT", body: patch });
      toast("Roteamento salvo");
      loadDockTab("roteamento");
    } catch (error) { toast("Não consegui salvar a chave"); }
  });
  $("[data-openrouter-toggle]")?.addEventListener("change", async event => {
    await api("/api/ai/settings", { method: "PUT", body: { openrouter_enabled: event.target.checked } });
    loadDockTab("roteamento");
  });
  $$("[data-policy]").forEach(button => button.addEventListener("click", async () => {
    await api("/api/ai/settings", { method: "PUT", body: { policy: button.dataset.policy } });
    loadDockTab("roteamento");
  }));
  $$("[data-slot-bind]").forEach(select => select.addEventListener("change", async () => {
    const bindings = {};
    $$("[data-slot-bind]").forEach(other => {
      const [provider, ...rest] = (other.value || "").split("|");
      if (provider && rest.length) bindings[other.dataset.slotBind] = { provider, model: rest.join("|") };
    });
    await api("/api/ai/settings", { method: "PUT", body: { bindings } });
    loadDockTab("roteamento");
  }));
}


function mountDock() {
  if ($("#side-dock-host")) return;
  const host = document.createElement("div");
  host.id = "side-dock-host";
  document.body.appendChild(host);
  const saved = Number(localStorage.getItem("cinenode.dock.width"));
  if (saved >= 300) state.dock.width = saved;
  renderDock();
  // Ctrl+B abre e fecha: a mão fica no teclado durante a montagem do grafo.
  window.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "b") {
      event.preventDefault();
      state.dock.open = !state.dock.open;
      renderDock();
      if (state.dock.open) {
        loadDockTab(state.dock.tab);
        if (state.dock.tab === "navegador" && !state.dock.page) dockNavigate(state.dock.url);
      }
    }
  });
}

/** Redesenha um nó só, no lugar, preservando o resto do canvas.

 *  Trocar um chip não pode custar a reconstrução de todos os cartões, todas as
 *  portas, todos os listeners e todos os contextos WebGL. Quando o nó não está na
 *  tela — ele acabou de nascer ou de morrer — cai para o render completo. */

/** Religa os controles de um único cartão, depois de ele ser substituído. */
function bindNodeInteractions(root) {
  root.addEventListener("click", event => {
    if (event.target.closest(".port, .port-block, .node-run, .node-preview, .node-body")) return;
    selecionarNo(root.dataset.nodeId);
  });
  bindPorts(root);
  bindVisualFields(root);
  bindInlineFields(root);
  root.querySelectorAll("[data-advanced-node]").forEach(details => details.addEventListener("toggle", () => {
    const id = details.dataset.advancedNode;
    if (details.open) state.expandedNodes.add(id); else state.expandedNodes.delete(id);
  }));
  root.querySelectorAll("[data-drag-handle]").forEach(handle => bindNodeDrag(handle));
}

/** Selecionar um nó muda uma classe em dois cards e a barra flutuante.
 *  Reconstruir o canvas inteiro para isso era o gargalo mais caro do editor:
 *  medido em 78 ms com 80 nós, contra menos de 1 ms fazendo a troca de classe. */
function selecionarNo(nodeId) {
  if (state.selectedNodeId === nodeId) return;
  state.selectedNodeId = nodeId;
  $$(".workflow-node.selected").forEach(card => card.classList.remove("selected"));
  if (nodeId) $(`.workflow-node[data-node-id="${CSS.escape(nodeId)}"]`)?.classList.add("selected");
  drawEdges();                       // a aresta do nó selecionado muda de traço
  if (nodeId) positionNodeToolbar(nodeId); else $(".node-toolbar")?.remove();
}

function renderNode(nodeId) {
  if (state.route !== "workflow") return renderWorkflow();
  const alvo = $(`.workflow-node[data-node-id="${CSS.escape(nodeId)}"]`);
  const node = state.graph.nodes.find(item => item.id === nodeId);
  if (!alvo || !node) return renderWorkflow();

  const asset = assetsByNode().get(node.id);
  const runState = nodeRunStates().get(node.id);
  const molde = document.createElement("div");
  molde.innerHTML = nodeHtml(node, asset, runState);
  const novo = molde.firstElementChild;
  if (!novo) return renderWorkflow();

  // Preserva rolagem do painel avançado: reindexar o scroll seria perder o lugar.
  const rolagem = alvo.querySelector(".node-advanced .nf-grid")?.scrollTop ?? 0;
  alvo.replaceWith(novo);
  const grade = novo.querySelector(".node-advanced .nf-grid");
  if (grade && rolagem) grade.scrollTop = rolagem;

  bindNodeInteractions(novo);
  drawEdges();
  mountGlbCanvases();
}

let renderPendente = 0;
/** Várias mudanças no mesmo tique viram um render só. */

/* ---------- Módulos: alerta de conclusão com evidência ---------- */

const MODULE_STATE_ICON = {
  CONCLUIDO: "concluido", EM_PROGRESSO: "progresso", BLOQUEADO: "bloqueado",
  REGREDIU: "atencao", PARCIAL: "pendente",
};
const GATE_ICON = { PASS: "concluido", FAIL: "erro", BLOCKED: "bloqueado", UNKNOWN: "pendente" };

function moduleAlertHtml(modulo) {
  const pendentes = modulo.gates.filter(g => g.status !== "PASS");
  return `<article class="module-alert" data-state="${escapeHtml(modulo.estado)}" data-module="${escapeHtml(modulo.id)}">
    <header class="module-alert__head">
      ${icon(MODULE_STATE_ICON[modulo.estado] || "pendente", 20)}
      <div>
        <small>${escapeHtml(modulo.estado.replace("_", " "))}</small>
        <h3>${escapeHtml(modulo.titulo)}</h3>
        <p>${modulo.nos_entregues.length}/${modulo.nos.length || 0} nós ·
           ${modulo.gates_ok}/${modulo.gates_total} gates ·
           ${pendentes.length} pendência${pendentes.length === 1 ? "" : "s"}</p>
      </div>
      <span class="module-alert__id">${escapeHtml(modulo.id)}</span>
    </header>

    <div class="module-alert__bar" role="progressbar" aria-valuenow="${modulo.progresso}">
      <i style="width:${modulo.progresso}%"></i>
    </div>

    <ul class="module-alert__gates">
      ${modulo.gates.map(gate => `<li data-status="${escapeHtml(gate.status)}" title="${escapeHtml(gate.regra)}">
        ${icon(GATE_ICON[gate.status] || "pendente", 12)}
        <strong>${escapeHtml(gate.rotulo)}</strong>
        <span>${escapeHtml((gate.detalhe || "sem evidência").slice(0, 60))}</span>
      </li>`).join("")}
    </ul>

    ${modulo.bloqueio ? `<p class="module-alert__block">${icon("bloqueado", 12)} ${escapeHtml(modulo.bloqueio)}</p>` : ""}
    ${modulo.nos_faltando.length ? `<p class="module-alert__missing">${icon("atencao", 12)}
      Nós ainda não entregues: <code>${modulo.nos_faltando.map(escapeHtml).join("</code> <code>")}</code></p>` : ""}

    ${modulo.nos_entregues.length ? `<div class="module-alert__thumbs">
      ${modulo.nos_entregues.slice(0, 6).map(tipo => {
        const item = catalogItem(tipo);
        return item ? `<figure title="${escapeHtml(item.description || "")}">
          ${nodeThumbHtml(item)}<figcaption>${escapeHtml(item.label)}</figcaption></figure>` : "";
      }).join("")}
      ${modulo.nos_entregues.length > 6 ? `<span class="more">+${modulo.nos_entregues.length - 6}</span>` : ""}
    </div>` : ""}
  </article>`;
}

/** Miniatura derivada do manifesto — mesma regra da biblioteca de nós. */
function nodeThumbHtml(item) {
  const dots = ports => parsePorts(ports).slice(0, 4).map(port =>
    `<i style="background:${portMeta(port.type).color}"></i>`).join("");
  return `<span class="node-thumb" data-cat="${escapeHtml(item.category || "")}">
    <span class="thumb-in">${dots(item.inputs)}</span>
    ${icon(CATEGORY_ICONS[item.category] || "utilidades", 14)}
    <span class="thumb-out">${dots(item.outputs)}</span>
  </span>`;
}

function phaseBannerHtml(fase, info) {
  if (!info.completa) return "";
  return `<div class="phase-banner">
    ${icon("concluido", 18)}
    <div><strong>FASE ${escapeHtml(fase)} CONCLUÍDA — ${escapeHtml(info.titulo)}</strong>
      <span>${info.modulos} módulos, todos os gates aprovados com evidência</span></div>
  </div>`;
}

function modulesPanelHtml() {
  const dados = state.modules;
  if (!dados) return `<div class="card"><div class="card-body">${icon("progresso", 18)} Avaliando módulos…</div></div>`;
  const porFase = {};
  dados.modulos.forEach(m => { (porFase[m.fase] ||= []).push(m); });
  return `<section class="modules-panel">
    <header class="modules-head">
      <div>
        <h2>Módulos de entrega</h2>
        <p>${dados.concluidos} de ${dados.total} concluídos · ${dados.progresso_geral}% geral ·
           avaliado em ${escapeHtml((dados.gerado_em || "").slice(0, 19).replace("T", " "))}</p>
      </div>
      <button class="btn small" data-modules-run title="Roda os comandos de cada gate e regrava a evidência" aria-label="Roda os comandos de cada gate e regrava a evidência">
        ${icon("progresso", 13)} Reavaliar gates
      </button>
    </header>
    ${Object.entries(porFase).map(([fase, modulos]) => `
      <div class="phase-block">
        <h3 class="phase-title">FASE ${escapeHtml(fase)} — ${escapeHtml(dados.fases[fase]?.titulo || "")}
          <span>${dados.fases[fase]?.concluidos}/${dados.fases[fase]?.modulos}</span></h3>
        ${phaseBannerHtml(fase, dados.fases[fase] || {})}
        <div class="modules-grid">${modulos.map(moduleAlertHtml).join("")}</div>
      </div>`).join("")}
  </section>`;
}

async function loadModules(executar = false) {
  try {
    state.modules = await api(`/api/governance/modules${executar ? "?executar=true" : ""}`);
  } catch (error) {
    state.modules = null;
    toast(`Não consegui avaliar os módulos: ${error.message}`, "error");
  }
}

function bindModulesPanel() {
  $("[data-modules-run]")?.addEventListener("click", async event => {
    const botao = event.currentTarget;
    botao.disabled = true;
    botao.textContent = "Executando os gates…";
    // Reavaliar roda pytest de verdade; pode levar dezenas de segundos.
    await loadModules(true);
    render();
    toast("Gates reavaliados e evidência regravada");
  });
}


/* ---------- UX-001: pré-voo antes de gastar GPU ---------- */

/** Marca os nós com problema e devolve se pode executar.
 *  Sem isto o usuário espera a fila para descobrir que faltava conectar um prompt. */
async function runPreflight() {
  try {
    const resultado = await api("/api/workflows/preflight", { method: "POST", body: state.graph });
    state.preflight = resultado;
    return resultado;
  } catch (error) {
    // Pré-voo indisponível não pode impedir a execução: ele é uma ajuda, não um portão.
    state.preflight = null;
    return { pronto: true, problemas: [], indisponivel: String(error).slice(0, 120) };
  }
}

function preflightDoNo(nodeId) {
  return (state.preflight?.problemas || []).filter(p => p.node_id === nodeId);
}

function preflightBannerHtml() {
  const pf = state.preflight;
  if (!pf || pf.pronto) return "";
  return `<div class="preflight-banner" role="alert">
    ${icon("atencao", 16)}
    <div>
      <strong>${pf.com_problema} de ${pf.total_nos} nós impedem a execução</strong>
      <span>Cada um está marcado no canvas com o motivo.</span>
    </div>
    <button class="btn small" data-preflight-dismiss>Executar mesmo assim</button>
  </div>`;
}

/* ---------- UI-001: declarar a base de direitos do asset ---------- */

const BASES_ROTULO = {
  sintetico: "sintético",
  proprio: "sou eu",
  titular_consentiu: "titular consentiu",
  licenciado: "licenciado",
  nao_declarado: "não declarado",
};

function rightsHtml(asset) {
  const atual = asset.direitos?.base || "nao_declarado";
  const titular = asset.direitos?.titular || "";
  const declarado = atual !== "nao_declarado";
  return `<div class="rights" data-rights-asset="${escapeHtml(asset.id)}">
    <span class="rights-label">${icon(declarado ? "consentimento" : "atencao", 12)} Base de direitos</span>
    <div class="chips">
      ${Object.entries(BASES_ROTULO).filter(([id]) => id !== "nao_declarado").map(([id, rotulo]) =>
        `<button type="button" class="chip ${atual === id ? "active" : ""}" data-rights-base="${id}">${rotulo}</button>`
      ).join("")}
    </div>
    ${atual === "titular_consentiu" ? `<input class="rights-titular" data-rights-titular
        placeholder="Quem autorizou (obrigatório)" value="${escapeHtml(titular)}">` : ""}
    ${declarado
      ? `<small class="rights-ok">${icon("concluido", 11)} declarado como ${escapeHtml(BASES_ROTULO[atual])}</small>`
      : `<small class="rights-pendente">${icon("pendente", 11)} sem declaração — geração explícita com rosto fica bloqueada</small>`}
  </div>`;
}

async function salvarDireitos(assetId, base, titular = "") {
  try {
    const resposta = await api(`/api/assets/${assetId}/direitos`, {
      method: "PUT", body: { base, titular },
    });
    toast(`Direitos declarados: ${BASES_ROTULO[base] || base}`);
    return resposta;
  } catch (error) {
    // "titular consentiu" sem nome é recusado pelo servidor, e a mensagem já explica.
    toast(error?.detail?.hint || error.message || "Não consegui salvar", "error", 7000);
    return null;
  }
}

function bindRights() {
  $$("[data-rights-asset]").forEach(bloco => {
    const assetId = bloco.dataset.rightsAsset;
    bloco.querySelectorAll("[data-rights-base]").forEach(chip => {
      chip.addEventListener("click", async event => {
        event.stopPropagation();
        const base = chip.dataset.rightsBase;
        const campo = bloco.querySelector("[data-rights-titular]");
        const titular = campo ? campo.value.trim() : "";
        if (base === "titular_consentiu" && !titular) {
          // Mostra o campo antes de tentar salvar: pedir e recusar na mesma ação irrita.
          const alvo = state.library?.itens?.find(item => item.id === assetId);
          if (alvo) { alvo.direitos = { base, titular: "" }; render(); }
          toast("Diga quem autorizou, e clique de novo");
          return;
        }
        const salvo = await salvarDireitos(assetId, base, titular);
        if (salvo) {
          const alvo = state.library?.itens?.find(item => item.id === assetId);
          if (alvo) alvo.direitos = salvo.direitos;
          render();
        }
      });
    });
  });
}

function renderWorkflow() {
  if (state.route !== "workflow") return;
  if (renderPendente) return;
  renderPendente = requestAnimationFrame(() => {
    renderPendente = 0;
    renderWorkflowAgora();
  });
}

function renderWorkflowAgora() {
  if (state.route !== "workflow") return;
  const main = $("#main");
  if (!main) return;
  main.innerHTML = workflowHtml();
  bindRoute();
  applyView();
  drawEdges();
  renderTopbar();
  mountGlbCanvases();
}

function bindWorkflow() {
  $("#palette-search")?.addEventListener("input", event => { state.paletteQuery = event.target.value; renderWorkflow(); });
  $$('[data-add-node]').forEach(button => {
    button.addEventListener("click", () => addNode(button.dataset.addNode));
    button.addEventListener("dragstart", event => event.dataTransfer.setData("text/cinenode-node", button.dataset.addNode));
  });
  $$('[data-toggle-category]').forEach(header => header.addEventListener("click", () => {
    const category = header.dataset.toggleCategory;
    if (state.collapsedCategories.has(category)) state.collapsedCategories.delete(category);
    else state.collapsedCategories.add(category);
    renderWorkflow();
  }));
  $$('[data-node-id]').forEach(node => node.addEventListener("click", event => {
    // O corpo do card é área de edição: clicar num campo não pode disparar re-render.
    if (event.target.closest(".port, .port-block, .node-run, .node-preview, .node-body")) return;
    selecionarNo(node.dataset.nodeId);
  }));
  bindPorts();
  $$('[data-tool]').forEach(button => button.addEventListener("click", () => { state.tool = button.dataset.tool; renderWorkflow(); }));
  $$('[data-palette-toggle]').forEach(button => button.addEventListener("click", () => { state.paletteOpen = !state.paletteOpen; renderWorkflow(); }));
  $$('[data-prompt-kind]').forEach(button => button.addEventListener("click", () => {
    state.promptDraft.kind = button.dataset.promptKind;
    state.promptDraft.profile = "";
    renderWorkflow();
  }));
  $("#prompt-input")?.addEventListener("input", event => { state.promptDraft.text = event.target.value; });
  $("#prompt-profile")?.addEventListener("change", event => { state.promptDraft.profile = event.target.value; });
  $("#prompt-bar")?.addEventListener("submit", event => { event.preventDefault(); generateFromPrompt(); });
  $$('[data-snapshots-toggle]').forEach(button => button.addEventListener("click", () => {
    state.snapshotsOpen = !state.snapshotsOpen;
    renderWorkflow();
    if (state.snapshotsOpen) refreshSnapshots();
  }));
  $("[data-snapshot-create]")?.addEventListener("click", createSnapshot);
  $$('[data-snapshot-restore]').forEach(button => button.addEventListener("click", () => restoreSnapshot(button.dataset.snapshotRestore)));
  $$('[data-snapshot-delete]').forEach(button => button.addEventListener("click", () => deleteSnapshot(button.dataset.snapshotDelete)));
  bindInlineFields();
  bindRangeMirrors();
  bindVisualFields();
  $$(".node-advanced .nf-grid").forEach(area => {
    area.addEventListener("wheel", event => event.stopPropagation(), { passive: true });
    area.addEventListener("pointerdown", event => event.stopPropagation());
  });
  $$('[data-advanced-node]').forEach(details => details.addEventListener("toggle", () => {
    if (details.open) state.expandedNodes.add(details.dataset.advancedNode);
    else state.expandedNodes.delete(details.dataset.advancedNode);
  }));
  $$('[data-node-run]').forEach(button => button.addEventListener("click", event => { event.stopPropagation(); runUpToNode(button.dataset.nodeRun); }));
  $$('[data-node-action]').forEach(button => button.addEventListener("click", event => { event.stopPropagation(); nodeMenuAction(button.dataset.nodeAction); }));
  $$('[data-node-preview]').forEach(preview => preview.addEventListener("click", event => { event.stopPropagation(); openAssetModal(preview.dataset.nodePreview); }));
  bindCanvasViewport();
  $$('[data-drag-handle]').forEach(handle => bindNodeDrag(handle));
  $$('[data-upload-asset]').forEach(button => button.addEventListener("click", () => uploadInput.click()));
  $("[data-workflow='undo']")?.addEventListener("click", undo);
  $("[data-workflow='redo']")?.addEventListener("click", redo);
  $("[data-workflow='validate']")?.addEventListener("click", validateCurrentWorkflow);
  $("[data-workflow='fit']")?.addEventListener("click", fitCanvas);
  $("[data-workflow='layout']")?.addEventListener("click", autoLayout);
  $("[data-workflow='chat']")?.addEventListener("click", () => { state.chat.open = !state.chat.open; renderWorkflow(); });
  bindChat();
  $("[data-workflow='preview']")?.addEventListener("click", () => { if (ensurePreviewNodes()) renderWorkflow(); else toast("Todo resultado já tem preview"); });
  $("[data-workflow='zoom-in']")?.addEventListener("click", () => setZoom(state.view.zoom * 1.2));
  $("[data-workflow='zoom-out']")?.addEventListener("click", () => setZoom(state.view.zoom / 1.2));
  $("[data-workflow='zoom-reset']")?.addEventListener("click", () => { state.view.zoom = 1; applyView(); });
  drawEdges();
  drawMinimap();
  bindMinimap();
  if (state.selectedNodeId) positionNodeToolbar(state.selectedNodeId);
}

/** Cria prompt + gerador conectados e executa — o fluxo "escreva e gere" do canvas. */
async function generateFromPrompt() {
  const text = state.promptDraft.text.trim();
  if (!text) { toast("Escreva um prompt antes de gerar", "warn"); return; }
  const type = state.promptDraft.kind === "image" ? "image.generate" : "video.generate";
  const item = catalogItem(type);
  if (!item) { toast(`Nó ${type} indisponível`, "error"); return; }
  const wrap = $("#canvas-wrap");
  const rect = wrap?.getBoundingClientRect();
  const center = rect ? canvasPoint(rect.left + rect.width / 2, rect.top + rect.height / 2 - 120) : { x: 320, y: 200 };

  pushHistory();
  const textNode = { id: newNodeId("input.text"), type: "input.text", position: { x: Math.round(center.x - 330), y: Math.round(center.y) }, config: { text } };
  const config = defaultConfig(item);
  if (state.promptDraft.profile) config.profile_id = state.promptDraft.profile;
  const genNode = { id: newNodeId(type), type, position: { x: Math.round(center.x + 40), y: Math.round(center.y) }, config };
  state.graph.nodes.push(textNode, genNode);
  state.graph.edges.push({ id: `edge-${textNode.id}-${genNode.id}-${Date.now()}`, source: textNode.id, target: genNode.id, source_handle: null, target_handle: null });
  ensurePreviewNodes({ silent: true });
  state.promptDraft.text = "";
  state.selectedNodeId = genNode.id;
  renderWorkflow();
  await runUpToNode(genNode.id);
}

/** Edição direta no card. Nunca re-renderiza durante a digitação: o foco tem de ficar onde está. */
function bindInlineFields(root = document) {
  $$('[data-inline-field]', root).forEach(control => {
    const nodeId = control.dataset.inlineNode;
    const key = control.dataset.inlineField;
    const commit = (value, silent) => {
      const node = state.graph.nodes.find(item => item.id === nodeId);
      if (!node) return;
      node.config[key] = value;
      state.dirty = true;
      if (!silent) renderTopbar();
    };
    const readValue = () => {
      if (control.dataset.jsonField != null) {
        try {
          const parsed = JSON.parse(control.value || "{}");
          control.classList.remove("invalid");
          return parsed;
        } catch {
          control.classList.add("invalid");
          return undefined;
        }
      }
      return control.type === "number" ? Number(control.value) : control.value;
    };
    const eventName = control.tagName === "SELECT" ? "change" : "input";
    control.addEventListener(eventName, () => {
      const value = readValue();
      if (value === undefined) return;
      commit(value, eventName === "input");
    });
    control.addEventListener("change", () => {
      const value = readValue();
      if (value === undefined) return;
      commit(value, false);
      // Trocar um asset muda o thumb; trocar perfil muda o rótulo, e um `show_if`
      // pode revelar campos. Redesenha só ESTE nó: o canvas inteiro custa ~100x mais.
      if (control.tagName === "SELECT") renderNode(nodeId);
    });
    // Digitar dentro do nó não deve arrastar o card nem apagar o nó com Delete.
    control.addEventListener("pointerdown", event => event.stopPropagation());
    control.addEventListener("keydown", event => event.stopPropagation());
  });

  $$('[data-drop-node]').forEach(zone => {
    const target = { nodeId: zone.dataset.dropNode, field: zone.dataset.dropField };
    zone.addEventListener("click", event => {
      event.stopPropagation();
      state.uploadTarget = target;
      uploadInput.click();
    });
    zone.addEventListener("dragover", event => { event.preventDefault(); zone.classList.add("dragging"); });
    zone.addEventListener("dragleave", () => zone.classList.remove("dragging"));
    zone.addEventListener("drop", async event => {
      event.preventDefault();
      event.stopPropagation();
      zone.classList.remove("dragging");
      const file = event.dataTransfer?.files?.[0];
      if (!file) return;
      state.uploadTarget = target;
      await uploadFile(file);
    });
  });
}

/** Upload real para /api/assets/upload; se houver nó alvo, já liga o asset nele. */
async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  const target = state.uploadTarget;
  try {
    setBusy("upload", true);
    const query = state.currentProject ? `?project_id=${encodeURIComponent(state.currentProject.id)}` : "";
    const asset = await api(`/api/assets/upload${query}`, { method: "POST", body: form });
    state.assets.unshift(asset);
    if (target) {
      const node = state.graph.nodes.find(item => item.id === target.nodeId);
      if (node) { node.config[target.field] = asset.id; state.dirty = true; }
    }
    toast(`Asset importado: ${asset.original_name}`);
    if (state.route === "gallery" || state.route === "workflow") render();
  } catch (error) {
    toast(`Upload falhou: ${error.message}`, "error", 10000);
  } finally {
    state.uploadTarget = null;
    setBusy("upload", false);
  }
}


/** Slider e leitura numérica são o mesmo valor: mexer num atualiza o outro na hora. */
function bindRangeMirrors() {
  $$(".nf-slider").forEach(group => {
    const range = group.querySelector(".nf-range");
    const number = group.querySelector(".slider-value");
    if (!range || !number) return;
    const paint = () => {
      const min = Number(range.min);
      const max = Number(range.max);
      range.style.setProperty("--fill", `${((Number(range.value) - min) / (max - min)) * 100}%`);
    };
    range.addEventListener("input", () => {
      number.value = range.value;
      number.dispatchEvent(new Event("input", { bubbles: true }));
      paint();
    });
    range.addEventListener("change", () => number.dispatchEvent(new Event("change", { bubbles: true })));
    number.addEventListener("input", () => { range.value = number.value; paint(); });
    range.addEventListener("pointerdown", event => event.stopPropagation());
  });

  $$(".nf-knob").forEach(group => {
    const knob = group.querySelector("[data-knob]");
    const number = group.querySelector(".knob-value");
    if (!knob || !number) return;
    const min = Number(number.min);
    const max = Number(number.max);
    const step = Number(number.step) || 0.01;
    const paint = () => {
      const pct = (Number(number.value) - min) / (max - min);
      knob.style.setProperty("--knob-turn", `${(pct * 270 - 135).toFixed(1)}deg`);
    };
    number.addEventListener("input", paint);
    // Arrastar na vertical gira o knob, como num plugin de áudio.
    knob.addEventListener("pointerdown", event => {
      event.preventDefault();
      event.stopPropagation();
      knob.setPointerCapture(event.pointerId);
      const startY = event.clientY;
      const startValue = Number(number.value);
      const move = moveEvent => {
        const delta = (startY - moveEvent.clientY) / 140 * (max - min);
        const next = Math.min(max, Math.max(min, Math.round((startValue + delta) / step) * step));
        number.value = Number(next.toFixed(4));
        paint();
        number.dispatchEvent(new Event("input", { bubbles: true }));
      };
      const end = () => {
        knob.removeEventListener("pointermove", move);
        knob.removeEventListener("pointerup", end);
        number.dispatchEvent(new Event("change", { bubbles: true }));
      };
      knob.addEventListener("pointermove", move);
      knob.addEventListener("pointerup", end);
    });
  });
}


/** Chips, proporção e seed escrevem no config e redesenham: a visibilidade pode mudar. */

function bindPickerItems() {
  $$("[data-picker-pick]").forEach(option => option.addEventListener("click", event => {
    event.stopPropagation();
    if (!state.openPicker) return;
    const node = state.graph.nodes.find(item => item.id === state.openPicker.node);
    if (node) {
      node.config[state.openPicker.field] = option.dataset.pickerPick;
      state.dirty = true;
    }
    state.openPicker = null;
    renderWorkflow();
  }));
}

function bindVisualFields(root = document) {
  const commit = (nodeId, key, value) => {
    const node = state.graph.nodes.find(item => item.id === nodeId);
    if (!node) return;
    node.config[key] = value;
    state.dirty = true;
    // Só o nó tocado precisa mudar; reconstruir o canvas inteiro era o gargalo.
    renderNode(node.id);
  };
  $$("[data-chips-node]", root).forEach(group => {
    $$(".chip", group).forEach(chip => chip.addEventListener("click", event => {
      event.stopPropagation();
      const raw = chip.dataset.chipValue;
      const numeric = raw !== "" && !Number.isNaN(Number(raw));
      commit(group.dataset.chipsNode, group.dataset.chipsField, numeric ? Number(raw) : raw);
    }));
  });
  $$("[data-profile-node]", root).forEach(group => {
    $$(".profile-card", group).forEach(card => card.addEventListener("click", event => {
      event.stopPropagation();
      commit(group.dataset.profileNode, group.dataset.profileField, card.dataset.profileValue);
    }));
  });
  $$("[data-ratio-node]", root).forEach(group => {
    $$(".ratio-chip", group).forEach(chip => chip.addEventListener("click", event => {
      event.stopPropagation();
      commit(group.dataset.ratioNode, group.dataset.ratioField, chip.dataset.ratioValue);
    }));
  });

  $$("[data-picker-node]", root).forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    const same = state.openPicker?.node === button.dataset.pickerNode && state.openPicker?.field === button.dataset.pickerField;
    state.openPicker = same ? null : { node: button.dataset.pickerNode, field: button.dataset.pickerField, query: "" };
    renderNode(button.dataset.pickerNode);
  }));

  $("[data-picker-search]")?.addEventListener("input", event => {
    // Só o popover é redesenhado; redesenhar tudo tiraria o foco da busca.
    if (!state.openPicker) return;
    state.openPicker.query = event.target.value;
    const grid = $(".picker-grid");
    if (!grid) return;
    const node = state.graph.nodes.find(item => item.id === state.openPicker.node);
    const item = catalogItem(node?.type);
    const field = (item?.fields || []).find(entry => entry.key === state.openPicker.field);
    const value = node?.config?.[state.openPicker.field];
    const query = state.openPicker.query.toLowerCase();
    const options = (field?.options || []).filter(option => !query || String(option).toLowerCase().includes(query));
    grid.innerHTML = options.length
      ? options.map(option => `<button type="button" class="picker-item ${String(option) === String(value) ? "active" : ""}" data-picker-pick="${escapeHtml(option)}">${escapeHtml(option)}</button>`).join("")
      : `<div class="picker-empty">nada encontrado</div>`;
    bindPickerItems();
  });
  bindPickerItems();

  $$("[data-expand-node]", root).forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    const id = button.dataset.expandNode;
    // Expandir é por nó, não global: o usuário quer ver UM resultado grande.
    if (state.expandedPreviews.has(id)) state.expandedPreviews.delete(id);
    else state.expandedPreviews.add(id);
    renderNode(id);
  }));

  $$("[data-seed-node]", root).forEach(button => button.addEventListener("click", event => {
    event.stopPropagation();
    const node = state.graph.nodes.find(item => item.id === button.dataset.seedNode);
    if (!node) return;
    const key = button.dataset.seedField;
    // Alterna entre aleatória e uma seed fixa sorteada, para poder repetir o resultado.
    node.config[key] = String(node.config[key]) === "-1" ? Math.floor(Math.random() * 2 ** 31) : -1;
    state.dirty = true;
    renderNode(node.id);
  }));

  if (state.route === "governance") bindModulesPanel();
  if (state.route === "gallery") bindRights();
  $("[data-preflight-dismiss]")?.addEventListener("click", () => {
    state.preflightIgnorado = true;
    state.preflight = null;
    renderWorkflow();
    runCurrentProject();
  });
}

function bindCanvasViewport() {
  const wrap = $("#canvas-wrap");
  if (!wrap) return;
  wrap.addEventListener("wheel", event => {
    event.preventDefault();
    if (event.ctrlKey || event.metaKey || !event.shiftKey) {
      setZoom(state.view.zoom * (event.deltaY < 0 ? 1.1 : 1 / 1.1), { x: event.clientX, y: event.clientY });
    } else {
      state.view.x -= event.deltaY;
      applyView();
    }
  }, { passive: false });

  wrap.addEventListener("pointerdown", event => {
    if (event.target.closest(".workflow-node, .float-pill, .prompt-bar, .palette-popover, .connect-menu, .snapshots-panel, .minimap")) return;
    if (event.button !== 0 && event.button !== 1) return;
    event.preventDefault();
    wrap.setPointerCapture(event.pointerId);
    wrap.classList.add("panning");
    const startX = event.clientX, startY = event.clientY;
    const originX = state.view.x, originY = state.view.y;
    let dragged = false;
    const move = moveEvent => {
      if (Math.abs(moveEvent.clientX - startX) + Math.abs(moveEvent.clientY - startY) > 3) dragged = true;
      state.view.x = originX + moveEvent.clientX - startX;
      state.view.y = originY + moveEvent.clientY - startY;
      applyView();
    };
    const end = () => {
      wrap.removeEventListener("pointermove", move);
      wrap.removeEventListener("pointerup", end);
      wrap.classList.remove("panning");
      // Clique limpo no vazio limpa seleção; arrasto apenas move o canvas.
      if (!dragged && (state.selectedNodeId || state.paletteOpen)) {
        state.selectedNodeId = null;
        state.paletteOpen = false;
        renderWorkflow();
      }
    };
    wrap.addEventListener("pointermove", move);
    wrap.addEventListener("pointerup", end);
  });

  wrap.addEventListener("dragover", event => { if (event.dataTransfer.types.includes("text/cinenode-node")) event.preventDefault(); });
  wrap.addEventListener("drop", event => {
    const type = event.dataTransfer.getData("text/cinenode-node");
    if (!type) return;
    event.preventDefault();
    addNode(type, canvasPoint(event.clientX, event.clientY));
  });
}

/** A barra contextual acompanha o nó selecionado, como no canvas do Spaces. */
function positionNodeToolbar(nodeId) {
  const toolbar = $("#node-toolbar");
  const node = $(`[data-node-id="${CSS.escape(nodeId)}"]`);
  const wrap = $("#canvas-wrap");
  if (!toolbar || !node || !wrap) return;
  const nodeRect = node.getBoundingClientRect();
  const wrapRect = wrap.getBoundingClientRect();
  const width = toolbar.offsetWidth || 300;
  const left = nodeRect.left - wrapRect.left + nodeRect.width / 2 - width / 2;
  const top = nodeRect.top - wrapRect.top - toolbar.offsetHeight - 10;
  toolbar.style.left = `${Math.max(10, Math.min(wrapRect.width - width - 10, left))}px`;
  toolbar.style.top = `${top < 10 ? nodeRect.bottom - wrapRect.top + 10 : top}px`;
  toolbar.style.opacity = "1";
}

function nodeMenuAction(action) {
  const nodeId = state.selectedNodeId;
  const node = state.graph.nodes.find(item => item.id === nodeId);
  if (!node) return;
  if (action === "run") { runUpToNode(nodeId); return; }
  if (action === "duplicate") {
    pushHistory();
    const copy = deepCopy(node);
    copy.id = newNodeId(node.type);
    copy.position = { x: Number(node.position.x) + 48, y: Number(node.position.y) + 48 };
    state.graph.nodes.push(copy);
    state.selectedNodeId = copy.id;
  }
  if (action === "rename") {
    const value = prompt("Novo ID do nó", node.id);
    if (value == null) { renderWorkflow(); return; }
    state.selectedNodeId = node.id;
    renameNode(value);
    return;
  }
  if (action === "disconnect") {
    pushHistory();
    state.graph.edges = state.graph.edges.filter(edge => edge.source !== nodeId && edge.target !== nodeId);
  }
  if (action === "delete") {
    state.selectedNodeId = nodeId;
    deleteSelectedNode();
    return;
  }
  renderWorkflow();
}


/** Todo resultado tem de aparecer. Gerador sem consumidor ganha um Saída/preview. */
const PRODUCER_TYPES = new Set([
  "image.generate", "video.generate", "image.upscale", "video.upscale", "image.resize",
  "video.interpolate", "video.concat", "video.trim", "audio.extract", "audio.mux",
  "media.export", "media.scopes", "media.filmlook",
]);

function ensurePreviewNodes({ silent = false } = {}) {
  const consumed = new Set(state.graph.edges.map(edge => edge.source));
  const orphans = state.graph.nodes.filter(node => PRODUCER_TYPES.has(node.type) && !consumed.has(node.id));
  if (!orphans.length) return 0;
  pushHistory();
  for (const node of orphans) {
    const preview = {
      id: newNodeId("output.preview"),
      type: "output.preview",
      position: { x: Number(node.position.x) + 330, y: Number(node.position.y) },
      config: {},
    };
    state.graph.nodes.push(preview);
    state.graph.edges.push({
      id: `edge-${node.id}-${preview.id}-${Date.now()}-${Math.round(preview.position.y)}`,
      source: node.id, target: preview.id, source_handle: null, target_handle: null,
    });
  }
  state.dirty = true;
  if (!silent) toast(`${orphans.length} preview conectado`);
  return orphans.length;
}

async function runUpToNode(nodeId) {
  if (!state.currentProject) { toast("Selecione um projeto antes de executar", "warn"); return; }
  const graph = ancestorSubgraph(nodeId);
  if (!graph.nodes.length) { toast("Nó não encontrado no grafo", "error"); return; }
  try {
    setBusy("run-node", true);
    await saveCurrentProject();
    const validation = await api("/api/workflows/validate", { method: "POST", body: graph });
    if (!validation.valid) throw new Error(validation.errors.map(item => item.message).join("; "));
    const job = await api("/api/jobs", { method: "POST", body: { project_id: state.currentProject.id, graph } });
    state.jobs.unshift(job);
    toast(`Job ${job.id.slice(-8)} enfileirado · ${graph.nodes.length} nós até ${nodeId}`);
    renderWorkflow();
  } catch (error) {
    toast(`Execução parcial não iniciada: ${error.message}`, "error", 10000);
  } finally {
    setBusy("run-node", false);
  }
}

function openAssetModal(assetId) {
  const asset = state.assets.find(item => item.id === assetId);
  if (!asset) return;
  modalRoot.innerHTML = `<div class="modal-backdrop"><div class="modal wide">
    <div class="modal-head"><h2>${escapeHtml(asset.original_name || asset.id)}</h2><button type="button" class="btn ghost" data-close-modal>${icon("close")}</button></div>
    <div class="modal-body"><div class="asset-preview large">${assetPreviewHtml(asset, { controls: true })}</div>
      <div class="mono subtle" style="margin-top:10px">${escapeHtml(asset.id)} · ${formatBytes(asset.size_bytes)} · ${escapeHtml(asset.metadata?.sha256?.slice(0, 32) || "sem hash")}</div>
    </div>
    <div class="modal-actions"><a class="btn" href="/media/${asset.id}" target="_blank" rel="noopener">Abrir arquivo</a><button type="button" class="btn" data-close-modal>Fechar</button></div>
  </div></div>`;
  $$('[data-close-modal]', modalRoot).forEach(button => button.addEventListener("click", closeModal));
  mountGlbCanvases();
}

function bindNodeDrag(handle) {
  handle.addEventListener("pointerdown", event => {
    if (event.button !== 0) return;
    if (event.target.closest(".node-kebab")) return;
    const nodeId = handle.dataset.dragHandle;
    const node = state.graph.nodes.find(item => item.id === nodeId); if (!node) return;
    event.preventDefault(); event.stopPropagation(); handle.setPointerCapture(event.pointerId);
    const startX = event.clientX, startY = event.clientY, originX = Number(node.position.x), originY = Number(node.position.y);
    pushHistory();
    const move = moveEvent => {
      // O canvas é transformado por scale(); o delta do ponteiro precisa voltar ao espaço do grafo.
      node.position.x = Math.max(0, Math.round(originX + (moveEvent.clientX - startX) / state.view.zoom));
      node.position.y = Math.max(0, Math.round(originY + (moveEvent.clientY - startY) / state.view.zoom));
      const element = $(`[data-node-id="${CSS.escape(nodeId)}"]`);
      if (element) { element.style.left = `${node.position.x}px`; element.style.top = `${node.position.y}px`; drawEdges(); drawMinimap(); }
    };
    const end = () => { handle.removeEventListener("pointermove", move); handle.removeEventListener("pointerup", end); state.dirty = true; renderTopbar(); };
    handle.addEventListener("pointermove", move); handle.addEventListener("pointerup", end);
  });
}

async function validateGraphLocally() { return api("/api/workflows/validate", { method: "POST", body: state.graph }); }
async function validateCurrentWorkflow() { try { const result = await validateGraphLocally(); if (result.valid) toast(`Workflow válido · ${result.order.length} nós · terminais: ${result.terminal_nodes.join(", ") || "nenhum"}`); else toast(result.errors.map(item => item.message).join("; "), "error", 10000); } catch (error) { toast(error.message, "error"); } }

function renameNode(value) {
  const node = currentNode(); if (!node) return;
  const clean = String(value).trim();
  if (!/^[A-Za-z0-9._-]{1,100}$/.test(clean)) { toast("ID inválido", "error"); renderWorkflow(); return; }
  if (state.graph.nodes.some(item => item.id === clean && item !== node)) { toast("ID já existe", "error"); renderWorkflow(); return; }
  pushHistory(); const old = node.id; node.id = clean;
  for (const edge of state.graph.edges) { if (edge.source === old) edge.source = clean; if (edge.target === old) edge.target = clean; }
  state.selectedNodeId = clean; state.dirty = true; renderWorkflow();
}

function deleteSelectedNode() {
  const id = state.selectedNodeId; if (!id) return;
  pushHistory(); state.graph.nodes = state.graph.nodes.filter(node => node.id !== id); state.graph.edges = state.graph.edges.filter(edge => edge.source !== id && edge.target !== id); state.selectedNodeId = null; renderWorkflow();
}

// ---------- Portas: render ----------
function portsHtml(node, item) {
  const inputs = parsePorts(item.inputs);
  const outputs = parsePorts(item.outputs);
  if (!inputs.length && !outputs.length) return "";

  const entradasLigadas = new Set((state.graph.edges || [])
    .filter(edge => edge.target === node.id)
    .map(edge => edge.target_handle || "*"));
  const saidasLigadas = new Set((state.graph.edges || [])
    .filter(edge => edge.source === node.id)
    .map(edge => edge.source_handle || "*"));

  const linha = (port, side) => {
    const meta = portMeta(port.type);
    const usadas = side === "in" ? entradasLigadas : saidasLigadas;
    const ligada = usadas.has(port.name) || usadas.has("*");
    const marca = port.multi ? "aceita várias" : port.optional ? "opcional" : "obrigatória";
    const titulo = `${port.label} · ${meta.label} · ${marca}`;
    return `<button class="port port-${side} type-${escapeHtml(port.type)}${ligada ? " connected" : ""}${port.optional ? " opcional" : ""}"
      style="--port-color:${meta.color}"
      data-port-side="${side}" data-port-node="${escapeHtml(node.id)}"
      data-port-name="${escapeHtml(port.name)}" data-port-type="${escapeHtml(port.type)}"
      data-port-multi="${port.multi ? 1 : 0}"
      title="${escapeHtml(titulo)}" aria-label="${escapeHtml(titulo)}">
      <span class="port-dot">${icon(meta.icon, 9)}</span><span class="port-name">${escapeHtml(port.label)}</span>${port.multi ? `<span class="port-mult">+</span>` : ""}
    </button>`;
  };

  return `<div class="port-block">
    <div class="port-col in">${inputs.map(port => linha(port, "in")).join("")}</div>
    <div class="port-col out">${outputs.map(port => linha(port, "out")).join("")}</div>
  </div>`;
}

// ---------- Arraste para conectar ----------
function bindPorts(root = document) {
  $$('[data-port-side="out"]', root).forEach(port => {
    port.addEventListener("pointerdown", event => {
      event.preventDefault();
      event.stopPropagation();
      startLink(port, event);
    });
  });
  // Soltar em cima do corpo do nó também conecta, na primeira entrada compatível.
  $$('[data-port-side="in"]', root).forEach(port => {
    port.addEventListener("pointerdown", event => event.stopPropagation());
  });
}

function startLink(portElement, downEvent) {
  const wrap = $("#canvas-wrap");
  const svg = $("#edge-layer");
  if (!wrap || !svg) return;
  const sourceId = portElement.dataset.portNode;
  const type = portElement.dataset.portType;

  state.linking = { sourceId, type };
  document.body.classList.add("is-linking");
  markCompatiblePorts(type);
  portElement.classList.add("source");
  // Cartão que tem alvo compatível ganha contorno: o olho acha o destino de longe.
  $$(".port.compatible").forEach(item =>
    item.closest(".workflow-node")?.classList.add("has-compatible"));

  const preview = document.createElementNS("http://www.w3.org/2000/svg", "path");
  preview.setAttribute("class", "edge-preview");
  preview.style.stroke = portMeta(type).color;
  svg.append(preview);

  const origin = portCenter(portElement);
  const move = moveEvent => {
    const point = canvasPoint(moveEvent.clientX, moveEvent.clientY);
    preview.setAttribute("d", edgePath(origin, point));
    const hovered = compatibleTargetAt(moveEvent.clientX, moveEvent.clientY, type);
    $$(".port.hot").forEach(item => item.classList.remove("hot"));
    if (hovered?.port) hovered.port.classList.add("hot");
  };
  const finish = async upEvent => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", finish);
    preview.remove();
    document.body.classList.remove("is-linking");
    $$(".port.hot, .port.compatible, .port.incompatible, .port.source").forEach(item =>
      item.classList.remove("hot", "compatible", "incompatible", "source"));
    $$(".workflow-node.has-compatible").forEach(item => item.classList.remove("has-compatible"));
    const target = compatibleTargetAt(upEvent.clientX, upEvent.clientY, type);
    state.linking = null;
    if (target?.nodeId) {
      connectNodes(sourceId, target.nodeId, target.handle);
      return;
    }
    // Soltou no vazio: oferece os nós que aceitam esse tipo.
    openConnectMenu(sourceId, type, upEvent.clientX, upEvent.clientY);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", finish);
  move(downEvent);
}

/** Porta simples já ocupada não é alvo válido — quem aceita várias declara `*`. */
function portaLivre(nodeId, handle, multi) {
  if (multi) return true;
  return !(state.graph.edges || []).some(edge => edge.target === nodeId && edge.target_handle === handle);
}

/** Primeira porta de entrada livre e compatível — destino de quem solta a linha
 *  no corpo do card em vez de mirar numa bolinha específica. */
function primeiraPortaLivre(nodeId, type) {
  const item = catalogItem(state.graph.nodes.find(entry => entry.id === nodeId)?.type);
  if (!item) return null;
  return parsePorts(item.inputs).find(port =>
    portsCompatible(type, port.type) && portaLivre(nodeId, port.name, port.multi)) || null;
}

/** Tipo que um nó entrega — usado quando a ligação vem do menu, sem porta mirada. */
function tipoDeSaida(nodeId) {
  const item = catalogItem(state.graph.nodes.find(entry => entry.id === nodeId)?.type);
  return parsePorts(item?.outputs)[0]?.type || "media";
}

function markCompatiblePorts(type) {
  $$('[data-port-side="in"]').forEach(port => {
    const ok = portsCompatible(type, port.dataset.portType)
      && portaLivre(port.dataset.portNode, port.dataset.portName, port.dataset.portMulti === "1");
    port.classList.add(ok ? "compatible" : "incompatible");
  });
}

/** Centro da porta em coordenadas do grafo (não da tela). */
function portCenter(portElement) {
  const wrap = $("#canvas-wrap");
  const rect = portElement.getBoundingClientRect();
  return canvasPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
}

function edgePath(from, to) {
  const bend = Math.max(60, Math.abs(to.x - from.x) * 0.45);
  return `M ${from.x} ${from.y} C ${from.x + bend} ${from.y}, ${to.x - bend} ${to.y}, ${to.x} ${to.y}`;
}

/** Porta de entrada compatível sob o cursor, ou o nó inteiro se soltar no card. */
function compatibleTargetAt(clientX, clientY, type) {
  const element = document.elementFromPoint(clientX, clientY);
  if (!element) return null;
  const port = element.closest('[data-port-side="in"]');
  if (port && portsCompatible(type, port.dataset.portType)
      && portaLivre(port.dataset.portNode, port.dataset.portName, port.dataset.portMulti === "1")) {
    return { nodeId: port.dataset.portNode, port, handle: port.dataset.portName };
  }
  const card = element.closest("[data-node-id]");
  if (card) {
    const livre = primeiraPortaLivre(card.dataset.nodeId, type);
    if (livre) return { nodeId: card.dataset.nodeId, port: null, handle: livre.name };
  }
  return null;
}

function connectNodes(sourceId, targetId, handle = null) {
  if (sourceId === targetId) { toast("Um nó não pode conectar em si mesmo", "warn"); return; }
  const alvo = handle || primeiraPortaLivre(targetId, tipoDeSaida(sourceId))?.name || null;
  if (!alvo) { toast("Esse nó não tem porta livre para esse tipo", "warn"); return; }
  // Duas ligações do mesmo par são legítimas quando vão para portas diferentes
  // (o mesmo quadro pode ser início e referência); o que se recusa é repetir a porta.
  if (state.graph.edges.some(edge => edge.source === sourceId && edge.target === targetId
      && (edge.target_handle || null) === alvo)) {
    toast("Essa conexão já existe", "warn");
    return;
  }
  pushHistory();
  const edge = { id: `edge-${sourceId}-${targetId}-${alvo}-${Date.now()}`,
                 source: sourceId, target: targetId, source_handle: null, target_handle: alvo };
  state.graph.edges.push(edge);
  validateGraphLocally().then(result => {
    if (!result.valid) {
      state.graph.edges = state.graph.edges.filter(item => item.id !== edge.id);
      toast(result.errors.map(item => item.message).join("; "), "error");
    }
    renderWorkflow();
  });
}

/** Menu que aparece ao soltar a linha no vazio, só com nós que aceitam o tipo. */
function openConnectMenu(sourceId, type, clientX, clientY) {
  const wrap = $("#canvas-wrap");
  if (!wrap) return;
  const options = (state.bootstrap?.node_catalog || []).filter(item => nodeAcceptsType(item, type));
  if (!options.length) { toast(`Nenhum nó aceita ${portMeta(type).label.toLowerCase()}`, "warn"); return; }
  const rect = wrap.getBoundingClientRect();
  const point = canvasPoint(clientX, clientY);
  const groups = {};
  for (const item of options) (groups[item.category] ||= []).push(item);

  const element = document.createElement("div");
  element.className = "connect-menu";
  element.style.left = `${Math.min(rect.width - 260, clientX - rect.left)}px`;
  element.style.top = `${Math.min(rect.height - 260, clientY - rect.top)}px`;
  element.innerHTML = `
    <div class="connect-menu-head">
      <span class="port-dot" style="--port-color:${portMeta(type).color}"></span>
      Conectar saída <strong>${escapeHtml(portMeta(type).label)}</strong> a…
    </div>
    <div class="connect-menu-body">
      ${Object.entries(groups).map(([category, items]) => `
        <div class="connect-menu-group"><h4>${icon(CATEGORY_ICONS[category] || "utilidades", 13)}${escapeHtml(category)}</h4>
        ${items.map(item => `<button data-connect-create="${escapeHtml(item.type)}"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></button>`).join("")}</div>`).join("")}
    </div>`;
  wrap.append(element);

  const close = () => element.remove();
  element.addEventListener("pointerdown", event => event.stopPropagation());
  $$("[data-connect-create]", element).forEach(button => button.addEventListener("click", () => {
    const created = addNode(button.dataset.connectCreate, { x: point.x + 40, y: point.y - 40 });
    close();
    if (created) connectNodes(sourceId, created.id);
  }));
  setTimeout(() => window.addEventListener("pointerdown", function once() {
    window.removeEventListener("pointerdown", once);
    close();
  }), 0);
}


/** Marca as portas que já participam de alguma aresta.
 *  Sem isto o grafo só é legível com o cursor por cima de cada nó. */
function marcarPortasConectadas() {
  const usadas = new Set();
  for (const edge of state.graph.edges || []) {
    usadas.add(`${edge.source}|out|${edge.source_handle || "*"}`);
    usadas.add(`${edge.target}|in|${edge.target_handle || "*"}`);
  }
  $$(".port").forEach(port => {
    const { portNode, portSide, portName } = port.dataset;
    port.classList.toggle("connected",
      usadas.has(`${portNode}|${portSide}|${portName}`) || usadas.has(`${portNode}|${portSide}|*`));
  });
}

function drawEdges() {
  marcarPortasConectadas();
  const svg = $("#edge-layer");
  if (!svg) return;
  const running = nodeRunStates();
  svg.innerHTML = state.graph.edges.map(edge => {
    const source = $(`[data-node-id="${CSS.escape(edge.source)}"]`);
    const target = $(`[data-node-id="${CSS.escape(edge.target)}"]`);
    if (!source || !target) return "";
    // Sai da porta de saída real e entra na porta de entrada real, não do meio do card.
    const item = catalogItem(state.graph.nodes.find(node => node.id === edge.source)?.type);
    const type = parsePorts(item?.outputs)[0]?.type || "media";
    const from = anchorOf(source, "out", type);
    const to = anchorOf(target, "in", type);
    const color = portMeta(type).color;
    const active = state.selectedNodeId === edge.source || state.selectedNodeId === edge.target;
    const isRunning = running.get(edge.target) === "RUNNING";
    const d = edgePath(from, to);
    return `<g class="edge-group ${isRunning ? "running" : ""}">
      <path class="edge-glow" style="stroke:${color}" d="${d}"></path>
      <path class="edge-path ${active ? "active" : ""}" d="${d}"></path>
      <path class="edge-flow" style="stroke:${color}" d="${d}"></path>
    </g>`;
  }).join("");
}

/** Ponto de ancoragem da aresta: centro da porta NOMEADA da ligação.
 *  É o que faz "início" e "fim" chegarem em alturas diferentes do card em vez
 *  de as duas curvas terminarem no mesmo ponto. */
function anchorOf(element, side, type, handle) {
  const col = `.port-col.${side}`;
  const port = (handle && element.querySelector(`${col} .port[data-port-name="${CSS.escape(handle)}"]`))
    || element.querySelector(`${col} .port[data-port-type="${type}"]`)
    || element.querySelector(`${col} .port`);
  if (port) return portCenter(port);
  const x = parseFloat(element.style.left) + (side === "out" ? element.offsetWidth : 0);
  return { x, y: parseFloat(element.style.top) + element.offsetHeight / 2 };
}

function graphBounds() {
  if (!state.graph.nodes.length) return null;
  const boxes = state.graph.nodes.map(node => {
    const element = $(`[data-node-id="${CSS.escape(node.id)}"]`);
    const x = Number(node.position?.x || 0);
    const y = Number(node.position?.y || 0);
    return { x, y, width: element?.offsetWidth || 230, height: element?.offsetHeight || 110 };
  });
  return {
    minX: Math.min(...boxes.map(box => box.x)),
    minY: Math.min(...boxes.map(box => box.y)),
    maxX: Math.max(...boxes.map(box => box.x + box.width)),
    maxY: Math.max(...boxes.map(box => box.y + box.height)),
    boxes,
  };
}


/** Organiza o grafo em colunas por nível topológico, medindo a altura real de cada card.
 *  Necessário porque os cards passaram a ter os campos dentro e ficaram altos. */

/** Caixa ocupada por um nó no espaço do grafo. Usa o tamanho real quando o nó já
 *  está na tela; senão, o tamanho típico do cartão. */
function nodeBox(node) {
  const element = $(`[data-node-id="${CSS.escape(node.id)}"]`);
  return {
    x: Number(node.position?.x || 0),
    y: Number(node.position?.y || 0),
    w: element?.offsetWidth || 268,
    h: element?.offsetHeight || 220,
  };
}

function boxesOverlap(a, b, folga = 24) {
  return !(a.x + a.w + folga <= b.x || b.x + b.w + folga <= a.x ||
           a.y + a.h + folga <= b.y || b.y + b.h + folga <= a.y);
}

/** Acha um lugar livre perto do ponto desejado, em espiral.
 *  Colocar no centro com jitter aleatório garantia sobreposição a partir do
 *  terceiro nó; a espiral acha o primeiro vão de verdade. */
function findFreeSpot(desejado, largura = 268, altura = 220) {
  const ocupados = state.graph.nodes.map(nodeBox);
  const candidato = { x: Math.round(desejado.x), y: Math.round(desejado.y), w: largura, h: altura };
  const livre = caixa => !ocupados.some(outro => boxesOverlap(caixa, outro));
  if (livre(candidato)) return { x: candidato.x, y: candidato.y };

  const PASSO_X = largura + 40;
  const PASSO_Y = altura + 40;
  for (let anel = 1; anel <= 8; anel++) {
    for (let dx = -anel; dx <= anel; dx++) {
      for (let dy = -anel; dy <= anel; dy++) {
        // Só a borda do anel: o interior já foi testado no anel anterior.
        if (Math.max(Math.abs(dx), Math.abs(dy)) !== anel) continue;
        const teste = {
          x: Math.round(desejado.x + dx * PASSO_X),
          y: Math.round(desejado.y + dy * PASSO_Y),
          w: largura, h: altura,
        };
        if (livre(teste)) return { x: teste.x, y: teste.y };
      }
    }
  }
  // Oito anéis cheios: empilha à direita de tudo em vez de sobrepor.
  const direita = Math.max(0, ...ocupados.map(o => o.x + o.w));
  return { x: Math.round(direita + 60), y: Math.round(desejado.y) };
}

/** Quantos pares de nós estão sobrepostos. É a métrica que o teste de layout usa. */
function countOverlaps() {
  const caixas = state.graph.nodes.map(nodeBox);
  let total = 0;
  for (let i = 0; i < caixas.length; i++) {
    for (let j = i + 1; j < caixas.length; j++) {
      if (boxesOverlap(caixas[i], caixas[j], 0)) total++;
    }
  }
  return total;
}

function autoLayout() {
  const nodes = state.graph.nodes;
  if (!nodes.length) return;
  const incoming = new Map(nodes.map(node => [node.id, 0]));
  const outgoing = new Map(nodes.map(node => [node.id, []]));
  for (const edge of state.graph.edges) {
    if (!incoming.has(edge.target) || !outgoing.has(edge.source)) continue;
    incoming.set(edge.target, incoming.get(edge.target) + 1);
    outgoing.get(edge.source).push(edge.target);
  }
  const level = new Map();
  let queue = nodes.filter(node => incoming.get(node.id) === 0).map(node => node.id);
  queue.forEach(id => level.set(id, 0));
  const pending = new Map(incoming);
  while (queue.length) {
    const id = queue.shift();
    for (const next of outgoing.get(id) || []) {
      level.set(next, Math.max(level.get(next) ?? 0, (level.get(id) ?? 0) + 1));
      pending.set(next, pending.get(next) - 1);
      if (pending.get(next) === 0) queue.push(next);
    }
  }
  const columns = new Map();
  for (const node of nodes) {
    const column = level.get(node.id) ?? 0;
    if (!columns.has(column)) columns.set(column, []);
    columns.get(column).push(node);
  }
  const GAP_X = 120;
  const GAP_Y = 40;
  const measure = id => {
    const element = $(`[data-node-id="${CSS.escape(id)}"]`);
    return { width: element?.offsetWidth || 268, height: element?.offsetHeight || 200 };
  };
  pushHistory();
  let x = 80;
  for (const column of [...columns.keys()].sort((a, b) => a - b)) {
    const group = columns.get(column);
    const widths = group.map(node => measure(node.id).width);
    let y = 80;
    for (const node of group) {
      const size = measure(node.id);
      node.position = { x: Math.round(x), y: Math.round(y) };
      y += size.height + GAP_Y;
    }
    x += Math.max(...widths) + GAP_X;
  }
  state.dirty = true;
  renderWorkflow();

  // Segunda passada: a altura do cartão muda quando ele entra na tela (painel
  // avançado, preview, erro). Medir antes de renderizar deixava colunas coladas.
  requestAnimationFrame(() => {
    let y0 = 80;
    let mudou = false;
    for (const column of [...columns.keys()].sort((a, b) => a - b)) {
      let y = 80;
      for (const node of columns.get(column)) {
        const real = nodeBox(node);
        if (node.position.y !== Math.round(y)) {
          node.position = { x: node.position.x, y: Math.round(y) };
          mudou = true;
        }
        y += real.h + GAP_Y;
      }
      y0 = Math.max(y0, y);
    }
    if (mudou) renderWorkflow();
    fitCanvas();
    const restantes = countOverlaps();
    toast(restantes
      ? `Grafo reorganizado — ${restantes} sobreposição${restantes > 1 ? "ões" : ""} restante${restantes > 1 ? "s" : ""}`
      : "Grafo reorganizado, sem sobreposições");
  });
}

function fitCanvas() {
  const wrap = $("#canvas-wrap");
  const bounds = graphBounds();
  if (!wrap || !bounds) return;
  const padding = 60;
  const width = Math.max(1, bounds.maxX - bounds.minX);
  const height = Math.max(1, bounds.maxY - bounds.minY);
  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, Math.min((wrap.clientWidth - padding * 2) / width, (wrap.clientHeight - padding * 2) / height)));
  state.view.zoom = zoom;
  state.view.x = (wrap.clientWidth - width * zoom) / 2 - bounds.minX * zoom;
  state.view.y = (wrap.clientHeight - height * zoom) / 2 - bounds.minY * zoom;
  applyView();
}

function bindMinimap() {
  const minimap = $(".minimap");
  const wrap = $("#canvas-wrap");
  if (!minimap || !wrap) return;
  minimap.addEventListener("pointerdown", event => {
    event.stopPropagation();
    const bounds = graphBounds();
    if (!bounds) return;
    const rect = minimap.getBoundingClientRect();
    const viewWidth = wrap.clientWidth / state.view.zoom;
    const viewHeight = wrap.clientHeight / state.view.zoom;
    const minX = Math.min(bounds.minX, -state.view.x / state.view.zoom);
    const minY = Math.min(bounds.minY, -state.view.y / state.view.zoom);
    const maxX = Math.max(bounds.maxX, minX + viewWidth);
    const maxY = Math.max(bounds.maxY, minY + viewHeight);
    const graphX = minX + ((event.clientX - rect.left) / rect.width) * (maxX - minX);
    const graphY = minY + ((event.clientY - rect.top) / rect.height) * (maxY - minY);
    state.view.x = wrap.clientWidth / 2 - graphX * state.view.zoom;
    state.view.y = wrap.clientHeight / 2 - graphY * state.view.zoom;
    applyView();
  });
}

function drawMinimap() {
  const svg = $("#minimap-svg");
  const wrap = $("#canvas-wrap");
  if (!svg || !wrap) return;
  const bounds = graphBounds();
  if (!bounds) { svg.innerHTML = ""; return; }
  const viewMinX = -state.view.x / state.view.zoom;
  const viewMinY = -state.view.y / state.view.zoom;
  const viewWidth = wrap.clientWidth / state.view.zoom;
  const viewHeight = wrap.clientHeight / state.view.zoom;
  const minX = Math.min(bounds.minX, viewMinX);
  const minY = Math.min(bounds.minY, viewMinY);
  const maxX = Math.max(bounds.maxX, viewMinX + viewWidth);
  const maxY = Math.max(bounds.maxY, viewMinY + viewHeight);
  const scaleX = 200 / Math.max(1, maxX - minX);
  const scaleY = 130 / Math.max(1, maxY - minY);
  const project = (x, y, width, height) => `x="${(x - minX) * scaleX}" y="${(y - minY) * scaleY}" width="${Math.max(1, width * scaleX)}" height="${Math.max(1, height * scaleY)}"`;
  svg.innerHTML = [
    `<rect class="minimap-view" ${project(viewMinX, viewMinY, viewWidth, viewHeight)}></rect>`,
    ...bounds.boxes.map((box, index) => `<rect class="minimap-node ${state.graph.nodes[index]?.id === state.selectedNodeId ? "selected" : ""}" ${project(box.x, box.y, box.width, box.height)}></rect>`),
  ].join("");
}

/** Versões do projeto atual. O backend guarda o grafo inteiro em cada snapshot. */
async function refreshSnapshots(renderAfter = true) {
  if (!state.currentProject) { state.snapshots = []; return; }
  try {
    state.snapshots = (await api(`/api/projects/${state.currentProject.id}/snapshots`)).items;
    if (renderAfter && state.route === "workflow") renderWorkflow();
  } catch (error) { toast(`Versões indisponíveis: ${error.message}`, "error"); }
}

async function createSnapshot() {
  if (!state.currentProject) return;
  const label = prompt("Nome desta versão", `v${state.snapshots.length + 1}`);
  if (label === null) return;
  try {
    setBusy("snapshot", true);
    if (state.dirty) await saveCurrentProject();
    const snapshot = await api(`/api/projects/${state.currentProject.id}/snapshots`, { method: "POST", body: { label, note: "" } });
    state.snapshots.unshift(snapshot);
    toast(`Versão "${snapshot.label}" salva`);
    renderWorkflow();
  } catch (error) { toast(error.message, "error"); }
  finally { setBusy("snapshot", false); }
}

async function restoreSnapshot(snapshotId) {
  const snapshot = state.snapshots.find(item => item.id === snapshotId);
  if (!confirm(`Restaurar "${snapshot?.label || snapshotId}"?\n\nO estado atual vira uma versão automática antes da troca, então nada é perdido.`)) return;
  try {
    setBusy("snapshot", true);
    const project = await api(`/api/snapshots/${snapshotId}/restore`, { method: "POST" });
    state.currentProject = project;
    state.projects = state.projects.map(item => item.id === project.id ? project : item);
    state.graph = deepCopy(project.graph);
    state.history = []; state.future = []; state.dirty = false; state.selectedNodeId = null;
    await refreshSnapshots(false);
    renderWorkflow();
    toast("Versão restaurada");
  } catch (error) { toast(error.message, "error"); }
  finally { setBusy("snapshot", false); }
}

async function deleteSnapshot(snapshotId) {
  if (!confirm("Excluir esta versão? O grafo atual não é afetado.")) return;
  try {
    await api(`/api/snapshots/${snapshotId}`, { method: "DELETE" });
    state.snapshots = state.snapshots.filter(item => item.id !== snapshotId);
    renderWorkflow();
  } catch (error) { toast(error.message, "error"); }
}

/** Coleções: bibliotecas, referências e galerias montadas pelo usuário. */
async function refreshCollections(renderAfter = true) {
  try {
    state.collections = (await api("/api/collections")).items;
    if (renderAfter && state.route === "gallery") render();
  } catch (error) { toast(`Coleções indisponíveis: ${error.message}`, "error"); }
}

function galleryQuery() {
  const filter = state.galleryFilter;
  const parts = ["limit=300"];
  if (filter.kind) parts.push(`kind=${encodeURIComponent(filter.kind)}`);
  if (filter.search) parts.push(`search=${encodeURIComponent(filter.search)}`);
  if (filter.deleted) parts.push("deleted=true");
  return parts.join("&");
}

async function deleteAsset(assetId) {
  try {
    await api(`/api/assets/${assetId}`, { method: "DELETE" });
    toast("Movido para a lixeira · dá para restaurar");
    await refreshAssets();
  } catch (error) { toast(error.message, "error"); }
}

async function restoreAsset(assetId) {
  try {
    await api(`/api/assets/${assetId}/restore`, { method: "POST" });
    toast("Asset restaurado");
    await refreshAssets();
  } catch (error) { toast(error.message, "error"); }
}

async function purgeAsset(assetId) {
  if (!confirm("Apagar definitivamente? O arquivo em disco será removido e isso não tem volta.")) return;
  try {
    const result = await api(`/api/assets/${assetId}/purge`, { method: "POST" });
    toast(result.file_removed ? "Arquivo apagado do disco" : "Registro removido; arquivo fora de data/ foi preservado", "warn");
    await refreshAssets();
  } catch (error) { toast(error.message, "error", 8000); }
}

async function emptyTrash() {
  const count = state.assets.length;
  if (!count) { toast("A lixeira já está vazia"); return; }
  if (!confirm(`Apagar definitivamente ${count} asset(s)? Não tem volta.`)) return;
  try {
    const result = await api("/api/assets/purge-deleted", { method: "POST" });
    toast(`${result.count} removidos · ${formatBytes(result.freed_bytes)} liberados`, "warn");
    await refreshAssets();
  } catch (error) { toast(error.message, "error"); }
}

async function createCollection() {
  const name = prompt("Nome da coleção");
  if (!name) return;
  try {
    const collection = await api("/api/collections", { method: "POST", body: { name, kind: "library", description: "" } });
    state.collections.unshift(collection);
    toast(`Coleção "${collection.name}" criada`);
    render();
  } catch (error) { toast(error.message, "error"); }
}

async function addAssetToCollection(assetId) {
  if (!state.collections.length) { toast("Crie uma coleção primeiro", "warn"); return; }
  const options = state.collections.map((item, index) => `${index + 1}) ${item.name}`).join("\n");
  const choice = prompt(`Adicionar a qual coleção?\n\n${options}`, "1");
  const collection = state.collections[Number(choice) - 1];
  if (!collection) return;
  try {
    const updated = await api(`/api/collections/${collection.id}/items`, { method: "POST", body: { asset_id: assetId } });
    state.collections = state.collections.map(item => item.id === updated.id ? { ...item, item_count: updated.item_count } : item);
    toast(`Adicionado a "${collection.name}"`);
    render();
  } catch (error) { toast(error.message, "error"); }
}

async function removeFromCollection(collectionId, assetId) {
  try {
    await api(`/api/collections/${collectionId}/items/${assetId}`, { method: "DELETE" });
    await refreshCollections(false);
    render();
  } catch (error) { toast(error.message, "error"); }
}

async function deleteCollection(collectionId) {
  const collection = state.collections.find(item => item.id === collectionId);
  if (!confirm(`Excluir a coleção "${collection?.name}"? Os assets não são apagados.`)) return;
  try {
    await api(`/api/collections/${collectionId}`, { method: "DELETE" });
    state.collections = state.collections.filter(item => item.id !== collectionId);
    if (state.galleryFilter.collection === collectionId) state.galleryFilter.collection = "";
    render();
  } catch (error) { toast(error.message, "error"); }
}

async function refreshJobs(renderAfter = true) { try { state.jobs = (await api("/api/jobs?limit=100")).items; if (renderAfter && state.route === "jobs") render(); } catch (error) { state.online = false; toast(error.message, "error"); renderTopbar(); } }
async function refreshAssets(renderAfter = true) {
  try {
    state.assets = (await api(`/api/assets?${galleryQuery()}`)).items;
    if (renderAfter && state.route === "gallery") render();
  } catch (error) { toast(error.message, "error"); }
}

async function refreshGovernance(renderAfter = true) {
  try {
    const snapshot = await api("/api/governance/snapshot", { headers: { "Cache-Control": "no-cache" } });
    // Validação mínima: um payload sem summary ou sem modules não é um snapshot,
    // e aceitá-lo faria a tela quebrar num `undefined` em vez de dizer o que houve.
    if (!snapshot?.summary || !Array.isArray(snapshot.modules)) throw new Error("snapshot inválido");
    state.governance = snapshot;
    state.governanceError = null;
    state.governanceCheckedAt = new Date().toISOString();
  } catch (error) {
    // O erro fica no estado, não só num toast. Um toast some em três segundos e a
    // tela continuava girando o spinner de carregamento para sempre.
    state.governanceError = error.message;
    state.governanceCheckedAt = new Date().toISOString();
  }
  if (renderAfter && state.route === "governance") render();
}

async function resolverAlerta(alertId, status) {
  try {
    state.governance = await api(`/api/governance/alerts/${alertId}`, {
      method: "PATCH",
      body: { status, resultado: status === "RESOLVED" ? "fechado pela interface" : "" },
    });
    toast(status === "RESOLVED" ? `Alerta ${alertId} resolvido` : `Alerta ${alertId} reaberto`);
    render();
  } catch (error) { toast(`Não consegui atualizar ${alertId}: ${error.message}`, "error"); }
}

async function sincronizarGovernanca() {
  try {
    const resultado = await api("/api/governance/sincronizar", { method: "POST" });
    state.governance = resultado.snapshot;
    state.governanceError = null;
    toast(`${resultado.componentes} componentes registrados, ${resultado.alertas_abertos} pendências de licença`);
    render();
  } catch (error) { toast(`Sincronização falhou: ${error.message}`, "error"); }
}

async function loadSettings(renderAfter = true) { try { state.settings = await api("/api/settings"); if (renderAfter && state.route === "settings") render(); } catch (error) { toast(error.message, "error"); } }
async function saveSettings() {
  try {
    const engines = JSON.parse($("#settings-engines").value); const profiles = JSON.parse($("#settings-profiles").value);
    state.settings = await api("/api/settings", { method: "PATCH", body: { values: { engines, model_profiles: profiles } } });
    toast("Configurações salvas"); await checkEngines(false); render();
  } catch (error) { toast(`Configuração inválida: ${error.message}`, "error", 10000); }
}

async function createBackup() { const target = $("#backup-results"); try { target.textContent = "Criando backup…"; const result = await api("/api/backups", { method: "POST", body: { include_assets: true, include_outputs: true } }); target.textContent = `${result.path}\nSHA-256 ${result.sha256}\n${formatBytes(result.size_bytes)}`; toast("Backup concluído"); } catch (error) { target.textContent = error.message; toast(error.message, "error"); } }
async function listBackups() { const target = $("#backup-results"); try { const data = await api("/api/backups"); target.textContent = data.items.length ? data.items.map(item => `${item.name} · ${formatBytes(item.size_bytes)} · ${item.sha256.slice(0,16)}…`).join("\n") : "Nenhum backup."; } catch (error) { target.textContent = error.message; } }
async function toggleTask(id, status) { try { const next = status === "DONE" ? "PENDING" : "DONE"; state.governance = await api(`/api/governance/tasks/${id}`, { method: "PATCH", body: { status: next, evidence: { source: "superadmin-ui" } } }); render(); } catch (error) { toast(error.message, "error"); } }

uploadInput.addEventListener("change", async () => {
  const file = uploadInput.files?.[0];
  if (!file) return;
  await uploadFile(file);
  uploadInput.value = "";
});

function connectEvents() {
  if (state.eventSource) state.eventSource.close();
  const source = new EventSource("/api/events"); state.eventSource = source;
  source.addEventListener("connected", () => { state.online = true; renderTopbar(); });
  source.addEventListener("jobs.updated", () => refreshJobs(state.route === "jobs" || state.route === "dashboard"));
  source.addEventListener("gallery.updated", () => refreshAssets(state.route === "gallery"));
  source.addEventListener("governance.updated", () => refreshGovernance(state.route === "governance"));
  source.addEventListener("projects.updated", async () => { state.projects = (await api("/api/projects")).items; renderTopbar(); });
  source.onerror = () => { state.online = false; renderTopbar(); };
}

function startPolling() {
  for (const timer of state.timers) clearInterval(timer);
  state.timers = [
    setInterval(() => refreshJobs(state.route === "jobs" || state.route === "dashboard"), 3000),
    setInterval(() => refreshGovernance(state.route === "governance"), 15000),
    setInterval(() => refreshAssets(state.route === "gallery"), 15000),
  ];
  window.addEventListener("focus", () => { refreshGovernance(state.route === "governance"); refreshJobs(state.route === "jobs"); });
  window.addEventListener("oraculo:governance-updated", () => refreshGovernance(state.route === "governance"));
}

window.addEventListener("keydown", event => {
  const tag = document.activeElement?.tagName;
  // A busca da paleta rouba o foco ao abrir; sem esta exceção o Esc nunca a fechava.
  const inPalette = !!document.activeElement?.closest?.(".palette-popover");
  const editing = ["INPUT", "TEXTAREA", "SELECT"].includes(tag) && !inPalette;
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); saveCurrentProject(); }
  if (state.route === "workflow" && !editing && (event.key === "Delete" || event.key === "Backspace")) { event.preventDefault(); deleteSelectedNode(); }
  if (state.route === "workflow" && !editing && event.key === "Escape") { selecionarNo(null); state.paletteOpen = false; renderWorkflow(); }
  if (state.route === "workflow" && !editing && !event.ctrlKey && !event.metaKey) {
    const key = event.key.toLowerCase();
    if (key === "v") { state.tool = "select"; renderWorkflow(); }
    if (key === "h" || event.code === "Space") { event.preventDefault(); state.tool = "pan"; renderWorkflow(); }
    if (key === "n") { event.preventDefault(); state.paletteOpen = !state.paletteOpen; renderWorkflow(); }
    if (key === "f") { event.preventDefault(); fitCanvas(); }
    if (key === "l") { event.preventDefault(); autoLayout(); }
    if (key === "p") { event.preventDefault(); if (ensurePreviewNodes()) renderWorkflow(); }
    if (key === "c") { event.preventDefault(); state.chat.open = !state.chat.open; renderWorkflow(); }
  }
  if (state.route === "workflow" && !editing && (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") { event.preventDefault(); event.shiftKey ? redo() : undo(); }
});

window.addEventListener("beforeunload", event => { if (state.dirty) { event.preventDefault(); event.returnValue = ""; } });
window.addEventListener("resize", () => { if (state.route === "workflow") { drawEdges(); drawMinimap(); } });

initialize();
