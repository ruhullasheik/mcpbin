/* mcpbin v2 — Light SaaS style with sidebar. */
"use strict";

const MCP_URL = "/mcp";
const PROTOCOL_VERSION = "2025-03-26";

const FEATURE_AREAS = [
  ["Echo",           (n) => n === "echo" || n.startsWith("echo_")],
  ["Response Types", (n) => n.startsWith("return_")],
  ["Errors",         (n) => n.startsWith("error_")],
  ["Delays",         (n) => n === "delay" || n.startsWith("delay_")],
  ["Schema",         (n) => n.startsWith("schema_")],
  ["Notifications",  (n) => n.startsWith("notify_")],
  ["Sampling",       (n) => n.startsWith("sampling_")],
  ["Inspect",        (n) => n.startsWith("inspect_")],
];

let tools = [], resources = [], prompts = [];
let activeSection = "home";
let searchQuery = "";
let connected = false, loading = true, error = null;

const $ = (s) => document.querySelector(s);
const sidebarNav = $("#sidebar-nav");
const sidebarStatus = $("#sidebar-status");
const content = $("#content");
const searchInput = $("#search-input");
const statusDot = $("#status-dot");

function areaFor(name) {
  for (const [label, pred] of FEATURE_AREAS) if (pred(name)) return label;
  return "Other";
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" })[c]);
}
function highlightText(textValue, query) {
  const safe = escapeHtml(textValue);
  if (!query) return safe;
  const q = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safe.replace(new RegExp(q, "gi"), (m) => `<mark>${m}</mark>`);
}
function jsonHighlight(value) {
  const json = escapeHtml(JSON.stringify(value, null, 2));
  return json.replace(/(\"(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\\"])*\"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (m) => {
    let cls = "j-num";
    if (/^"/.test(m)) cls = /:$/.test(m) ? "j-key" : "j-str";
    else if (/true|false/.test(m)) cls = "j-bool";
    else if (/null/.test(m)) cls = "j-null";
    return `<span class="${cls}">${m}</span>`;
  });
}
function buildHay(...parts) { return parts.filter(Boolean).join(" ").toLowerCase(); }
function el(tag, cls, ...children) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  for (const c of children) {
    if (typeof c === "string") e.innerHTML += c;
    else if (c instanceof Node) e.appendChild(c);
  }
  return e;
}
function iconSvg(d) {
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
}

// ---- MCP Client ----
let sessionId = null, nextId = 1;
function parseBody(contentType, text) {
  if (contentType && contentType.includes("text/event-stream")) {
    const dl = text.split(/\r?\n/).filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim());
    const j = dl.join("");
    return j ? JSON.parse(j) : null;
  }
  return text ? JSON.parse(text) : null;
}
async function send(method, params, isNotification) {
  const body = { jsonrpc: "2.0", method };
  if (params !== undefined) body.params = params;
  if (!isNotification) body.id = nextId++;
  const headers = { "Content-Type": "application/json", Accept: "application/json, text/event-stream" };
  if (sessionId) headers["Mcp-Session-Id"] = sessionId;
  const resp = await fetch(MCP_URL, { method: "POST", headers, body: JSON.stringify(body) });
  const sid = resp.headers.get("Mcp-Session-Id");
  if (sid) sessionId = sid;
  if (!resp.ok && resp.status >= 400 && isNotification) return null;
  const text = await resp.text();
  if (isNotification) return null;
  const msg = parseBody(resp.headers.get("Content-Type"), text);
  if (msg && msg.error) throw new Error(msg.error.message || "JSON-RPC error");
  return msg ? msg.result : null;
}
async function initialize() {
  await send("initialize", { protocolVersion: PROTOCOL_VERSION, capabilities: {}, clientInfo: { name: "mcpbin-frontend", version: "2.0.0" } });
  await send("notifications/initialized", {}, true);
}
async function listAll(method, field) {
  const items = []; let cursor;
  do {
    const result = await send(method, cursor ? { cursor } : {});
    (result[field] || []).forEach((it) => items.push(it));
    cursor = result.nextCursor;
  } while (cursor);
  return items;
}

// ---- Sidebar ----
function renderSidebar() {
  const sections = [
    { id: "home",     label: "Home",     icon: `<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>` },
    { id: "tools",    label: "Tools",     icon: `<path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>`, count: () => tools.length },
    { id: "resources", label: "Resources", icon: `<path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>`, count: () => resources.length },
    { id: "prompts",  label: "Prompts",   icon: `<path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>`, count: () => prompts.length },
  ];

  sidebarNav.innerHTML = '<div class="nav-section-label">Navigation</div>';
  for (const s of sections) {
    const btn = el("button", `nav-item${activeSection === s.id ? " active" : ""}`);
    btn.innerHTML = iconSvg(s.icon) + `<span>${s.label}</span>`;
    if (s.count) {
      const c = el("span", "count", String(s.count()));
      btn.appendChild(c);
    }
    btn.addEventListener("click", () => { activeSection = s.id; render(); });
    sidebarNav.appendChild(btn);
  }
}

function updateSidebarStatus() {
  if (loading) { sidebarStatus.textContent = "Connecting…"; return; }
  if (error) { sidebarStatus.textContent = "Disconnected"; return; }
  sidebarStatus.innerHTML = `<span class="dot dot-green"></span> Connected &middot; MCP ${PROTOCOL_VERSION}`;
}

function updateTopbarDot() {
  if (loading) statusDot.className = "status-dot loading";
  else if (connected) statusDot.className = "status-dot online";
  else statusDot.className = "status-dot offline";
}

// ---- Card renderers ----
function renderToolCard(tool, query) {
  const card = el("article", "card"); card.id = "tool-" + tool.name;
  const head = el("div", "card-head");
  head.innerHTML += `<span class="badge badge-area">${escapeHtml(areaFor(tool.name))}</span>`;
  const title = el("h4", "card-title"); title.innerHTML = highlightText(tool.name, query); head.appendChild(title);
  card.appendChild(head);
  if (tool.description) { const d = el("p", "card-desc"); d.innerHTML = highlightText(tool.description, query); card.appendChild(d); }
  const schema = tool.inputSchema || {};
  const hasProps = schema.properties && Object.keys(schema.properties).length;
  const details = el("details", "schema-details"); if (hasProps) details.open = true;
  details.appendChild(el("summary", "schema-summary", hasProps ? "Input schema" : "Input schema (no arguments)"));
  const pre = el("pre", "schema-pre"); pre.innerHTML = jsonHighlight(schema); details.appendChild(pre);
  card.appendChild(details);
  return card;
}
function renderResourceCard(resource, query) {
  const label = resource.name || resource.uri;
  const card = el("article", "card"); card.id = "res-" + encodeURIComponent(resource.uri);
  const head = el("div", "card-head");
  head.innerHTML += `<span class="badge badge-uri">${escapeHtml(resource.mimeType || "resource")}</span>`;
  const title = el("h4", "card-title"); title.innerHTML = highlightText(label, query); head.appendChild(title);
  card.appendChild(head);
  if (resource.description) { const d = el("p", "card-desc"); d.innerHTML = highlightText(resource.description, query); card.appendChild(d); }
  const dl = el("dl", "meta-grid");
  dl.innerHTML = `<dt>URI</dt><dd class="mono">${escapeHtml(resource.uri)}</dd>`;
  if (resource.mimeType) dl.innerHTML += `<dt>MIME</dt><dd class="mono">${escapeHtml(resource.mimeType)}</dd>`;
  card.appendChild(dl);
  return card;
}
function renderPromptCard(prompt, query) {
  const card = el("article", "card"); card.id = "prompt-" + prompt.name;
  const head = el("div", "card-head");
  head.innerHTML += `<span class="badge badge-prompt">prompt</span>`;
  const title = el("h4", "card-title"); title.innerHTML = highlightText(prompt.name, query); head.appendChild(title);
  card.appendChild(head);
  const desc = el("p", "card-desc"); desc.innerHTML = prompt.description ? highlightText(prompt.description, query) : "(no description)"; card.appendChild(desc);
  const args = prompt.arguments || [];
  if (args.length) {
    const table = el("table", "args-table");
    table.innerHTML = "<thead><tr><th>Argument</th><th>Required</th><th>Description</th></tr></thead><tbody></tbody>";
    const tb = table.querySelector("tbody");
    for (const a of args) {
      const tr = el("tr");
      tr.innerHTML = `<td class="mono">${escapeHtml(a.name)}</td><td><span class="${a.required ? "req" : "opt"}">${a.required ? "required" : "optional"}</span></td><td>${escapeHtml(a.description || "")}</td>`;
      tb.appendChild(tr);
    }
    card.appendChild(table);
  } else card.appendChild(el("p", "muted", "No arguments."));
  return card;
}

// ---- Section renderers ----
function renderHomeSection() {
  const origin = window.location.origin || "http://localhost:8000";
  const chips = connected
    ? `<span class="chip">${tools.length} tool${tools.length !== 1 ? "s" : ""}</span><span class="chip">${resources.length} resource${resources.length !== 1 ? "s" : ""}</span><span class="chip">${prompts.length} prompt${prompts.length !== 1 ? "s" : ""}</span>`
    : "";
  content.innerHTML = `
    <section class="hero">
      <div class="hero-top">
        <img class="hero-logo" src="logo.svg" width="56" height="56" alt="" />
        <div>
          <h1 class="hero-title">mcpbin</h1>
          <p class="hero-tagline">Like <a href="https://httpbin.org" target="_blank" rel="noopener">httpbin</a> for REST APIs — a test server for Model Context Protocol (MCP) clients.</p>
        </div>
      </div>
      <p class="hero-lead">A deterministic, self-hostable MCP server for <b>MCP client developers</b>. Point your client at mcpbin to verify protocol compliance, validate error handling, and explore edge cases — without building throwaway servers.</p>
      <div class="chips">${chips}<span class="chip chip-dim">echo</span><span class="chip chip-dim">errors</span><span class="chip chip-dim">delays</span><span class="chip chip-dim">schema</span><span class="chip chip-dim">pagination</span><span class="chip chip-dim">notifications</span><span class="chip chip-dim">sampling</span></div>
      <h2 class="hero-h2">How to use it</h2>
      <ol class="how">
        <li><b>Connect your MCP client.</b> Streamable HTTP endpoint: <pre class="snippet"><span class="j-key">${escapeHtml(origin)}/mcp</span></pre> or stdio: <pre class="snippet">uv run mcpbin</pre></li>
        <li><b>Browse or search.</b> Every tool, resource, and prompt is fetched live from <code>/mcp</code>. Use search <kbd>/</kbd>.</li>
        <li><b>Exercise edge cases.</b> <code>error_*</code> for error codes, <code>delay_*</code> for timeouts, <code>sampling_*</code> / <code>notify_*</code> for server→client flows.</li>
        <li><b>Inspect responses.</b> Every result carries a <code>_meta</code> block. Call <code>inspect_session</code> to confirm capabilities.</li>
      </ol>
      <p class="hero-note">Switch capability profiles with <code>--profile {full,tools-only,no-sampling,minimal}</code>. This UI is documentation-only — no &ldquo;run tool&rdquo; button.</p>
    </section>`;
}

function renderToolsSection(query) {
  const q = query ? query.toLowerCase() : "";
  const filtered = q ? tools.filter((t) => buildHay(t.name, t.description || "", JSON.stringify(t.inputSchema || {})).includes(q)) : tools;
  if (!filtered.length && q) { content.innerHTML = `<div class="empty"><p>No tools match &ldquo;<strong>${escapeHtml(query)}</strong>&rdquo;</p></div>`; return; }

  const byArea = new Map();
  for (const t of filtered) { const a = areaFor(t.name); if (!byArea.has(a)) byArea.set(a, []); byArea.get(a).push(t); }

  const frag = document.createDocumentFragment();
  for (const [label] of FEATURE_AREAS.concat([["Other", () => false]])) {
    const items = byArea.get(label); if (!items) continue;
    const section = el("section", "group");
    const header = el("button", "group-header");
    header.innerHTML = `<span class="group-chevron open">${iconSvg('<path d="M6 9l6 6 6-6"/>')}</span><span class="group-label">${escapeHtml(label)}</span><span class="group-count">${items.length}</span>`;
    header.addEventListener("click", () => {
      const b = header.nextElementSibling; const ch = header.querySelector(".group-chevron");
      const exp = b.style.display !== "none"; b.style.display = exp ? "none" : "block";
      ch.className = "group-chevron" + (exp ? " closed" : " open");
    });
    const body = el("div", "group-body");
    for (const t of items) body.appendChild(renderToolCard(t, query));
    section.appendChild(header); section.appendChild(body); frag.appendChild(section);
  }
  content.innerHTML = ""; content.appendChild(frag);
}

function renderResourcesSection(query) {
  const q = query ? query.toLowerCase() : "";
  const filtered = q ? resources.filter((r) => buildHay(r.name || r.uri, r.uri || "", r.mimeType || "", r.description || "").includes(q)) : resources;
  if (!filtered.length && q) { content.innerHTML = `<div class="empty"><p>No resources match &ldquo;<strong>${escapeHtml(query)}</strong>&rdquo;</p></div>`; return; }
  const frag = document.createDocumentFragment();
  for (const r of filtered) frag.appendChild(renderResourceCard(r, query));
  content.innerHTML = ""; content.appendChild(frag);
}

function renderPromptsSection(query) {
  const q = query ? query.toLowerCase() : "";
  const filtered = q ? prompts.filter((p) => { const at = (p.arguments || []).map((a) => a.name + " " + (a.description || "")).join(" "); return buildHay(p.name, p.description || "", at).includes(q); }) : prompts;
  if (!filtered.length && q) { content.innerHTML = `<div class="empty"><p>No prompts match &ldquo;<strong>${escapeHtml(query)}</strong>&rdquo;</p></div>`; return; }
  const frag = document.createDocumentFragment();
  for (const p of filtered) frag.appendChild(renderPromptCard(p, query));
  content.innerHTML = ""; content.appendChild(frag);
}

function renderContent() {
  if (loading) { content.innerHTML = `<div class="loading-wrap"><span class="spinner-lg"></span><span>Loading mcpbin catalog&hellip;</span></div>`; return; }
  if (error) { content.innerHTML = `<div class="error-card"><h2>Connection failed</h2><p>${escapeHtml(error)}</p><button class="btn btn-primary" onclick="boot()">Retry</button></div>`; return; }
  if (activeSection === "home") renderHomeSection();
  else if (activeSection === "tools") renderToolsSection(searchQuery);
  else if (activeSection === "resources") renderResourcesSection(searchQuery);
  else if (activeSection === "prompts") renderPromptsSection(searchQuery);
}

function render() {
  renderSidebar();
  updateSidebarStatus();
  updateTopbarDot();
  renderContent();
}

// ---- Search ----
function applyFilter(query) {
  searchQuery = query.trim();
  if (activeSection === "home") { activeSection = "tools"; }
  render();
}

// ---- Boot ----
async function boot() {
  tools = []; resources = []; prompts = [];
  connected = false; loading = true; error = null;
  sessionId = null; nextId = 1;
  activeSection = "home"; searchQuery = "";
  searchInput.value = "";
  render();

  try {
    await initialize(); connected = true;
    [tools, resources, prompts] = await Promise.all([
      listAll("tools/list", "tools"), listAll("resources/list", "resources"), listAll("prompts/list", "prompts"),
    ]);
  } catch (e) { error = "Could not reach MCP server at /mcp"; }
  finally { loading = false; render(); }
}

// ---- Events ----
function wireEvents() {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchInput._timer);
    searchInput._timer = setTimeout(() => applyFilter(searchInput.value), 80);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== searchInput) { e.preventDefault(); searchInput.focus(); searchInput.select(); }
    else if (e.key === "Escape" && document.activeElement === searchInput) { searchInput.value = ""; applyFilter(""); searchInput.blur(); }
  });
}

wireEvents();
boot();
