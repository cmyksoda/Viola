import { renderMarkdown, escapeHtml } from "./markdown.js";

const $ = (id) => document.getElementById(id);

const ICONS = {
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
  sidebar: '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M9.5 4v16"/>',
  settings: '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
  dots:
    '<circle cx="5.5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="18.5" cy="12" r="1.2" fill="currentColor"/>',
  folder: '<path d="M3.5 7.5a2 2 0 0 1 2-2h3.6l2 2h7.4a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  chevron: '<path d="m6.5 9.5 5.5 5.5 5.5-5.5"/>',
  "chevron-right": '<path d="m9.5 6.5 5.5 5.5-5.5 5.5"/>',
  "arrow-up": '<path d="M12 19V5.5M6 11l6-6 6 6"/>',
  "arrow-down": '<path d="M12 5v13.5M18 13l-6 6-6-6"/>',
  "arrow-up-left": '<path d="M17.5 17.5 7 7M7 15V7h8"/>',
  "arrow-left": '<path d="M19 12H5.5M11 6l-6 6 6 6"/>',
  camera:
    '<path d="M4 8.5A2.5 2.5 0 0 1 6.5 6h1.8l1.4-2h4.6l1.4 2h1.8A2.5 2.5 0 0 1 20 8.5v8a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 16.5z"/><circle cx="12" cy="12.5" r="3.5"/>',
  image:
    '<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="9.5" r="1.6"/><path d="m20.5 16-4.5-4.5-8.5 8"/>',
  paperclip:
    '<path d="m19.5 11.5-7.6 7.6a4.9 4.9 0 0 1-6.9-6.9l8-8a3.3 3.3 0 0 1 4.6 4.6l-8 8a1.6 1.6 0 0 1-2.3-2.3l7.3-7.3"/>',
  file:
    '<path d="M7 3.5h6.5l5 5V19a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M13.5 3.5v5h5"/>',
  chat: '<path d="M5 19.5V7.5A2.5 2.5 0 0 1 7.5 5h9A2.5 2.5 0 0 1 19 7.5v6a2.5 2.5 0 0 1-2.5 2.5H9z"/>',
  stop: '<rect x="5" y="5" width="14" height="14" rx="2.5" fill="currentColor" stroke="none"/>',
  copy:
    '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5V6a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 6v8A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  pencil: '<path d="M4.5 19.5h3.8L19 8.8a2.2 2.2 0 0 0-3.1-3.1L5.2 16.4z"/>',
  terminal: '<rect x="3" y="4.5" width="18" height="15" rx="2.5"/><path d="m7.5 9.5 3 2.5-3 2.5M13 15h3.5"/>',
  trash:
    '<path d="M4.5 7h15M10 11v6M14 11v6M6.5 7l.9 12a1.5 1.5 0 0 0 1.5 1.5h6.2a1.5 1.5 0 0 0 1.5-1.5l.9-12M9.5 7V4.5h5V7"/>',
  x: '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
  lock: '<rect x="5.5" y="10.5" width="13" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
  unlock: '<rect x="5.5" y="10.5" width="13" height="9.5" rx="2"/><path d="M8.5 10.5V8a3.5 3.5 0 0 1 6.7-1.4"/>',
  shield:
    '<path d="M12 3.5 5.5 6v5.2c0 4 2.7 7.4 6.5 8.8 3.8-1.4 6.5-4.8 6.5-8.8V6z"/><path d="m9.2 11.8 2 2 3.8-3.9"/>',
  plan:
    '<path d="M9 6.5h10M9 12h10M9 17.5h6"/><circle cx="5" cy="6.5" r="1" fill="currentColor"/><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="5" cy="17.5" r="1" fill="currentColor"/>',
  alert: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5v5.5M12 16.2v.1"/>',
};

const icon = (name) =>
  `<svg class="ico ico-${name}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;

function applyIcons(root) {
  for (const el of root.querySelectorAll("[data-icon]")) el.innerHTML = icon(el.dataset.icon);
}

// Viola's mark: Claude Code's teardrop asterisk, mirrored on both axes.
const PETAL_LONG =
  "M0,-1.6C1.2375,-4.3 2.25,-5.5375 2.25,-8.35A2.25,2.25 0 0 0 -2.25,-8.35C-2.25,-5.5375 -1.2375,-4.3 0,-1.6Z";
const PETAL_SHORT =
  "M0,-1.6C0.9625,-3.34 1.75,-3.4625 1.75,-5.65A1.75,1.75 0 0 0 -1.75,-5.65C-1.75,-3.4625 -0.9625,-3.34 0,-1.6Z";

function mark(extraClass = "") {
  const petals = [...Array(8).keys()]
    .map((i) => `<path transform="rotate(${i * 45})" d="${i % 2 ? PETAL_SHORT : PETAL_LONG}"/>`)
    .join("");
  return `<svg class="mark ${extraClass}" viewBox="0 0 24 24" fill="currentColor"><g transform="translate(12 12)">${petals}</g></svg>`;
}

const EFFORTS = ["low", "medium", "high", "xhigh", "max"];
const EFFORT_LABEL = { low: "Low", medium: "Medium", high: "High", xhigh: "XHigh", max: "Max" };
const LINES = ["fable", "opus", "sonnet", "haiku"];
const GLYPHS = ["·", "✢", "✳", "✶", "✻", "✽", "✻", "✶", "✳", "✢"];
// None of these are in Claude Code's own list, so nothing shows up twice as often as the rest.
const VERBS = [
  "Musing", "Conjuring", "Weaving", "Whittling", "Theorizing", "Making", "Building", "Studying",
  "Reminiscing", "Analyzing", "Engineering", "Disproving the Jacobian Conjecture",
];
const VERB_SECONDS = 10;
// Claude Code's own verbs join these once the backend has read them from the installed program.
let verbs = VERBS;

const MODES = {
  auto: { label: "Auto", icon: "shield", desc: "A safety check approves routine actions and stops risky ones." },
  acceptEdits: {
    label: "Accept edits",
    short: "Edits",
    icon: "pencil",
    desc: "Edits files without asking. Commands that would need approval are refused.",
  },
  plan: {
    label: "Plan",
    icon: "plan",
    desc: "Reads and plans without changing anything. Approve the plan to start building.",
  },
  bypassPermissions: { label: "Bypass", icon: "unlock", desc: "Runs everything with no checks at all." },
  dontAsk: { label: "Don't ask", icon: "shield", desc: "Refuses anything that isn't already allowed." },
  manual: { label: "Ask", icon: "shield", desc: "Refuses anything that would ask for approval." },
};
const MODE_ORDER = ["auto", "acceptEdits", "plan", "bypassPermissions"];
const THREAD_WINDOW = 40;

const state = {
  token: "",
  settings: {},
  credits: { balance: null, spent: 0, enabled: true },
  convs: [],
  sessions: [],
  current: null,
  loading: null,
  models: [],
  draft: {},
  openSteps: new Set(),
  live: { tokens: 0, phase: "", verb: "", verbAt: 0 },
  showMoreModels: false,
  showAll: false,
  slash: { items: [], index: 0 },
  browse: { path: "", parent: null },
  disconnected: false,
};

/* ---------- plumbing ---------- */

async function api(method, path, body) {
  const headers = { "X-Viola-Token": state.token };
  if (body) headers["Content-Type"] = "application/json";
  const res = await fetch(`/api/${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || res.statusText), { status: res.status });
  return data;
}

let toastTimer;
function toast(text) {
  const el = $("toast");
  el.textContent = text;
  el.hidden = false;
  el.style.animation = "none";
  void el.offsetWidth;
  el.style.animation = "";
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 3600);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Plain http on the tailnet isn't a secure context, so the async clipboard API is missing there.
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    // While a modal dialog is open the rest of the page is inert, and nothing in it can be selected.
    (document.querySelector("dialog[open]") || document.body).append(area);
    area.focus();
    area.setSelectionRange(0, text.length);
    const copied = document.execCommand("copy");
    area.remove();
    return copied;
  }
}

// Shows `done` on the button for a moment once the text is copied, or says that it wasn't.
async function copyWithLabel(btn, text, done = "Copied") {
  if (btn.dataset.copied) return;
  if (!(await copyText(text))) return toast("Couldn't copy. Select the text and copy it by hand.");
  const label = btn.innerHTML;
  btn.dataset.copied = "1";
  btn.innerHTML = done;
  setTimeout(() => {
    btn.innerHTML = label;
    delete btn.dataset.copied;
  }, 1400);
}

function shortPath(path) {
  const sep = state.settings.sep || "/";
  const home = (state.settings.home || "").replace(/[\\/]$/, "");
  if (home && (path === home || path.startsWith(home + sep))) return "~" + path.slice(home.length);
  return path.replace(/^\/home\/[^/]+/, "~");
}

// Message times come from the computer's clock, which a phone's clock may not agree with.
let clockSkew = 0;
const serverNow = () => Date.now() + clockSkew;

const fmtTokens = (n) => (n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : `${n}`);

function fmtDuration(ms) {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor(s / 60) % 60}m`;
}

function fmtCost(cost) {
  if (cost >= 1) return `$${cost.toFixed(2)}`;
  if (cost >= 0.01) return `$${cost.toFixed(3)}`;
  return `$${cost.toFixed(4)}`;
}

function modelName(id) {
  const found = state.models.find((m) => m.id === id);
  if (found) return found.name;
  return (id || "")
    .replace(/^claude-/, "")
    .replace(/\[.*\]$/, "")
    .replace(/-(\d+)-(\d+)$/, " $1.$2")
    .replace(/^\w/, (c) => c.toUpperCase());
}

const isPhone = () => matchMedia("(max-width: 760px)").matches;
// Remote sharing and opening a terminal only make sense on the computer Viola runs on.
const onComputer = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
// WebKitGTK can report a desktop as a touch screen ("hover: none"), so the pointer actually in use decides.
let lastPointer = navigator.maxTouchPoints > 0 && matchMedia("(hover: none)").matches ? "touch" : "mouse";
const isTouch = () => lastPointer === "touch";
function notePointer(e) {
  lastPointer = e.pointerType;
  document.documentElement.classList.toggle("mouse", !isTouch());
}
document.documentElement.classList.toggle("mouse", !isTouch());
addEventListener("pointermove", notePointer, { passive: true });
addEventListener("pointerdown", notePointer, { passive: true });

/* ---------- theme ---------- */

const THEMES = [
  { id: "system", name: "System" },
  { id: "clay-light", name: "Classic Light", mode: "light" },
  { id: "clay-dark", name: "Classic Dark", mode: "dark" },
  { id: "latte", name: "Catppuccin Latte", mode: "light" },
  { id: "frappe", name: "Catppuccin Frappé", mode: "dark" },
  { id: "macchiato", name: "Catppuccin Macchiato", mode: "dark" },
  { id: "mocha", name: "Catppuccin Mocha", mode: "dark" },
  { id: "solarized-light", name: "Solarized Light", mode: "light" },
  { id: "solarized-dark", name: "Solarized Dark", mode: "dark" },
  { id: "gruvbox-light", name: "Gruvbox Light", mode: "light" },
  { id: "gruvbox-dark", name: "Gruvbox Dark", mode: "dark" },
  { id: "rose-pine-dawn", name: "Rosé Pine Dawn", mode: "light" },
  { id: "rose-pine", name: "Rosé Pine", mode: "dark" },
  { id: "tokyo-night", name: "Tokyo Night", mode: "dark" },
  { id: "dracula", name: "Dracula", mode: "dark" },
  { id: "nord", name: "Nord", mode: "dark" },
  { id: "matrix", name: "Matrix", mode: "dark" },
  { id: "win95", name: "Windows 95", mode: "light" },
];
// Settings saved before themes existed say "light" or "dark".
const themeId = (choice) => ({ light: "clay-light", dark: "clay-dark" })[choice] || choice || "system";

const darkQuery = matchMedia("(prefers-color-scheme: dark)");
function resolveTheme(choice) {
  const theme = THEMES.find((t) => t.id === themeId(choice));
  return theme?.mode ? theme : THEMES.find((t) => t.id === (darkQuery.matches ? "clay-dark" : "clay-light"));
}

function applyTheme() {
  const theme = resolveTheme(state.settings.theme);
  const root = document.documentElement;
  const refit = root.dataset.theme !== theme.id;
  root.dataset.theme = theme.id;
  root.dataset.mode = theme.mode;
  if (refit) {
    for (const done of [...pendingCloses]) done();
    if (!$("welcome").hidden) $("greeting-text").textContent = greeting();
    fitBubbles();
    snapToPixels();
  }
  localStorage.setItem("viola.theme", themeId(state.settings.theme));
  localStorage.setItem("viola.mode", theme.mode);
  const ground = getComputedStyle(document.body).backgroundColor;
  document.querySelector('meta[name="theme-color"]').content = ground;
  window.ViolaAndroid?.setDark?.(theme.mode === "dark");
  window.ViolaAndroid?.setAccent?.(theme.id);
  const iconTheme = localStorage.getItem("viola.matchIcon") && !theme.id.startsWith("clay") ? theme.id : "";
  window.ViolaAndroid?.setIcon?.(iconTheme);
  matchDesktopIcon(iconTheme);
  const [r, g, b] = ground.match(/\d+/g).map(Number);
  window.ViolaAndroid?.setGround?.((r << 16) | (g << 8) | b);
}
darkQuery.addEventListener("change", applyTheme);

// On the computer Viola runs on, the launcher and taskbar icon follows the theme too, and so does the open window's.
// Every theme change runs applyTheme a few times, and GTK reloads the icon file each time it's sent,
// so only changes go out.
// The first one after a load always reaches the backend, which reinstalls the icon only if its file has changed.
let windowIcon = null;
function matchDesktopIcon(iconTheme) {
  if (!onComputer || !state.settings.app_icon || window.ViolaAndroid || iconTheme === windowIcon) return;
  if (windowIcon !== null || iconTheme) window.webkit?.messageHandlers?.violaIcon?.postMessage(iconTheme);
  windowIcon = iconTheme;
  api("POST", "app-icon", { theme: iconTheme }).catch((e) => toast(e.message));
}

// Centered boxes land on half pixels when the space around them is odd, which blurs Windows 95's bitmap fonts sideways,
// so there they're nudged onto whole pixels. The chat column only moves sideways: its height changes as it scrolls.
const SNAPPED = [
  ".thread",
  ".composer",
  ".composer-note",
  ".greeting",
  "dialog[open]",
  ".popover:not([hidden]) .attach-tile > span",
];
function snapToPixels() {
  const pixelFonts = document.documentElement.dataset.theme === "win95";
  for (const el of document.querySelectorAll(SNAPPED.join(","))) {
    el.style.translate = "";
    if (!pixelFonts) continue;
    const r = el.getBoundingClientRect();
    const dx = Math.round(r.left) - r.left;
    const dy = el.matches(".thread") ? 0 : Math.round(r.top) - r.top;
    if (dx || dy) el.style.translate = `${dx}px ${dy}px`;
  }
}
const pixelSnapper = new ResizeObserver(() => snapToPixels());

// Pixel icons snap to whole screen pixels with this, so their one-pixel lines all come out the same thickness.
const setScreenPixel = () => document.documentElement.style.setProperty("--dpx", `${1 / devicePixelRatio}px`);
setScreenPixel();
addEventListener("resize", setScreenPixel);

function renderThemeIcon() {
  $("icon-preview").classList.toggle("classic", resolveTheme(state.settings.theme).id.startsWith("clay"));
}

/* ---------- sidebar ---------- */

function dateGroup(ts) {
  const now = new Date();
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const then = new Date(ts);
  const days = Math.round((day(now) - day(then)) / 86400000);
  if (days < 1) return "Today";
  if (days < 2) return "Yesterday";
  if (days < 7) return "Previous 7 days";
  if (days < 30) return "Previous 30 days";
  return then.toLocaleDateString([], {
    month: "long",
    year: then.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}

function sidebarItems(query) {
  const ids = new Set(state.convs.map((c) => c.id));
  const all = [...state.convs, ...state.sessions.filter((s) => !ids.has(s.id))]
    .filter((c) => state.settings.terminal_chats || !c.terminal)
    .sort((a, b) => b.updated - a.updated);
  if (!query) return all;
  return all.filter((c) => c.title.toLowerCase().includes(query) || (c.cwd || "").toLowerCase().includes(query));
}

function renderSidebar() {
  const list = $("conv-list");
  const items = sidebarItems("");
  list.innerHTML = "";
  if (!items.length) {
    list.innerHTML = `<div class="conv-empty">No chats yet</div>`;
    return;
  }
  let group = "";
  const frag = document.createDocumentFragment();
  for (const c of items) {
    const label = dateGroup(c.updated);
    if (label !== group) {
      group = label;
      const head = document.createElement("div");
      head.className = "sidebar-label";
      head.textContent = label;
      frag.append(head);
    }
    const btn = document.createElement("button");
    btn.className = "conv" + (state.current?.id === c.id ? " active" : "");
    btn.dataset.id = c.id;
    const lead = c.terminal ? `<span class="conv-icon">${icon("terminal")}</span>` : "";
    const tail = c.running
      ? `<span class="glyph">${GLYPHS[glyphFrame]}</span>`
      : c.live
        ? '<span class="live-dot"></span>'
        : "";
    btn.innerHTML = `${lead}<span class="conv-name">${escapeHtml(c.title)}</span>${tail}`;
    btn.title = c.terminal && c.cwd ? `${c.title}\n${shortPath(c.cwd)}` : c.title;
    btn.onclick = () => openConv(c.id, false, c.title);
    frag.append(btn);
  }
  list.append(frag);
}

/* ---------- search ---------- */

const SEARCH_LIMIT = 80;
let searchActive = 0;

function shortDay(ts) {
  const now = new Date();
  const then = new Date(ts);
  const day = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((day(now) - day(then)) / 86400000);
  if (days < 1) return then.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  if (days < 2) return "Yesterday";
  if (days < 7) return then.toLocaleDateString([], { weekday: "long" });
  return then.toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: then.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}

function markMatch(text, query) {
  const at = query ? text.toLowerCase().indexOf(query) : -1;
  if (at < 0) return escapeHtml(text);
  return (
    escapeHtml(text.slice(0, at)) +
    `<mark>${escapeHtml(text.slice(at, at + query.length))}</mark>` +
    escapeHtml(text.slice(at + query.length))
  );
}

function renderSearch() {
  const query = $("search-input").value.trim().toLowerCase();
  $("clear-search").hidden = !query;
  const box = $("search-results");
  const items = sidebarItems(query).slice(0, SEARCH_LIMIT);
  searchActive = 0;
  if (!items.length) {
    box.innerHTML =
      `<div class="search-empty">${query ? `No chats match “${escapeHtml(query)}”` : "No chats yet"}</div>`;
    return;
  }
  const rows = items.map((c, i) => {
    const folder =
      c.cwd && shortPath(c.cwd) !== "~"
        ? c.cwd.split(state.settings.sep || "/").filter(Boolean).pop()
        : "";
    const meta = escapeHtml(shortDay(c.updated)) + (folder ? ` · ${markMatch(folder, query)}` : "");
    return (
      `<button type="button" class="result${query && i === 0 ? " active" : ""}" data-id="${escapeHtml(c.id)}">` +
      `<span class="result-icon">${icon(c.terminal ? "terminal" : "chat")}</span>` +
      `<span class="result-text"><span class="result-title">${markMatch(c.title, query)}</span><span class="result-meta">${meta}</span></span></button>`
    );
  });
  box.innerHTML = (query ? "" : `<div class="menu-heading">Recent</div>`) + rows.join("");
  box.scrollTop = 0;
}

function openSearch() {
  const dialog = $("search-dialog");
  if (dialog.open) return dialog.classList.remove("closing");
  closePopover(true);
  $("search-input").value = "";
  renderSearch();
  dialog.showModal();
  $("search-input").focus();
}

function pickResult(row) {
  if (!row) return;
  closeDialog($("search-dialog"));
  openConv(row.dataset.id, false, sidebarChat(row.dataset.id)?.title);
}

function moveSearch(step) {
  const rows = [...$("search-results").querySelectorAll(".result")];
  if (!rows.length) return;
  searchActive = (rows.findIndex((r) => r.classList.contains("active")) + step + rows.length) % rows.length;
  rows.forEach((r, i) => r.classList.toggle("active", i === searchActive));
  rows[searchActive].scrollIntoView({ block: "nearest" });
}

function upsertConv(summary) {
  const i = state.convs.findIndex((c) => c.id === summary.id);
  if (i >= 0) state.convs[i] = summary;
  else state.convs.push(summary);
  state.sessions = state.sessions.filter((s) => s.id !== summary.id);
}

let glyphFrame = 0;
setInterval(() => {
  glyphFrame = (glyphFrame + 1) % GLYPHS.length;
  for (const g of document.querySelectorAll(".glyph")) g.textContent = GLYPHS[glyphFrame];
}, 120);

// Android's WebView can leave a faint copy of a closed full-screen layer on screen until something
// forces a redraw; briefly giving the app its own layer makes it re-render.
function repaint() {
  const app = $("app");
  app.style.transform = "translateZ(0)";
  requestAnimationFrame(() => requestAnimationFrame(() => (app.style.transform = "")));
}

function toggleSidebar(force) {
  const app = $("app");
  if (isPhone()) {
    const was = app.classList.contains("sidebar-open");
    app.classList.toggle("sidebar-open", force);
    if (was && !app.classList.contains("sidebar-open")) setTimeout(repaint, 340);
  } else {
    const collapsed = app.classList.toggle("sidebar-collapsed", force === undefined ? undefined : !force);
    localStorage.setItem("viola.sidebar", collapsed ? "closed" : "open");
  }
}

const assistantName = () => state.settings.assistant_name?.trim() || "Claude";

function renderProfile() {
  const name = state.settings.name || "You";
  $("profile-name").textContent = name;
  $("avatar").textContent = name.slice(0, 1).toUpperCase();
  for (const el of document.querySelectorAll(".assistant-name")) el.textContent = assistantName();
  updateComposer();
  $("profile-sub").textContent = state.settings.auth === "promo" ? "API credits" : "Claude subscription";
}

/* ---------- credits ---------- */

function setOdometer(el, text, roll) {
  if (el.dataset.value === text) return;
  const sameShape = el.dataset.value && el.dataset.value.length === text.length;
  if (!sameShape) {
    el.innerHTML = "";
    for (const ch of text) {
      if (/\d/.test(ch)) {
        const digit = document.createElement("span");
        digit.className = "odo-digit";
        digit.innerHTML =
          `<span class="odo-strip">${[...Array(10).keys()].map((d) => `<span>${d}</span>`).join("")}</span>`;
        el.append(digit);
      } else {
        const span = document.createElement("span");
        span.className = "odo-char";
        span.textContent = ch;
        el.append(span);
      }
    }
  }
  el.dataset.value = text;
  const strips = el.querySelectorAll(".odo-strip");
  const digits = [...text].filter((c) => /\d/.test(c));
  const place = () => strips.forEach((s, i) => (s.style.transform = `translateY(${-digits[i] * 1.25}rem)`));
  if (!sameShape && roll) requestAnimationFrame(() => requestAnimationFrame(place));
  else place();
}

function renderCredits(cost = 0) {
  const pill = $("credits");
  const { enabled } = state.credits;
  const balance = shownBalance();
  pill.hidden = !enabled;
  if (!enabled) return;
  const odo = $("odometer");
  pill.classList.toggle("unset", balance == null);
  pill.classList.toggle("low", balance != null && balance < 5);
  if (balance == null) {
    odo.dataset.value = "";
    odo.textContent = "Set credits";
  } else {
    if (!odo.querySelector(".odo-strip") && odo.textContent) odo.textContent = "";
    setOdometer(odo, `$${Math.max(balance, 0).toFixed(2)}`, true);
  }
  if (cost > 0) {
    pill.classList.remove("ticking");
    void pill.offsetWidth;
    pill.classList.add("ticking");
    const float = document.createElement("span");
    float.className = "credit-float";
    float.textContent = `−${fmtCost(cost)}`;
    pill.append(float);
    setTimeout(() => float.remove(), 1900);
  }
  renderCreditsPop();
}

// A running reply's cost is estimated from its tokens until Claude Code reports the exact figure at the end.
function shownBalance() {
  const { balance, pending } = state.credits;
  return balance == null ? null : balance - (pending || 0);
}

function renderCreditsPop() {
  const { spent, live, pending } = state.credits;
  const balance = shownBalance();
  $("credits-big").textContent = balance == null ? "Not set" : `$${balance.toFixed(4)}`;
  $("credits-pending").hidden = !(pending > 0) || balance == null;
  $("credits-pending").textContent =
    `Includes an estimated ${fmtCost(pending || 0)} for the current turn. It will be replaced by the exact cost when the turn ends.`;
  if (live) {
    const now = new Date();
    const closes = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1));
    const at = closes.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
    $("credits-note").textContent =
      `Anthropic's API bill, including spending outside Viola, reports once a day (${at} local time). Until then, Viola counts today's replies itself.`;
    return;
  }
  $("credits-note").textContent =
    (spent > 0 ? `${fmtCost(spent)} spent since you last set it. ` : "") +
    "Viola subtracts the cost Claude Code reports after each reply. A reply cut off by quitting the app reports nothing, so check the Console now and then.";
}

/* ---------- thread rendering ---------- */

function toolArg(block) {
  const input = block.input || {};
  const path = (p) => (p ? shortPath(p) : "");
  switch (block.name) {
    case "Bash":
      return (input.command || "").split("\n")[0];
    case "Read":
    case "Write":
    case "Edit":
    case "NotebookEdit":
      return path(input.file_path || input.notebook_path);
    case "Grep":
      return `${input.pattern || ""}${input.path ? `  in ${path(input.path)}` : ""}`;
    case "Glob":
      return input.pattern || "";
    case "WebFetch":
      return input.url || "";
    case "WebSearch":
      return input.query || "";
    case "Agent":
    case "Task":
      return input.description || "";
    case "Skill":
      return input.skill || "";
    case "TodoWrite":
      return `${(input.todos || []).length} todos`;
    case "ExitPlanMode":
      return "Plan ready";
    default: {
      const first = Object.values(input).find((v) => typeof v === "string");
      return first ? first.split("\n")[0] : "";
    }
  }
}

function toolName(name) {
  const mcp = name.match(/^mcp__(.+?)__(.+)$/);
  return mcp ? `${mcp[2]} (${mcp[1]})` : name;
}

function toolInputText(block) {
  const input = block.input;
  if (!input) return "";
  if (block.name === "Bash") return input.command || "";
  if (block.name === "Edit") return `${input.file_path}\n\n− ${input.old_string || ""}\n\n+ ${input.new_string || ""}`;
  if (block.name === "Write") return `${input.file_path}\n\n${input.content || ""}`;
  return JSON.stringify(input, null, 2);
}

const stepKey = (msg, i) => `${msg.ts}:${i}`;

function markdown(text) {
  try {
    return renderMarkdown(text || "");
  } catch {
    // A renderer bug shouldn't blank a reply; plain text is better than nothing.
    return `<p>${escapeHtml(text || "").replace(/\n/g, "<br>")}</p>`;
  }
}

function renderBlock(msg, block, i, m) {
  if (block.type === "text") {
    const el = document.createElement("div");
    el.className = "md";
    el.innerHTML = markdown(block.text);
    return el;
  }
  const el = document.createElement("div");
  el.className = "step";
  el.dataset.key = stepKey(msg, i);
  el.dataset.m = m;
  el.dataset.b = i;

  if (block.type === "notice") {
    el.classList.add("notice-step");
    if (block.kind === "info") el.classList.add("info");
    el.innerHTML = `<span class="notice ${block.kind === "info" ? "info" : ""}">${escapeHtml(block.text)}</span>`;
    return el;
  }

  let head;
  let expandable = true;
  if (block.type === "thinking") {
    el.classList.add("thinking");
    const done = !!block.ended;
    expandable = !!block.text.trim();
    head = `<span class="step-name ${done ? "" : "shimmer"}">${
      done ? `Thought for ${fmtDuration(Math.max(1000, block.ended - block.started))}` : "Thinking"
    }</span>`;
  } else if (block.type === "tool") {
    el.classList.add(block.state || "running");
    head = `<span class="step-name">${escapeHtml(toolName(block.name))}</span><span class="step-arg">${
      escapeHtml(toolArg(block))
    }</span>`;
  } else {
    return document.createElement("div");
  }
  const chev = expandable ? icon("chevron-right").replace('class="ico ', 'class="ico chev ') : "";
  el.innerHTML = `<button class="step-head">${head}${chev}</button>`;
  if (expandable && state.openSteps.has(el.dataset.key)) {
    el.classList.add("open");
    fillStep(el, block);
  }
  return el;
}

// Step bodies are only built when opened; long chats used to carry every tool output in the page.
function fillStep(el, block) {
  let inner;
  if (block.type === "thinking") {
    inner = `<div class="step-inner thinking-text">${escapeHtml(block.text)}</div>`;
  } else if (block.name === "ExitPlanMode" && block.input?.plan) {
    inner = `<div class="step-inner md">${markdown(block.input.plan)}</div>`;
  } else {
    const input = toolInputText(block);
    const sub = (block.sub || []).join("\n\n");
    const error = block.state === "error";
    inner =
      `<div class="step-inner">` +
      (input ? `<div class="io"><div class="io-label">Input</div><pre>${escapeHtml(input)}</pre></div>` : "") +
      (sub ? `<div class="sub-log">${escapeHtml(sub)}</div>` : "") +
      (block.partial ? `<div class="io"><div class="io-loading">Loading the full output…</div></div>` : "") +
      (block.result != null && !block.partial
        ? `<div class="io ${error ? "err" : ""}"><div class="io-label">${error ? "Error" : "Output"}</div><pre>${
            escapeHtml(block.result || "(no output)")
          }</pre></div>`
        : "") +
      `</div>`;
  }
  let body = el.querySelector(".step-body");
  if (!body) {
    body = document.createElement("div");
    body.className = "step-body";
    el.append(body);
  }
  body.innerHTML = `<div>${inner}</div>`;
}

async function loadFullStep(el) {
  const conv = state.current;
  const m = Number(el.dataset.m);
  const b = Number(el.dataset.b);
  try {
    const block = await api("GET", `conversations/${conv.id}/block?m=${m}&b=${b}`);
    if (state.current !== conv) return;
    conv.messages[m].blocks[b] = block;
    fillStep(el, block);
  } catch (e) {
    const loading = el.querySelector(".io-loading");
    if (loading) loading.textContent = `Couldn't load it: ${e.message}`;
  }
}

function resetLive(verb = "", verbAt = 0) {
  clearTimeout(state.live.waitTimer);
  state.live = { tokens: 0, phase: "", verb, verbAt };
}

function pickVerb() {
  const name = (state.settings.assistant_name || "").trim();
  // Claude Code already says "Clauding", so only another name gets a verb of its own.
  const pool = name && name.toLowerCase() !== "claude" ? [...verbs, `${name}-ing`] : verbs;
  let verb;
  do verb = pool[Math.floor(Math.random() * pool.length)];
  while (verb === state.live.verb && pool.length > 1);
  state.live.verb = verb;
  state.live.verbAt = Date.now();
  return verb;
}

function statusLine(msg, text) {
  const el = document.createElement("div");
  el.className = "status-line";
  if (!state.live.verb) pickVerb();
  el.innerHTML = `<span class="glyph">${GLYPHS[glyphFrame]}</span><span class="status-verb shimmer">${
    escapeHtml(text || `${state.live.verb}…`)
  }</span><span class="status-stats"></span>`;
  if (msg) updateStats(el, msg);
  return el;
}

function updateStats(el, msg) {
  const stats = el.querySelector(".status-stats");
  if (!stats) return;
  const secs = Math.max(0, Math.round((serverNow() - msg.ts) / 1000));
  const parts = [fmtDuration(secs * 1000)];
  if (state.live.tokens) parts.push(`↓ ${fmtTokens(state.live.tokens)} tokens`);
  if (!isPhone()) parts.push("esc to interrupt");
  stats.textContent = `(${parts.join(" · ")})`;
}

setInterval(() => {
  const el = document.querySelector(".msg.streaming .status-line");
  const msg = state.current?.messages.at(-1);
  if (!el || !msg) return;
  updateStats(el, msg);
  // Like Claude Code, the verb changes every few seconds so a long reply doesn't look stuck.
  if (state.live.phase !== "background" && Date.now() - state.live.verbAt > VERB_SECONDS * 1000) {
    el.querySelector(".status-verb").textContent = `${pickVerb()}…`;
  }
}, 1000);

function messageText(msg) {
  return msg.blocks.filter((b) => b.type === "text").map((b) => b.text).join("\n\n");
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(bytes < 10240 ? 1 : 0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fileCard(name, size) {
  const ext = /\.(\w{1,5})$/.exec(name)?.[1].toUpperCase() || "File";
  const meta = size != null ? `${ext} · ${fmtSize(size)}` : ext;
  return `<span class="file-card"><span class="file-badge">${icon("file")}</span><span class="file-text"><span class="file-name">${escapeHtml(name)}</span><span class="file-meta">${meta}</span></span></span>`;
}

const fileUrl = (a) => `/api/files/${a.id}/${encodeURIComponent(a.name)}?token=${encodeURIComponent(state.token)}`;

function attachmentsHtml(attachments) {
  return attachments
    .map((a) =>
      a.kind === "image"
        ? `<button type="button" class="att-image" data-src="${escapeHtml(fileUrl(a))}"><img src="${
            escapeHtml(fileUrl(a))
          }" alt="${escapeHtml(a.name)}" loading="lazy"></button>`
        : `<span class="att-file">${fileCard(a.name, a.size)}</span>`,
    )
    .join("");
}

function renderUser(msg, pending = false) {
  const el = document.createElement("div");
  el.className = "msg user" + (pending ? " pending" : "");
  el.innerHTML =
    (msg.attachments?.length ? `<div class="msg-attachments">${attachmentsHtml(msg.attachments)}</div>` : "") +
    (msg.text ? `<div class="bubble"></div>` : "");
  if (msg.text) el.querySelector(".bubble").textContent = keepSpaces(msg.text);
  if (pending) {
    el.insertAdjacentHTML("beforeend", `<div class="pending-note">Queued</div>`);
    return el;
  }
  if (!msg.text) return el;
  el.insertAdjacentHTML(
    "beforeend",
    `<div class="msg-actions"><button class="icon-btn" title="Copy">${icon("copy")}</button></div>`,
  );
  el.querySelector(".msg-actions .icon-btn").onclick = (e) => flashCopy(e.currentTarget, msg.text);
  el.querySelector(".bubble").addEventListener("click", () => {
    if (isTouch() && !getSelection().toString()) el.classList.toggle("show-actions");
  });
  return el;
}

// Bubbles use pre-line, which drops the space at the end of a wrapped line (pre-wrap kept it and widened the fit),
// so runs of spaces become no-break spaces.
const keepSpaces = (text) =>
  text.replace(/\t/g, "    ").replace(/ {2,}/g, (run) => "\u00a0".repeat(run.length - 1) + " ");

// A wrapped bubble stays as wide as it may be, leaving a ragged gap after its lines; shrink it to the longest one.
function fittedWidth(bubble) {
  const lines = document.createRange();
  lines.selectNodeContents(bubble);
  const rects = [...lines.getClientRects()];
  if (rects.length < 2) return "";
  // A loop, since spreading a huge paste's rects into Math.max would pass more arguments than the engine allows.
  let left = Infinity;
  let right = -Infinity;
  for (const r of rects) {
    left = Math.min(left, r.left);
    right = Math.max(right, r.right);
  }
  const text = right - left;
  const style = getComputedStyle(bubble);
  return `${Math.ceil(text + parseFloat(style.paddingLeft) + parseFloat(style.paddingRight)) + 1}px`;
}

// All bubbles are reset, then measured, then set, so a long chat is laid out once rather than once per bubble.
function fitBubbles(bubbles = $("thread").querySelectorAll(".bubble")) {
  for (const bubble of bubbles) bubble.style.width = "";
  const widths = [...bubbles].map(fittedWidth);
  [...bubbles].forEach((bubble, i) => (bubble.style.width = widths[i]));
}

new MutationObserver((records) => {
  const added = records.flatMap((r) => [...r.addedNodes]).filter((n) => n.nodeType === 1);
  fitBubbles(added.flatMap((n) => [...n.querySelectorAll(".bubble")]));
}).observe($("thread"), { childList: true });
document.fonts.addEventListener("loadingdone", () => fitBubbles());

const flashCopy = (btn, text) => copyWithLabel(btn, text, icon("check"));

function planWaiting(msg, index) {
  const conv = state.current;
  return (
    conv &&
    conv.permission_mode === "plan" &&
    !conv.running &&
    msg.status === "done" &&
    index === conv.messages.length - 1
  );
}

function renderAssistant(msg, index) {
  const el = document.createElement("div");
  el.className = "msg assistant";
  el.dataset.index = index;
  const blocks = document.createElement("div");
  blocks.className = "blocks";
  msg.blocks.forEach((b, i) => blocks.append(renderBlock(msg, b, i, index)));
  el.append(blocks);

  // Two notes picked up at the same pause leave an empty reply part between them.
  if (!msg.blocks.length && msg.status === "done" && index < (state.current?.messages.length ?? 0) - 1) {
    el.hidden = true;
    return el;
  }
  if (msg.status === "streaming") {
    el.classList.add("streaming");
    el.append(statusLine(msg));
    return el;
  }
  // A terminal is still writing this reply; the "working" line under it stands in for the actions.
  if (state.current?.live?.status === "busy" && index === state.current.messages.length - 1) return el;
  if (msg.status === "error") {
    const card = document.createElement("div");
    card.className = "error-card";
    card.innerHTML = `<strong>That reply didn't finish.</strong><pre></pre><button class="btn">Try again</button>`;
    card.querySelector("pre").textContent = msg.error || "Unknown error";
    card.querySelector("button").onclick = () => retry(index);
    el.append(card);
  } else if (msg.status === "interrupted") {
    const note = document.createElement("div");
    note.className = "stopped";
    note.textContent = "Stopped.";
    el.append(note);
  }
  if (planWaiting(msg, index)) {
    const next = MODES[defaultBuildMode()].label;
    const bar = document.createElement("div");
    bar.className = "plan-bar";
    bar.innerHTML = `<span>Plan mode changes nothing. Approving switches this chat to ${escapeHtml(next)} and asks ${
      escapeHtml(assistantName())
    } to build it.</span><button class="btn">Approve plan</button>`;
    bar.querySelector("button").onclick = approvePlan;
    el.append(bar);
  }

  const meta = [modelName(msg.model), EFFORT_LABEL[msg.effort] || msg.effort];
  if (msg.duration_ms) meta.push(fmtDuration(msg.duration_ms));
  if (msg.cost) meta.push(fmtCost(msg.cost));
  if (msg.context_tokens) meta.push(`${fmtTokens(msg.context_tokens)} context`);
  const cache = msg.cache;
  const prompt = cache ? cache.read + cache.write + cache.fresh : 0;
  if (prompt) meta.push(`${Math.round((cache.read / prompt) * 100)}% cached`);
  const actions = document.createElement("div");
  actions.className = "msg-actions";
  actions.innerHTML =
    `<span class="tail-mark">${mark()}</span>` +
    `<button class="icon-btn" data-act="copy" title="Copy">${icon("copy")}</button>` +
    `<span class="meta">${escapeHtml(meta.filter(Boolean).join(" · "))}</span>`;
  actions.querySelector('[data-act="copy"]').onclick = (e) => flashCopy(e.currentTarget, messageText(msg));
  el.append(actions);
  return el;
}

function renderMessage(msg, index) {
  return msg.role === "user" ? renderUser(msg) : renderAssistant(msg, index);
}

function markLast() {
  const msgs = $("thread").querySelectorAll(".msg.assistant");
  msgs.forEach((m, i) => m.classList.toggle("last", i === msgs.length - 1));
}

function renderPending() {
  const thread = $("thread");
  thread.querySelectorAll(".msg.pending, .terminal-status").forEach((el) => el.remove());
  for (const msg of state.current?.pending || []) thread.append(renderUser(msg, true));
  if (state.current?.live?.status === "busy" && !state.current.running) {
    const line = statusLine(null, "Working in the terminal…");
    line.classList.add("terminal-status");
    thread.append(line);
  }
}

const GREETING_FACES = {
  morning: ["(◕‿◕)", "ヾ(^▽^)", "(｡•ᴗ•｡)", "٩(◕‿◕｡)۶", "(✿◠‿◠)", "(ﾉ◕ヮ◕)ﾉ", "(*^▽^*)", "(•‿•)", "(｡･ω･｡)"],
  afternoon: ["(◕ᴗ◕✿)", "ヽ(´▽`)/", "(´｡• ᵕ •｡`)", "(◍•ᴗ•◍)", "ʕ•ᴥ•ʔ", "(=^･ω･^=)", "(*´▽`*)", "(✧ω✧)", "(◕ᴥ◕)"],
  evening: [
    "(◕‿◕✿)", "(っ˘ω˘ς)", "(｡•̀ᴗ-)✧", "(｡♥‿♥｡)", "(o˘◡˘o)", "(っ´ω`c)",
    "(≧◡≦)", "(っ◕‿◕)っ", "ʕっ•ᴥ•ʔっ", "(●´ω`●)", "(◡‿◡✿)",
  ],
  night: ["(⊙ω⊙)", "(˘ω˘)", "☆(◕ω◕)", "(｡-ω-)zzz", "(∪｡∪)｡｡｡zZ", "(˘ω˘)☾", "ʕ-ᴥ-ʔ", "(=^-ω-^=)"],
};
// Plain ASCII, which the Windows 95 pixel fonts have, and how faces looked in 1995.
const WIN95_FACES = {
  morning: ["(^_^)/", "\\(^o^)/", "(^o^)", "(*^_^*)", "(^-^)/", "(^_^)v", "(^.^)/"],
  afternoon: ["(^_^)", "(^o^)/", "(=^.^=)", "(*^.^*)", "(^_~)", "\\(^_^)/", "(^-^)"],
  evening: ["(^_^)", "(^.^)", "(*^_^*)", "(^_~)", "(=^_^=)", "(^-^)/", "(-_^)"],
  night: ["(-_-)zzz", "(-.-)zZ", "(=-_-=)", "(u_u)", "(-_-)", "(o_o)", "(-.-)Zzz"],
};
// Picked once per part of the day, so the face doesn't change every time the welcome screen redraws.
const greetingFaces = {};

function greeting() {
  const h = new Date().getHours();
  const name = state.settings.name?.trim();
  const part = h >= 5 && h < 12 ? "morning" : h >= 12 && h < 17 ? "afternoon" : h >= 17 && h < 23 ? "evening" : "night";
  const win95 = document.documentElement.dataset.theme === "win95";
  const choices = (win95 ? WIN95_FACES : GREETING_FACES)[part];
  const face = (greetingFaces[part + win95] ??= choices[Math.floor(Math.random() * choices.length)]);
  const words = part === "night" ? "Hello, night owl" : `Good ${part}${name ? `, ${name}` : ""}`;
  return `${words} ${face}`;
}

function renderThread({ keepScroll = false } = {}) {
  const conv = state.current;
  const thread = $("thread");
  const fromBottom = scroller.scrollHeight - scroller.scrollTop;
  thread.innerHTML = "";
  const empty = !conv || !conv.messages.length;
  $("app").classList.toggle("empty", empty);
  $("welcome").hidden = !empty;
  if (empty) {
    $("greeting-text").textContent = greeting();
    $("welcome-spark").innerHTML = mark("pop");
  } else {
    const msgs = conv.messages;
    const start = threadStart(msgs);
    if (start > 0) {
      const more = document.createElement("button");
      more.className = "earlier";
      more.textContent = `Show ${start} earlier message${start === 1 ? "" : "s"}`;
      more.onclick = () => {
        state.showAll = true;
        renderThread({ keepScroll: true });
      };
      thread.append(more);
    } else if (conv.trimmed) {
      thread.insertAdjacentHTML(
        "beforeend",
        `<p class="trimmed-note">${conv.trimmed} earlier messages are only in the terminal transcript.</p>`,
      );
    }
    thread.append(renderMessages(msgs, start));
  }
  markLast();
  renderPending();
  renderTitle();
  updateComposer();
  gliding = false;
  if (keepScroll) scroller.scrollTop = scroller.scrollHeight - fromBottom;
  else scrollToBottom(true);
}

function threadStart(msgs) {
  let start = state.showAll ? 0 : Math.max(0, msgs.length - THREAD_WINDOW);
  while (start > 0 && msgs[start].role !== "user") start--;
  return start;
}

function renderMessages(msgs, from) {
  const frag = document.createDocumentFragment();
  for (let i = from; i < msgs.length; i++) {
    const el = renderMessage(msgs[i], i);
    el.dataset.index = i;
    el.style.animation = "none";
    frag.append(el);
  }
  return frag;
}

// A followed terminal chat grows at the end, so only the messages that changed are drawn again.
// Rebuilding the whole thread every few seconds froze scrolling for 200 ms at a time.
function updateThread(before) {
  const msgs = state.current.messages;
  const thread = $("thread");
  const first = thread.querySelector(".msg[data-index]");
  if (!first || Number(first.dataset.index) !== threadStart(msgs)) return renderThread({ keepScroll: !pinned });
  let same = Number(first.dataset.index);
  const shared = Math.min(before.length, msgs.length);
  while (same < shared && JSON.stringify(before[same]) === JSON.stringify(msgs[same])) same++;
  for (const el of thread.querySelectorAll(".msg[data-index]")) if (Number(el.dataset.index) >= same) el.remove();
  thread.append(renderMessages(msgs, same));
  markLast();
  renderPending();
  updateComposer();
  scrollToBottom();
}

function renderTitle() {
  const conv = state.current;
  const title = $("conv-title");
  title.innerHTML = conv ? `${conv.source ? icon("terminal") : ""}<span></span>` : "";
  if (conv) title.querySelector("span").textContent = conv.title;
  title.hidden = !conv;
  $("conv-menu-btn").hidden = !conv;
  document.title = conv ? `${conv.title} · Viola` : "Viola";
}

/* ---------- scrolling ---------- */

const scroller = $("scroller");
let pinned = true;

function nearBottom() {
  return scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 80;
}

function scrollToBottom(force) {
  if (gliding) return;
  if (force || pinned) {
    scroller.scrollTop = scroller.scrollHeight;
    pinned = true;
  }
  $("jump").hidden = pinned || !state.current?.messages.length;
}

let fromBottom = 0;
const measureFromBottom = () => (fromBottom = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight);

let gliding = false;

function glideToBottom() {
  const end = () => scroller.scrollHeight - scroller.clientHeight;
  // From far up, start the glide a screen and a half from the end so it stays short.
  const from = Math.max(scroller.scrollTop, end() - scroller.clientHeight * 1.5);
  const start = performance.now();
  pinned = true;
  gliding = true;
  $("jump").hidden = true;
  // Aims at the live end each frame, so a reply growing mid-glide still lands exactly.
  const step = (now) => {
    if (!gliding) return;
    const t = Math.min(1, (now - start) / 420);
    scroller.scrollTop = from + (end() - from) * (1 - (1 - t) ** 3);
    if (t < 1) requestAnimationFrame(step);
    else gliding = false;
  };
  requestAnimationFrame(step);
}

const stopGlide = () => (gliding = false);
scroller.addEventListener("touchstart", stopGlide, { passive: true });
scroller.addEventListener("wheel", stopGlide, { passive: true });

// Late font loads and expanding steps grow the thread after we've already scrolled.
new ResizeObserver(() => {
  if (pinned && !gliding) scroller.scrollTop = scroller.scrollHeight;
  measureFromBottom();
}).observe($("thread"));

// Only the chat column's own width changes how bubbles wrap; it stays put while the sidebar slides on a wide window.
let threadWidth = 0;
new ResizeObserver(() => {
  if ($("thread").clientWidth === threadWidth) return;
  threadWidth = $("thread").clientWidth;
  fitBubbles();
}).observe($("thread"));

// The keyboard opening or closing resizes the chat; the text just above the composer stays put.
new ResizeObserver(() => {
  if (gliding) return;
  scroller.scrollTop = pinned ? scroller.scrollHeight : scroller.scrollHeight - scroller.clientHeight - fromBottom;
}).observe(scroller);

scroller.addEventListener("scroll", () => {
  if (gliding) return;
  pinned = nearBottom();
  measureFromBottom();
  $("jump").hidden = pinned || !state.current?.messages.length;
});

/* ---------- live turn events ---------- */

const dirty = new Set();
let frameQueued = false;

function lastAssistantEl() {
  const all = $("thread").querySelectorAll(".msg.assistant");
  return all[all.length - 1];
}

function rerenderBlock(i) {
  const msgs = state.current?.messages;
  const msg = msgs?.at(-1);
  const el = lastAssistantEl();
  if (!msg || !el || !msg.blocks[i]) return;
  const blocks = el.querySelector(".blocks");
  const fresh = renderBlock(msg, msg.blocks[i], i, msgs.length - 1);
  const old = blocks.querySelector(`:scope > [data-b="${i}"]`) || blocks.children[i];
  if (old) old.replaceWith(fresh);
  else blocks.append(fresh);
}

// Each render parses the whole block again, so a very long one is redrawn a few times a second, not every frame.
const BIG_BLOCK = 20000;
const BIG_BLOCK_MS = 120;
let bigRenderAt = 0;

function renderDirty() {
  frameQueued = false;
  const stick = pinned;
  const blocks = state.current?.messages.at(-1)?.blocks || [];
  const now = performance.now();
  const wait = bigRenderAt + BIG_BLOCK_MS - now;
  for (const index of [...dirty]) {
    const big = (blocks[index]?.text?.length || 0) > BIG_BLOCK;
    if (big && wait > 0) continue;
    if (big) bigRenderAt = now;
    dirty.delete(index);
    rerenderBlock(index);
  }
  if (dirty.size) {
    frameQueued = true;
    setTimeout(() => requestAnimationFrame(renderDirty), wait);
  }
  if (stick) scrollToBottom(true);
  else $("jump").hidden = false;
}

function scheduleRender(i) {
  dirty.add(i);
  if (frameQueued) return;
  frameQueued = true;
  requestAnimationFrame(renderDirty);
}

function settleMessage(msg) {
  for (const block of msg.blocks) {
    if (block.type === "thinking" && !block.ended) block.ended = serverNow();
    if (block.type === "tool" && block.state === "running") block.state = "done";
  }
}

function replaceLastAssistant(msg, index) {
  const fresh = renderMessage(msg, index);
  fresh.style.animation = "none";
  lastAssistantEl()?.replaceWith(fresh);
  return fresh;
}

function applyTurnEvent(ev) {
  const conv = state.current;
  if (ev.seq <= conv.seq) return;
  conv.seq = ev.seq;
  const msgs = conv.messages;
  const last = msgs.at(-1);
  switch (ev.t) {
    case "turn_start": {
      const wasEmpty = !msgs.length;
      msgs.push(ev.user, ev.msg);
      conv.running = true;
      resetLive();
      if (wasEmpty) {
        renderThread();
      } else {
        lastAssistantEl()?.querySelector(".plan-bar")?.remove();
        $("thread").append(renderMessage(ev.user, msgs.length - 2), renderMessage(ev.msg, msgs.length - 1));
        markLast();
        renderPending();
        scrollToBottom(true);
      }
      updateComposer();
      break;
    }
    case "turn_split": {
      last.status = "done";
      settleMessage(last);
      msgs.push(ev.user, ev.msg);
      replaceLastAssistant(last, msgs.length - 3);
      conv.pending = ev.pending || [];
      resetLive(state.live.verb, state.live.verbAt);
      $("thread").append(renderMessage(ev.user, msgs.length - 2), renderMessage(ev.msg, msgs.length - 1));
      markLast();
      renderPending();
      scrollToBottom(true);
      break;
    }
    case "pending":
      conv.pending = ev.pending || [];
      renderPending();
      if (pinned) scrollToBottom(true);
      break;
    case "block":
    case "block_set":
      last.blocks[ev.i] = ev.block;
      scheduleRender(ev.i);
      break;
    case "delta":
      if (last.blocks[ev.i]) {
        last.blocks[ev.i].text += ev.text;
        scheduleRender(ev.i);
      }
      break;
    case "status":
      if (ev.tokens != null) state.live.tokens = ev.tokens;
      if (ev.phase) {
        state.live.phase = ev.phase;
        clearTimeout(state.live.waitTimer);
        const setVerb = (text) => {
          const verb = lastAssistantEl()?.querySelector(".status-verb");
          if (verb) verb.textContent = text;
        };
        // Every turn reports a result just before exiting, so only call it waiting if the process lingers.
        if (ev.phase === "background")
          state.live.waitTimer = setTimeout(() => setVerb("Waiting on background agents…"), 1500);
        else setVerb(`${state.live.verb || pickVerb()}…`);
      }
      break;
    case "turn_end": {
      clearTimeout(state.live.waitTimer);
      msgs[msgs.length - 1] = ev.msg;
      conv.running = false;
      conv.pending = [];
      // Messages queued behind a stopped reply aren't sent; they come back to the box to send or change.
      const unsent = ev.msg.status === "interrupted" ? (ev.pending || []).map((m) => m.text).filter(Boolean) : [];
      if (unsent.length) {
        const input = $("input");
        input.value = [...unsent, input.value].filter(Boolean).join("\n\n");
        autosize();
        stashDraft();
      }
      const stick = pinned;
      const fresh = replaceLastAssistant(ev.msg, msgs.length - 1);
      markLast();
      renderPending();
      fresh.querySelector(".tail-mark .mark")?.classList.add("pop");
      updateComposer();
      if (stick) scrollToBottom(true);
      break;
    }
  }
}

function handleEvent(ev) {
  switch (ev.t) {
    case "conv_meta":
      upsertConv(ev.conv);
      renderSidebar();
      if (state.current?.id === ev.conv.id) {
        state.current.title = ev.conv.title;
        renderTitle();
      }
      break;
    case "conv_deleted":
      state.convs = state.convs.filter((c) => c.id !== ev.id);
      renderSidebar();
      if (state.current?.id === ev.id) {
        // Whatever was being typed carries over to the new chat rather than staying with the deleted one.
        const typed = $("input").value;
        state.current = null;
        newChat();
        if (typed.trim()) {
          $("input").value = typed;
          autosize();
          stashDraft();
        }
      }
      break;
    case "unsent": {
      // The text goes back where it can be sent again: the box for the open chat, that chat's draft otherwise.
      toast(`Your queued message wasn't sent: ${ev.error}`);
      if (state.current?.id === ev.conv_id) {
        $("input").value = [ev.text, $("input").value].filter(Boolean).join("\n\n");
        autosize();
        stashDraft();
      } else {
        drafts[ev.conv_id] = [ev.text, drafts[ev.conv_id]].filter(Boolean).join("\n\n");
        localStorage.setItem("viola.drafts", JSON.stringify(drafts));
      }
      break;
    }
    case "sessions":
      state.sessions = ev.sessions || [];
      renderSidebar();
      break;
    case "credits":
      state.credits = {
        balance: ev.balance,
        pending: ev.pending,
        spent: ev.spent,
        enabled: ev.enabled,
        live: ev.live,
        error: ev.error,
      };
      renderAdminNote();
      renderCredits(ev.cost);
      break;
    case "settings":
      state.settings = ev.settings;
      state.credits = ev.credits;
      applyTheme();
      renderProfile();
      renderCredits();
      renderSidebar();
      fillSettings();
      if ($("setup").open) renderSetup();
      break;
    default:
      // Events for a chat that's still loading wait until its snapshot arrives.
      if (state.loading && ev.conv_id === state.loading.id) state.loading.events.push(ev);
      else if (ev.conv_id && state.current?.id === ev.conv_id) applyTurnEvent(ev);
  }
}

let events = null;
let retryDelay = 1000;
let retryTimer = null;
function connectEvents() {
  clearTimeout(retryTimer);
  events?.close();
  const es = (events = new EventSource(`/api/events?token=${encodeURIComponent(state.token)}`));
  es.onmessage = (e) => handleEvent(JSON.parse(e.data));
  es.onopen = () => {
    retryDelay = 1000;
    if (state.disconnected) {
      state.disconnected = false;
      resync();
    }
  };
  es.onerror = () => {
    if (!state.disconnected) toast("Lost the connection to Viola's backend. Reconnecting…");
    state.disconnected = true;
    // A refused connection is retried by the browser itself, but any error reply (a proxy's 502, a 401) ends it for good.
    if (es.readyState === EventSource.CLOSED) {
      retryTimer = setTimeout(reconnect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, 30000);
    }
  };
}

async function reconnect() {
  try {
    await api("GET", "state");
  } catch (e) {
    if (e.status === 401) return showNoLink();
  }
  connectEvents();
}

function showNoLink() {
  events?.close();
  document.body.innerHTML =
    '<p style="padding:2rem;font-family:var(--font-ui)">Viola needs its secret link to open. Use the app window, ' +
    "or copy the remote link from Settings on your computer.</p>";
}

// Only a refused token means the link is wrong; anything else is the backend being away, which a reload may fix.
function showUnreachable() {
  events?.close();
  document.body.innerHTML =
    '<p style="padding:2rem;font-family:var(--font-ui)">Viola\'s backend isn\'t answering. Check that Viola is ' +
    'running on your computer, then <a href="">try again</a>.</p>';
}

async function resync() {
  await loadState();
  if (state.current) await openConv(state.current.id, true);
}

/* ---------- conversations ---------- */

let openCount = 0;

// Unsent text belongs to the chat it was typed in, and survives the app closing.
const drafts = JSON.parse(localStorage.getItem("viola.drafts") || "{}");
const draftKey = () => state.current?.id || "new";

function stashDraft() {
  const text = $("input").value;
  if (text.trim()) drafts[draftKey()] = text;
  else delete drafts[draftKey()];
  localStorage.setItem("viola.drafts", JSON.stringify(drafts));
}

function restoreDraft() {
  renderTray();
  $("input").value = drafts[draftKey()] || "";
  closeSlash();
  autosize();
}

function showLoading(title) {
  $("app").classList.remove("empty");
  $("welcome").hidden = true;
  $("thread").innerHTML = `<div class="thread-loading"><span></span><span></span><span></span></div>`;
  const el = $("conv-title");
  el.hidden = false;
  el.innerHTML = "<span></span>";
  el.querySelector("span").textContent = title;
}

async function openConv(id, quiet, title) {
  const ticket = ++openCount;
  if (isPhone()) toggleSidebar(false);
  if (!quiet) {
    if (state.current?.id !== id) stashDraft();
    closePopover();
    state.current = null;
    state.showAll = false;
    showLoading(title || "");
    renderSidebarActive(id);
  }
  state.loading = { id, events: [] };
  let conv;
  try {
    conv = await api("GET", `conversations/${id}`);
  } catch (e) {
    if (ticket !== openCount) return;
    state.loading = null;
    if (e.status === 404 || e.status === 400) {
      localStorage.removeItem("viola.current");
      return newChat();
    }
    toast(e.message);
    return;
  }
  if (ticket !== openCount) return;
  const buffered = state.loading?.events || [];
  state.loading = null;
  state.current = conv;
  localStorage.setItem("viola.current", id);
  if (!quiet) state.openSteps.clear();
  const last = conv.messages.at(-1);
  conv.running = last?.status === "streaming";
  if (!conv.running || !quiet) resetLive();
  renderThread();
  if (!quiet) restoreDraft();
  for (const ev of buffered) applyTurnEvent(ev);
  renderSidebar();
  watchTerminal();
  if (!quiet && !isTouch()) $("input").focus();
}

function renderSidebarActive(id) {
  for (const el of $("conv-list").querySelectorAll(".conv")) el.classList.toggle("active", el.dataset.id === id);
}

function newChat() {
  if (state.current) stashDraft();
  openCount++;
  state.loading = null;
  state.current = null;
  state.showAll = false;
  state.draft = {
    model: state.settings.model,
    effort: state.settings.effort,
    cwd: state.settings.cwd,
    permission_mode: state.settings.permission_mode || "auto",
  };
  localStorage.removeItem("viola.current");
  renderThread();
  restoreDraft();
  renderSidebar();
  watchTerminal();
  if (isPhone()) toggleSidebar(false);
  if (!isTouch()) $("input").focus();
}

function target() {
  return state.current || state.draft;
}

async function patchTarget(changes) {
  Object.assign(target(), changes);
  updateComposer();
  if (state.current) await api("PATCH", `conversations/${state.current.id}`, changes).catch((e) => toast(e.message));
}

const trays = {};
const tray = () => (trays[draftKey()] ||= []);
const PHOTO_EDGE = 2000;
let trayCount = 0;
const INLINE_LIMIT = 4.5 * 1024 * 1024;

// Phone photos are several megabytes; Claude reads them just as well at 2000 px,
// and big ones exceed the API's 5 MB cap.
async function shrinkImage(file) {
  if (!/^image\/(jpeg|png|webp)$/.test(file.type)) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, PHOTO_EDGE / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size <= INLINE_LIMIT) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const encode = (type, quality) => new Promise((done) => canvas.toBlob(done, type, quality));
    let blob = file.type === "image/png" ? await encode("image/png") : null;
    if (!blob || blob.size > INLINE_LIMIT) blob = await encode("image/jpeg", 0.86);
    const name = blob.type === "image/jpeg" ? file.name.replace(/\.\w+$/, "") + ".jpg" : file.name;
    return new File([blob], name, { type: blob.type });
  } catch {
    return file;
  }
}

function renderTray() {
  const items = tray();
  const box = $("tray");
  box.hidden = !items.length;
  box.innerHTML = items
    .map((item) => {
      const status = item.status === "done" ? "" : ` ${item.status}`;
      const body =
        item.kind === "image" ? `<img src="${item.preview}" alt="">` : fileCard(item.name, item.size);
      const spinner = item.status === "uploading" ? `<span class="glyph">${GLYPHS[glyphFrame]}</span>` : "";
      return `<div class="tray-item${item.kind === "image" ? "" : " file"}${status}" data-key="${item.key}">${body}${spinner}<button type="button" class="tray-remove" title="Remove">${icon("x")}</button></div>`;
    })
    .join("");
  syncSendButtons();
}

async function addFiles(files) {
  const key = draftKey();
  for (const file of files) {
    const image = file.type.startsWith("image/");
    const item = {
      key: String(++trayCount),
      name: file.name || "file",
      kind: image ? "image" : "file",
      size: file.size,
      status: "uploading",
    };
    if (image) item.preview = URL.createObjectURL(file);
    (trays[key] ||= []).push(item);
    renderTray();
    try {
      const body = await shrinkImage(file);
      const res = await fetch("/api/upload", {
        method: "POST",
        headers: {
          "X-Viola-Token": state.token,
          "X-File-Name": encodeURIComponent(body.name || item.name),
          "Content-Type": body.type || "application/octet-stream",
        },
        body,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok)
        throw new Error(
          res.status === 404 ? "Viola needs a restart before it can take files" : data.error || res.statusText,
        );
      Object.assign(item, { status: "done", att: data });
    } catch (e) {
      item.status = "error";
      toast(`Couldn't add ${item.name}: ${e.message}`);
    }
    if (draftKey() === key) renderTray();
  }
}

function clearTray(key) {
  for (const item of trays[key] || []) if (item.preview) URL.revokeObjectURL(item.preview);
  trays[key] = [];
}

let creating = null;
async function send(textOverride, attachmentsOverride) {
  const input = $("input");
  const text = (textOverride ?? input.value).trim();
  const key = draftKey();
  const ready = textOverride == null ? tray().filter((i) => i.status === "done") : [];
  const attachments = attachmentsOverride ?? ready.map((i) => i.att);
  if ((!text && !attachments.length) || state.current?.live) return;
  if (textOverride == null && tray().some((i) => i.status === "uploading")) return toast("Still adding your files…");
  if (textOverride == null) {
    input.value = "";
    stashDraft();
    clearTray(key);
    renderTray();
    autosize();
    closeSlash();
  }
  try {
    if (!state.current) {
      // A second send while the chat is still being made joins that chat instead of making another.
      creating ??= api("POST", "conversations", state.draft).finally(() => (creating = null));
      const conv = await creating;
      if (!state.current) {
        state.current = conv;
        localStorage.setItem("viola.current", conv.id);
        upsertConv({
          id: conv.id,
          title: conv.title,
          updated: conv.updated,
          created: conv.created,
          running: false,
          cwd: conv.cwd,
        });
        renderSidebar();
      }
    }
    const conv = state.current;
    if (!conv.running) {
      conv.running = true;
      updateComposer();
    }
    await api("POST", `conversations/${conv.id}/send`, {
      text,
      attachments,
      model: conv.model,
      effort: conv.effort,
      permission_mode: conv.permission_mode,
    });
  } catch (e) {
    if (state.current && !state.current.messages?.at(-1)?.status?.startsWith("stream")) state.current.running = false;
    updateComposer();
    if (textOverride == null) {
      input.value = text;
      stashDraft();
      autosize();
    }
    toast(e.message);
  }
}

function retry(index) {
  const msgs = state.current?.messages || [];
  for (let i = index; i >= 0; i--) {
    if (msgs[i].role === "user") return send(msgs[i].text, msgs[i].attachments || []);
  }
}

async function stop() {
  if (state.current?.running) await api("POST", `conversations/${state.current.id}/stop`).catch(() => {});
}

function defaultBuildMode() {
  const mode = state.settings.permission_mode;
  return mode && mode !== "plan" && MODES[mode] ? mode : "auto";
}

async function approvePlan() {
  const conv = state.current;
  if (!conv || conv.running) return;
  conv.permission_mode = defaultBuildMode();
  await send("The plan looks good. Go ahead and build it.");
}

/* ---------- chats from the terminal ---------- */

let terminalTimer = null;

// An imported chat that's open in a terminal right now is followed live by checking its transcript.
function watchTerminal() {
  clearTimeout(terminalTimer);
  const conv = state.current;
  if (!conv?.source) return;
  terminalTimer = setTimeout(async () => {
    if (state.current !== conv) return;
    if (!document.hidden && !conv.running) {
      try {
        const fresh = await api("GET", `conversations/${conv.id}?known=${conv.source.offset}`);
        if (fresh.unchanged) {
          if (fresh.live?.status !== conv.live?.status) {
            conv.live = fresh.live;
            renderPending();
            updateComposer();
            scrollToBottom();
          }
        } else if (state.current === conv && !conv.running) {
          const changed =
            fresh.messages.length !== conv.messages.length ||
            JSON.stringify(fresh.messages.at(-1)) !== JSON.stringify(conv.messages.at(-1)) ||
            fresh.live?.status !== conv.live?.status;
          if (changed) {
            const before = conv.messages;
            fresh.running = false;
            Object.assign(conv, fresh);
            updateThread(before);
          }
        }
      } catch {
        // A missed check is retried on the next tick.
      }
    }
    watchTerminal();
  }, conv.live ? 4000 : 20000);
}

/* ---------- composer ---------- */

function autosize() {
  const input = $("input");
  const max = innerHeight * 0.4;
  const stick = pinned;
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, max)}px`;
  if (stick) scroller.scrollTop = scroller.scrollHeight;
  // Fractional display scaling leaves scrollHeight a pixel over the height, which would show scrollbars.
  input.style.overflowY = input.scrollHeight > max ? "auto" : "hidden";
  syncSendButtons();
}

function syncSendButtons() {
  const running = !!state.current?.running;
  const hasText = !!$("input").value.trim() || tray().some((i) => i.status === "done");
  $("stop").hidden = !running;
  $("send").hidden = running && !hasText;
  $("send").disabled = !hasText || !!state.current?.live;
}

function updateComposer() {
  const t = target();
  const conv = state.current;
  $("model-label").textContent = modelName(t.model);
  $("effort-label").textContent = EFFORT_LABEL[t.effort] || t.effort || "";
  const locked = !!conv?.session_started;
  $("cwd-label").textContent = shortPath(t.cwd || "~");
  $("cwd-chip").classList.toggle("locked", locked);
  $("cwd-chip").querySelector(".chip-icon").innerHTML = icon(locked ? "lock" : "folder");
  const mode = t.permission_mode || state.settings.permission_mode || "auto";
  const info = MODES[mode] || MODES.auto;
  const chip = $("mode-chip");
  chip.className = `chip mode-chip mode-${mode}`;
  chip.hidden = mode === "auto";
  chip.querySelector(".chip-icon").innerHTML = icon(info.icon);
  $("mode-label").textContent = isPhone() ? info.short || info.label : info.label;
  const name = assistantName();
  $("input").placeholder = conv?.running
    ? `Add something while ${name} works…`
    : conv?.messages?.length
      ? `Reply to ${name}…`
      : "How can I help you today?";
  const note = $("live-note");
  if (conv?.live) {
    note.innerHTML =
      `<span class="live-dot"></span><span>This chat is open in a terminal${
        conv.live.name ? ` (${escapeHtml(conv.live.name)})` : ""
      }. ` +
      `Viola follows along as it goes. Reply there, or here once it's closed.</span>`;
  }
  note.hidden = !conv?.live;
  autosize();
}

function filteredSlash(query) {
  const all = state.settings.slash_commands || [];
  const q = query.toLowerCase();
  const starts = all.filter((c) => c.name.toLowerCase().startsWith(q));
  const contains = all.filter((c) => !c.name.toLowerCase().startsWith(q) && c.name.toLowerCase().includes(q));
  return [...starts, ...contains].slice(0, 40);
}

// The /word just before the cursor, at the start or after a space, so commands work mid-message too.
function slashToken() {
  const input = $("input");
  const before = input.value.slice(0, input.selectionStart);
  const m = before.match(/(^|\s)\/([\w:.-]*)$/);
  return m ? { query: m[2], start: before.length - m[2].length - 1, end: input.selectionStart } : null;
}

function updateSlash() {
  const token = slashToken();
  if (!token) return closeSlash();
  state.slash.items = filteredSlash(token.query);
  state.slash.index = Math.min(state.slash.index, Math.max(0, state.slash.items.length - 1));
  const menu = $("slash-menu");
  if (!state.slash.items.length) return closeSlash();
  menu.innerHTML = "";
  state.slash.items.forEach((c, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "slash-item" + (i === state.slash.index ? " active" : "");
    b.innerHTML = `<span class="slash-name">/${escapeHtml(c.name)}</span><span class="slash-desc">${
      escapeHtml(c.description || "")
    }</span>`;
    b.onmousedown = (e) => {
      e.preventDefault();
      pickSlash(i);
    };
    menu.append(b);
  });
  menu.hidden = false;
  // Scrolling only the menu: scrollIntoView would also nudge the page itself.
  const item = menu.children[state.slash.index];
  if (item && item.offsetTop < menu.scrollTop) menu.scrollTop = item.offsetTop;
  else if (item && item.offsetTop + item.offsetHeight > menu.scrollTop + menu.clientHeight)
    menu.scrollTop = item.offsetTop + item.offsetHeight - menu.clientHeight;
}

function pickSlash(i) {
  const c = state.slash.items[i];
  const token = slashToken();
  if (!c || !token) return;
  const input = $("input");
  const after = input.value.slice(token.end).replace(/^\S*/, "");
  input.value = `${input.value.slice(0, token.start)}/${c.name} ${after.replace(/^ /, "")}`;
  const caret = token.start + c.name.length + 2;
  input.setSelectionRange(caret, caret);
  closeSlash();
  autosize();
  stashDraft();
  input.focus();
}

function closeSlash() {
  $("slash-menu").hidden = true;
  state.slash = { items: [], index: 0 };
}

/* ---------- popovers and sheets ---------- */

let openPop = null;
let popAnchor = null;
let popOptions = {};

const MENUS = ".model-menu, .submenu, .plus-menu, .select-menu, .conv-menu";
// A menu opened with the keyboard takes focus; one opened with the mouse doesn't, since WebKitGTK would draw a focus ring.
let keyboardLast = false;
document.addEventListener("keydown", () => (keyboardLast = true), true);
document.addEventListener("pointerdown", () => (keyboardLast = false), true);

const menuItems = (menu) =>
  [...menu.querySelectorAll("button:not(:disabled)")].filter((b) => b.getClientRects().length);

function focusMenu(menu) {
  const items = menuItems(menu);
  (items.find((b) => b.classList.contains("selected")) || items[0])?.focus();
}

function moveInMenu(key) {
  const menu = document.activeElement?.closest(MENUS) || openPop;
  const items = menuItems(menu);
  const at = items.indexOf(document.activeElement);
  const down = key === "ArrowDown";
  let next = (at + (down ? 1 : -1) + items.length) % items.length;
  if (key === "Home" || (at < 0 && down)) next = 0;
  if (key === "End" || (at < 0 && !down)) next = items.length - 1;
  items[next]?.focus();
}

function showPopover(pop, anchor, options = {}) {
  closePopover(true);
  // A modal dialog sits in the top layer, so anything opened from inside it has to live inside it too.
  const host = document.querySelector("dialog[open]") || document.body;
  if (pop.parentElement !== host) host.append(pop);
  const scrim = $("sheet-scrim");
  if (scrim.parentElement !== host) host.append(scrim);
  openPop = pop;
  popAnchor = anchor;
  popOptions = options;
  pop.classList.remove("closing");
  pop.style.transform = "";
  if (isPhone()) {
    // Dismiss the keyboard first; a resize mid-tap used to close the menu again.
    if (document.activeElement && document.activeElement !== document.body) document.activeElement.blur();
    pop.classList.add("sheet");
    pop.hidden = false;
    pop.scrollTop = 0;
    scrim.classList.remove("closing");
    scrim.hidden = false;
  } else {
    pop.classList.remove("sheet");
    pop.hidden = false;
    placePopover();
    snapToPixels();
    if (keyboardLast && pop.matches(MENUS)) focusMenu(pop);
  }
}

function placePopover() {
  if (!openPop || openPop.classList.contains("sheet") || !popAnchor) return;
  const pop = openPop;
  const { above = false, alignRight = false, at = null } = popOptions;
  const r = at ? new DOMRect(at[0], at[1], 0, 0) : popAnchor.getBoundingClientRect();
  const gap = at ? 2 : 8;
  pop.style.maxHeight = "";
  const roomAbove = r.top - 16;
  const roomBelow = innerHeight - r.bottom - 16;
  const up = above ? roomAbove > 220 || roomAbove > roomBelow : roomBelow < 220 && roomAbove > roomBelow;
  pop.style.maxHeight = `${Math.max(160, up ? roomAbove : roomBelow)}px`;
  const w = pop.offsetWidth;
  const h = pop.offsetHeight;
  let left = alignRight ? r.right - w : r.left;
  left = Math.max(8, Math.min(left, innerWidth - w - 8));
  const top = up ? r.top - h - gap : r.bottom + gap;
  // A dialog that snapToPixels nudged becomes the frame fixed positions are measured from, so they're made relative to it.
  const dialog = pop.parentElement.closest("dialog[open]");
  const frame = dialog?.style.translate ? dialog.getBoundingClientRect() : null;
  const dx = frame ? frame.left + dialog.clientLeft : 0;
  const dy = frame ? frame.top + dialog.clientTop : 0;
  pop.style.left = `${Math.round(left - dx)}px`;
  pop.style.top = `${Math.round(Math.max(8, top) - dy)}px`;
  pop.style.setProperty("--origin", `${up ? "bottom" : "top"} ${alignRight ? "right" : "left"}`);
}

// Plays an element's closing animation, then hides it; a theme without one (Windows 95) hides it at once.
// WebKitGTK doesn't send animationcancel when a theme switch removes the animation, so applyTheme finishes
// pending closes itself, and the timer covers anything else.
const pendingCloses = new Set();
function hideAfterAnimation(el, hide) {
  el.classList.add("closing");
  const done = (e) => {
    if (e?.target && e.target !== el) return;
    pendingCloses.delete(done);
    el.removeEventListener("animationend", done);
    el.removeEventListener("animationcancel", done);
    clearTimeout(timer);
    if (!el.classList.contains("closing")) return;
    el.classList.remove("closing");
    hide();
  };
  const timer = setTimeout(done, 600);
  pendingCloses.add(done);
  if (getComputedStyle(el).animationName === "none") return done();
  el.addEventListener("animationend", done);
  el.addEventListener("animationcancel", done);
}

function closeDialog(dialog) {
  if (dialog.open && !dialog.classList.contains("closing")) hideAfterAnimation(dialog, () => dialog.close());
}

function closePopover(instant = false) {
  closeMoreModels(true);
  const pop = openPop;
  if (keyboardLast && pop && document.activeElement?.closest(MENUS)) popAnchor?.focus();
  openPop = null;
  popAnchor = null;
  $("plus-btn").setAttribute("aria-expanded", "false");
  const del = document.querySelector(".conv-menu .delete-label");
  if (del) del.textContent = deleteLabel();
  if (!pop) return;
  const scrim = $("sheet-scrim");
  if (pop.classList.contains("sheet") && !instant) {
    pop.classList.add("closing");
    scrim.classList.add("closing");
    setTimeout(() => {
      if (openPop === pop) return;
      pop.hidden = true;
      pop.classList.remove("closing");
      pop.style.transform = "";
      if (!openPop) scrim.hidden = true;
      repaint();
    }, 230);
  } else if (instant || pop.classList.contains("sheet")) {
    pop.classList.remove("closing");
    pop.hidden = true;
    if (!openPop) scrim.hidden = true;
  } else {
    hideAfterAnimation(pop, () => (pop.hidden = true));
  }
}

function enableSwipeDown(pop) {
  let startY = null;
  let dy = 0;
  pop.addEventListener("touchstart", (e) => {
    if (!pop.classList.contains("sheet") || pop.scrollTop > 0) return;
    startY = e.touches[0].clientY;
    dy = 0;
    pop.style.transition = "none";
  }, { passive: true });
  pop.addEventListener("touchmove", (e) => {
    if (startY == null) return;
    dy = Math.max(0, e.touches[0].clientY - startY);
    pop.style.transform = dy ? `translateY(${dy}px)` : "";
  }, { passive: true });
  pop.addEventListener("touchend", () => {
    if (startY == null) return;
    startY = null;
    pop.style.transition = "";
    // Closing slides on from where the finger let go; resetting first made it jump back up.
    if (dy > 90) {
      closePopover();
    } else {
      pop.style.transform = "";
    }
  });
}

document.addEventListener("mousedown", (e) => {
  if (
    openPop &&
    !openPop.classList.contains("sheet") &&
    !openPop.contains(e.target) &&
    !e.target.closest("[data-pop-anchor], #model-more")
  )
    closePopover();
});

function primaryModels() {
  return LINES.map((line) => state.models.find((m) => m.line === line)).filter(Boolean);
}

function modelItem(m) {
  return (
    `<button class="menu-item ${m.id === target().model ? "selected" : ""}" data-model="${escapeHtml(m.id)}">` +
    `<span class="menu-text"><span>${escapeHtml(m.name)}</span></span><span class="check">${icon("check")}</span></button>`
  );
}

function otherModels() {
  const primary = primaryModels();
  return state.models.filter((m) => !primary.includes(m));
}

function modelChanges(id) {
  const model = state.models.find((m) => m.id === id);
  const changes = { model: id };
  if (model?.efforts?.length && !model.efforts.includes(target().effort)) changes.effort = model.efforts.at(-1);
  return changes;
}

function renderModelMenu() {
  const menu = $("model-menu");
  const t = target();
  const primary = primaryModels();
  const others = otherModels();
  const current = state.models.find((m) => m.id === t.model);
  // Phones slide the other models open in place; computers show them in a menu beside this one.
  const inline = isPhone();
  let html = `<div class="menu-heading">Model</div>` + primary.map(modelItem).join("");
  if (current && !primary.includes(current) && !(inline && state.showMoreModels)) html += modelItem(current);
  if (others.length && inline) {
    const open = state.showMoreModels;
    html +=
      `<button class="menu-item more-models" data-more="1" aria-expanded="${open}"><span class="menu-text">${
        open ? "Fewer models" : "More models"
      }</span>${icon("chevron-right")}</button>` +
      `<div class="more-list${open ? " open" : ""}"><div>${others.map(modelItem).join("")}</div></div>`;
  } else if (others.length) {
    html += `<button class="menu-item more-models flyout" aria-haspopup="true" aria-expanded="false"><span class="menu-text">More models</span>${icon("chevron-right")}</button>`;
  }
  if (state.current?.messages.length) {
    html += `<p class="menu-note">Each model keeps its own prompt cache, so switching mid-chat makes the next reply re-read the whole conversation at full price.</p>`;
  }
  const allowed = current?.efforts?.length ? current.efforts : EFFORTS;
  html +=
    `<div class="menu-sep"></div><div class="menu-heading">Effort</div><div class="segmented effort-row"><span class="seg-pill"></span>` +
    EFFORTS.map(
      (e) =>
        `<button type="button" data-effort="${e}" class="${e === t.effort ? "selected" : ""}" ${
          allowed.includes(e) ? "" : "disabled"
        }>${EFFORT_LABEL[e]}</button>`,
    ).join("") +
    `</div>`;
  menu.innerHTML = html;
  placePill(menu.querySelector(".effort-row"), false);
}

function placePill(row, animate) {
  const sel = row?.querySelector("button.selected");
  const pill = row?.querySelector(".seg-pill");
  if (!pill) return;
  if (!animate) pill.style.transition = "none";
  if (sel) {
    pill.style.transform = `translateX(${sel.offsetLeft}px)`;
    pill.style.width = `${sel.offsetWidth}px`;
    pill.style.opacity = "1";
  } else pill.style.opacity = "0";
  if (!animate) requestAnimationFrame(() => (pill.style.transition = ""));
}

$("model-menu").addEventListener("click", async (e) => {
  const btn = e.target.closest("button");
  if (!btn) return;
  if (btn.classList.contains("flyout")) {
    if (!moreOpen()) openMoreModels(btn);
    else closeMoreModels();
    return;
  }
  // The extra models slide open in place; rebuilding the menu made the sheet jump.
  if (btn.dataset.more) {
    const open = (state.showMoreModels = !state.showMoreModels);
    btn.setAttribute("aria-expanded", open);
    btn.querySelector(".menu-text").textContent = open ? "Fewer models" : "More models";
    btn.nextElementSibling.classList.toggle("open", open);
    return;
  }
  if (btn.dataset.model) {
    const changes = modelChanges(btn.dataset.model);
    renderModelMenuSelection(changes);
    await patchTarget(changes);
  }
  if (btn.dataset.effort) {
    renderModelMenuSelection({ effort: btn.dataset.effort });
    await patchTarget({ effort: btn.dataset.effort });
  }
});

let moreTimer = 0;
let pointerTrail = [];

// True while the pointer moves into the triangle between where it was a moment ago and the side menu's near edge.
function headingToMore(x, y) {
  const from = pointerTrail[0];
  const more = $("model-more").getBoundingClientRect();
  if (!from || !moreOpen()) return false;
  const edge = more.left >= $("model-menu").getBoundingClientRect().right - 1 ? more.left : more.right;
  const side = (ax, ay, bx, by) => (bx - ax) * (y - ay) - (by - ay) * (x - ax);
  const a = side(from[0], from[1], edge, more.top);
  const b = side(edge, more.top, edge, more.bottom);
  const c = side(edge, more.bottom, from[0], from[1]);
  return (a >= 0 && b >= 0 && c >= 0) || (a <= 0 && b <= 0 && c <= 0);
}

// Moving onto another row closes the side menu at once; a move heading for it gets a moment to arrive.
function leaveFlyout(e) {
  clearTimeout(moreTimer);
  if (!moreOpen()) return;
  const more = $("model-more").getBoundingClientRect();
  const inside = e.clientX >= more.left && e.clientX <= more.right && e.clientY >= more.top && e.clientY <= more.bottom;
  if (inside) return;
  if (headingToMore(e.clientX, e.clientY)) moreTimer = setTimeout(closeMoreUnlessHovered, 250);
  else closeMoreModels();
}

$("model-menu").addEventListener("mousemove", (e) => {
  if ($("model-menu").classList.contains("sheet")) return;
  const now = performance.now();
  // The last position is kept through a pause, so hesitating on the way still counts as heading there.
  const recent = pointerTrail.filter((p) => now - p[2] < 80);
  pointerTrail = recent.length ? recent : pointerTrail.slice(-1);
  const row = e.target.closest(".flyout");
  if (row) {
    clearTimeout(moreTimer);
    if (!moreOpen()) openMoreModels(row);
  } else {
    leaveFlyout(e);
  }
  pointerTrail.push([e.clientX, e.clientY, now]);
});
$("model-menu").addEventListener("mouseleave", leaveFlyout);
$("model-more").addEventListener("mouseenter", () => clearTimeout(moreTimer));
$("model-more").addEventListener("mouseleave", () => {
  clearTimeout(moreTimer);
  moreTimer = setTimeout(closeMoreUnlessHovered, 250);
});

function closeMoreUnlessHovered() {
  if (!$("model-more").matches(":hover")) closeMoreModels();
}

function openMoreModels(row) {
  const menu = $("model-menu");
  const more = $("model-more");
  more.innerHTML = otherModels().map(modelItem).join("");
  if (more.parentElement !== menu.parentElement) menu.parentElement.append(more);
  more.style.maxHeight = `${innerHeight - 16}px`;
  more.classList.remove("closing");
  more.hidden = false;
  const m = menu.getBoundingClientRect();
  const r = row.getBoundingClientRect();
  const w = more.offsetWidth;
  const h = more.offsetHeight;
  const right = m.right + 4 + w <= innerWidth - 8;
  more.style.left = `${Math.round(right ? m.right + 4 : m.left - w - 4)}px`;
  more.style.top = `${Math.round(Math.max(8, Math.min(r.top - 6, innerHeight - h - 8)))}px`;
  more.style.setProperty("--origin", `top ${right ? "left" : "right"}`);
  row.setAttribute("aria-expanded", "true");
  if (menu.contains(document.activeElement)) focusMenu(more);
}

// Shrinks away the way it popped in, unless the whole menu is closing with it.
function closeMoreModels(instant = false) {
  clearTimeout(moreTimer);
  const more = $("model-more");
  $("model-menu").querySelector(".flyout")?.setAttribute("aria-expanded", "false");
  if (instant || more.hidden) {
    more.classList.remove("closing");
    more.hidden = true;
  } else if (!more.classList.contains("closing")) {
    hideAfterAnimation(more, () => (more.hidden = true));
  }
}

const moreOpen = () => !$("model-more").hidden && !$("model-more").classList.contains("closing");

$("model-more").addEventListener("click", async (e) => {
  const btn = e.target.closest("[data-model]");
  if (!btn) return;
  closeMoreModels();
  await patchTarget(modelChanges(btn.dataset.model));
  if (openPop !== $("model-menu")) return;
  renderModelMenu();
  placePopover();
});

// Updates the open menu in place, so picking something doesn't rebuild it under your finger.
function renderModelMenuSelection(changes) {
  const menu = $("model-menu");
  if (changes.model) {
    for (const b of menu.querySelectorAll("[data-model]"))
      b.classList.toggle("selected", b.dataset.model === changes.model);
    const model = state.models.find((m) => m.id === changes.model);
    const allowed = model?.efforts?.length ? model.efforts : EFFORTS;
    for (const b of menu.querySelectorAll("[data-effort]")) b.disabled = !allowed.includes(b.dataset.effort);
  }
  const effort = changes.effort || target().effort;
  for (const b of menu.querySelectorAll("[data-effort]")) b.classList.toggle("selected", b.dataset.effort === effort);
  placePill(menu.querySelector(".effort-row"), true);
}

function modeItem(mode, selected) {
  const info = MODES[mode];
  return (
    `<button type="button" class="menu-item mode-item ${selected ? "selected" : ""}" data-mode="${mode}">` +
    `<span class="mode-icon">${icon(info.icon)}</span>` +
    `<span class="menu-text"><span>${info.label}</span><span class="menu-sub">${escapeHtml(info.desc)}</span></span>` +
    `<span class="check">${icon("check")}</span></button>`
  );
}

function openPlusMenu() {
  const menu = $("plus-menu");
  if (openPop === menu) return closePopover();
  const current = target().permission_mode || state.settings.permission_mode || "auto";
  const order = MODE_ORDER.includes(current) ? MODE_ORDER : [...MODE_ORDER, current];
  const tiles = [
    isTouch() && ["camera", "camera", "Camera"],
    ["photos", "image", "Photos"],
    ["files", "paperclip", "Files"],
  ].filter(Boolean);
  menu.innerHTML =
    `<div class="attach-row">${tiles
      .map(
        ([pick, name, label]) =>
          `<button type="button" class="attach-tile" data-pick="${pick}">${icon(name)}<span>${label}</span></button>`,
      )
      .join("")}</div>` +
    `<div class="menu-sep"></div><div class="menu-heading">Mode</div>` +
    order.map((m) => modeItem(m, m === current)).join("") +
    (state.current?.running
      ? `<p class="menu-note">The reply that's running keeps its mode. The change starts with the next one.</p>`
      : "");
  showPopover(menu, $("plus-btn"), { above: !$("app").classList.contains("empty") });
  $("plus-btn").setAttribute("aria-expanded", "true");
}

$("plus-menu").addEventListener("click", async (e) => {
  const tile = e.target.closest("[data-pick]");
  if (tile) {
    closePopover(true);
    // Opening the picker has to happen inside the tap itself, or the browser blocks it.
    $(`pick-${tile.dataset.pick}`).click();
    return;
  }
  const btn = e.target.closest("[data-mode]");
  if (!btn) return;
  closePopover();
  await patchTarget({ permission_mode: btn.dataset.mode });
});

/* ---------- working folder ---------- */

function recentFolders(exclude) {
  const seen = new Set([exclude]);
  const found = [];
  for (const c of [...state.convs, ...state.sessions].sort((a, b) => b.updated - a.updated)) {
    if (!c.cwd || seen.has(c.cwd)) continue;
    seen.add(c.cwd);
    found.push(c.cwd);
    if (found.length === 5) break;
  }
  return found;
}

function openFolderPicker() {
  const pop = $("cwd-pop");
  if (openPop === pop) return closePopover();
  const locked = !!state.current?.session_started;
  $("cwd-browser").hidden = locked;
  pop.querySelector(".cwd-locked")?.remove();
  if (locked) {
    $("cwd-note").insertAdjacentHTML(
      "beforebegin",
      `<div class="cwd-locked">${escapeHtml(shortPath(state.current.cwd))}</div>`,
    );
    $("cwd-note").textContent =
      "This chat's Claude Code session lives in this folder, so it can't move now. Start a new chat to work somewhere else.";
  } else {
    $("cwd-note").textContent =
      "Claude Code starts here, and the chat stays in this folder once the first message is sent.";
    $("cwd-input").value = "";
    browse(target().cwd || state.settings.home || "~", true);
  }
  showPopover(pop, $("cwd-chip"), { above: !$("app").classList.contains("empty") });
}

async function browse(path, withRecent = false) {
  const list = $("cwd-list");
  let data;
  try {
    data = await api("GET", `dirs?path=${encodeURIComponent(path)}`);
  } catch (e) {
    if (e.status === 404) {
      // Before a backend restart there's no folder listing, so only typing a path works.
      list.innerHTML = `<div class="cwd-empty">Type a path below.</div>`;
      state.browse = { path, parent: null };
      $("cwd-path").textContent = shortPath(path);
      return;
    }
    toast(e.message);
    return;
  }
  state.browse = data;
  $("cwd-path").textContent = shortPath(data.path);
  $("cwd-up").disabled = !data.parent;
  const row = (path, label, iconName, chevron) =>
    `<button type="button" class="cwd-row" data-path="${escapeHtml(path)}">${icon(iconName)}<span>${escapeHtml(label)}</span>` +
    (chevron ? icon("chevron-right").replace('class="ico ', 'class="ico chev ') : "") +
    `</button>`;
  let html = "";
  const recent = withRecent ? recentFolders(data.path) : [];
  if (recent.length) {
    html += `<div class="menu-heading">Recent</div>` + recent.map((p) => row(p, shortPath(p), "clock", false)).join("");
    html += `<div class="menu-heading">Folders in ${escapeHtml(shortPath(data.path))}</div>`;
  }
  html += data.dirs.length
    ? data.dirs
        .map((name) =>
          row(`${data.path.replace(/[\\/]$/, "")}${state.settings.sep || "/"}${name}`, name, "folder", true),
        )
        .join("")
    : `<div class="cwd-empty">No folders in here.</div>`;
  list.innerHTML = html;
  list.scrollTop = 0;
}

async function useFolder(path) {
  closePopover();
  await patchTarget({ cwd: path });
}

/* ---------- settings ---------- */

function renderAdminNote() {
  const s = state.settings;
  const note = $("admin-note");
  if (!s.admin_hint) {
    note.textContent =
      "With an admin key, Viola checks what Anthropic actually billed, so the counter stays exact. You still set the balance once.";
  } else if (state.credits.error) {
    note.textContent = state.credits.error;
  } else if (state.credits.balance == null) {
    note.textContent =
      "Set your balance once by tapping the counter, and Viola keeps it in step with what Anthropic billed.";
  } else {
    note.textContent = state.credits.live
      ? "Accurate billing is on. Every night, the counter will sync with your official API balance."
      : "Checking with Anthropic…";
  }
  note.style.color = state.credits.error && s.admin_hint ? "hsl(var(--danger))" : "";
}

function enhanceSelects(root) {
  for (const select of root.querySelectorAll("select.kselect")) {
    const control = document.createElement("div");
    control.className = "kselect";
    select.after(control);
    select.hidden = true;
    select.control = control;
    control.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (btn) openSelectMenu(select, btn);
    });
    renderSelect(select);
  }
}

function renderSelect(select) {
  const control = select.control;
  if (!control) return;
  const option = select.selectedOptions[0];
  const mode = select.name === "permission_mode" ? MODES[select.value] : null;
  control.innerHTML =
    `<button type="button" class="kselect-btn" data-pop-anchor>${
      mode ? `<span class="mode-icon mode-item" data-mode="${select.value}">${icon(mode.icon)}</span>` : ""
    }` +
    `<span class="kselect-label">${escapeHtml(option?.text || "")}</span>${icon("chevron")}</button>`;
}

function pickSelect(select, value) {
  if (select.value === value) return;
  select.value = value;
  renderSelect(select);
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

function openSelectMenu(select, anchor) {
  const menu = $("select-menu");
  if (openPop === menu && menu.dataset.for === select.name) return closePopover();
  menu.dataset.for = select.name;
  const modes = select.name === "permission_mode";
  menu.innerHTML = [...select.options]
    .map((o) =>
      modes
        ? modeItem(o.value, o.value === select.value)
        : `<button type="button" class="menu-item ${o.value === select.value ? "selected" : ""}" data-value="${o.value}"><span class="menu-text">${escapeHtml(o.text)}</span><span class="check">${icon("check")}</span></button>`,
    )
    .join("");
  menu.onclick = (e) => {
    const btn = e.target.closest("[data-value], [data-mode]");
    if (!btn) return;
    closePopover();
    pickSelect(select, btn.dataset.value || btn.dataset.mode);
  };
  showPopover(menu, anchor, {});
}

function fillSettings() {
  const form = $("settings-form");
  const s = state.settings;
  for (const el of form.elements) {
    if (!el.name || el.name === "api_key" || el.name === "admin_key") continue;
    if (el.type === "checkbox") el.checked = !!s[el.name];
    else if (el.name === "theme") el.value = themeId(s.theme);
    else if (document.activeElement !== el) el.value = s[el.name] ?? "";
    if (el.tagName === "SELECT") renderSelect(el);
  }
  renderAdminNote();
  renderThemeIcon();
  $("icon-setting").hidden = !window.ViolaAndroid?.setIcon && !(onComputer && s.app_icon);
  $("icon-note").textContent = window.ViolaAndroid
    ? "The icon switches when you leave Viola. Some launchers take the old one off the home screen, so you may need to add Viola back from the app drawer."
    : "Viola's icon in your app launcher and taskbar changes with the theme.";
  $("match-icon").checked = !!localStorage.getItem("viola.matchIcon");
  $("forget-key").hidden = s.key_source !== "app settings";
  $("admin-set-row").hidden = !s.admin_hint;
  $("admin-input-row").hidden = !!s.admin_hint;
  $("admin-hint").textContent = s.admin_hint || "";
  $("key-hint").textContent = s.key_hint ? `${s.key_hint}  (from ${s.key_source})` : "No key found";
  $("remote-section").hidden = !onComputer;
  $("remote-box").hidden = !s.remote_url;
  $("remote-url").textContent = s.remote_url || "";
  const note = $("remote-note");
  note.textContent = s.remote_error || note.dataset.default;
  note.style.color = s.remote_error ? "hsl(var(--danger))" : "";
}

async function saveSetting(el) {
  const value = el.type === "checkbox" ? el.checked : el.value;
  if (el.name === "theme") {
    state.settings.theme = value;
    applyTheme();
    renderThemeIcon();
  }
  if ((el.name === "api_key" || el.name === "admin_key") && !value) return;
  try {
    state.settings = await api("PATCH", "settings", { [el.name]: value });
    if (el.name === "api_key" || el.name === "admin_key") {
      el.value = "";
      loadModels();
    }
    if (el.name === "auth") loadModels();
    if (el.name === "permission_mode" && !state.current) state.draft.permission_mode = value;
    applyTheme();
    renderProfile();
    renderSidebar();
    fillSettings();
  } catch (e) {
    toast(e.message);
    fillSettings();
  }
}

/* ---------- first-run setup ---------- */

function setTick(id, ok) {
  const el = $(id);
  el.classList.toggle("ok", ok);
  el.innerHTML = ok ? icon("check") : "";
}

function renderSetup() {
  const s = state.settings;
  setTick("tick-claude", !!s.claude_version);
  $("setup-claude").textContent = s.claude_version
    ? `Found Claude Code ${s.claude_version}.`
    : "Viola couldn't find Claude Code. Paste this into a terminal to install it, then check again.";
  $("setup-install").hidden = !!s.claude_version;
  const keyReady = s.auth === "subscription" || !!s.key_hint;
  setTick("tick-key", keyReady);
  const msg = $("setup-key-msg");
  if (!msg.classList.contains("bad")) {
    msg.textContent =
      s.auth === "subscription"
        ? "Using your Claude subscription login."
        : s.key_hint
          ? `Using ${s.key_hint}.`
          : "";
  }
  if (s.admin_hint && !$("setup-admin-msg").classList.contains("bad"))
    $("setup-admin-msg").textContent = `Added ${s.admin_hint}.`;
  $("setup-start").disabled = !!s.needs_setup;
}

async function setupPatch(changes, msgId) {
  const msg = $(msgId);
  msg.classList.remove("bad");
  msg.textContent = "Checking with Anthropic…";
  try {
    state.settings = await api("PATCH", "settings", changes);
    msg.textContent = "";
    renderSetup();
    renderProfile();
    loadModels();
    return true;
  } catch (e) {
    msg.classList.add("bad");
    msg.textContent = e.message;
    return false;
  }
}

function bindSetup() {
  const dialog = $("setup");
  dialog.addEventListener("cancel", (e) => {
    if (state.settings.needs_setup) e.preventDefault();
  });
  $("setup-key-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = $("setup-key").value.trim();
    if (key && (await setupPatch({ api_key: key, auth: "promo" }, "setup-key-msg"))) $("setup-key").value = "";
  });
  $("setup-admin-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const key = $("setup-admin").value.trim();
    if (key && (await setupPatch({ admin_key: key }, "setup-admin-msg"))) $("setup-admin").value = "";
  });
  $("copy-install").onclick = (e) => copyWithLabel(e.currentTarget, $("install-cmd").textContent);
  $("recheck").onclick = async () => {
    state.settings = await api("POST", "setup/recheck");
    renderSetup();
  };
  $("setup-start").onclick = () => {
    dialog.close();
    newChat();
  };
  $("forget-key").onclick = async () => {
    state.settings = await api("PATCH", "settings", { api_key: "" });
    fillSettings();
    if (state.settings.needs_setup) {
      $("settings").close();
      renderSetup();
      dialog.showModal();
    }
  };
  $("forget-admin").onclick = async () => {
    state.settings = await api("PATCH", "settings", { admin_key: "" });
    fillSettings();
  };
}

/* ---------- boot ---------- */

async function loadState() {
  const data = await api("GET", "state");
  if (data.now) clockSkew = data.now - Date.now();
  state.settings = data.settings;
  state.credits = data.credits;
  state.convs = data.conversations;
  state.sessions = data.sessions || [];
  if (!state.current && !state.draft.permission_mode)
    state.draft.permission_mode = state.settings.permission_mode || "auto";
  applyTheme();
  renderProfile();
  renderCredits();
  renderSidebar();
  fillSettings();
}

async function loadVerbs() {
  try {
    const extra = (await api("GET", "verbs")).verbs;
    verbs = [...new Set([...VERBS, ...extra])];
  } catch {
    // Viola's own verbs are enough.
  }
}

async function loadModels() {
  try {
    state.models = (await api("GET", "models")).models;
  } catch {
    state.models = [];
  }
  updateComposer();
}

function readToken() {
  const m = location.hash.match(/token=([^&]+)/);
  if (m) {
    localStorage.setItem("viola.token", decodeURIComponent(m[1]));
    history.replaceState(null, "", location.pathname);
  }
  return localStorage.getItem("viola.token") || "";
}

let menuChat = null;

function deleteLabel() {
  return menuChat?.terminal ? "Remove from Viola" : "Delete";
}

function openChatMenu(chat, anchor, options) {
  if (!chat) return;
  menuChat = chat;
  const menu = $("conv-menu");
  menu.querySelector('[data-action="terminal"]').hidden = !onComputer;
  menu.querySelector(".delete-label").textContent = deleteLabel();
  showPopover(menu, anchor, options);
}

function sidebarChat(id) {
  return state.convs.find((c) => c.id === id) || state.sessions.find((s) => s.id === id);
}

// A terminal chat Viola hasn't opened yet has to be read in before it can be renamed or removed.
async function ensureImported(id) {
  if (state.sessions.some((s) => s.id === id) && !state.convs.some((c) => c.id === id))
    await api("GET", `conversations/${id}`);
}

function bindLongPress(list) {
  let timer = null;
  let start = null;
  let held = false;
  const cancel = () => {
    clearTimeout(timer);
    start = null;
    for (const row of list.querySelectorAll(".conv[data-mark]")) {
      clearTimeout(Number(row.dataset.mark));
      delete row.dataset.mark;
    }
    list.querySelector(".conv.held")?.classList.remove("held");
  };
  const open = (row) => {
    held = true;
    cancel();
    openChatMenu(sidebarChat(row.dataset.id), row, {});
  };
  list.addEventListener("pointerdown", (e) => {
    const row = e.target.closest(".conv");
    if (!row || e.pointerType === "mouse") return;
    held = false;
    start = [e.clientX, e.clientY];
    const mark = setTimeout(() => start && row.classList.add("held"), 160);
    timer = setTimeout(() => {
      clearTimeout(mark);
      navigator.vibrate?.(12);
      open(row);
    }, 450);
    row.dataset.mark = mark;
  });
  list.addEventListener("pointermove", (e) => {
    if (start && Math.hypot(e.clientX - start[0], e.clientY - start[1]) > 10) cancel();
  });
  list.addEventListener("pointerup", cancel);
  list.addEventListener("pointercancel", cancel);
  list.addEventListener("contextmenu", (e) => {
    const row = e.target.closest(".conv");
    if (!row) return;
    e.preventDefault();
    if (held) return;
    // Only a long press goes through open(): a right-click has no finger-lift to swallow,
    // so it would eat the next click.
    if (start) open(row);
    else openChatMenu(sidebarChat(row.dataset.id), row, e.clientX || e.clientY ? { at: [e.clientX, e.clientY] } : {});
  });
  // The tap that ends a long press mustn't also open the chat.
  list.addEventListener("click", (e) => {
    if (!held) return;
    held = false;
    e.stopPropagation();
    e.preventDefault();
  }, true);
}

// Android's back button closes whatever is on top before it leaves the app.
window.violaBack = () => {
  if (!$("lightbox").hidden) {
    $("lightbox").hidden = true;
    return true;
  }
  if (openPop) {
    closePopover();
    return true;
  }
  const dialog = document.querySelector("dialog[open]");
  if (dialog && dialog.id !== "setup") {
    dialog.close();
    return true;
  }
  if ($("app").classList.contains("sidebar-open")) {
    toggleSidebar(false);
    return true;
  }
  return false;
};

function bind() {
  for (const el of [scroller, $("composer-wrap"), $("welcome"), $("settings"), $("search-dialog"), $("setup")])
    pixelSnapper.observe(el);
  const input = $("input");
  input.addEventListener("input", () => {
    autosize();
    updateSlash();
    stashDraft();
  });
  input.addEventListener("click", updateSlash);
  input.addEventListener("keydown", (e) => {
    if (e.isComposing || e.keyCode === 229) return;
    const slashOpen = !$("slash-menu").hidden;
    if (slashOpen && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      e.preventDefault();
      const n = state.slash.items.length;
      state.slash.index = (state.slash.index + (e.key === "ArrowDown" ? 1 : n - 1)) % n;
      updateSlash();
      return;
    }
    if (slashOpen && (e.key === "Tab" || (e.key === "Enter" && !e.shiftKey))) {
      e.preventDefault();
      pickSlash(state.slash.index);
      return;
    }
    if (e.key === "Enter" && !e.shiftKey && !isPhone()) {
      e.preventDefault();
      send();
    }
  });
  input.addEventListener("blur", () => setTimeout(closeSlash, 150));

  $("composer").addEventListener("submit", (e) => {
    e.preventDefault();
    send();
  });
  $("stop").onclick = stop;
  $("new-chat").onclick = newChat;
  $("open-search").onclick = openSearch;
  $("close-search").onclick = () => closeDialog($("search-dialog"));
  $("search-field").onclick = () => $("search-input").focus();
  $("clear-search").onclick = (e) => {
    e.stopPropagation();
    $("search-input").value = "";
    renderSearch();
    $("search-input").focus();
  };
  $("search-input").addEventListener("input", renderSearch);
  $("search-input").addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      moveSearch(e.key === "ArrowDown" ? 1 : -1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      pickResult($("search-results").querySelector(".result.active") || $("search-results").querySelector(".result"));
    }
  });
  $("search-results").addEventListener("click", (e) => pickResult(e.target.closest(".result")));
  // A click on the dimmed backdrop lands on the dialog itself.
  $("search-dialog").addEventListener("click", (e) => {
    if (e.target === $("search-dialog")) closeDialog($("search-dialog"));
  });
  $("collapse-sidebar").onclick = () => toggleSidebar(false);
  $("expand-sidebar").onclick = () => toggleSidebar(true);
  $("scrim").onclick = () => toggleSidebar(false);
  $("sheet-scrim").onclick = () => closePopover();
  $("jump").onclick = glideToBottom;

  for (const id of ["model-btn", "cwd-chip", "plus-btn", "mode-chip", "conv-menu-btn", "credits"])
    $(id).dataset.popAnchor = "1";
  for (const id of ["model-menu", "plus-menu", "select-menu", "cwd-pop", "conv-menu", "rename-pop", "credits-pop"])
    enableSwipeDown($(id));

  $("model-btn").onclick = () => {
    if (openPop === $("model-menu")) return closePopover();
    renderModelMenu();
    showPopover($("model-menu"), $("model-btn"), { above: !$("app").classList.contains("empty"), alignRight: true });
    placePill($("model-menu").querySelector(".effort-row"), false);
  };
  $("plus-btn").onclick = openPlusMenu;
  $("mode-chip").onclick = openPlusMenu;
  for (const pick of ["camera", "photos", "files"]) {
    $(`pick-${pick}`).addEventListener("change", (e) => {
      addFiles([...e.target.files]);
      e.target.value = "";
    });
  }
  $("tray").addEventListener("click", (e) => {
    const remove = e.target.closest(".tray-remove");
    if (!remove) return;
    const key = remove.closest(".tray-item").dataset.key;
    const items = tray();
    const item = items.find((i) => i.key === key);
    if (item?.preview) URL.revokeObjectURL(item.preview);
    items.splice(items.indexOf(item), 1);
    renderTray();
  });
  $("input").addEventListener("paste", (e) => {
    const files = [...(e.clipboardData?.files || [])];
    if (!files.length) return;
    e.preventDefault();
    addFiles(files);
  });
  $("composer").addEventListener("dragover", (e) => e.preventDefault());
  $("composer").addEventListener("drop", (e) => {
    if (!e.dataTransfer?.files.length) return;
    e.preventDefault();
    addFiles([...e.dataTransfer.files]);
  });
  $("lightbox").onclick = () => ($("lightbox").hidden = true);

  $("cwd-chip").onclick = openFolderPicker;
  $("cwd-up").onclick = () => state.browse.parent && browse(state.browse.parent);
  $("cwd-list").addEventListener("click", (e) => {
    const row = e.target.closest(".cwd-row");
    if (!row) return;
    if (row.querySelector(".chev")) browse(row.dataset.path);
    else useFolder(row.dataset.path);
  });
  $("cwd-use").onclick = () => {
    const typed = $("cwd-input").value.trim();
    useFolder(typed || state.browse.path);
  };
  $("cwd-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.value.trim()) {
      e.preventDefault();
      browse(e.target.value.trim());
      e.target.value = "";
    }
  });

  $("conv-menu-btn").onclick = () => {
    if (openPop === $("conv-menu")) return closePopover();
    const conv = state.current;
    if (conv)
      openChatMenu(
        { id: conv.id, title: conv.title, terminal: !!conv.source },
        $("conv-menu-btn"),
        { alignRight: true },
      );
  };
  bindLongPress($("conv-list"));
  $("conv-menu").addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn || !menuChat) return;
    const { id } = menuChat;
    if (btn.dataset.action === "rename") {
      $("rename-input").value = menuChat.title;
      showPopover($("rename-pop"), popAnchor || $("conv-menu-btn"), {});
      if (!isTouch()) $("rename-input").select();
    } else if (btn.dataset.action === "terminal") {
      closePopover();
      try {
        await ensureImported(id);
        const res = await api("POST", `conversations/${id}/terminal`);
        toast(`Opened this chat in ${res.terminal} on your computer`);
      } catch (err) {
        toast(err.message);
      }
    } else if (btn.dataset.action === "delete") {
      const label = btn.querySelector(".delete-label");
      if (label.textContent === deleteLabel()) {
        label.textContent = isTouch() ? "Tap again to confirm" : "Click again to confirm";
        return;
      }
      closePopover();
      try {
        await ensureImported(id);
        await api("DELETE", `conversations/${id}`);
      } catch (err) {
        toast(err.message);
      }
    }
  });
  $("rename-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const title = $("rename-input").value.trim();
    const chat = menuChat;
    $("rename-input").blur();
    closePopover();
    if (!chat || !title || title === chat.title) return;
    try {
      await ensureImported(chat.id);
      await api("PATCH", `conversations/${chat.id}`, { title });
      if (state.current?.id === chat.id) {
        state.current.title = title;
        renderTitle();
      }
    } catch (err) {
      toast(err.message);
    }
  });

  $("conv-title").onclick = startRename;
  const titleInput = $("conv-title-input");
  titleInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") titleInput.blur();
    if (e.key === "Escape") {
      // Cancelling the rename mustn't also stop a running reply.
      e.stopPropagation();
      titleInput.value = state.current?.title || "";
      titleInput.blur();
    }
  });
  titleInput.addEventListener("blur", async () => {
    titleInput.hidden = true;
    $("conv-title").hidden = false;
    const title = titleInput.value.trim();
    if (state.current && title && title !== state.current.title) {
      state.current.title = title;
      renderTitle();
      await api("PATCH", `conversations/${state.current.id}`, { title }).catch((e) => toast(e.message));
    }
  });

  $("credits").onclick = () => {
    if (openPop === $("credits-pop")) return closePopover();
    renderCreditsPop();
    $("credits-input").value = state.credits.balance != null ? state.credits.balance.toFixed(2) : "";
    // Most clicks are just to look at the balance, so the field waits to be clicked.
    showPopover($("credits-pop"), $("credits"), { alignRight: true });
  };
  $("credits-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = $("credits-input").value.replace(/[$,\s]/g, "");
    const balance = raw === "" ? null : Number(raw);
    if (raw !== "" && !Number.isFinite(balance)) return toast("That doesn't look like a number");
    $("credits-input").blur();
    await api("POST", "credits", { balance }).catch((err) => toast(err.message));
    closePopover();
  });

  let settingsByMouse = false;
  $("open-settings").onclick = (e) => {
    if ($("settings").open) return $("settings").classList.remove("closing");
    fillSettings();
    $("settings").showModal();
    $("settings").querySelector(".settings-body").scrollTop = 0;
    // WebKitGTK draws the keyboard focus ring wherever a modal puts focus, even after a click.
    settingsByMouse = e.detail > 0;
    if (settingsByMouse) document.activeElement.blur();
  };
  let pressOnBackdrop = false;
  $("settings").addEventListener("mousedown", (e) => (pressOnBackdrop = e.target === $("settings") && !openPop));
  $("settings").addEventListener("click", (e) => {
    if (e.target === $("settings") && pressOnBackdrop) closeDialog($("settings"));
  });
  $("settings-form").addEventListener("submit", (e) => {
    e.preventDefault();
    closeDialog($("settings"));
  });
  for (const id of ["settings", "search-dialog"]) {
    $(id).addEventListener("cancel", (e) => {
      e.preventDefault();
      closeDialog($(id));
    });
  }
  // A menu opened from a setting can't follow it as Settings scrolls, so it closes.
  $("settings")
    .querySelector(".settings-body")
    .addEventListener("scroll", () => openPop && closePopover(), { passive: true });
  $("settings").addEventListener("close", () => {
    closePopover(true);
    if (settingsByMouse) $("open-settings").blur();
    repaint();
  });
  $("search-dialog").addEventListener("close", repaint);
  $("setup").addEventListener("close", repaint);
  $("remote-note").dataset.default = $("remote-note").textContent;
  const form = $("settings-form");
  form.elements.theme.innerHTML = THEMES.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("");
  enhanceSelects(form);
  form.addEventListener("change", (e) => {
    if (e.target.name) saveSetting(e.target);
  });
  $("match-icon").addEventListener("change", (e) => {
    if (e.target.checked) localStorage.setItem("viola.matchIcon", "1");
    else localStorage.removeItem("viola.matchIcon");
    applyTheme();
  });
  $("copy-remote").onclick = (e) => copyWithLabel(e.currentTarget, state.settings.remote_url);
  // A new link stops the old one working everywhere, so it takes a second click.
  $("reset-remote").onclick = async (e) => {
    const btn = e.currentTarget;
    if (btn.textContent === "Reset link") {
      btn.textContent = isTouch() ? "Tap again" : "Click again";
      setTimeout(() => (btn.textContent = "Reset link"), 4000);
      return;
    }
    btn.textContent = "Reset link";
    try {
      const { token, ...settings } = await api("POST", "remote/reset");
      if (token) {
        state.token = token;
        localStorage.setItem("viola.token", token);
        connectEvents();
      }
      state.settings = settings;
      fillSettings();
      toast("Made a new link. The old one no longer works, so open the new one on your phone.");
    } catch (err) {
      toast(err.message);
    }
  };

  $("thread").addEventListener("click", (e) => {
    const picture = e.target.closest(".att-image");
    if (picture) {
      $("lightbox-img").src = picture.dataset.src;
      $("lightbox").hidden = false;
      return;
    }
    const copyBtn = e.target.closest(".code-copy");
    if (copyBtn) {
      copyWithLabel(copyBtn, copyBtn.closest(".code-block").querySelector("pre").textContent);
      return;
    }
    const head = e.target.closest(".step-head");
    if (!head) return;
    const step = head.closest(".step");
    if (!head.querySelector(".chev")) return;
    const opening = !step.classList.contains("open");
    if (opening) {
      const block = state.current?.messages[step.dataset.m]?.blocks[step.dataset.b];
      if (!block) return;
      if (!step.querySelector(".step-body")) fillStep(step, block);
      if (block.partial) loadFullStep(step);
      void step.offsetHeight;
      state.openSteps.add(step.dataset.key);
    } else {
      state.openSteps.delete(step.dataset.key);
    }
    step.classList.toggle("open", opening);
  });

  document.addEventListener("keydown", (e) => {
    const mod = e.ctrlKey || e.metaKey;
    // WebKit ends a composition before its keydown arrives, so only keyCode 229 tells an IME's keys apart.
    if (e.isComposing || e.keyCode === 229) return;
    if (e.key === "Escape") {
      // Without preventDefault, a menu inside Settings would close Settings too.
      if (openPop) {
        e.preventDefault();
        return closePopover();
      }
      if (!$("lightbox").hidden) return ($("lightbox").hidden = true);
      // Esc closes the open dialog (a search field would otherwise swallow it), and mustn't also stop a running reply.
      const dialog = document.querySelector("dialog[open]");
      if (dialog) {
        e.preventDefault();
        if (dialog.id !== "setup") closeDialog(dialog);
        return;
      }
      if (!$("slash-menu").hidden) return closeSlash();
      if (state.current?.running) return stop();
    }
    if (openPop?.matches(MENUS) && !e.target.matches("input, textarea")) {
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) {
        e.preventDefault();
        return moveInMenu(e.key);
      }
      if (e.key === "Tab" && openPop.contains(document.activeElement)) closePopover();
    }
    if (mod && e.shiftKey && e.key.toLowerCase() === "o") {
      e.preventDefault();
      newChat();
    } else if (mod && !e.shiftKey && e.key.toLowerCase() === "n") {
      e.preventDefault();
      newChat();
    } else if (mod && e.key.toLowerCase() === "b") {
      e.preventDefault();
      toggleSidebar();
    } else if (mod && e.key.toLowerCase() === "k") {
      e.preventDefault();
      openSearch();
    }
  });

  addEventListener("resize", () => {
    if (!openPop) return;
    if (openPop.classList.contains("sheet") !== isPhone()) closePopover(true);
    else placePopover();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden)
      api("GET", "sessions").then((d) => (state.sessions = d.sessions || [])).then(renderSidebar).catch(() => {});
  });
}

function startRename() {
  if (!state.current) return;
  const input = $("conv-title-input");
  input.value = state.current.title;
  input.hidden = false;
  $("conv-title").hidden = true;
  input.focus();
  input.select();
}

async function boot() {
  applyIcons(document);
  state.token = readToken();
  if (localStorage.getItem("viola.sidebar") === "closed" && !isPhone()) $("app").classList.add("sidebar-collapsed");
  bind();
  bindSetup();
  try {
    await loadState();
  } catch (err) {
    return err.status === 401 ? showNoLink() : showUnreachable();
  }
  connectEvents();
  if (state.settings.needs_setup) {
    renderSetup();
    $("setup").showModal();
  }
  await loadModels();
  loadVerbs();
  const saved = localStorage.getItem("viola.current");
  if (saved && [...state.convs, ...state.sessions].some((c) => c.id === saved)) await openConv(saved, true);
  else newChat();
  restoreDraft();
}

boot();
