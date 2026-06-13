/* mcpbin reference UI — fetches the live catalog from /mcp (Streamable HTTP).
 * Documentation-only: no tool execution. No external dependencies.
 * Features: live search/filter across tools+resources+prompts, match highlighting,
 * JSON-schema syntax coloring, per-section counts, click-to-scroll, "/" to search. */
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
    const result = await send(method, cursor ? { cursor } : {});
    (result[field] || []).forEach((it) => items.push(it));
    cursor = result.nextCursor;
  } while (cursor);
  return items;
}

// --- DOM helpers ----------------------------------------------------------- //
const content = document.getElementById("content");

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

// Highlight every occurrence of `query` (case-insensitive) inside plain text.
function highlight(textValue, query) {
  const safe = escapeHtml(textValue);
  if (!query) return safe;
  const q = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safe.replace(new RegExp(q, "gi"), (m) => `<mark>${m}</mark>`);
}

// Pretty-print + lightly syntax-colour a JSON value for readable schema blocks.
function jsonHighlight(value) {
  const json = escapeHtml(JSON.stringify(value, null, 2));
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false)\b|\bnull\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (m) => {
      let cls = "j-num";
      if (/^"/.test(m)) cls = /:$/.test(m) ? "j-key" : "j-str";
      else if (/true|false/.test(m)) cls = "j-bool";
      else if (/null/.test(m)) cls = "j-null";
      return `<span class="${cls}">${m}</span>`;
    }
  );
}

// --- Catalog state for filtering ------------------------------------------ //
// entries: { card, nav, name, desc, extra, titleEl, navLabelEl }
const entries = [];

function registerEntry(opts) {
  entries.push(opts);
}

function makeCard(category, id) {
  const card = el("article", "card");
  card.id = id;
  card.dataset.category = category;
  return card;
}

function navItem(listId, label, targetId) {
  const li = el("li");
  const a = el("span", "nav-label");
  a.innerHTML = escapeHtml(label);
  li.appendChild(a);
  li.addEventListener("click", () => focusCard(targetId));
  document.getElementById(listId).appendChild(li);
  return { li, labelEl: a };
}

function focusCard(id) {
  const card = document.getElementById(id);
  if (!card) return;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  card.classList.add("flash");
  setTimeout(() => card.classList.remove("flash"), 1200);
}

// --- Rendering ------------------------------------------------------------- //
function sectionHeading(text) {
  return el("h2", "section-heading", text);
}

function groupHeading(text) {
  const h = el("h3", "group-heading", text);
  return h;
}

function renderToolCard(tool, id) {
  const card = makeCard("tool", id);
  const title = el("h4", "card-title");
  title.innerHTML = `<span class="badge-area">${escapeHtml(areaFor(tool.name))}</span>${escapeHtml(tool.name)}`;
  card.appendChild(title);
  if (tool.description) card.appendChild(el("p", "desc", tool.description));

  const schema = tool.inputSchema || {};
  const hasProps = schema.properties && Object.keys(schema.properties).length;
  const details = el("details", "schema-details");
  if (hasProps) details.open = true;
  const summary = el("summary", null, hasProps ? "Input schema" : "Input schema (no arguments)");
  details.appendChild(summary);
  const pre = el("pre", "schema");
  pre.innerHTML = jsonHighlight(schema);
  details.appendChild(pre);
  card.appendChild(details);

  const titleNameEl = title; // for highlight we re-render name part
  return { card, title, descText: tool.description || "" };
}

function renderResourceCard(r, id) {
  const card = makeCard("resource", id);
  const title = el("h4", "card-title");
  title.innerHTML = `<span class="badge-area badge-uri">${escapeHtml(r.mimeType || "resource")}</span>${escapeHtml(r.name || r.uri)}`;
  card.appendChild(title);
  if (r.description) card.appendChild(el("p", "desc", r.description));
  const dl = el("dl", "meta-grid");
  for (const [k, v] of [["URI", r.uri], ["MIME type", r.mimeType]]) {
    if (v == null) continue;
    dl.appendChild(el("dt", null, k));
    dl.appendChild(el("dd", "mono", String(v)));
  }
  card.appendChild(dl);
  return { card, title, descText: r.description || "" };
}

function renderPromptCard(p, id) {
  const card = makeCard("prompt", id);
  const title = el("h4", "card-title");
  title.innerHTML = `<span class="badge-area badge-prompt">prompt</span>${escapeHtml(p.name)}`;
  card.appendChild(title);
  card.appendChild(el("p", "desc", p.description || "(no description)"));
  const args = p.arguments || [];
  if (args.length) {
    const table = el("table", "args");
    const thead = el("tr");
    ["Argument", "Required", "Description"].forEach((h) => thead.appendChild(el("th", null, h)));
    table.appendChild(thead);
    for (const a of args) {
      const tr = el("tr");
      tr.appendChild(el("td", "mono", a.name));
      const req = el("td", a.required ? "req" : "opt", a.required ? "required" : "optional");
      tr.appendChild(req);
      tr.appendChild(el("td", null, a.description || ""));
      table.appendChild(tr);
    }
    card.appendChild(table);
  } else {
    card.appendChild(el("p", "desc muted", "No arguments."));
  }
  return { card, title, descText: p.description || "" };
}

function renderCatalog(tools, resources, prompts) {
  content.innerHTML = "";

  // ---- Tools, grouped by feature area ----
  if (tools.length) {
    content.appendChild(sectionHeading("Tools"));
    const byArea = new Map();
    for (const t of tools) {
      const a = areaFor(t.name);
      if (!byArea.has(a)) byArea.set(a, []);
      byArea.get(a).push(t);
    }
    for (const [label] of FEATURE_AREAS.concat([["Other", () => false]])) {
      if (!byArea.has(label)) continue;
      const gh = groupHeading(label);
      gh.dataset.group = "tool:" + label;
      content.appendChild(gh);
      const groupCards = [];
      for (const t of byArea.get(label)) {
        const id = "tool-" + t.name;
        const { card, title, descText } = renderToolCard(t, id);
        content.appendChild(card);
        groupCards.push(card);
        const nav = navItem("tools-list", t.name, id);
        registerEntry({
          card, nav: nav.li, navLabelEl: nav.labelEl, titleEl: title,
          name: t.name, area: label, descText,
          hay: (t.name + " " + descText + " " + JSON.stringify(t.inputSchema || {})).toLowerCase(),
          renderTitle: (q) => {
            title.innerHTML = `<span class="badge-area">${escapeHtml(label)}</span>` + highlight(t.name, q);
          },
        });
      }
      gh._cards = groupCards;
    }
  }

  // ---- Resources ----
  if (resources.length) {
    content.appendChild(sectionHeading("Resources"));
    for (const r of resources) {
      const id = "res-" + encodeURIComponent(r.uri);
      const { card, title, descText } = renderResourceCard(r, id);
      content.appendChild(card);
      const label = r.name || r.uri;
      const nav = navItem("resources-list", label, id);
      registerEntry({
        card, nav: nav.li, navLabelEl: nav.labelEl, titleEl: title,
        name: label, descText,
        hay: (label + " " + (r.uri || "") + " " + (r.mimeType || "") + " " + descText).toLowerCase(),
        renderTitle: (q) => {
          title.innerHTML = `<span class="badge-area badge-uri">${escapeHtml(r.mimeType || "resource")}</span>` + highlight(label, q);
        },
      });
    }
  }

  // ---- Prompts ----
  if (prompts.length) {
    content.appendChild(sectionHeading("Prompts"));
    for (const p of prompts) {
      const id = "prompt-" + p.name;
      const { card, title, descText } = renderPromptCard(p, id);
      content.appendChild(card);
      const nav = navItem("prompts-list", p.name, id);
      const argText = (p.arguments || []).map((a) => a.name + " " + (a.description || "")).join(" ");
      registerEntry({
        card, nav: nav.li, navLabelEl: nav.labelEl, titleEl: title,
        name: p.name, descText,
        hay: (p.name + " " + descText + " " + argText).toLowerCase(),
        renderTitle: (q) => {
          title.innerHTML = `<span class="badge-area badge-prompt">prompt</span>` + highlight(p.name, q);
        },
      });
    }
  }
}

// --- Search / filter ------------------------------------------------------- //
function updateCounts() {
  const tally = { tool: [0, 0], resource: [0, 0], prompt: [0, 0] };
  for (const e of entries) {
    const cat = e.card.dataset.category;
    tally[cat][1]++;
    if (!e.card.hidden) tally[cat][0]++;
  }
  const fmt = ([shown, total]) => (shown === total ? `${total}` : `${shown}/${total}`);
  document.getElementById("tools-count").textContent = fmt(tally.tool);
  document.getElementById("resources-count").textContent = fmt(tally.resource);
  document.getElementById("prompts-count").textContent = fmt(tally.prompt);
}

function applyFilter(query) {
  const q = query.trim().toLowerCase();
  let anyVisible = false;
  for (const e of entries) {
    const match = !q || e.hay.includes(q);
    e.card.hidden = !match;
    e.nav.hidden = !match;
    if (match) {
      anyVisible = true;
      e.renderTitle(query.trim());
      // highlight description too
      const descEl = e.card.querySelector(".desc");
      if (descEl && e.descText) descEl.innerHTML = highlight(e.descText, query.trim());
    }
  }
  // Hide section + group headings that have no visible cards beneath them.
  document.querySelectorAll(".section-heading, .group-heading").forEach((h) => {
    h.hidden = !headingHasVisibleCards(h);
  });

  document.getElementById("no-results").hidden = anyVisible;
  document.getElementById("nr-q").textContent = query.trim();
  updateCounts();
}

function headingHasVisibleCards(heading) {
  const isSection = heading.classList.contains("section-heading");
  let n = heading.nextElementSibling;
  while (n) {
    if (n.classList.contains("section-heading")) break;
    if (!isSection && n.classList.contains("group-heading")) break;
    if (n.classList.contains("card") && !n.hidden) return true;
    n = n.nextElementSibling;
  }
  return false;
}

function wireSearch() {
  const input = document.getElementById("search");
  let t;
  input.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(() => applyFilter(input.value), 80);
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "/" && document.activeElement !== input) {
      ev.preventDefault();
      input.focus();
      input.select();
    } else if (ev.key === "Escape" && document.activeElement === input) {
      input.value = "";
      applyFilter("");
      input.blur();
    }
  });
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

function showError(listId, message) {
  const ul = document.getElementById(listId);
  ul.innerHTML = "";
  const li = el("li", "nav-error", message);
  ul.appendChild(li);
}

// --- Boot ------------------------------------------------------------------ //
async function boot() {
  wireCollapsers();
  wireSearch();
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

  let tools = [], resources = [], prompts = [];
  const errs = [];
  try { tools = await listAll("tools/list", "tools"); }
  catch (e) { showError("tools-list", UNREACHABLE); errs.push("tools"); }
  try { resources = await listAll("resources/list", "resources"); }
  catch (e) { showError("resources-list", UNREACHABLE); errs.push("resources"); }
  try { prompts = await listAll("prompts/list", "prompts"); }
  catch (e) { showError("prompts-list", UNREACHABLE); errs.push("prompts"); }

  renderCatalog(tools, resources, prompts);
  applyFilter("");
}

boot();
