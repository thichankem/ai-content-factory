"use strict";

/* ==========================================================================
   NODE FLOW — drag-and-drop production DAG
   --------------------------------------------------------------------------
   The Node Flow workspace is a live view of the project's workflow document:

     * drag a block from the palette onto the canvas (or click to append)
     * drag a block to move it; it snaps to the grid
     * click a block, then drag its ＋ handle into another block to link them
     * Backspace deletes the selected block or link, Esc cancels a link
     * the pre-save checklist gates saving, exactly like the consoles this
       studio is modelled on: "Checklist Audit" → fix → "Save DAG"
     * "Execute Workflow Run" runs the real pipeline and streams each block's
       status, output, and timing into the console

   Every read and write goes through the API, so the canvas can never drift
   from what the pipeline actually executes. This module owns the DAG view:
   app.js delegates `loadWorkflowDAG()` here.
   ========================================================================== */

const flow = {
  projectId: null,
  catalog: [],
  name: "Production pipeline",
  nodes: [],
  edges: [],
  version: 1,
  selected: null,
  selectedEdge: null,
  linking: null,
  drag: null,
  dirty: false,
  loading: null,
  lastRun: null,
  ready: null,
};

const FLOW_NODE_WIDTH = 220;
const FLOW_NODE_HEIGHT = 76;
const FLOW_COLUMN_STEP = 250;
const FLOW_ROW_STEP = 110;

/*: Inspector fields per block type; everything else is driven by the palette. */
const FLOW_PARAM_SPEC = {
  research: [{ key: "include_web", label: "Search the web", type: "bool" }],
  gate: [
    {
      key: "stage",
      label: "Gate stage",
      type: "select",
      options: [
        { value: "script", label: "Script review (Gate 1)" },
        { value: "video", label: "Final video (Gate 2)" },
      ],
    },
  ],
  publish: [{ key: "platforms", label: "Platforms (comma separated)", type: "list" }],
  ai_assist: [
    { key: "fit", label: "Fit durations to narration", type: "bool" },
    { key: "beat", label: "Beat-sync cuts", type: "bool" },
    { key: "bpm", label: "Tempo (BPM)", type: "number" },
  ],
};

const FLOW_STATUS_TEXT = {
  ok: "Complete",
  failed: "Failed",
  blocked: "Waiting",
  skipped: "Skipped",
  running: "Running",
  pending: "Pending",
};

/* ---------- small helpers ---------- */

function flowApi(suffix = "") {
  return `/projects/${flow.projectId}/workflow${suffix}`;
}

function flowMeta(type) {
  return flow.catalog.find((b) => b.type === type) || { type, icon: "▫", label: type };
}

function flowNode(id) {
  return flow.nodes.find((n) => n.id === id) || null;
}

function flowNewId(prefix) {
  return prefix + Math.random().toString(36).slice(2, 8);
}

function flowProject() {
  return state.projects.find((x) => x.id === state.selectedId) || null;
}

const flowConsole = { lines: [], runAt: -1 };

function flowPaintConsole() {
  const el = $("dag-term-logs");
  if (!el) return;
  el.textContent = flowConsole.lines.length
    ? `${flowConsole.lines.join("\n")}\n`
    : "";
  el.scrollTop = el.scrollHeight;
}

function flowLog(line) {
  flowConsole.lines.push(line);
  flowPaintConsole();
}

function flowLogReset(line) {
  flowConsole.lines = line ? [line] : [];
  flowConsole.runAt = -1;
  flowPaintConsole();
}

/** Render a run (complete or in progress) as console lines. */
function flowRunLines(run) {
  const steps = run.steps || [];
  const lines = [
    `Run ${run.id} · ${String(run.status).toUpperCase()}`,
    `${steps.length} block(s) recorded`,
  ];
  if (run.status === "running") lines.push("Streaming block results as they finish…");
  (run.steps || []).forEach((step) => {
    lines.push(
      `  · ${step.label} → ${step.status} (${step.duration_ms}ms)` +
        (step.error ? ` — ${step.error}` : ""),
    );
    if (step.output && Object.keys(step.output).length) {
      lines.push(`      ↳ ${JSON.stringify(step.output)}`);
    }
  });
  if (run.message) lines.push(`Message: ${run.message}`);
  return lines;
}

/** Replace the run section of the console, leaving earlier lines intact. */
function flowPaintRun(run) {
  const head =
    flowConsole.runAt >= 0
      ? flowConsole.lines.slice(0, flowConsole.runAt)
      : flowConsole.lines.slice();
  flowConsole.lines = head.concat(flowRunLines(run));
  flowPaintConsole();
}

function flowSetStatus(line) {
  const el = $("dag-status-line");
  if (el) el.textContent = line;
}

function flowMarkDirty() {
  flow.dirty = true;
  flowRefreshStatusLine();
}

function flowRefreshStatusLine() {
  if (!flow.projectId) return;
  const bits = [
    `${flow.nodes.length} block${flow.nodes.length === 1 ? "" : "s"}`,
    `${flow.edges.length} link${flow.edges.length === 1 ? "" : "s"}`,
    `v${flow.version}`,
  ];
  if (flow.dirty) bits.push("unsaved");
  flowSetStatus(bits.join(" · "));
}

/* ---------- palette ---------- */

async function flowLoadCatalog() {
  if (flow.catalog.length) return flow.catalog;
  try {
    flow.catalog = await api("/workflow/blocks");
    flowRenderPalette();
  } catch (err) {
    const host = $("dag-palette-list");
    if (host) host.innerHTML = `<div class="muted small">${esc(err.message)}</div>`;
  }
  return flow.catalog;
}

function flowRenderPalette() {
  const host = $("dag-palette-list");
  if (!host) return;
  host.innerHTML = "";
  flow.catalog.forEach((block) => {
    const item = document.createElement("div");
    item.className = "flow-palette-item";
    item.draggable = true;
    item.dataset.type = block.type;
    item.title = block.description;
    item.innerHTML =
      `<span class="fp-icon">${esc(block.icon || "▫")}</span>` +
      `<span class="fp-body"><strong>${esc(block.label)}</strong>` +
      `<span class="fp-desc">${esc(block.description || "")}</span></span>`;
    item.addEventListener("dragstart", (ev) => {
      ev.dataTransfer.setData("text/plain", block.type);
      ev.dataTransfer.effectAllowed = "copy";
    });
    item.addEventListener("click", () => flowAppendBlock(block.type));
    host.appendChild(item);
  });
}

/* ---------- loading the document ---------- */

async function flowLoad(projectId, options = {}) {
  flow.projectId = projectId;
  flow.selected = null;
  flow.selectedEdge = null;
  await flowLoadCatalog();
  try {
    const doc = await api(flowApi());
    flow.name = doc.name || "Production pipeline";
    flow.nodes = doc.nodes || [];
    flow.edges = doc.edges || [];
    flow.version = doc.version || 1;
    flow.dirty = false;
    flowRenderAll();
    await flowChecklist();
    // A run refreshes the document but must keep its own console output.
    if (!options.quiet) {
      flowLogReset(
        `[DAG Ready] Loaded '${flow.name}' v${flow.version} · ${flow.nodes.length} blocks, ` +
          `${flow.edges.length} links.\nDrag blocks to rearrange, drag a ＋ handle to wire them, ` +
          `then audit the checklist before saving.`,
      );
    }
  } catch (err) {
    flowSetStatus("Could not load the flow");
    flowLogReset(`[Load Error] ${err.message}`);
  }
}

/* ---------- rendering ---------- */

function flowAnchor(node) {
  return {
    out: { x: node.x + FLOW_NODE_WIDTH, y: node.y + FLOW_NODE_HEIGHT / 2 },
    in: { x: node.x, y: node.y + FLOW_NODE_HEIGHT / 2 },
  };
}

function flowCurve(from, to) {
  const bend = Math.max(40, Math.abs(to.x - from.x) * 0.45);
  return `M ${from.x} ${from.y} C ${from.x + bend} ${from.y}, ${to.x - bend} ${to.y}, ${to.x} ${to.y}`;
}

function flowIncoming(id) {
  return flow.edges.filter((e) => e.target === id).length;
}

function flowOutgoing(id) {
  return flow.edges.filter((e) => e.source === id).length;
}

function flowRenderAll() {
  flowRenderNodes();
  flowRenderLinks();
  flowRenderInspector();
  flowRefreshStatusLine();
  const empty = $("dag-empty");
  if (empty) empty.hidden = flow.nodes.length > 0;
}

function flowRenderNodes() {
  const layer = $("dag-nodes-flow");
  if (!layer) return;
  layer.innerHTML = "";
  let maxX = 1200;
  let maxY = 700;
  const statuses = flowStepStatuses();
  flow.nodes.forEach((node) => {
    maxX = Math.max(maxX, node.x + FLOW_NODE_WIDTH + 120);
    maxY = Math.max(maxY, node.y + FLOW_NODE_HEIGHT + 120);
    const meta = flowMeta(node.type);
    const status = statuses[node.id];
    const el = document.createElement("div");
    el.className = "dag-node flow-node";
    el.dataset.id = node.id;
    el.style.left = `${Math.max(0, node.x)}px`;
    el.style.top = `${Math.max(0, node.y)}px`;
    if (node.id === flow.selected) el.classList.add("selected");
    if (node.enabled === false) el.classList.add("disabled");
    if (node.type === "gate") el.classList.add("gate-node");
    if (status) el.classList.add(status);
    el.innerHTML =
      `<div class="dag-node-header"><span class="dag-node-icon">${esc(meta.icon || "▫")}</span>` +
      `<span class="dag-node-title">${esc(node.label || meta.label)}</span>` +
      `<span class="dag-node-status ${esc(status || "pending")}">${esc(
        FLOW_STATUS_TEXT[status] || "Ready",
      )}</span></div>` +
      `<div class="dag-node-body">${esc(node.type)} · ${flowIncoming(node.id)} in / ` +
      `${flowOutgoing(node.id)} out${node.enabled === false ? " · off" : ""}</div>` +
      `<span class="flow-target"></span>` +
      `<span class="flow-port" title="Drag into another block to link">＋</span>`;
    el.addEventListener("pointerdown", flowNodePointerDown);
    layer.appendChild(el);
  });
  layer.style.width = `${maxX}px`;
  layer.style.height = `${maxY}px`;
  const svg = $("dag-links");
  if (svg) {
    svg.style.width = `${maxX}px`;
    svg.style.height = `${maxY}px`;
  }
}

function flowStepStatuses() {
  const map = {};
  if (flow.lastRun && flow.lastRun.steps) {
    flow.lastRun.steps.forEach((step) => {
      map[step.node_id] = step.status;
    });
  }
  return map;
}

function flowRenderLinks() {
  const svg = $("dag-links");
  if (!svg) return;
  const paths = flow.edges
    .map((edge) => {
      const source = flowNode(edge.source);
      const target = flowNode(edge.target);
      if (!source || !target) return "";
      const selected = edge.id === flow.selectedEdge ? " selected" : "";
      return (
        `<path class="flow-link${selected}" data-edge="${esc(edge.id)}" ` +
        `d="${flowCurve(flowAnchor(source).out, flowAnchor(target).in)}" ` +
        `marker-end="url(#flow-arrow)"></path>`
      );
    })
    .join("");
  const rubber = flow.linking
    ? `<path class="flow-rubber" id="flow-rubber" d="${flow.linking.d}"></path>`
    : "";
  svg.innerHTML =
    `<defs><marker id="flow-arrow" viewBox="0 0 10 10" refX="9" refY="5" ` +
    `markerWidth="7" markerHeight="7" orient="auto-start-reverse">` +
    `<path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"></path></marker></defs>` +
    paths +
    rubber;
  svg.querySelectorAll("path.flow-link").forEach((path) => {
    path.addEventListener("click", (ev) => {
      ev.stopPropagation();
      flow.selectedEdge = path.dataset.edge;
      flow.selected = null;
      flowRenderAll();
    });
  });
}

function flowHighlight(ids) {
  const flagged = new Set(ids || []);
  document.querySelectorAll("#dag-nodes-flow .dag-node").forEach((el) => {
    el.classList.toggle("flagged", flagged.has(el.dataset.id));
  });
}

/* ---------- moving blocks ---------- */

function flowNodePointerDown(ev) {
  const el = ev.currentTarget;
  const node = flowNode(el.dataset.id);
  if (!node) return;
  if (ev.target.closest(".flow-port")) {
    ev.preventDefault();
    flowStartLink(node, ev);
    return;
  }
  ev.preventDefault();
  flow.selected = node.id;
  flow.selectedEdge = null;
  flowRenderAll();

  const rect = $("dag-nodes-flow").getBoundingClientRect();
  flow.drag = {
    id: node.id,
    dx: ev.clientX - rect.left - node.x,
    dy: ev.clientY - rect.top - node.y,
    moved: false,
  };
  el.setPointerCapture(ev.pointerId);
  el.addEventListener("pointermove", flowNodePointerMove);
  el.addEventListener("pointerup", flowNodePointerUp);
  el.addEventListener("pointercancel", flowNodePointerUp);
}

function flowSnap(value) {
  return Math.max(0, Math.round(value / 10) * 10);
}

function flowNodePointerMove(ev) {
  const drag = flow.drag;
  if (!drag) return;
  const node = flowNode(drag.id);
  const el = document.querySelector(`#dag-nodes-flow .dag-node[data-id="${drag.id}"]`);
  if (!node || !el) return;
  const rect = $("dag-nodes-flow").getBoundingClientRect();
  node.x = flowSnap(ev.clientX - rect.left - drag.dx);
  node.y = flowSnap(ev.clientY - rect.top - drag.dy);
  el.style.left = `${node.x}px`;
  el.style.top = `${node.y}px`;
  drag.moved = true;
  flowRenderLinks();
}

function flowNodePointerUp(ev) {
  const el = ev.currentTarget;
  el.removeEventListener("pointermove", flowNodePointerMove);
  el.removeEventListener("pointerup", flowNodePointerUp);
  el.removeEventListener("pointercancel", flowNodePointerUp);
  if (flow.drag && flow.drag.moved) {
    flowMarkDirty();
    flowRenderInspector();
  }
  flow.drag = null;
}

/* ---------- linking blocks ---------- */

function flowStartLink(node, ev) {
  flow.selected = node.id;
  flow.selectedEdge = null;
  flow.linking = { from: node.id, d: "" };
  const wrap = $("dag-canvas-wrap");
  if (wrap) wrap.classList.add("linking");
  flowRenderAll();

  const move = (moveEv) => {
    if (!flow.linking) return;
    const rect = $("dag-nodes-flow").getBoundingClientRect();
    const from = flowAnchor(node).out;
    const to = { x: moveEv.clientX - rect.left, y: moveEv.clientY - rect.top };
    flow.linking.d = flowCurve(from, to);
    const rubber = $("flow-rubber");
    if (rubber) rubber.setAttribute("d", flow.linking.d);
    else flowRenderLinks();
  };
  const up = (upEv) => {
    document.removeEventListener("pointermove", move);
    document.removeEventListener("pointerup", up);
    flow.linking = null;
    if (wrap) wrap.classList.remove("linking");
    // Hit-test the block rectangles instead of the DOM: the pointer may sit
    // over a scrolled-out block, which elementFromPoint cannot see.
    const rect = $("dag-nodes-flow").getBoundingClientRect();
    const x = upEv.clientX - rect.left;
    const y = upEv.clientY - rect.top;
    const hit = [...flow.nodes]
      .reverse()
      .find(
        (candidate) =>
          x >= candidate.x &&
          x <= candidate.x + FLOW_NODE_WIDTH &&
          y >= candidate.y &&
          y <= candidate.y + FLOW_NODE_HEIGHT,
      );
    if (hit && hit.id !== node.id) {
      flowAddEdge(node.id, hit.id);
    }
    flowRenderAll();
  };
  document.addEventListener("pointermove", move);
  document.addEventListener("pointerup", up);
}

function flowAddEdge(source, target) {
  if (flow.edges.some((e) => e.source === source && e.target === target)) {
    showToast("Those blocks are already linked.", "info");
    return;
  }
  flow.edges.push({ id: flowNewId("e"), source, target });
  flowMarkDirty();
  flowChecklist();
}

/* ---------- adding and deleting blocks ---------- */

function flowNextSpot() {
  if (!flow.nodes.length) return { x: 60, y: 120 };
  const columns = flow.nodes.map((node) =>
    Math.round((node.x - 60) / FLOW_COLUMN_STEP),
  );
  const rows = {};
  columns.forEach((column) => {
    rows[column] = (rows[column] || 0) + 1;
  });
  const column = Math.max(...columns) + 1;
  return { x: 60 + column * FLOW_COLUMN_STEP, y: 120 };
}

function flowAppendBlock(type) {
  const spot = flowNextSpot();
  flowAddBlock(type, spot.x, spot.y);
}

function flowAddBlock(type, x, y) {
  const meta = flowMeta(type);
  const node = {
    id: flowNewId("n"),
    type,
    label: meta.label || type,
    x,
    y,
    enabled: true,
    params: JSON.parse(JSON.stringify(meta.default_params || {})),
  };
  flow.nodes.push(node);
  flow.selected = node.id;
  flow.selectedEdge = null;
  flowMarkDirty();
  flowRenderAll();
  flowChecklist();
  return node;
}

function flowDeleteNode(id) {
  flow.nodes = flow.nodes.filter((n) => n.id !== id);
  flow.edges = flow.edges.filter((e) => e.source !== id && e.target !== id);
  if (flow.selected === id) flow.selected = null;
  flowMarkDirty();
  flowRenderAll();
  flowChecklist();
}

/* ---------- inspector ---------- */

function flowRenderInspector() {
  const host = $("dag-inspector-body");
  if (!host) return;
  host.innerHTML = "";

  if (flow.selectedEdge) {
    const edge = flow.edges.find((e) => e.id === flow.selectedEdge);
    if (!edge) {
      host.innerHTML = '<div class="muted small">Click a block to edit it.</div>';
      return;
    }
    const from = flowNode(edge.source);
    const to = flowNode(edge.target);
    const info = document.createElement("div");
    info.className = "flow-field";
    info.innerHTML =
      `<span class="flow-static">${esc(flowMeta(from?.type).label)} → ` +
      `${esc(flowMeta(to?.type).label)}</span>` +
      '<span class="muted small">This link feeds the target block its input.</span>';
    const remove = document.createElement("button");
    remove.className = "btn danger block";
    remove.textContent = "🗑 Delete Link";
    remove.addEventListener("click", () => {
      flow.edges = flow.edges.filter((e) => e.id !== edge.id);
      flow.selectedEdge = null;
      flowMarkDirty();
      flowRenderAll();
      flowChecklist();
    });
    host.append(info, remove);
    return;
  }

  const node = flowNode(flow.selected);
  if (!node) {
    host.innerHTML =
      '<div class="muted small">Click a block on the canvas to edit it.</div>';
    return;
  }
  const meta = flowMeta(node.type);

  const heading = document.createElement("div");
  heading.className = "flow-static";
  heading.textContent = `${meta.icon || "▫"} ${meta.type}`;
  host.appendChild(heading);

  const nameField = flowField("Block Name");
  const nameInput = document.createElement("input");
  nameInput.type = "text";
  nameInput.value = node.label || "";
  nameInput.addEventListener("input", () => {
    node.label = nameInput.value;
    flowMarkDirty();
    const el = document.querySelector(
      `#dag-nodes-flow .dag-node[data-id="${node.id}"] .dag-node-title`,
    );
    if (el) el.textContent = node.label || meta.label;
  });
  nameField.appendChild(nameInput);
  host.appendChild(nameField);

  const enabled = document.createElement("label");
  enabled.className = "flow-inline";
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = node.enabled !== false;
  box.addEventListener("change", () => {
    node.enabled = box.checked;
    flowMarkDirty();
    flowRenderAll();
  });
  enabled.append(box, document.createTextNode("Enabled in runs"));
  host.appendChild(enabled);

  (FLOW_PARAM_SPEC[node.type] || []).forEach((spec) =>
    flowParamField(host, node, spec),
  );

  const hint = document.createElement("div");
  hint.className = "muted small";
  hint.textContent = meta.description || "";
  host.appendChild(hint);

  const pos = document.createElement("div");
  pos.className = "flow-static";
  pos.textContent = `x ${Math.round(node.x)} · y ${Math.round(node.y)}`;
  host.appendChild(pos);

  const remove = document.createElement("button");
  remove.className = "btn danger block";
  remove.textContent = "🗑 Delete Block";
  remove.addEventListener("click", () => flowDeleteNode(node.id));
  host.appendChild(remove);
}

function flowField(label) {
  const wrap = document.createElement("div");
  wrap.className = "flow-field";
  const span = document.createElement("label");
  span.textContent = label;
  wrap.appendChild(span);
  return wrap;
}

function flowParamField(host, node, spec) {
  const wrap = flowField(spec.label);
  const current = node.params ? node.params[spec.key] : undefined;
  const set = (value) => {
    node.params = { ...(node.params || {}), [spec.key]: value };
    flowMarkDirty();
  };
  if (spec.type === "bool") {
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = Boolean(current);
    input.addEventListener("change", () => {
      set(input.checked);
      flowChecklist();
    });
    wrap.appendChild(input);
  } else if (spec.type === "select") {
    const select = document.createElement("select");
    spec.options.forEach((option) => {
      const opt = document.createElement("option");
      opt.value = option.value;
      opt.textContent = option.label;
      opt.selected = current === option.value;
      select.appendChild(opt);
    });
    select.addEventListener("change", () => {
      set(select.value);
      flowChecklist();
    });
    wrap.appendChild(select);
  } else if (spec.type === "number") {
    const input = document.createElement("input");
    input.type = "number";
    input.value = Number.isFinite(current) ? current : 120;
    input.addEventListener("input", () => set(Number(input.value)));
    wrap.appendChild(input);
  } else {
    const input = document.createElement("input");
    input.type = "text";
    input.value = Array.isArray(current) ? current.join(", ") : current || "";
    input.addEventListener("input", () =>
      set(
        input.value
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    );
    wrap.appendChild(input);
  }
  host.appendChild(wrap);
}

/* ---------- checklist ---------- */

function flowRenderChecklist(checklist) {
  const host = $("dag-checklist");
  if (!host) return;
  flow.ready = checklist ? checklist.ready : null;
  host.innerHTML = "";
  if (!checklist) {
    host.innerHTML = '<div class="muted small">Checklist unavailable.</div>';
    return;
  }
  if (!checklist.issues.length) {
    host.innerHTML =
      '<div class="flow-check-item info">✓ Every block is named, wired, and reachable.</div>';
    return;
  }
  checklist.issues.forEach((issue) => {
    const item = document.createElement("div");
    item.className = `flow-check-item ${issue.severity}`;
    item.innerHTML =
      `<div><strong>${esc(issue.message)}</strong>` +
      (issue.hint ? `<span class="fc-hint">${esc(issue.hint)}</span>` : "") +
      "</div>";
    if (issue.node_id) {
      item.addEventListener("click", () => {
        flow.selected = issue.node_id;
        flow.selectedEdge = null;
        flowRenderAll();
      });
    }
    host.appendChild(item);
  });
}

async function flowChecklist() {
  if (!flow.projectId) return null;
  try {
    const checklist = await flowApiChecklist();
    flowRenderChecklist(checklist);
    flowHighlight(
      checklist.issues
        .filter((issue) => issue.severity === "error" && issue.node_id)
        .map((issue) => issue.node_id),
    );
    return checklist;
  } catch (err) {
    flowSetStatus(err.message);
    return null;
  }
}

function flowApiChecklist() {
  // Audit what is on the canvas, not the last saved version: POST the current
  // document so unsaved edits are checked too.
  return api(flowApi("/checklist"), {
    method: "POST",
    body: JSON.stringify({
      workflow: {
        name: flow.name || "Production pipeline",
        nodes: flow.nodes,
        edges: flow.edges,
        version: flow.version || 1,
      },
    }),
  });
}

/* ---------- audit / save ---------- */

async function flowAudit() {
  if (!flow.projectId) {
    showToast("Select a project first.", "error");
    return;
  }
  flowLogReset("[Audit] Running the pre-save checklist…");
  const checklist = await flowChecklist();
  if (!checklist) return;
  flowLog(`Ready to save: ${checklist.ready ? "YES ✓" : "NO ✕"}`);
  flowLog(
    `Order: ${checklist.order.map((id) => flowNode(id)?.label || id).join(" → ")}`,
  );
  if (checklist.issues.length) {
    flowLog(`Findings (${checklist.issues.length}):`);
    checklist.issues.forEach((issue) => {
      const node = issue.node_id ? flowNode(issue.node_id) : null;
      flowLog(
        `  · [${issue.severity.toUpperCase()}] ${node ? `${node.label}: ` : ""}${issue.message}`,
      );
      if (issue.hint) flowLog(`      ↳ ${issue.hint}`);
    });
  } else {
    flowLog("No findings: every block is named, wired, and reachable.");
  }
  showToast(
    checklist.ready ? "Checklist passed — safe to save." : "Checklist found issues.",
    checklist.ready ? "success" : "info",
  );
}

async function flowSave() {
  if (!flow.projectId) {
    showToast("Select a project first.", "error");
    return;
  }
  try {
    const project = await api(flowApi(), {
      method: "PUT",
      body: JSON.stringify({
        workflow: {
          name: flow.name || "Production pipeline",
          nodes: flow.nodes,
          edges: flow.edges,
          version: flow.version || 1,
        },
        force: false,
      }),
    });
    const saved = project.workflow || {};
    flow.nodes = saved.nodes || flow.nodes;
    flow.edges = saved.edges || flow.edges;
    flow.version = saved.version || flow.version;
    flow.dirty = false;
    flowRenderAll();
    await flowChecklist();
    flowLog(`[Saved] Flow persisted as version ${flow.version}.`);
    showToast(`DAG saved · version ${flow.version}`, "success");
    await loadProjects();
  } catch (err) {
    const detail = err.detail;
    if (err.status === 422 && detail && detail.checklist) {
      flowRenderChecklist(detail.checklist);
      flowHighlight(
        detail.checklist.issues
          .filter((issue) => issue.severity === "error" && issue.node_id)
          .map((issue) => issue.node_id),
      );
      flowLog(`[Save Blocked] ${detail.message}`);
      showToast("The checklist blocked this save.", "error");
      return;
    }
    flowLog(`[Save Error] ${err.message}`);
    showToast(err.message, "error");
  }
}

/* ---------- running ---------- */

function flowInputValues() {
  const area = $("dag-inputs");
  const raw = area ? area.value.trim() : "";
  if (!raw) return {};
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error("Run inputs must be valid JSON.");
  }
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Run inputs must be a JSON object.");
  }
  const clean = {};
  Object.entries(parsed).forEach(([key, value]) => {
    if (value === "" || value === null) return;
    clean[key] = value;
  });
  return clean;
}

async function flowRun() {
  const project = flowProject();
  if (!project) {
    showToast("Select a project first.", "error");
    return;
  }
  let inputs;
  try {
    inputs = flowInputValues();
  } catch (err) {
    showToast(err.message, "error");
    return;
  }
  const statusEl = $("dag-run-status");
  if (statusEl) statusEl.textContent = "Executing…";
  flowLogReset(`[Execution Started] ${project.name} · status ${project.status}`);
  flowConsole.runAt = flowConsole.lines.length;
  flowConsole.lines.push("Starting…");
  flowPaintConsole();
  try {
    // Runs go to the background so the console can stream each block as it
    // finishes instead of holding one long request open.
    const started = await api(`${flowApi("/run")}?background=true`, {
      method: "POST",
      body: JSON.stringify({ inputs }),
    });
    const result = await flowWatchRun(started.id);
    if (statusEl) {
      statusEl.textContent = `${result.status.toUpperCase()} · ${result.duration_ms}ms`;
    }
    await loadProjects();
    await flowLoad(flow.projectId, { quiet: true });
    showToast(
      `Workflow run: ${result.status}`,
      result.status === "ok" ? "success" : "info",
    );
  } catch (err) {
    flowLog(`[Execution Halted] ${err.message}`);
    if (statusEl) statusEl.textContent = "Halted";
    showToast(err.message, "error");
  }
}

/** Poll a running flow, repainting the console and node badges as it goes. */
async function flowWatchRun(runId) {
  let run = null;
  for (let attempt = 0; attempt < 600; attempt += 1) {
    run = await api(`/workflow/runs/${runId}`);
    flow.lastRun = run;
    flowPaintRun(run);
    flowRenderNodes();
    flowRenderInspector();
    if (run.status !== "running") return run;
    await new Promise((resolve) => setTimeout(resolve, 600));
  }
  return run;
}

/* ---------- tidy ---------- */

async function flowTidy() {
  if (!flow.nodes.length) return;
  const checklist = await flowChecklist();
  const order =
    checklist && checklist.order && checklist.order.length === flow.nodes.length
      ? checklist.order
      : flow.nodes.map((n) => n.id);
  order.forEach((id, index) => {
    const node = flowNode(id);
    if (!node) return;
    node.x = 60 + index * FLOW_COLUMN_STEP;
    node.y = 120;
  });
  flowMarkDirty();
  flowRenderAll();
  flowLog("[Tidy] Blocks re-laid out in execution order.");
}

/* ---------- events ---------- */

function flowInitEvents() {
  const wrap = $("dag-canvas-wrap");
  const layer = $("dag-nodes-flow");
  if (!wrap || !layer) return;

  wrap.addEventListener("dragover", (ev) => {
    ev.preventDefault();
    ev.dataTransfer.dropEffect = "copy";
    wrap.classList.add("drop-target");
  });
  wrap.addEventListener("dragleave", () => wrap.classList.remove("drop-target"));
  wrap.addEventListener("drop", (ev) => {
    ev.preventDefault();
    wrap.classList.remove("drop-target");
    const type = ev.dataTransfer.getData("text/plain");
    if (!type || !flow.catalog.some((b) => b.type === type)) return;
    const rect = layer.getBoundingClientRect();
    flowAddBlock(
      type,
      flowSnap(ev.clientX - rect.left - FLOW_NODE_WIDTH / 2),
      flowSnap(ev.clientY - rect.top - FLOW_NODE_HEIGHT / 2),
    );
  });
  wrap.addEventListener("click", (ev) => {
    if (ev.target.closest(".dag-node") || ev.target.closest("path.flow-link")) return;
    flow.selected = null;
    flow.selectedEdge = null;
    flowRenderAll();
  });

  document.addEventListener("keydown", (ev) => {
    const view = $("view-workflow");
    if (!view || !view.classList.contains("active")) return;
    const tag = ev.target && ev.target.tagName;
    if (tag && /INPUT|TEXTAREA|SELECT/.test(tag)) return;
    if (ev.key === "Escape") {
      flow.linking = null;
      wrap.classList.remove("linking");
      flow.selected = null;
      flow.selectedEdge = null;
      flowRenderAll();
      return;
    }
    if (ev.key !== "Backspace" && ev.key !== "Delete") return;
    if (flow.selectedEdge) {
      flow.edges = flow.edges.filter((e) => e.id !== flow.selectedEdge);
      flow.selectedEdge = null;
    } else if (flow.selected) {
      const id = flow.selected;
      flow.nodes = flow.nodes.filter((n) => n.id !== id);
      flow.edges = flow.edges.filter((e) => e.source !== id && e.target !== id);
      flow.selected = null;
    } else {
      return;
    }
    ev.preventDefault();
    flowMarkDirty();
    flowRenderAll();
    flowChecklist();
  });

  $("btn-dag-checklist")?.addEventListener("click", () => run(flowAudit));
  $("btn-dag-save")?.addEventListener("click", () => run(flowSave));
  $("btn-dag-run")?.addEventListener("click", () => run(flowRun));
  $("btn-dag-tidy")?.addEventListener("click", () => run(flowTidy));
  $("btn-dag-reset")?.addEventListener("click", () => {
    if (!flow.projectId) return;
    flowLoad(flow.projectId);
    flowLog("[Reset] Reloaded the saved flow.");
    showToast("Reloaded the saved flow.", "info");
  });
}

/* app.js hands the DAG view over to this module. */
async function loadWorkflowDAG() {
  const project = flowProject();
  const statusEl = $("dag-run-status");
  if (!project) {
    if (statusEl) statusEl.textContent = "No project selected";
    flowLogReset("Select an active project to load its flow.");
    const empty = $("dag-nodes-flow");
    if (empty) empty.innerHTML = "";
    return;
  }
  await flowLoadCatalog();
  if (flow.projectId === project.id && flow.nodes.length) {
    flowRenderAll();
    return;
  }
  await flowLoad(project.id);
}

flowInitEvents();
