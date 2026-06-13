/* mcpbin reference UI — fetches the live catalog from /mcp (Streamable HTTP).
 * Documentation-only: no tool execution. No external dependencies. */
"use strict";

const MCP_URL = "/mcp";
const PROTOCOL_VERSION = "2025-03-26";
const UNREACHABLE = "Could not reach MCP server at /mcp";

// Feature-area grouping for tools (matches the PRD feature areas).
const FEATURE_AREAS = [
  ["Echo", (n) => n === "echo" || n.startsWith("echo_")],
  ["Response Types", (n) => n.startsWith("return_")],
  ["Errors", (n) => n.startsWith("error_")],
  ["Delays", (n) => n === "delay" || n.startsWith("delay_")],
  ["Schema", (n) => n.startsWith("schema_")],
  ["Notifications", (n) => n.startsWith("notify_")],
  ["Sampling", (n) => n.startsWith("sampling_")],
  ["Inspect", (n) => n.startsWith("inspect_")],
];

function areaFor(name) {
  for (const [label, pred] of FEATURE_AREAS) if (pred(name)) return label;
  return "Other";
}

// --- Minimal JSON-RPC over Streamable HTTP -------------------------------- //
let sessionId = null;
let nextId = 1;

function parseBody(contentType, text) {
  // Streamable HTTP may answer with application/json or text/event-stream (SSE).
  if (contentType && contentType.includes("text/event-stream")) {
    const dataLines = text
      .split(/\r?\n/)
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.slice(5).trim());
    const joined = dataLines.join("");
    return joined ? JSON.parse(joined) : null;
  }
  return text ? JSON.parse(text) : null;
}

async function send(method, params, isNotification) {
  const body = { jsonrpc: "2.0", method };
  if (params !== undefined) body.params = params;
  if (!isNotification) body.id = nextId++;

  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json, text/event-stream",
  };
  if (sessionId) headers["Mcp-Session-Id"] = sessionId;

  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
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
  const result = await send("initialize", {
    protocolVersion: PROTOCOL_VERSION,
    capabilities: {},
    clientInfo: { name: "mcpbin-frontend", version: "0.1.0" },
  });
  await send("notifications/initialized", {}, true);
  return result;
}

// Follow every nextCursor page to build a complete list.
async function listAll(method, field) {
  const items = [];
  let cursor;
  do {
    const params = cursor ? { cursor } : {};
    const result = await send(method, params);
    (result[field] || []).forEach((it) => items.push(it));
    cursor = result.nextCursor;
  } while (cursor);
  return items;
}

// --- Rendering ------------------------------------------------------------- //
const content = document.getElementById("content");

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function showError(listId, message) {
  const ul = document.getElementById(listId);
  ul.innerHTML = "";
  const li = el("li", null, message);
  li.style.color = "#ff8a8a";
  li.style.whiteSpace = "normal";
  ul.appendChild(li);
}

function sidebarItem(listId, label, onClick) {
  const li = el("li", null, label);
  li.addEventListener("click", () => {
    document
      .querySelectorAll(".nav-list li.active")
      .forEach((x) => x.classList.remove("active"));
    li.classList.add("active");
    onClick();
  });
  document.getElementById(listId).appendChild(li);
}

function renderTool(tool) {
  content.innerHTML = "";
  const card = el("div", "card");
  card.appendChild(el("h2", null, tool.name));
  if (tool.description) card.appendChild(el("p", "desc", tool.description));
  const pre = el("pre", "schema");
  pre.textContent = JSON.stringify(tool.inputSchema || {}, null, 2);
  card.appendChild(pre);
  content.appendChild(card);
}

function renderResource(r) {
  content.innerHTML = "";
  const card = el("div", "card");
  card.appendChild(el("h2", null, r.name || r.uri));
  if (r.description) card.appendChild(el("p", "desc", r.description));
  const rows = [
    ["URI", r.uri],
    ["Name", r.name],
    ["MIME type", r.mimeType],
  ];
  for (const [k, v] of rows) {
    if (v == null) continue;
    const row = el("div", "meta-row");
    row.appendChild(el("b", null, k + ": "));
    row.appendChild(document.createTextNode(String(v)));
    card.appendChild(row);
  }
  content.appendChild(card);
}

function renderPrompt(p) {
  content.innerHTML = "";
  const card = el("div", "card");
  card.appendChild(el("h2", null, p.name));
  if (p.description) card.appendChild(el("p", "desc", p.description));
  const args = p.arguments || [];
  if (args.length) {
    const table = el("table", "args");
    const thead = el("tr");
    ["Name", "Required", "Description"].forEach((h) => thead.appendChild(el("th", null, h)));
    table.appendChild(thead);
    for (const a of args) {
      const tr = el("tr");
      tr.appendChild(el("td", null, a.name));
      tr.appendChild(el("td", a.required ? "req" : null, a.required ? "yes" : "no"));
      tr.appendChild(el("td", null, a.description || ""));
      table.appendChild(tr);
    }
    card.appendChild(table);
  } else {
    card.appendChild(el("p", "desc", "(no arguments)"));
  }
  content.appendChild(card);
}

function renderToolGroups(tools) {
  content.innerHTML = "";
  const byArea = new Map();
  for (const t of tools) {
    const area = areaFor(t.name);
    if (!byArea.has(area)) byArea.set(area, []);
    byArea.get(area).push(t);
  }
  for (const [label] of FEATURE_AREAS) {
    if (!byArea.has(label)) continue;
    content.appendChild(el("h2", "group-heading", label));
    const labelEl = el("div", "nav-group-label", label);
    document.getElementById("tools-list").appendChild(labelEl);
    for (const t of byArea.get(label)) {
      renderToolCardInto(content, t);
      sidebarItem("tools-list", t.name, () => renderTool(t));
    }
  }
}

function renderToolCardInto(parent, tool) {
  const card = el("div", "card");
  card.appendChild(el("h2", null, tool.name));
  if (tool.description) card.appendChild(el("p", "desc", tool.description));
  const pre = el("pre", "schema");
  pre.textContent = JSON.stringify(tool.inputSchema || {}, null, 2);
  card.appendChild(pre);
  parent.appendChild(card);
}

function wireCollapsers() {
  document.querySelectorAll(".nav-header").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ul = document.getElementById(btn.dataset.target);
      const expanded = btn.getAttribute("aria-expanded") === "true";
      btn.setAttribute("aria-expanded", String(!expanded));
      ul.classList.toggle("collapsed", expanded);
    });
  });
}

// --- Boot ------------------------------------------------------------------ //
async function boot() {
  wireCollapsers();
  try {
    await initialize();
  } catch (e) {
    showError("tools-list", UNREACHABLE);
    showError("resources-list", UNREACHABLE);
    showError("prompts-list", UNREACHABLE);
    content.innerHTML = "";
    content.appendChild(el("div", "error", UNREACHABLE));
    return;
  }

  // Tools (default view, grouped by feature area).
  try {
    const tools = await listAll("tools/list", "tools");
    renderToolGroups(tools);
  } catch (e) {
    showError("tools-list", UNREACHABLE);
  }

  // Resources (omitted under some profiles -> show the inline message).
  try {
    const resources = await listAll("resources/list", "resources");
    resources.forEach((r) => sidebarItem("resources-list", r.name || r.uri, () => renderResource(r)));
    if (!resources.length) showError("resources-list", UNREACHABLE);
  } catch (e) {
    showError("resources-list", UNREACHABLE);
  }

  // Prompts.
  try {
    const prompts = await listAll("prompts/list", "prompts");
    prompts.forEach((p) => sidebarItem("prompts-list", p.name, () => renderPrompt(p)));
    if (!prompts.length) showError("prompts-list", UNREACHABLE);
  } catch (e) {
    showError("prompts-list", UNREACHABLE);
  }
}

boot();
