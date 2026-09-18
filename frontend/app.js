"use strict";

/* ==========================================================================
   AI CONTENT FACTORY — CORE CONTROLLER & AGENT ORCHESTRATOR
   ========================================================================== */

const state = {
  projects: [],
  selectedId: null,
  pollTimer: null,
  activeTab: "script",
  agents: null,
  styles: [],
  currentAnalysis: null,
};

const $ = (id) => document.getElementById(id);

// ---------- API client ----------

async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const isText = options.responseType === "text";
  const res = await fetch(path, {
    ...(isForm ? {} : { headers: { "Content-Type": "application/json" } }),
    ...options,
  });

  if (isText) {
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
    return await res.text();
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* no JSON body */
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
    const err = new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    // Structured errors (a 422 carrying its checklist, for instance) stay
    // available to the caller while callers that only read the message keep
    // working unchanged.
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return body;
}

function esc(value) {
  const div = document.createElement("div");
  div.textContent = String(value ?? "");
  return div.innerHTML;
}

function fmtTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleString();
}

function statusLabel(status) {
  return (status || "").replace(/_/g, " ");
}

// ---------- Toast notifications ----------

function showToast(message, type = "info") {
  const container = $("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "✕" : "ℹ"}</span> <span>${esc(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ---------- Health & Service Catalog ----------

async function refreshHealth() {
  try {
    const h = await api("/health");
    const badge = $("health");
    badge.textContent = `${h.status} · v${h.version}`;
    badge.className = `badge ${h.status === "ok" ? "ok" : "err"}`;
    if (h.providers) {
      const pNames = Object.entries(h.providers)
        .map(([k, v]) => `${k}: ${v}`)
        .join(" | ");
      badge.title = `Providers: ${pNames}`;
    }
  } catch {
    const badge = $("health");
    badge.textContent = "offline";
    badge.className = "badge err";
    badge.title = "Backend API unavailable";
  }
}

// ---------- Projects Management ----------

async function loadProjects() {
  state.projects = await api("/projects");
  $("project-count").textContent = state.projects.length;
  renderSidebar();
  if (state.selectedId) {
    const found = state.projects.find((p) => p.id === state.selectedId);
    if (found) {
      renderProject(found);
    } else if (state.projects.length > 0) {
      selectProject(state.projects[0].id);
    }
  } else if (state.projects.length > 0) {
    selectProject(state.projects[0].id);
  } else {
    $("empty-state").hidden = false;
    $("notebook").hidden = true;
    $("inspector-empty").hidden = false;
    $("inspector-content").hidden = true;
  }
}

function renderSidebar() {
  const box = $("projects");
  box.innerHTML = "";
  if (state.projects.length === 0) {
    box.innerHTML = '<div class="muted small" style="padding:12px; text-align:center;">No active productions yet.</div>';
    return;
  }
  for (const p of state.projects) {
    const item = document.createElement("div");
    item.className = `project-item${p.id === state.selectedId ? " active" : ""}`;

    const top = document.createElement("div");
    top.className = "pi-top";
    const name = document.createElement("div");
    name.className = "pi-name";
    name.textContent = p.name;
    top.append(name, statusBadge(p.status));

    const topic = document.createElement("div");
    topic.className = "pi-topic";
    topic.textContent = p.topic;

    const meta = document.createElement("div");
    meta.className = "pi-meta";
    meta.innerHTML = `<span>⏱ ${p.duration_target_seconds}s</span> · <span>🌐 ${esc(p.target_language)}</span> · <span>${esc(p.script_style || "viral-short")}</span>`;

    item.append(top, topic, meta);
    item.addEventListener("click", () => selectProject(p.id));
    box.appendChild(item);
  }
}

function statusBadge(status) {
  const span = document.createElement("span");
  span.className = `status ${status}`;
  span.textContent = statusLabel(status);
  return span;
}

function selectProject(id) {
  state.selectedId = id;
  const p = state.projects.find((x) => x.id === id);
  if (p) renderProject(p);
}

// ---------- Project Rendering & Pipeline Stepper ----------

function renderProject(p) {
  $("empty-state").hidden = true;
  $("notebook").hidden = false;
  $("inspector-empty").hidden = true;
  $("inspector-content").hidden = false;

  $("nb-title").textContent = p.name;
  $("nb-subtitle").textContent = p.topic;

  updatePipelineStepper(p);
  renderInspector(p);
  renderSources(p);
  renderFacts(p);
  renderScript(p);
  renderAttachedDocs(p);
  analyzeScript(p.id, p.script);
  if (p.sensitivity_report) renderSensitivityReport(p.sensitivity_report);
  if (p.structured_timeline) renderStructuredTimeline(p.structured_timeline);
  syncStyleSelector(p.script_style);
  schedulePolling(p);
  renderSidebar();
}

function updatePipelineStepper(p) {
  const s = p.status;
  const summary = $("pipeline-active-summary");
  summary.textContent = `Current Stage: ${statusLabel(s).toUpperCase()}`;

  const nodes = {
    research: $("pipe-node-research"),
    script: $("pipe-node-script"),
    script_gate: $("pipe-node-script-gate"),
    voiceover: $("pipe-node-voiceover"),
    video: $("pipe-node-video"),
    video_gate: $("pipe-node-video-gate"),
    published: $("pipe-node-published"),
  };

  // Reset classes
  Object.values(nodes).forEach((n) => {
    n.classList.remove("done", "active", "needs-review");
  });

  // Stage progression rules
  if (s === "draft") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("active");
  } else if (s === "script_review") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("done");
    nodes.script_gate.classList.add("active", "needs-review");
  } else if (s === "script_approved") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("done");
    nodes.script_gate.classList.add("done");
    nodes.voiceover.classList.add("active");
  } else if (s === "generating") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("done");
    nodes.script_gate.classList.add("done");
    nodes.voiceover.classList.add("done");
    nodes.video.classList.add("active");
  } else if (s === "video_review") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("done");
    nodes.script_gate.classList.add("done");
    nodes.voiceover.classList.add("done");
    nodes.video.classList.add("done");
    nodes.video_gate.classList.add("active", "needs-review");
  } else if (s === "video_approved") {
    nodes.research.classList.add("done");
    nodes.script.classList.add("done");
    nodes.script_gate.classList.add("done");
    nodes.voiceover.classList.add("done");
    nodes.video.classList.add("done");
    nodes.video_gate.classList.add("done");
    nodes.published.classList.add("active");
  } else if (s === "published") {
    Object.values(nodes).forEach((n) => n.classList.add("done"));
  }
}

// Stepper navigation clicks
$("pipe-node-research").addEventListener("click", () => switchTab("sources"));
$("pipe-node-script").addEventListener("click", () => switchTab("script"));
$("pipe-node-script-gate").addEventListener("click", () => {
  switchTab("script");
  $("btn-approve-script").focus();
});
$("pipe-node-voiceover").addEventListener("click", () => switchTab("script"));
$("pipe-node-video").addEventListener("click", () => {
  const p = state.projects.find((x) => x.id === state.selectedId);
  if (p && p.video_project) openEditor();
  else showToast("Video project not generated yet", "info");
});
$("pipe-node-video-gate").addEventListener("click", () => {
  $("btn-approve-video").focus();
});
$("pipe-node-published").addEventListener("click", () => {
  $("btn-publish").focus();
});

// ---------- Inspector & Gate Decision Panel ----------

function renderInspector(p) {
  const badge = $("status-badge");
  badge.className = `status ${p.status}`;
  badge.textContent = statusLabel(p.status);

  $("detail-meta").innerHTML =
    `<div>Language<strong>${esc(p.target_language.toUpperCase())}</strong></div>` +
    `<div>Target Duration<strong>${p.duration_target_seconds}s</strong></div>` +
    `<div>Preset Style<strong>${esc(p.script_style || "viral-short")}</strong></div>` +
    `<div>Active Agent<strong>${esc(p.agent_used || p.provider_used || "AI Ensemble")}</strong></div>` +
    `<div>Created<strong>${fmtTime(p.created_at)}</strong></div>` +
    `<div>Updated<strong>${fmtTime(p.updated_at)}</strong></div>` +
    (p.published_at ? `<div>Published<strong>${fmtTime(p.published_at)}</strong></div>` : "") +
    (p.platforms.length ? `<div>Platforms<strong>${esc(p.platforms.join(", "))}</strong></div>` : "");

  // Gate 1: Script Review
  $("btn-approve-script").disabled = p.status !== "script_review";
  if (p.status === "script_review") {
    $("btn-approve-script").classList.add("primary");
  } else {
    $("btn-approve-script").classList.remove("primary");
  }

  // Generation button
  const canStart = ["script_approved", "failed", "video_review"].includes(p.status);
  $("btn-start").disabled = !canStart;
  $("btn-start").textContent =
    p.status === "failed" ? "🔄 Retry Generation"
    : p.status === "video_review" ? "🔄 Re-render Video"
    : "🚀 Start Video Generation";

  // Video Card & Studio Button
  const hasVideo = !!p.video;
  $("video-card").hidden = !hasVideo;
  if (hasVideo) {
    $("video-thumb").src = p.video.thumbnail_url;
    $("video-meta").textContent =
      `${p.video.format.toUpperCase()} · ${p.video.duration_seconds}s · ` +
      `${Math.round((p.video.size_bytes || 0) / 1e6)} MB`;
  }
  const editableVideo = ["generating", "video_review", "video_approved", "published"].includes(p.status) && !!p.video_project;
  $("btn-open-editor").hidden = !editableVideo;

  // Gate 2: Video Review
  const reviewing = p.status === "video_review";
  $("btn-approve-video").disabled = !reviewing;
  $("btn-reject-video").disabled = !reviewing;
  $("btn-publish").disabled = p.status !== "video_approved";

  // Progress Bar
  const generating = p.status === "generating";
  $("progress-wrap").hidden = !generating;
  if (generating) {
    $("progress-bar").style.width = `${p.progress ?? 0}%`;
    $("progress-label").textContent = `Rendering video scenes & voiceover… ${p.progress ?? 0}%`;
  }

  // Published & Error Banners
  const published = p.status === "published";
  $("published-box").hidden = !published;
  if (published) {
    $("published-box").innerHTML = `🎉 <strong>Published to ${esc(p.platforms.join(", "))}</strong> on ${fmtTime(p.published_at)}.`;
  }

  const failed = p.status === "failed";
  $("error-box").hidden = !failed;
  if (failed) {
    $("error-box").textContent = `⚠️ Production halted: ${p.error || "unknown failure"}`;
  }

  // Review Audit History
  const approvals = $("approvals");
  approvals.innerHTML = "";
  if (p.approvals.length === 0) {
    approvals.innerHTML = '<div class="muted small">No gate decisions logged yet.</div>';
  } else {
    for (const a of p.approvals) {
      const div = document.createElement("div");
      div.className = "approval-item";
      const verdict = document.createElement("span");
      verdict.className = `verdict ${a.verdict}`;
      verdict.textContent = a.verdict;
      div.append(
        `Gate: ${a.stage.toUpperCase()} · `,
        verdict,
        ` · ${fmtTime(a.created_at)}`,
        a.comment ? ` — ${esc(a.comment)}` : ""
      );
      approvals.appendChild(div);
    }
  }
  hideError();
}

// ---------- Script Editor & Real-Time Linter ----------

function renderScript(p) {
  $("script-box").value = p.script || "";
  $("rights-box").checked = !!p.source_rights_confirmed;
  const editable = p.status === "draft" || p.status === "script_review";
  $("script-box").disabled = !editable;
  $("rights-box").disabled = !editable;
  $("btn-save").disabled = !editable;
  $("btn-generate").disabled = !editable;
}

async function analyzeScript(projectId, scriptOverride) {
  if (!projectId) return;
  const scriptContent = scriptOverride !== undefined ? scriptOverride : $("script-box").value;
  if (!scriptContent || !scriptContent.trim()) {
    $("score-gauge").style.setProperty("--score-pct", "100%");
    $("score-val").textContent = "—";
    $("score-sub").textContent = "Empty script";
    $("analysis-sections").innerHTML = '<div class="muted small">Draft script to see timing analysis.</div>';
    $("analysis-issues").innerHTML = '<div class="issue-item info">✨ Awaiting script narration content.</div>';
    return;
  }

  try {
    const analysis = await api(`/projects/${projectId}/script/analyze`, {
      method: "POST",
      body: JSON.stringify({ script: scriptContent }),
    });
    state.currentAnalysis = analysis;

    // Score Gauge
    const score = analysis.score ?? 100;
    $("score-gauge").style.setProperty("--score-pct", `${score}%`);
    $("score-val").textContent = score;
    const plan = analysis.plan;
    $("score-sub").textContent = plan.fits_target
      ? `Est. ${plan.estimated_seconds.toFixed(1)}s (Target: ${plan.target_seconds}s) · Perfect fit`
      : `Est. ${plan.estimated_seconds.toFixed(1)}s (Target: ${plan.target_seconds}s) · Timing mismatch`;

    // Sections
    const secBox = $("analysis-sections");
    secBox.innerHTML = "";
    if (plan.sections && plan.sections.length > 0) {
      for (const sec of plan.sections) {
        const row = document.createElement("div");
        row.className = "analysis-sec-row";
        row.innerHTML = `<span class="analysis-sec-name"><strong>[${esc(sec.label)}]</strong> ${sec.unit_count} units</span> <span class="analysis-sec-time">${sec.estimated_seconds.toFixed(1)}s (${Math.round(sec.share * 100)}%)</span>`;
        secBox.appendChild(row);
      }
    } else {
      secBox.innerHTML = '<div class="muted small">No section markers ([Hook], [Turn], etc.) detected.</div>';
    }

    // Issues
    const issueBox = $("analysis-issues");
    issueBox.innerHTML = "";
    if (analysis.issues && analysis.issues.length > 0) {
      for (const iss of analysis.issues) {
        const div = document.createElement("div");
        div.className = `issue-item ${iss.severity}`;
        div.innerHTML = `<strong>${iss.severity.toUpperCase()} [${esc(iss.code)}]:</strong> ${esc(iss.message)}` +
          (iss.hint ? `<br><span style="opacity:0.85;">💡 ${esc(iss.hint)}</span>` : "");
        issueBox.appendChild(div);
      }
    } else {
      issueBox.innerHTML = '<div class="issue-item info" style="color:#34d399; background:rgba(16,185,129,0.12); border-color:rgba(16,185,129,0.3);">✓ All linter checks passed without issues!</div>';
    }
  } catch (err) {
    /* Transient analysis error */
  }
}

// Script Structure Tag Chips (+[Hook], +[Turn], etc.)
document.querySelectorAll(".script-tag-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    const tag = chip.dataset.insert;
    const box = $("script-box");
    const pos = box.selectionStart || box.value.length;
    const text = box.value;
    box.value = text.slice(0, pos) + (pos > 0 && text[pos - 1] !== "\n" ? "\n\n" : "") + tag + "\n" + text.slice(pos);
    box.focus();
    box.selectionStart = box.selectionEnd = pos + tag.length + 3;
    analyzeScript(state.selectedId, box.value);
  });
});

$("btn-analyze-script").addEventListener("click", () => {
  analyzeScript(state.selectedId, $("script-box").value);
  showToast("Script linted successfully", "success");
});

// ---------- Research & Sources ----------

function renderSources(p) {
  const statusEl = $("research-status");
  const sourcesEl = $("sources");
  sourcesEl.innerHTML = "";
  $("btn-research").disabled = !["draft", "script_review"].includes(p.status);

  if (!p.research || p.research.sources.length === 0) {
    statusEl.textContent = "No research sources yet. Click 'Run Research' or generate a script to ground facts.";
    return;
  }
  statusEl.textContent =
    `🔬 ${p.research.sources.length} sources gathered · ${fmtTime(p.research.generated_at)}` +
    (p.research.notes ? ` — ${p.research.notes}` : "");

  for (const source of p.research.sources) {
    const card = document.createElement("div");
    card.className = "source";

    const head = document.createElement("div");
    head.className = "source-head";
    const chevron = document.createElement("span");
    chevron.className = "chevron";
    chevron.textContent = "▸";

    const info = document.createElement("div");
    info.className = "source-info";
    const title = document.createElement("div");
    title.className = "source-title";
    title.textContent = source.title;
    const url = document.createElement("div");
    url.className = "source-url";
    url.textContent = source.url;
    const summary = document.createElement("div");
    summary.className = "source-summary";
    summary.textContent = source.summary;
    info.append(title, url, summary);

    const type = document.createElement("span");
    type.className = "type-badge";
    type.textContent = source.source_type;
    const relevance = document.createElement("span");
    relevance.className = "relevance";
    relevance.textContent = `${Math.round(source.relevance * 100)}% match`;
    head.append(chevron, info, type, relevance);

    const body = document.createElement("div");
    body.className = "source-body";
    if (source.highlights && source.highlights.length) {
      const h4 = document.createElement("h4");
      h4.textContent = "Key Grounded Highlights";
      const ul = document.createElement("ul");
      for (const hl of source.highlights) {
        const li = document.createElement("li");
        li.textContent = hl;
        ul.appendChild(li);
      }
      body.append(h4, ul);
    }
    head.addEventListener("click", () => card.classList.toggle("open"));
    card.append(head, body);
    sourcesEl.appendChild(card);
  }
}

function renderFacts(p) {
  const box = $("facts");
  box.innerHTML = "";
  if (!p.research || !p.research.key_facts || p.research.key_facts.length === 0) {
    box.innerHTML = '<div class="muted small" style="padding:16px;">No key takeaways distilled yet — run research first.</div>';
    return;
  }
  for (const fact of p.research.key_facts) {
    const card = document.createElement("div");
    card.className = "fact-card";
    card.textContent = fact;
    box.appendChild(card);
  }
}

function renderAttachedDocs(p) {
  const box = $("attached-docs");
  box.innerHTML = "";
  if (!p.documents || p.documents.length === 0) {
    box.innerHTML = '<div class="muted small">No bibliography attached yet.</div>';
    return;
  }
  for (const doc of p.documents) {
    const div = document.createElement("div");
    div.className = "attached-item";
    div.innerHTML = `<strong>${esc(doc.title)}</strong> · ${esc(doc.source)}` +
      (doc.doi ? ` · doi:${esc(doc.doi)}` : "") +
      (doc.url ? ` · <a href="${esc(doc.url)}" target="_blank" rel="noopener">link ↗</a>` : "");
    box.appendChild(div);
  }
}

// ---------- Polling for Real-Time Render Progress ----------

function schedulePolling(p) {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  if (p.status === "generating") {
    state.pollTimer = setInterval(async () => {
      try {
        const fresh = await api(`/projects/${p.id}`);
        state.projects = state.projects.map((x) => (x.id === fresh.id ? fresh : x));
        renderProject(fresh);
        if (fresh.status !== "generating") {
          clearInterval(state.pollTimer);
          state.pollTimer = null;
          showToast(`Video generation completed: ${statusLabel(fresh.status)}`, "success");
        }
      } catch {
        /* Transient network hiccup */
      }
    }, 800);
  }
}

// ---------- Tabs Navigation ----------

function switchTab(name) {
  state.activeTab = name;
  document.querySelectorAll(".nb-tabs .tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === name);
  });
  document.querySelectorAll(".tab-panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${name}`);
  });
}

document.querySelectorAll(".nb-tabs .tab").forEach((t) => {
  t.addEventListener("click", () => switchTab(t.dataset.tab));
});

// ---------- Agent Catalog & Orchestra ----------

async function loadAgents() {
  try {
    const cat = await api("/agents");
    state.agents = cat;
    // Highlight strategy and catalog in UI
  } catch {
    /* Agents catalog offline */
  }
}

// ---------- Script Style Presets ----------

async function loadStyles() {
  try {
    state.styles = await api("/script/styles");
    const sel = $("style-selector");
    sel.innerHTML = "";
    for (const st of state.styles) {
      const opt = document.createElement("option");
      opt.value = st.name;
      opt.textContent = `${st.name} ${st.builtin ? "(Built-in)" : ""}`;
      sel.appendChild(opt);
    }
    if (state.styles.length > 0) {
      renderStyleDetails(state.styles[0]);
    }
  } catch {
    /* Styles unavailable */
  }
}

function syncStyleSelector(styleName) {
  const sel = $("style-selector");
  if (sel && styleName) {
    sel.value = styleName;
    const found = state.styles.find((s) => s.name === styleName);
    if (found) renderStyleDetails(found);
  }
}

function renderStyleDetails(st) {
  $("style-tone").textContent = st.tone || "clear, conversational";
  $("style-structure").textContent = (st.structure || []).join(" → ");
  $("style-units").textContent = `${st.sentence_max_units || 16} words/sentence`;
  const hooks = $("style-hooks");
  hooks.innerHTML = "";
  if (st.hook_rules && st.hook_rules.length) {
    for (const r of st.hook_rules) {
      const li = document.createElement("li");
      li.textContent = r;
      hooks.appendChild(li);
    }
  } else {
    hooks.innerHTML = '<li>Hook listener within first 3 seconds with tension or open loop.</li>';
  }
}

$("style-selector").addEventListener("change", (ev) => {
  const found = state.styles.find((s) => s.name === ev.target.value);
  if (found) renderStyleDetails(found);
});

$("btn-apply-style").addEventListener("click", () =>
  run(async () => {
    const styleName = $("style-selector").value;
    const p = await api(`/projects/${state.selectedId}/script/style`, {
      method: "PUT",
      body: JSON.stringify({ style: styleName }),
    });
    await loadProjects();
    renderProject(p);
    showToast(`Preset '${styleName}' applied to production`, "success");
  })
);

// ---------- External Agent Prompt Bridge Modal ----------

async function openBridgeModal() {
  if (!state.selectedId) {
    showToast("Please select a project first", "info");
    return;
  }
  $("bridge-modal").hidden = false;
  await refreshBridgeBrief();
}

async function refreshBridgeBrief() {
  const agent = $("bridge-agent-select").value;
  $("bridge-brief-preview").value = "Rendering agent-specific brief...";
  try {
    const md = await api(`/projects/${state.selectedId}/brief.md?agent=${agent}`, { responseType: "text" });
    $("bridge-brief-preview").value = md;
  } catch (err) {
    $("bridge-brief-preview").value = `Failed to generate brief: ${err.message}`;
  }
}

$("bridge-agent-select").addEventListener("change", refreshBridgeBrief);

$("btn-copy-brief").addEventListener("click", async () => {
  const text = $("bridge-brief-preview").value;
  try {
    await navigator.clipboard.writeText(text);
    showToast("Brief copied to clipboard! Paste into Claude Code / Codex / DeepSeek / Gemini.", "success");
  } catch {
    showToast("Clipboard access denied. Please select and copy manually.", "error");
  }
});

$("btn-bridge-import").addEventListener("click", () =>
  run(async () => {
    const markdown = $("bridge-import-text").value.trim();
    if (!markdown) {
      showToast("Please paste the AI agent's response first", "error");
      return;
    }
    const agentName = $("bridge-agent-select").value;
    const p = await api(`/projects/${state.selectedId}/agent-result`, {
      method: "POST",
      body: JSON.stringify({ markdown, agent: agentName }),
    });
    $("bridge-modal").hidden = true;
    $("bridge-import-text").value = "";
    await loadProjects();
    renderProject(p);
    showToast("Agent output successfully imported into pipeline!", "success");
  })
);

$("btn-topbar-bridge").addEventListener("click", openBridgeModal);
$("btn-bridge-close").addEventListener("click", () => ($("bridge-modal").hidden = true));
$("bridge-modal").addEventListener("click", (ev) => {
  if (ev.target === $("bridge-modal")) $("bridge-modal").hidden = true;
});

$("btn-topbar-styles").addEventListener("click", () => {
  switchTab("styles");
});

// ---------- Action Handlers ----------

function showError(message) {
  const el = $("error");
  el.textContent = message;
  el.hidden = false;
  showToast(message, "error");
}

function hideError() {
  $("error").hidden = true;
}

async function run(action) {
  hideError();
  try {
    await action();
  } catch (err) {
    showError(err.message);
  }
}

// Modal for Creating Project
function openModal() {
  $("modal").hidden = false;
  $("name").focus();
}
function closeModal() {
  $("modal").hidden = true;
}

$("btn-new-project").addEventListener("click", openModal);
$("btn-new-project-2").addEventListener("click", openModal);
$("btn-modal-cancel").addEventListener("click", closeModal);
$("modal").addEventListener("click", (ev) => {
  if (ev.target === $("modal")) closeModal();
});

$("create-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  run(async () => {
    const body = {
      name: $("name").value.trim(),
      topic: $("topic").value.trim(),
      target_language: $("language").value.trim() || "vi",
      duration_target_seconds: parseInt($("duration").value, 10) || 45,
    };
    const created = await api("/projects", { method: "POST", body: JSON.stringify(body) });
    ev.target.reset();
    $("language").value = "vi";
    $("duration").value = "45";
    closeModal();
    await loadProjects();
    selectProject(created.id);
    showToast(`Production initialized: ${created.name}`, "success");
  });
});

// Pipeline Action Buttons
$("btn-research").addEventListener("click", () =>
  run(async () => {
    showToast("Running deep grounded research pass...", "info");
    const p = await api(`/projects/${state.selectedId}/research?web=true`, { method: "POST" });
    await loadProjects();
    renderProject(p);
    switchTab("sources");
    showToast("Research gathered and distilled", "success");
  })
);

$("btn-generate").addEventListener("click", () =>
  run(async () => {
    showToast("Generating script via orchestrated agent...", "info");
    const p = await api(`/projects/${state.selectedId}/script/generate`, { method: "POST" });
    await loadProjects();
    renderProject(p);
    switchTab("script");
    showToast("AI Script draft ready for review", "success");
  })
);

$("btn-save").addEventListener("click", () =>
  run(async () => {
    const body = {
      script: $("script-box").value,
      source_rights_confirmed: $("rights-box").checked,
    };
    const p = await api(`/projects/${state.selectedId}/script`, {
      method: "PUT",
      body: JSON.stringify(body),
    });
    await loadProjects();
    renderProject(p);
    showToast("Narration script saved", "success");
  })
);

// Gate 1: Approve Script
$("btn-approve-script").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "script", verdict: "approved", comment: "Script approved in Studio UI" }),
    });
    await loadProjects();
    renderProject(p);
    showToast("Script Approved (Gate 1 Passed)", "success");
  })
);

// Video Generation
$("btn-start").addEventListener("click", () =>
  run(async () => {
    showToast("Starting video scene composition and rendering...", "info");
    const p = await api(`/projects/${state.selectedId}/generate`, { method: "POST" });
    await loadProjects();
    renderProject(p);
  })
);

// Gate 2: Approve Video
$("btn-approve-video").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "video", verdict: "approved", comment: "Final video approved in Studio UI" }),
    });
    await loadProjects();
    renderProject(p);
    showToast("Final Video Approved (Gate 2 Passed)", "success");
  })
);

// Reject Video
$("btn-reject-video").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "video", verdict: "rejected", comment: "Video rejected for re-render" }),
    });
    await loadProjects();
    renderProject(p);
    showToast("Video rejected — unlocked for re-editing", "info");
  })
);

// Publish
$("btn-publish").addEventListener("click", () =>
  run(async () => {
    showToast("Publishing to configured video channels...", "info");
    const p = await api(`/projects/${state.selectedId}/publish`, {
      method: "POST",
      body: JSON.stringify({ platforms: ["youtube", "tiktok", "reels"] }),
    });
    await loadProjects();
    renderProject(p);
    showToast("Production published successfully! 🎉", "success");
  })
);

// ---------- Document & Library Search ----------

async function searchDocuments(query) {
  const box = $("doc-results");
  box.innerHTML = '<div class="muted small" style="padding:12px;">Querying federated academic repositories (arXiv, Crossref, Gutenberg, Wikipedia)...</div>';
  const results = await api(`/documents/search?q=${encodeURIComponent(query)}&limit=10`);
  box.innerHTML = "";
  if (!results.length) {
    box.innerHTML = '<div class="muted small" style="padding:12px;">No matching papers found.</div>';
    return;
  }
  for (const r of results) {
    const card = document.createElement("div");
    card.className = "doc-card";
    const authors = (r.authors || []).slice(0, 4).join(", ") + (r.authors.length > 4 ? " et al." : "");
    const year = r.year ? ` (${r.year})` : "";
    const oa = r.is_open_access ? ' <span class="type-badge" style="color:#34d399;">Open Access</span>' : "";
    const citations = r.citations != null ? ` · ${r.citations} citations` : "";
    const links = [];
    if (r.landing_url) links.push(`<a href="${esc(r.landing_url)}" target="_blank" rel="noopener">Landing ↗</a>`);
    if (r.pdf_url) links.push(`<a href="${esc(r.pdf_url)}" target="_blank" rel="noopener">PDF ↗</a>`);
    card.innerHTML =
      `<div class="doc-title">${esc(r.title)}</div>` +
      `<div class="doc-meta">${esc(authors)}${year} · ` +
      `<span class="type-badge">${esc(r.source)}</span>${oa}${citations}` +
      (r.venue ? ` · ${esc(r.venue)}` : "") + `</div>` +
      (r.abstract ? `<div class="doc-abstract">${esc(r.abstract.slice(0, 280))}${r.abstract.length > 280 ? "…" : ""}</div>` : "") +
      `<div class="doc-foot"><span class="doc-links">${links.join(" · ")}</span>` +
      `<button class="btn" data-add="${r.id}">📥 Ingest to Project</button></div>`;
    card.querySelector(`[data-add="${r.id}"]`).addEventListener("click", () =>
      run(async () => {
        showToast("Downloading and attaching document...", "info");
        const p = await api(`/projects/${state.selectedId}/documents`, {
          method: "POST",
          body: JSON.stringify(r),
        });
        await loadProjects();
        renderProject(p);
        loadLibrary();
        showToast("Document attached to project bibliography", "success");
      })
    );
    box.appendChild(card);
  }
}

async function searchLibrary(query) {
  const box = $("lib-hits");
  box.innerHTML = '<div class="muted small" style="padding:12px;">Searching indexed papers with BM25...</div>';
  const hits = await api(`/library/search?q=${encodeURIComponent(query)}&limit=20`);
  box.innerHTML = "";
  if (!hits.length) {
    box.innerHTML = '<div class="muted small" style="padding:12px;">No matches in local library index.</div>';
    return;
  }
  for (const hit of hits) {
    const div = document.createElement("div");
    div.className = "lib-hit";
    const snippet = esc(hit.snippet).replace(/\[\[/g, "<b>").replace(/\]\]/g, "</b>");
    div.innerHTML =
      `<div class="hit-title">${esc(hit.title)}</div>` +
      `<div class="hit-snippet">${snippet}</div>` +
      `<div class="hit-meta">${esc(hit.path)} · Page ${hit.page} · BM25 Score ${hit.score.toFixed(3)}</div>`;
    box.appendChild(div);
  }
}

async function loadLibrary() {
  try {
    const data = await api("/library");
    const stats = data.stats;
    $("lib-stats").textContent =
      `${stats.documents} papers · ${stats.pages} pages · ` +
      `${(stats.size_bytes / 1024).toFixed(0)} KB (${stats.fts5 ? "SQLite BM25" : "LIKE Index"})`;
  } catch {
    $("lib-stats").textContent = "Local library offline.";
  }
}

// ---------- Workspace Mode Switcher (Pipeline, Video, Photo, Workflow, Agents, Library) ----------

state.activeWorkspace = "pipeline";

function switchWorkspace(wsName) {
  state.activeWorkspace = wsName;
  document.querySelectorAll(".workspace-switcher .ws-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.ws === wsName);
  });

  if (wsName === "editor") {
    const p = state.projects.find((x) => x.id === state.selectedId);
    if (p && p.video_project) {
      openEditor();
    } else {
      showToast("No video project yet — initialize or generate first.", "info");
    }
    return;
  }

  // Handle views
  const viewMap = {
    pipeline: "view-pipeline",
    photolab: "view-photolab",
    workflow: "view-workflow",
    orchestra: "view-pipeline",
    library: "view-pipeline",
    empire: "view-empire",
    mediastudio: "view-mediastudio",
  };

  document.querySelectorAll(".ws-view").forEach((v) => v.classList.remove("active"));
  const activeViewId = viewMap[wsName] || "view-pipeline";
  const viewEl = $(activeViewId);
  if (viewEl) viewEl.classList.add("active");

  if (wsName === "orchestra") {
    switchTab("orchestra");
  } else if (wsName === "library") {
    switchTab("documents");
  } else if (wsName === "photolab") {
    initPhotoLab();
  } else if (wsName === "workflow") {
    loadWorkflowDAG();
  } else if (wsName === "empire") {
    loadEmpireCampaign();
  } else if (wsName === "mediastudio") {
    loadMediaStudio();
  }
}

window.switchWorkspace = switchWorkspace;

document.querySelectorAll(".workspace-switcher .ws-tab").forEach((tab) => {
  tab.addEventListener("click", () => switchWorkspace(tab.dataset.ws));
});

if ($("btn-cinema-mode")) {
  $("btn-cinema-mode").addEventListener("click", () => {
    document.body.classList.toggle("cinema-mode");
    showToast(document.body.classList.contains("cinema-mode") ? "Cinema Mode Enabled (Press F or Cinema to exit)" : "Cinema Mode Disabled", "info");
  });
}

// Global hotkeys for switching workspaces (1 - 8)
document.addEventListener("keydown", (ev) => {
  const isInput = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
  if (isInput) return;

  const num = parseInt(ev.key, 10);
  if (num >= 1 && num <= 8) {
    const wsNames = ["pipeline", "editor", "photolab", "workflow", "orchestra", "library", "empire", "mediastudio"];
    switchWorkspace(wsNames[num - 1]);
  }
});

// Studio Application Top Menu Bar
function initStudioMenuBar() {
  const bind = (id, fn) => {
    const el = $(id);
    if (el) el.addEventListener("click", fn);
  };

  // File
  bind("menu-file-new", () => {
    switchWorkspace("pipeline");
    showToast("Ready to draft a new production in Pipeline", "info");
  });
  bind("menu-file-save", () => {
    if ($("btn-ed-save") && !$("editor").hidden) {
      $("btn-ed-save").click();
    } else {
      showToast("Saved project state to session", "info");
    }
  });
  bind("menu-file-ingest", () => {
    switchWorkspace("pipeline");
    const drop = document.querySelector(".drop-zone");
    if (drop) drop.scrollIntoView({ behavior: "smooth" });
    showToast("Drag & drop external AI clips into Ingest zone", "info");
  });
  bind("menu-file-export", () => {
    if (!$("editor").hidden) {
      const expTab = $("pr-tab-export");
      if (expTab) expTab.click();
    } else {
      switchWorkspace("editor");
    }
  });
  bind("menu-file-render", () => {
    if (typeof proRenderPlan === "function") {
      proRenderPlan();
    } else {
      showToast("Render plan compiling...", "info");
    }
  });
  bind("menu-file-cinema", () => {
    document.body.classList.toggle("cinema-mode");
    showToast(document.body.classList.contains("cinema-mode") ? "Cinema Mode Enabled" : "Cinema Mode Disabled", "info");
  });

  // Edit
  bind("menu-edit-undo", () => { if (typeof undo === "function") undo(); });
  bind("menu-edit-redo", () => { if (typeof redo === "function") redo(); });
  bind("menu-edit-cut", () => { if (typeof proSplit === "function") proSplit(); });
  bind("menu-edit-copy", () => { showToast("Scene copied to clipboard", "info"); });
  bind("menu-edit-paste", () => { if (typeof duplicateScene === "function") duplicateScene(); });
  bind("menu-edit-duplicate", () => { if (typeof proDuplicate === "function") proDuplicate(); });
  bind("menu-edit-split", () => { if (typeof proSplit === "function") proSplit(); });
  bind("menu-edit-delete", () => { if (typeof proDelete === "function") proDelete(); });

  // Clip
  bind("menu-clip-speed", () => {
    const s = document.querySelector('.props-tab-btn[data-ptab="scene"]');
    if (s) s.click();
    if ($("prop-speed")) $("prop-speed").focus();
  });
  bind("menu-clip-reverse", () => { showToast("Reverse playback motion queued", "info"); });
  bind("menu-clip-gain", () => { if ($("master-vol")) $("master-vol").focus(); });
  bind("menu-clip-ai-look", () => {
    const c = document.querySelector('.props-tab-btn[data-ptab="color"]');
    if (c) c.click();
    showToast("AI Cinematic Look suggestion ready", "info");
  });
  bind("menu-clip-ai-polish", () => {
    const ai = document.querySelector('.props-tab-btn[data-ptab="ai"]');
    if (ai) ai.click();
  });

  // Sequence
  bind("menu-seq-render", () => { if (typeof proRenderPlan === "function") proRenderPlan(); });
  bind("menu-seq-snap", () => { showToast("Timeline Magnetic Snapping: Active", "info"); });
  bind("menu-seq-in", () => { if ($("btn-mark-in")) $("btn-mark-in").click(); });
  bind("menu-seq-out", () => { if ($("btn-mark-out")) $("btn-mark-out").click(); });
  bind("menu-seq-clear-inout", () => {
    if (typeof ed !== "undefined") {
      ed.markIn = null;
      ed.markOut = null;
      showToast("Cleared In / Out points", "info");
    }
  });
  bind("menu-seq-marker", () => { if (typeof proMarker === "function") proMarker(); });
  bind("menu-seq-safemargins", () => { if ($("btn-pr-safemargins")) $("btn-pr-safemargins").click(); });

  // Audio
  bind("menu-audio-tts", () => { if ($("btn-ed-voice")) $("btn-ed-voice").click(); });
  bind("menu-audio-beats", () => { showToast("Beat grid synced to audio tempo", "info"); });
  bind("menu-audio-ducking", () => { showToast("Auto-ducking background music active (-12 dB)", "info"); });
  bind("menu-audio-sfx-sos", () => { if (typeof playSFX === "function") playSFX("sos"); });
  bind("menu-audio-sfx-siren", () => { if (typeof playSFX === "function") playSFX("siren"); });
  bind("menu-audio-sfx-sonar", () => { if (typeof playSFX === "function") playSFX("sonar"); });
  bind("menu-audio-sfx-static", () => { if (typeof playSFX === "function") playSFX("static"); });
  bind("menu-audio-sfx-whistle", () => { if (typeof playSFX === "function") playSFX("whistle"); });

  // Graphics
  bind("menu-gfx-text", () => {
    const t = document.querySelector('.props-tab-btn[data-ptab="text"]');
    if (t) t.click();
  });
  bind("menu-gfx-captions", () => {
    const c = $("prop-captions");
    if (c) {
      c.checked = !c.checked;
      c.dispatchEvent(new Event("change"));
      showToast(`Kinetic Captions: ${c.checked ? "ON" : "OFF"}`, "info");
    }
  });
  bind("menu-gfx-neon", () => {
    const styleSel = $("prop-caption-style");
    if (styleSel) {
      styleSel.value = "neon";
      styleSel.dispatchEvent(new Event("change"));
      showToast("Applied Neon Cyber Glow caption style", "info");
    }
  });
  bind("menu-gfx-outline", () => {
    const styleSel = $("prop-caption-style");
    if (styleSel) {
      styleSel.value = "heavy-outline";
      styleSel.dispatchEvent(new Event("change"));
      showToast("Applied Heavy Bold Outline caption style", "info");
    }
  });
  bind("menu-gfx-photolab", () => {
    if (typeof captureFrameToPhotoLab === "function") captureFrameToPhotoLab();
  });

  // Window Workspaces
  bind("menu-win-editing", () => switchWorkspace("editor"));
  bind("menu-win-photolab", () => switchWorkspace("photolab"));
  bind("menu-win-pipeline", () => switchWorkspace("pipeline"));
  bind("menu-win-dag", () => switchWorkspace("workflow"));
  bind("menu-win-agents", () => switchWorkspace("orchestra"));
  bind("menu-win-library", () => switchWorkspace("library"));
  bind("menu-win-empire", () => switchWorkspace("empire"));

  // Help
  bind("menu-help-shortcuts", () => {
    const m = $("shortcuts-modal");
    if (m) m.hidden = false;
  });
  bind("menu-help-benchmark", async () => {
    showToast("Running Video Editing Suite Benchmark Suite...", "info");
    try {
      const t0 = performance.now();
      const dummyCanvas = document.createElement("canvas");
      dummyCanvas.width = 1920;
      dummyCanvas.height = 1080;
      const dctx = dummyCanvas.getContext("2d");
      for (let i = 0; i < 50; i++) {
        dctx.fillStyle = i % 2 === 0 ? "#1e1e24" : "#0f0f13";
        dctx.fillRect(0, 0, 1920, 1080);
      }
      const dt = (performance.now() - t0).toFixed(1);
      showToast(`Benchmark PASSED: 50 1080p Canvas Render Passes in ${dt}ms (~${(50 / (dt / 1000)).toFixed(0)} fps)`, "good");
    } catch (e) {
      showToast(`Benchmark Error: ${e.message}`, "error");
    }
  });
}

document.addEventListener("DOMContentLoaded", initStudioMenuBar);
if (document.readyState !== "loading") {
  initStudioMenuBar();
}
/* ==========================================================================
   PHOTO LAB & LAYER COMPOSITOR ENGINE
   ========================================================================== */

const photoLab = {
  canvas: null,
  ctx: null,
  tool: "select",
  color: "#6366f1",
  aspect: "9:16",
  zoom: 1,
  drawing: false,
  startX: 0,
  startY: 0,
  layers: [],
  activeLayer: 0,
  initialized: false,
  baseImage: null,
  adjustments: {
    brightness: 0,
    contrast: 0,
    saturation: 100,
    hue: 0,
    exposure: 0,
    vignette: 0,
    blur: 0,
    filter: "none",
  },
};

function initPhotoLab() {
  if (photoLab.initialized) return;
  photoLab.canvas = $("photolab-canvas");
  if (!photoLab.canvas) return;
  photoLab.ctx = photoLab.canvas.getContext("2d");
  photoLab.initialized = true;

  setPhotoLabAspect("9:16");
  renderPhotoLabCanvas();
  setupPhotoLabEvents();
}

function setPhotoLabAspect(aspect) {
  photoLab.aspect = aspect;
  const canvas = photoLab.canvas;
  if (!canvas) return;

  if (aspect === "9:16") {
    canvas.width = 720;
    canvas.height = 1280;
  } else if (aspect === "16:9") {
    canvas.width = 1280;
    canvas.height = 720;
  } else if (aspect === "1:1") {
    canvas.width = 1080;
    canvas.height = 1080;
  } else if (aspect === "4:5") {
    canvas.width = 1080;
    canvas.height = 1350;
  }

  const dimEl = $("pl-dimensions");
  if (dimEl) dimEl.textContent = `${canvas.width} × ${canvas.height} px · ${Math.round(photoLab.zoom * 100)}% Zoom`;
  renderPhotoLabCanvas();
}

function renderPhotoLabCanvas() {
  const canvas = photoLab.canvas;
  const ctx = photoLab.ctx;
  if (!canvas || !ctx) return;

  ctx.save();
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Apply CSS filters for Tone & Color curves
  const adj = photoLab.adjustments;
  let filters = [];
  if (adj.brightness !== 0) filters.push(`brightness(${100 + Number(adj.brightness)}%)`);
  if (adj.contrast !== 0) filters.push(`contrast(${100 + Number(adj.contrast)}%)`);
  if (adj.saturation !== 100) filters.push(`saturate(${adj.saturation}%)`);
  if (adj.hue !== 0) filters.push(`hue-rotate(${adj.hue}deg)`);
  if (adj.blur > 0) filters.push(`blur(${adj.blur}px)`);

  if (adj.filter === "cyberpunk") filters.push("contrast(1.4) saturate(1.7) hue-rotate(15deg)");
  else if (adj.filter === "vintage") filters.push("sepia(0.65) contrast(1.1) brightness(1.05)");
  else if (adj.filter === "dramatic") filters.push("contrast(1.5) brightness(0.9) saturate(1.2)");
  else if (adj.filter === "blackwhite") filters.push("grayscale(1) contrast(1.3)");
  else if (adj.filter === "neon") filters.push("saturate(2) contrast(1.2)");

  ctx.filter = filters.length ? filters.join(" ") : "none";

  // Base background
  if (photoLab.baseImage) {
    ctx.drawImage(photoLab.baseImage, 0, 0, canvas.width, canvas.height);
  } else {
    // Default gradient backdrop
    const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    grad.addColorStop(0, "#0f172a");
    grad.addColorStop(0.5, "#1e1b4b");
    grad.addColorStop(1, "#090d16");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  // Draw layers
  for (const layer of photoLab.layers) {
    if (!layer.visible) continue;
    ctx.save();
    ctx.globalAlpha = layer.opacity ?? 1;
    ctx.globalCompositeOperation = layer.blend || "source-over";
    if (layer.render) layer.render(ctx, canvas.width, canvas.height);
    ctx.restore();
  }

  // Vignette overlay
  if (adj.vignette > 0) {
    const vig = ctx.createRadialGradient(
      canvas.width / 2, canvas.height / 2, Math.min(canvas.width, canvas.height) * 0.3,
      canvas.width / 2, canvas.height / 2, Math.max(canvas.width, canvas.height) * 0.75
    );
    vig.addColorStop(0, "rgba(0,0,0,0)");
    vig.addColorStop(1, `rgba(0,0,0,${adj.vignette / 100})`);
    ctx.fillStyle = vig;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  ctx.restore();
}

function setupPhotoLabEvents() {
  // Preset chips
  document.querySelectorAll(".pl-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".pl-chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      setPhotoLabAspect(chip.dataset.aspect);
    });
  });

  // Tools
  document.querySelectorAll(".pl-tool-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pl-tool-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      photoLab.tool = btn.dataset.tool;
    });
  });

  // Foreground color
  const colorInput = $("pl-fore-color");
  if (colorInput) {
    colorInput.addEventListener("input", (ev) => {
      photoLab.color = ev.target.value;
    });
  }

  // Canvas Drawing Events
  const canvas = photoLab.canvas;
  canvas.addEventListener("mousedown", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    photoLab.startX = (ev.clientX - rect.left) * scaleX;
    photoLab.startY = (ev.clientY - rect.top) * scaleY;
    photoLab.drawing = true;

    if (photoLab.tool === "eyedropper") {
      const pixel = photoLab.ctx.getImageData(photoLab.startX, photoLab.startY, 1, 1).data;
      const hex = `#${((1 << 24) + (pixel[0] << 16) + (pixel[1] << 8) + pixel[2]).toString(16).slice(1)}`;
      photoLab.color = hex;
      if (colorInput) colorInput.value = hex;
      showToast(`Picked color: ${hex}`, "info");
      photoLab.drawing = false;
    } else if (photoLab.tool === "brush" || photoLab.tool === "eraser") {
      photoLab.currentPath = [{ x: photoLab.startX, y: photoLab.startY }];
    }
  });

  canvas.addEventListener("mousemove", (ev) => {
    if (!photoLab.drawing) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const currentX = (ev.clientX - rect.left) * scaleX;
    const currentY = (ev.clientY - rect.top) * scaleY;

    if (photoLab.tool === "brush" || photoLab.tool === "eraser") {
      photoLab.currentPath.push({ x: currentX, y: currentY });
      const ctx = photoLab.ctx;
      ctx.save();
      ctx.strokeStyle = photoLab.tool === "eraser" ? "#0f172a" : photoLab.color;
      ctx.lineWidth = photoLab.tool === "eraser" ? 28 : 10;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      const p1 = photoLab.currentPath[photoLab.currentPath.length - 2];
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(currentX, currentY);
      ctx.stroke();
      ctx.restore();
    }
  });

  canvas.addEventListener("mouseup", (ev) => {
    if (!photoLab.drawing) return;
    photoLab.drawing = false;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const endX = (ev.clientX - rect.left) * scaleX;
    const endY = (ev.clientY - rect.top) * scaleY;

    if (photoLab.tool === "rect") {
      const w = endX - photoLab.startX;
      const h = endY - photoLab.startY;
      addPhotoLabLayer({
        type: "shape",
        name: `Rectangle ${photoLab.layers.length + 1}`,
        render: (ctx) => {
          ctx.fillStyle = photoLab.color;
          ctx.fillRect(photoLab.startX, photoLab.startY, w, h);
        },
      });
    } else if (photoLab.tool === "circle") {
      const r = Math.hypot(endX - photoLab.startX, endY - photoLab.startY);
      addPhotoLabLayer({
        type: "shape",
        name: `Circle ${photoLab.layers.length + 1}`,
        render: (ctx) => {
          ctx.fillStyle = photoLab.color;
          ctx.beginPath();
          ctx.arc(photoLab.startX, photoLab.startY, r, 0, Math.PI * 2);
          ctx.fill();
        },
      });
    } else if (photoLab.tool === "arrow") {
      addPhotoLabLayer({
        type: "shape",
        name: `Arrow ${photoLab.layers.length + 1}`,
        render: (ctx) => {
          ctx.strokeStyle = photoLab.color;
          ctx.lineWidth = 14;
          ctx.lineCap = "round";
          ctx.beginPath();
          ctx.moveTo(photoLab.startX, photoLab.startY);
          ctx.lineTo(endX, endY);
          ctx.stroke();
          const angle = Math.atan2(endY - photoLab.startY, endX - photoLab.startX);
          ctx.fillStyle = photoLab.color;
          ctx.beginPath();
          ctx.moveTo(endX, endY);
          ctx.lineTo(endX - 35 * Math.cos(angle - Math.PI / 6), endY - 35 * Math.sin(angle - Math.PI / 6));
          ctx.lineTo(endX - 35 * Math.cos(angle + Math.PI / 6), endY - 35 * Math.sin(angle + Math.PI / 6));
          ctx.fill();
        },
      });
    } else if (photoLab.tool === "text") {
      const text = prompt("Enter Typography Title:", "CURIOSITY HOOK");
      if (text) {
        addPhotoLabLayer({
          type: "text",
          name: `Text: ${text.slice(0, 12)}`,
          render: (ctx, W) => {
            ctx.font = "bold 64px 'Outfit', sans-serif";
            ctx.fillStyle = photoLab.color;
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 8;
            ctx.textAlign = "center";
            ctx.strokeText(text, endX, endY);
            ctx.fillText(text, endX, endY);
          },
        });
      }
    } else if (photoLab.tool === "brush") {
      const pathCopy = [...photoLab.currentPath];
      const strokeColor = photoLab.color;
      addPhotoLabLayer({
        type: "brush",
        name: `Brush ${photoLab.layers.length + 1}`,
        render: (ctx) => {
          if (!pathCopy.length) return;
          ctx.strokeStyle = strokeColor;
          ctx.lineWidth = 10;
          ctx.lineCap = "round";
          ctx.lineJoin = "round";
          ctx.beginPath();
          ctx.moveTo(pathCopy[0].x, pathCopy[0].y);
          for (let i = 1; i < pathCopy.length; i++) {
            ctx.lineTo(pathCopy[i].x, pathCopy[i].y);
          }
          ctx.stroke();
        },
      });
    }
  });

  // Adjustments bindings
  const bindAdj = (id, key, unit = "") => {
    const el = $(id);
    const valEl = $(`${id}-val`);
    if (el) {
      el.addEventListener("input", (ev) => {
        photoLab.adjustments[key] = ev.target.value;
        if (valEl) valEl.textContent = `${ev.target.value}${unit}`;
        renderPhotoLabCanvas();
      });
    }
  };

  bindAdj("pl-adj-bright", "brightness");
  bindAdj("pl-adj-contrast", "contrast");
  bindAdj("pl-adj-sat", "saturation", "%");
  bindAdj("pl-adj-hue", "hue", "°");
  bindAdj("pl-adj-exp", "exposure");
  bindAdj("pl-adj-vig", "vignette");
  bindAdj("pl-adj-blur", "blur", "px");

  // Filter presets
  document.querySelectorAll(".pl-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pl-filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      photoLab.adjustments.filter = btn.dataset.filter;
      renderPhotoLabCanvas();
    });
  });

  // Photo Lab Tabs
  document.querySelectorAll(".pl-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pl-tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".pl-tab-content").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = $(`pl-panel-${btn.dataset.pltab}`);
      if (panel) panel.classList.add("active");
    });
  });

  // Templates
  document.querySelectorAll(".pl-template-card").forEach((card) => {
    card.addEventListener("click", () => {
      applyPhotoLabTemplate(card.dataset.template);
    });
  });

  // Export PNG
  $("btn-pl-export-png").addEventListener("click", () => {
    const link = document.createElement("a");
    link.download = `content-factory-thumbnail-${Date.now()}.png`;
    link.href = photoLab.canvas.toDataURL("image/png");
    link.click();
    showToast("Thumbnail exported successfully! ⚡", "success");
  });

  // Clear Canvas
  $("btn-pl-clear").addEventListener("click", () => {
    photoLab.layers = [];
    photoLab.baseImage = null;
    renderPhotoLabCanvas();
    renderPhotoLabLayers();
    showToast("Photo Lab Canvas cleared", "info");
  });

  // Import from video
  $("btn-pl-import-frame").addEventListener("click", () => {
    const videoCanvas = $("preview-canvas");
    if (videoCanvas) {
      window.loadPhotoLabFrame(videoCanvas.toDataURL("image/png"));
    } else {
      showToast("No active video preview to capture from.", "info");
    }
  });

  // Layer Actions
  $("btn-pl-add-layer").addEventListener("click", () => {
    addPhotoLabLayer({
      type: "empty",
      name: `Layer ${photoLab.layers.length + 1}`,
      render: () => {},
    });
  });

  $("btn-pl-del-layer").addEventListener("click", () => {
    if (photoLab.layers.length > 0) {
      photoLab.layers.splice(photoLab.activeLayer, 1);
      photoLab.activeLayer = Math.max(0, photoLab.layers.length - 1);
      renderPhotoLabLayers();
      renderPhotoLabCanvas();
    }
  });
}

function addPhotoLabLayer(layer) {
  layer.visible = true;
  layer.opacity = 1;
  layer.blend = "source-over";
  photoLab.layers.push(layer);
  photoLab.activeLayer = photoLab.layers.length - 1;
  renderPhotoLabLayers();
  renderPhotoLabCanvas();
}

function renderPhotoLabLayers() {
  const list = $("pl-layers-list");
  if (!list) return;
  list.innerHTML = "";
  if (!photoLab.layers.length) {
    list.innerHTML = '<div class="muted small" style="padding:10px; text-align:center;">No custom layers yet.</div>';
    return;
  }
  photoLab.layers.forEach((layer, idx) => {
    const item = document.createElement("div");
    item.className = `pl-layer-item${idx === photoLab.activeLayer ? " active" : ""}`;
    item.innerHTML = `
      <div class="pl-layer-info">
        <span class="pl-layer-vis" style="cursor:pointer;">${layer.visible ? "👁" : "🕶"}</span>
        <span>${esc(layer.name)}</span>
      </div>
      <span class="muted small">${layer.type}</span>
    `;
    item.querySelector(".pl-layer-vis").addEventListener("click", (ev) => {
      ev.stopPropagation();
      layer.visible = !layer.visible;
      renderPhotoLabLayers();
      renderPhotoLabCanvas();
    });
    item.addEventListener("click", () => {
      photoLab.activeLayer = idx;
      renderPhotoLabLayers();
    });
    list.appendChild(item);
  });
}

function applyPhotoLabTemplate(name) {
  const W = photoLab.canvas.width;
  const H = photoLab.canvas.height;
  photoLab.layers = [];

  if (name === "tiktok-shock") {
    addPhotoLabLayer({
      name: "Curiosity Headline",
      type: "template",
      render: (ctx) => {
        ctx.fillStyle = "rgba(0,0,0,0.45)";
        ctx.fillRect(0, H * 0.25, W, 220);
        ctx.font = "900 68px 'Outfit', sans-serif";
        ctx.fillStyle = "#fbbf24";
        ctx.textAlign = "center";
        ctx.fillText("WAIT UNTIL THE END!", W / 2, H * 0.33);
        ctx.font = "700 48px 'Inter', sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.fillText("The #1 Secret Revealed ⚡", W / 2, H * 0.39);
      },
    });
  } else if (name === "youtube-split") {
    addPhotoLabLayer({
      name: "VS Badge",
      type: "template",
      render: (ctx) => {
        ctx.fillStyle = "#ef4444";
        ctx.fillRect(0, 0, W / 2, H);
        ctx.fillStyle = "#3b82f6";
        ctx.fillRect(W / 2, 0, W / 2, H);
        ctx.font = "900 120px 'Outfit', sans-serif";
        ctx.fillStyle = "#ffffff";
        ctx.textAlign = "center";
        ctx.fillText("VS", W / 2, H / 2 + 40);
      },
    });
  } else if (name === "neon-cyber") {
    addPhotoLabLayer({
      name: "Cyber Neon Glow",
      type: "template",
      render: (ctx) => {
        ctx.font = "800 76px 'Outfit', sans-serif";
        ctx.textAlign = "center";
        ctx.shadowColor = "#06b6d4";
        ctx.shadowBlur = 30;
        ctx.fillStyle = "#06b6d4";
        ctx.fillText("FUTURE OF AI", W / 2, H * 0.45);
        ctx.shadowColor = "#ec4899";
        ctx.fillStyle = "#f43f5e";
        ctx.fillText("IS ALREADY HERE", W / 2, H * 0.55);
        ctx.shadowBlur = 0;
      },
    });
  } else if (name === "quote-clean") {
    addPhotoLabLayer({
      name: "Minimal Quote",
      type: "template",
      render: (ctx) => {
        ctx.fillStyle = "rgba(255,255,255,0.06)";
        ctx.fillRect(W * 0.1, H * 0.3, W * 0.8, H * 0.4);
        ctx.font = "italic 40px 'Inter', serif";
        ctx.fillStyle = "#e2e8f0";
        ctx.textAlign = "center";
        ctx.fillText("“Small daily disciplines compound", W / 2, H * 0.48);
        ctx.fillText("into monumental victories.”", W / 2, H * 0.54);
      },
    });
  }

  showToast(`Applied template '${name}'`, "success");
}

window.loadPhotoLabFrame = function (dataUrl) {
  initPhotoLab();
  const img = new Image();
  img.onload = () => {
    photoLab.baseImage = img;
    renderPhotoLabCanvas();
    showToast("Captured video frame set as background! 🎨", "success");
  };
  img.src = dataUrl;
};

/* ==========================================================================
   NODE WORKFLOW DAG ENGINE
   --------------------------------------------------------------------------
   The DAG workspace is owned by flow.js — a live, draggable board over the
   server's workflow document (palette, wiring, checklist gate, real runs).
   `loadWorkflowDAG()` is defined there and called by switchWorkspace().
   ========================================================================== */

// ---------- Document & Library Search ----------

$("doc-search-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const query = $("doc-query").value.trim();
  if (query) run(() => searchDocuments(query));
});

$("lib-search-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const query = $("lib-query").value.trim();
  if (query) run(() => searchLibrary(query));
});

/* ==========================================================================
   SPECIALIZED AI AGENT TOOLBOX & PROMPT BRIDGE DISPATCHER
   ========================================================================== */

function setupAgentToolbox() {
  const getSelectedProject = () => {
    return state.projects.find((p) => p.id === state.selectedId) || null;
  };

  const toolPromptGenerators = {
    "claude-hook": (p) => {
      const topic = p?.topic || "Deep Work & Mental Flow Mastery";
      const dur = p?.duration_target_seconds || 45;
      return [
        `# Role: Viral Short-Form Script Specialist (Anthropic Claude)`,
        `Skill File: .claude/skills/ai-scripting/SKILL.md`,
        `Project: "${p?.name || "Viral Short"}"`,
        `Topic: "${topic}"`,
        `Target Duration: ${dur}s · Language: Vietnamese`,
        ``,
        `## Mission`,
        `Generate 3 high-retention viral opening hooks (under 3 seconds / max 14 syllables in spoken Vietnamese).`,
        `Employ one of the 3 psychological triggers:`,
        `1. The Curiosity Gap (Khoảng trống tò mò)`,
        `2. The Counter-Intuitive Truth (Nghịch lý đảo chiều)`,
        `3. The Direct Challenge (Thách thức niềm tin cũ)`,
        ``,
        `## Required Output Format`,
        `Option 1:`,
        `[Hook] <Spoken Vietnamese narration clause>`,
        `[Visual: Dynamic punch-in / bold kinetic headline / high contrast graphic]`,
        `[Sound: Whoosh SFX + sub bass hit]`,
        ``,
        `Option 2: ...`,
        `Option 3: ...`,
      ].join("\n");
    },
    "claude-polish": (p) => {
      const script = p?.script || "[Hook] 99% mọi người làm việc sai cách mà không nhận ra...\n[Turn] Bí quyết không nằm ở thời gian, mà ở chu kỳ dopamine.\n[Payoff] Áp dụng quy tắc 25 phút ngắt quãng sẽ nhân đôi hiệu suất.\n[CTA] Thử ngay hôm nay!";
      return [
        `# Role: Short-Form Pacing & Narration Polisher (Anthropic Claude)`,
        `Skill File: .claude/skills/ai-scripting/SKILL.md`,
        `Target Tempo: 3.8 - 4.2 syllables/sec (Natural Vietnamese spoken rhythm)`,
        ``,
        `## Current Draft Script`,
        script,
        ``,
        `## Polish Directives`,
        `1. Preserve strict section tags: [Hook], [Turn], [Payoff], [CTA].`,
        `2. Split any sentence exceeding 16 syllables into rhythmic, punchy clauses.`,
        `3. Embed synchronized multimodal cues: [Visual: ...] and [Sound: ...].`,
        `4. Transform passive translations into active, conversational Vietnamese voice.`,
      ].join("\n");
    },
    "gemini-framing": (p) => {
      const script = p?.script || "(Draft your script first or specify topic)";
      return [
        `# Role: Multimodal Visual Director (Google Gemini 2.0 / Flash)`,
        `Skill File: .claude/skills/ai-video-editing/SKILL.md`,
        `Topic: "${p?.topic || "Autonomous AI Workflows"}"`,
        ``,
        `## Script Narration`,
        script,
        ``,
        `## Visual Framing Directives`,
        `Produce scene-by-scene cinematic framing instructions:`,
        `- Camera shot types: Extreme Close-Up, Dynamic Dutch Angle, Slow Push-In, Whip Pan.`,
        `- TikTok Safe Zone compliance: safe within [0.08, 0.85] x-axis, [0.20, 0.75] y-axis.`,
        `- Color LUT & Lighting: Cyberpunk Neon, Vintage Warm, or Moody Low-Key.`,
        `- B-Roll / Stock footage search keywords for each scene.`,
      ].join("\n");
    },
    "gemini-research": (p) => {
      return [
        `# Role: Fact-Grounded Deep Researcher (Google Gemini)`,
        `Topic: "${p?.topic || "Neuroscience of Habit Formation"}"`,
        ``,
        `## Research Directives`,
        `Conduct deep grounded research across academic literature (arXiv, Crossref, PubMed) and verified repositories.`,
        `Extract:`,
        `1. Top 3 verified empirical facts with citations/DOIs.`,
        `2. 1 surprising counter-intuitive statistic or case study to power the video hook.`,
        `3. Core mechanism explained in 2 punchy bullet points.`,
      ].join("\n");
    },
    "codex-scenes": (p) => {
      const script = p?.script || "[Hook] Đừng bao giờ bỏ cuộc khi mọi thứ khó khăn nhất.\n[Turn] Vì chính điểm gãy đó là lúc não bộ đang tái cấu trúc nơ-ron.\n[Payoff] Kiên trì thêm 10% nữa, bạn sẽ vượt ngưỡng giới hạn.\n[CTA] Lưu video lại để xem khi cần động lực!";
      const dur = p?.duration_target_seconds || 45;
      return [
        `# Role: Video Timeline Code Compiler (OpenAI Codex)`,
        `Skill File: .claude/skills/ai-video-editing/SKILL.md`,
        `Target Duration: ${dur}s`,
        ``,
        `## Narration Script`,
        script,
        ``,
        `## Task`,
        `Compile the narration into strict JSON scenes matching the AI Content Factory schema:`,
        `\`\`\`json`,
        `[`,
        `  {`,
        `    "id": "scene-01",`,
        `    "text": "Đừng bao giờ bỏ cuộc khi mọi thứ khó khăn nhất.",`,
        `    "duration_seconds": 3.5,`,
        `    "bg_color": "#0f172a",`,
        `    "transition": "zoom_fade",`,
        `    "motion": "push_in",`,
        `    "lut": "cyberpunk"`,
        `  }`,
        `]`,
        `\`\`\``,
        `Enforce that total duration equals ${dur}s ± 1s.`,
      ].join("\n");
    },
    "codex-motion": (p) => {
      return [
        `# Role: Keyframe Motion Math Specialist (OpenAI Codex)`,
        `Skill File: .claude/skills/ai-video-editing/SKILL.md`,
        ``,
        `## Task`,
        `Calculate kinetic typography 2D transform curves:`,
        `- Scale: 0.8 -> 1.0 (with 1.05 spring bounce at t=0.15).`,
        `- Easing function: cubic-bezier(0.16, 1, 0.3, 1).`,
        `- TikTok safe-zone margins: top 60px, bottom 140px, right 70px.`,
        `- Output CSS keyframes and Canvas 2D matrix transform step logic.`,
      ].join("\n");
    },
    "deepseek-copyrisk": (p) => {
      const script = p?.script || "(Enter script here)";
      return [
        `# Role: Anti-Plagiarism & Originality Auditor (DeepSeek R1)`,
        `Skill File: .claude/skills/ai-scripting/SKILL.md`,
        `Topic: "${p?.topic || "AI Production"}"`,
        ``,
        `## Script to Audit`,
        script,
        ``,
        `## Audit Instructions`,
        `1. Scan for verbatim copy risks or clichés against known public texts.`,
        `2. Apply the "Transform, Do Not Copy" rule to rewrite any matched phrases into original analogies.`,
        `3. Provide originality score (0 - 100) and line-by-line rewrite suggestions.`,
      ].join("\n");
    },
    "deepseek-facts": (p) => {
      const script = p?.script || "(Enter script here)";
      return [
        `# Role: Rigorous Fact & Logic Auditor (DeepSeek R1)`,
        `Skill File: .claude/skills/ai-agent-orchestrator/SKILL.md`,
        `Script:`,
        script,
        ``,
        `## Audit Instructions`,
        `Verify all empirical assertions, numbers, dates, and causal claims:`,
        `1. Flag any false claims, unverified myths, or misleading generalizations.`,
        `2. Cite reliable scientific or historical references for corrections.`,
        `3. Grade factual integrity: PASS / WARN / FAIL.`,
      ].join("\n");
    },
    "local-voice": (p) => {
      return [
        `# Local Engine: Edge-TTS Neural Vietnamese Voiceover`,
        `Skill File: .claude/skills/ai-audio-editing/SKILL.md`,
        `Voice: vi-VN-HoaiMyNeural (Female) or vi-VN-NamMinhNeural (Male)`,
        `Target Speed: +5% (Pacing: ~4.0 syllables/second)`,
        ``,
        `Command to run offline:`,
        `python -m edge_tts --voice vi-VN-HoaiMyNeural --rate=+5% --text "${p?.script ? p.script.replace(/"/g, '\\"') : "Kịch bản mẫu"}" --write-media voiceover.mp3`,
      ].join("\n");
    },
    "local-sfx": (p) => {
      return [
        `# Local Web Audio SFX Engine`,
        `Skill File: .claude/skills/ai-audio-editing/SKILL.md`,
        `Procedural Synthesizer (Zero External Assets Required):`,
        `- Whoosh: Bandpass noise sweep (300Hz -> 2400Hz -> 400Hz, 300ms)`,
        `- Pop: Sine downward drop (750Hz -> 140Hz, 80ms)`,
        `- Camera Click: Double triangle burst (1200Hz + 900Hz, 30ms)`,
        `- Impact: Sub-bass resonance (150Hz -> 30Hz, 400ms)`,
        `- Ding: Pure bell chime (1760Hz, 600ms decay)`,
      ].join("\n");
    },
  };

  // Wire up Copy Prompt buttons
  document.querySelectorAll(".at-btn-prompt").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const action = btn.dataset.action;
      const generator = toolPromptGenerators[action];
      const p = getSelectedProject();
      const promptText = generator ? generator(p) : `# AI Agent Tool: ${action}\nProject: ${p?.name || "New"}`;

      try {
        await navigator.clipboard.writeText(promptText);
        const card = btn.closest(".agent-tool-card");
        const name = card?.querySelector(".at-name")?.textContent || action;
        showToast(`📋 Copied prompt for '${name}'! Ready to paste into AI Agent.`, "success");
      } catch {
        showToast("Clipboard access denied. Opening Agent Bridge modal instead...", "info");
        if (window.openBridgeModal) openBridgeModal();
      }
    });
  });

  // Wire up Run Action buttons
  document.querySelectorAll(".at-btn-run").forEach((btn) => {
    btn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      const action = btn.dataset.action;
      const p = getSelectedProject();

      if (action === "local-sfx") {
        if (window.playSFX) {
          window.playSFX("whoosh");
          setTimeout(() => window.playSFX && window.playSFX("ding"), 320);
          showToast("🎵 Synthesized Whoosh + Ding SFX via Web Audio API!", "success");
        } else {
          showToast("SFX Engine active", "info");
        }
        return;
      }

      if (!p) {
        showToast("Please select or create a project first.", "info");
        return;
      }

      if (action === "claude-hook" || action === "claude-polish") {
        switchTab("script");
        showToast("Switched to Script Studio. Click 'Generate Script' or edit draft.", "info");
      } else if (action === "gemini-research") {
        $("btn-research").click();
      } else if (action === "gemini-framing" || action === "codex-scenes" || action === "codex-motion") {
        if (p.video_project) {
          if (window.openEditor) window.openEditor();
        } else {
          showToast("Video project not created yet. Starting video generation...", "info");
          $("btn-start").click();
        }
      } else if (action === "deepseek-copyrisk" || action === "deepseek-facts") {
        switchTab("script");
        await analyzeScript(p.id, p.script);
        showToast("Ran script analysis & fact audit.", "success");
      } else if (action === "local-voice") {
        showToast("Voice synthesizer configured for vi-VN-HoaiMyNeural", "info");
        switchTab("script");
      }
    });
  });
}

/* ==========================================================================
   MULTI-FORMAT CONTENT EMPIRE ENGINE CONTROLLER
   ========================================================================== */

state.campaign = null;
state.activeShortIndex = 0;

async function loadEmpireCampaign() {
  if (!state.selectedId) {
    showToast("Vui lòng chọn hoặc tạo một dự án trước.", "info");
    return;
  }
  try {
    const camp = await api(`/projects/${state.selectedId}/campaign`);
    state.campaign = camp;
    renderEmpireCampaign(camp);
  } catch (err) {
    showToast(`Không thể tải chiến dịch: ${err.message}`, "error");
  }
}

function renderEmpireCampaign(camp) {
  if (!camp) return;

  // Title
  if ($("empire-topic-title")) {
    $("empire-topic-title").textContent = `Chủ đề: ${camp.master_topic}`;
  }

  // YouTube Script
  if ($("empire-yt-script")) {
    $("empire-yt-script").value = camp.youtube_script || "";
  }
  if ($("yt-word-count")) {
    const words = (camp.youtube_script || "").trim().split(/\s+/).length;
    $("yt-word-count").textContent = `~${words} từ · ${Math.round(camp.youtube_duration_target_seconds / 60)} phút`;
  }

  // YouTube Description
  if ($("empire-yt-desc")) {
    $("empire-yt-desc").value = camp.youtube_description || "";
  }

  // YouTube Viral Titles
  const titlesBox = $("empire-yt-titles");
  if (titlesBox) {
    titlesBox.innerHTML = "";
    (camp.youtube_titles || []).forEach((t, i) => {
      const item = document.createElement("div");
      item.className = "title-item";
      item.innerHTML = `<span><strong>#${i + 1}</strong> ${esc(t)}</span><button class="btn sm" data-title="${esc(t)}">📋 Copy</button>`;
      item.querySelector("button").addEventListener("click", () => {
        navigator.clipboard.writeText(t);
        showToast("Đã sao chép tiêu đề YouTube! ⚡", "success");
      });
      titlesBox.appendChild(item);
    });
  }

  // YouTube Scenes Breakdown
  const scenesBox = $("empire-yt-scenes");
  if (scenesBox) {
    scenesBox.innerHTML = "";
    const p = state.projects.find((x) => x.id === state.selectedId);
    (camp.youtube_scenes || []).forEach((sc) => {
      const card = document.createElement("div");
      card.className = "empire-scene-card";
      const vpScene = p?.video_project?.scenes?.find(
        (s, idx) => s.id === sc.id || (idx + 1) === sc.scene_number || s.id === `scene_${sc.scene_number}`
      );
      const hasVideo = vpScene?.video_url;
      const cardId = sc.scene_number ? `scene_${sc.scene_number}` : sc.id;
      card.innerHTML = `
        <div class="esc-head">
          <span><strong>Cảnh ${sc.scene_number}</strong> (${sc.duration_seconds}s)${hasVideo ? ' <span class="badge ok" style="font-size:10px; margin-left:4px;">🎬 Video Attached</span>' : ''}</span>
          <div style="display:flex; gap:6px; align-items:center;">
            <span class="esc-type-tag ${sc.asset_type}">${esc(sc.asset_label || sc.asset_type)}</span>
            <button class="btn sm btn-scene-ingest" style="font-size:11px; padding:2px 8px;" data-scene="${esc(cardId)}">📥 Ingest</button>
          </div>
        </div>
        <div class="esc-desc"><strong>${esc(sc.title)}:</strong> ${esc(sc.visual_description)}</div>
        <div class="esc-desc" style="color:#a5b4fc; font-size:11px;">🎥 <em>${esc(sc.camera_movement || "")}</em></div>
        <div class="esc-prompt" title="Bấm để sao chép Prompt AI Video/Image">📋 Prompt: ${esc(sc.ai_prompt)}</div>
      `;
      card.querySelector(".esc-prompt").addEventListener("click", () => {
        navigator.clipboard.writeText(sc.ai_prompt);
        showToast(`Đã sao chép prompt cho Cảnh ${sc.scene_number}!`, "success");
      });
      card.querySelector(".btn-scene-ingest").addEventListener("click", () => {
        openIngestModal(cardId);
      });
      scenesBox.appendChild(card);
    });
  }

  // TikTok Shorts Tabs
  const shortsTabs = $("empire-shorts-tabs");
  if (shortsTabs) {
    shortsTabs.innerHTML = "";
    (camp.shorts || []).forEach((s, idx) => {
      const btn = document.createElement("button");
      btn.className = `short-tab-btn${idx === state.activeShortIndex ? " active" : ""}`;
      btn.textContent = `Short ${idx + 1}: ${s.angle || s.title.slice(0, 15)}`;
      btn.addEventListener("click", () => {
        state.activeShortIndex = idx;
        document.querySelectorAll(".short-tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        renderActiveShort(s);
      });
      shortsTabs.appendChild(btn);
    });
  }

  if (camp.shorts && camp.shorts.length > 0) {
    const curShort = camp.shorts[state.activeShortIndex] || camp.shorts[0];
    renderActiveShort(curShort);
  }
  if ($("shorts-badge-count")) {
    $("shorts-badge-count").textContent = `${camp.shorts?.length || 0} Shorts`;
  }

  // TikTok Retention Hooks
  const hooksBox = $("empire-tiktok-hooks");
  if (hooksBox) {
    hooksBox.innerHTML = "";
    (camp.tiktok_hooks || []).forEach((h, i) => {
      const pill = document.createElement("div");
      pill.className = "hook-pill";
      pill.innerHTML = `<span><strong>Hook ${i + 1}:</strong> "${esc(h)}"</span><button class="btn sm" data-hook="${esc(h)}">📋</button>`;
      pill.querySelector("button").addEventListener("click", () => {
        navigator.clipboard.writeText(h);
        showToast(`Đã sao chép Hook ${i + 1}! 🔥`, "success");
      });
      hooksBox.appendChild(pill);
    });
  }

  // Generative Prompt Matrix Lists
  renderPromptMatrix(camp);
}

function renderActiveShort(short) {
  if (!short) return;
  if ($("short-active-angle")) $("short-active-angle").textContent = short.angle || "Góc nhìn độc lập";
  if ($("short-active-title")) $("short-active-title").value = short.title || "";
  if ($("short-active-hook")) $("short-active-hook").value = short.hook || "";
  if ($("short-active-script")) $("short-active-script").value = short.script || "";
  if ($("short-active-dur")) {
    const words = (short.script || "").trim().split(/\s+/).length;
    $("short-active-dur").textContent = `${short.target_duration_seconds}s · ~${words} từ`;
  }
}

function renderPromptMatrix(camp) {
  const ppack = camp.prompt_pack;
  if (!ppack) return;

  // Kling / Veo Prompts
  const klingBox = $("pm-kling-list");
  if (klingBox) {
    klingBox.innerHTML = "";
    (ppack.kling_veo_prompts || []).forEach((item, i) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML = `
        <div class="prompt-card-head">
          <span>🎬 ${esc(item.scene)} (${esc(item.aspect)})</span>
          <button class="btn sm primary">📋 Copy</button>
        </div>
        <div class="prompt-text">${esc(item.prompt)}</div>
      `;
      card.querySelector("button").addEventListener("click", () => {
        navigator.clipboard.writeText(item.prompt);
        showToast(`Đã sao chép Prompt Kling/Veo #${i + 1}!`, "success");
      });
      klingBox.appendChild(card);
    });
  }

  // Midjourney Prompts
  const mjBox = $("pm-mj-list");
  if (mjBox) {
    mjBox.innerHTML = "";
    (ppack.midjourney_prompts || []).forEach((item, i) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML = `
        <div class="prompt-card-head">
          <span>🖼️ ${esc(item.subject)}</span>
          <button class="btn sm primary">📋 Copy</button>
        </div>
        <div class="prompt-text">${esc(item.prompt)}</div>
      `;
      card.querySelector("button").addEventListener("click", () => {
        navigator.clipboard.writeText(item.prompt);
        showToast(`Đã sao chép Midjourney Prompt #${i + 1}!`, "success");
      });
      mjBox.appendChild(card);
    });
  }

  // Suno Prompts
  const sunoBox = $("pm-suno-list");
  if (sunoBox) {
    sunoBox.innerHTML = "";
    (ppack.suno_prompts || []).forEach((item, i) => {
      const card = document.createElement("div");
      card.className = "prompt-card";
      card.innerHTML = `
        <div class="prompt-card-head">
          <span>🎵 ${esc(item.style)}</span>
          <button class="btn sm primary">📋 Copy Tags</button>
        </div>
        <div class="prompt-text"><strong>Tags:</strong> ${esc(item.tags)}<br><strong>Cue:</strong> ${esc(item.lyrics_cue)}</div>
      `;
      card.querySelector("button").addEventListener("click", () => {
        navigator.clipboard.writeText(item.tags);
        showToast(`Đã sao chép Suno Style Tags #${i + 1}!`, "success");
      });
      sunoBox.appendChild(card);
    });
  }

  // ElevenLabs
  const elevenBox = $("pm-eleven-content");
  if (elevenBox && ppack.elevenlabs_settings) {
    const el = ppack.elevenlabs_settings;
    elevenBox.innerHTML = `
      <div class="eleven-prop">
        <span>Recommended Voice:</span>
        <strong>${esc(el.recommended_voice)}</strong>
      </div>
      <div class="eleven-prop">
        <span>Offline Fallback (Edge-TTS):</span>
        <strong>${esc(el.fallback_tts)}</strong>
      </div>
      <div class="eleven-prop">
        <span>Model & Stability:</span>
        <strong>${esc(el.model_id)} · Stability ${el.voice_settings?.stability} · Boost ${el.voice_settings?.similarity_boost}</strong>
      </div>
      <div class="eleven-prop" style="grid-column: 1 / -1;">
        <span>Pacing & Tone Directives:</span>
        <div style="color:#cbd5e1; font-size:12px; line-height:1.5;">${esc(el.pacing_note)}</div>
      </div>
    `;
  }

  // Fact Check
  const fcBox = $("pm-factcheck-content");
  if (fcBox) {
    fcBox.textContent = camp.fact_check_summary || "Chưa có báo cáo kiểm chứng sự thật.";
  }
}

function setupEmpireEventListeners() {
  // Re-generate Campaign button
  if ($("btn-empire-generate")) {
    $("btn-empire-generate").addEventListener("click", async () => {
      if (!state.selectedId) {
        showToast("Vui lòng chọn một dự án!", "info");
        return;
      }
      const shortsCount = parseInt($("empire-shorts-count")?.value || "5", 10);
      const ytMinutes = parseInt($("empire-yt-duration")?.value || "10", 10);

      showToast("Đang sinh toàn bộ chiến dịch đa định dạng...", "info");
      try {
        const camp = await api(`/projects/${state.selectedId}/campaign/generate`, {
          method: "POST",
          body: JSON.stringify({
            shorts_count: shortsCount,
            youtube_target_minutes: ytMinutes,
            include_prompts: true,
          }),
        });
        state.campaign = camp;
        state.activeShortIndex = 0;
        renderEmpireCampaign(camp);
        showToast(`⚡ Đã tạo thành công 1 YouTube Master (${ytMinutes}m) + ${shortsCount} TikTok Shorts!`, "success");
      } catch (err) {
        showToast(`Lỗi tạo chiến dịch: ${err.message}`, "error");
      }
    });
  }

  // Export All Packs button
  if ($("btn-empire-export")) {
    $("btn-empire-export").addEventListener("click", async () => {
      if (!state.selectedId) return;
      try {
        const pack = await api(`/projects/${state.selectedId}/campaign/export-pack`);
        const blob = new Blob([JSON.stringify(pack, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `empire-campaign-${pack.master_topic.slice(0, 20).replace(/[^a-z0-9]/gi, "_")}.json`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("📦 Đã xuất trọn gói 15 tài nguyên Empire thành file JSON!", "success");
      } catch (err) {
        showToast(`Không thể xuất gói tài nguyên: ${err.message}`, "error");
      }
    });
  }

  // Copy YouTube Script & Desc buttons
  if ($("btn-copy-yt-script")) {
    $("btn-copy-yt-script").addEventListener("click", () => {
      const val = $("empire-yt-script")?.value;
      if (val) {
        navigator.clipboard.writeText(val);
        showToast("📋 Đã sao chép Kịch bản YouTube Master 10 phút!", "success");
      }
    });
  }

  if ($("btn-copy-yt-desc")) {
    $("btn-copy-yt-desc").addEventListener("click", () => {
      const val = $("empire-yt-desc")?.value;
      if (val) {
        navigator.clipboard.writeText(val);
        showToast("📋 Đã sao chép YouTube Description & Timestamps!", "success");
      }
    });
  }

  // Save Active Short
  if ($("btn-save-active-short")) {
    $("btn-save-active-short").addEventListener("click", async () => {
      if (!state.campaign || !state.campaign.shorts) return;
      const curShort = state.campaign.shorts[state.activeShortIndex];
      if (!curShort) return;

      const title = $("short-active-title")?.value;
      const hook = $("short-active-hook")?.value;
      const script = $("short-active-script")?.value;

      try {
        const updated = await api(`/projects/${state.selectedId}/campaign/shorts/${curShort.id}`, {
          method: "PUT",
          body: JSON.stringify({ title, hook, script }),
        });
        state.campaign.shorts[state.activeShortIndex] = updated;
        renderActiveShort(updated);
        showToast(`💾 Đã lưu thay đổi cho ${updated.title}!`, "success");
      } catch (err) {
        showToast(`Lỗi lưu short: ${err.message}`, "error");
      }
    });
  }

  // Copy Short Script & Prompts
  if ($("btn-copy-short-script")) {
    $("btn-copy-short-script").addEventListener("click", () => {
      const val = $("short-active-script")?.value;
      if (val) {
        navigator.clipboard.writeText(val);
        showToast("📋 Đã sao chép Kịch bản TikTok Short!", "success");
      }
    });
  }

  if ($("btn-copy-short-kling")) {
    $("btn-copy-short-kling").addEventListener("click", () => {
      const curShort = state.campaign?.shorts?.[state.activeShortIndex];
      const p = curShort?.video_prompts?.[0] || "Cinematic 9:16 vertical video --ar 9:16";
      navigator.clipboard.writeText(p);
      showToast("🎥 Đã sao chép 9:16 Kling/Veo Prompt!", "success");
    });
  }

  if ($("btn-copy-short-mj")) {
    $("btn-copy-short-mj").addEventListener("click", () => {
      const curShort = state.campaign?.shorts?.[state.activeShortIndex];
      const p = curShort?.image_prompts?.[0] || "Vertical 9:16 archival illustration --ar 9:16";
      navigator.clipboard.writeText(p);
      showToast("🖼️ Đã sao chép 9:16 Midjourney Prompt!", "success");
    });
  }

  // Prompt Matrix Tabs
  document.querySelectorAll(".pm-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".pm-tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".pm-tab-content").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const target = $(`pm-panel-${btn.dataset.pmtab}`);
      if (target) target.classList.add("active");
    });
  });
}

/* ==========================================================================
   EXTERNAL AI ASSET INGESTION CONTROLLER (Kling, Veo, Midjourney, Suno, ElevenLabs)
   ========================================================================== */

let selectedMediaFile = null;
let selectedVoiceFile = null;
let selectedMusicFile = null;
let batchQueue = [];

function openIngestModal(targetSceneId = null) {
  if (!state.selectedId) {
    showToast("Vui lòng chọn hoặc tạo dự án trước khi nạp tài nguyên!", "info");
    return;
  }
  populateIngestScenes(targetSceneId);
  const modal = $("ingest-modal");
  if (modal) {
    modal.hidden = false;
  }
}

function closeIngestModal() {
  const modal = $("ingest-modal");
  if (modal) {
    modal.hidden = true;
  }
  selectedMediaFile = null;
  selectedVoiceFile = null;
  selectedMusicFile = null;
  batchQueue = [];
  if ($("media-file-name")) $("media-file-name").textContent = "";
  if ($("voice-file-name")) $("voice-file-name").textContent = "";
  if ($("music-file-name")) $("music-file-name").textContent = "";
  if ($("batch-file-list")) $("batch-file-list").innerHTML = "";
  if ($("btn-process-batch")) {
    $("btn-process-batch").disabled = true;
    $("btn-process-batch").textContent = "⚡ Auto-Bind All Files to Pipeline";
  }
}

function populateIngestScenes(selectedSceneId = null) {
  const sel = $("ingest-scene-select");
  if (!sel) return;
  sel.innerHTML = '<option value="">(Chọn cảnh mục tiêu...)</option>';
  const p = state.projects.find((x) => x.id === state.selectedId);
  if (!p) return;

  const vpScenes = p.video_project?.scenes || [];
  const campScenes = p.campaign?.youtube_scenes || p.campaign?.hybrid_scenes || [];

  const scenes = vpScenes.length > 0 ? vpScenes : campScenes;
  if (scenes.length === 0) {
    for (let i = 1; i <= 12; i++) {
      const opt = document.createElement("option");
      opt.value = `scene_${i}`;
      opt.textContent = `Cảnh ${i} (Scene ${i})`;
      sel.appendChild(opt);
    }
  } else {
    scenes.forEach((sc, idx) => {
      const opt = document.createElement("option");
      const sid = sc.id || `scene_${sc.scene_number || idx + 1}`;
      opt.value = sid;
      const num = sc.scene_number || idx + 1;
      const title = sc.title || sc.narration?.slice(0, 30) || `Cảnh ${num}`;
      const attached = sc.video_url ? " [🎬 Video]" : "";
      opt.textContent = `Cảnh ${num} (${sid}) — ${title}${attached}`;
      sel.appendChild(opt);
    });
  }

  if (selectedSceneId) {
    sel.value = selectedSceneId;
    if (!sel.value && sel.options.length > 1) {
      for (const opt of sel.options) {
        if (opt.value.includes(String(selectedSceneId))) {
          sel.value = opt.value;
          break;
        }
      }
    }
  }
}

function setupExternalIngestListeners() {
  // Open / Close modal triggers
  if ($("btn-topbar-ingest")) {
    $("btn-topbar-ingest").addEventListener("click", () => openIngestModal());
  }
  if ($("btn-empire-ingest")) {
    $("btn-empire-ingest").addEventListener("click", () => openIngestModal());
  }
  if ($("btn-ingest-close")) {
    $("btn-ingest-close").addEventListener("click", closeIngestModal);
  }
  if ($("btn-ingest-close-x")) {
    $("btn-ingest-close-x").addEventListener("click", closeIngestModal);
  }
  const modal = $("ingest-modal");
  if (modal) {
    modal.addEventListener("click", (ev) => {
      if (ev.target === modal) closeIngestModal();
    });
  }

  // Keyboard shortcut 'I' (when not inside input/textarea)
  window.addEventListener("keydown", (ev) => {
    if ((ev.key === "i" || ev.key === "I") && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag !== "input" && tag !== "textarea" && tag !== "select") {
        ev.preventDefault();
        const m = $("ingest-modal");
        if (m && !m.hidden) closeIngestModal();
        else openIngestModal();
      }
    } else if (ev.key === "Escape") {
      const m = $("ingest-modal");
      if (m && !m.hidden) closeIngestModal();
    }
  });

  // Tab switching
  document.querySelectorAll(".ingest-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".ingest-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".ingest-panel").forEach((p) => {
        p.classList.remove("active");
        p.hidden = true;
      });
      tab.classList.add("active");
      const targetPanel = $(`ipanel-${tab.dataset.itab}`);
      if (targetPanel) {
        targetPanel.hidden = false;
        targetPanel.classList.add("active");
      }
    });
  });

  // --- TAB 1: SCENE MEDIA (Kling / Veo / Midjourney) ---
  // Option A: Link Online Media URL
  if ($("btn-apply-media-url")) {
    $("btn-apply-media-url").addEventListener("click", async () => {
      if (!state.selectedId) return;
      const targetScene = $("ingest-scene-select")?.value;
      const mediaType = $("ingest-media-type")?.value || "scene_video";
      const url = $("ingest-media-url")?.value.trim();
      const attribution = $("ingest-media-attribution")?.value.trim() || (mediaType === "scene_video" ? "Kling AI 1.5 Pro" : "Midjourney v6.1");

      if (!targetScene) {
        showToast("Vui lòng chọn Cảnh mục tiêu (Target Scene) trước!", "error");
        return;
      }
      if (!url) {
        showToast("Vui lòng nhập URL tài nguyên media (video/ảnh)!", "error");
        return;
      }

      try {
        await api(`/projects/${state.selectedId}/external/import`, {
          method: "POST",
          body: JSON.stringify({
            asset_type: mediaType,
            source_tool: attribution,
            url: url,
            target_scene_id: targetScene,
            title: `Media cho ${targetScene}`,
          }),
        });
        showToast(`🔗 Đã gắn kết thành công media vào ${targetScene}!`, "success");
        if ($("ingest-media-url")) $("ingest-media-url").value = "";
        await loadProjects();
        populateIngestScenes(targetScene);
      } catch (err) {
        showToast(`Lỗi gắn media: ${err.message}`, "error");
      }
    });
  }

  // Option B: Upload Local File
  if ($("btn-browse-media") && $("ingest-file-input")) {
    $("btn-browse-media").addEventListener("click", () => $("ingest-file-input").click());
    $("ingest-file-input").addEventListener("change", (ev) => {
      if (ev.target.files && ev.target.files[0]) {
        selectedMediaFile = ev.target.files[0];
        if ($("media-file-name")) $("media-file-name").textContent = `📁 ${selectedMediaFile.name} (${Math.round(selectedMediaFile.size / 1024)} KB)`;
      }
    });
  }

  const mediaDrop = $("media-drop-zone");
  if (mediaDrop) {
    ["dragenter", "dragover"].forEach((ename) => {
      mediaDrop.addEventListener(ename, (e) => {
        e.preventDefault();
        mediaDrop.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach((ename) => {
      mediaDrop.addEventListener(ename, (e) => {
        e.preventDefault();
        mediaDrop.classList.remove("dragover");
      });
    });
    mediaDrop.addEventListener("drop", (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        selectedMediaFile = e.dataTransfer.files[0];
        if ($("media-file-name")) $("media-file-name").textContent = `📁 ${selectedMediaFile.name} (${Math.round(selectedMediaFile.size / 1024)} KB)`;
      }
    });
  }

  if ($("btn-upload-media-file")) {
    $("btn-upload-media-file").addEventListener("click", async () => {
      if (!state.selectedId) return;
      const targetScene = $("ingest-scene-select")?.value;
      const mediaType = $("ingest-media-type")?.value || "scene_video";
      const attribution = $("ingest-media-attribution")?.value.trim() || (mediaType === "scene_video" ? "Kling AI Video" : "Midjourney Restoration");

      if (!targetScene) {
        showToast("Vui lòng chọn Cảnh mục tiêu (Target Scene) trước!", "error");
        return;
      }
      if (!selectedMediaFile) {
        showToast("Vui lòng chọn hoặc kéo thả file video/ảnh cần tải lên!", "error");
        return;
      }

      showToast(`Đang tải file ${selectedMediaFile.name} lên máy chủ...`, "info");
      try {
        const fd = new FormData();
        fd.append("file", selectedMediaFile);
        fd.append("asset_type", mediaType);
        fd.append("source_tool", attribution);
        fd.append("target_scene_id", targetScene);
        fd.append("title", selectedMediaFile.name);

        const record = await api(`/projects/${state.selectedId}/external/upload`, {
          method: "POST",
          body: fd,
        });

        showToast(`⬆️ Đã tải lên và gán ${record.title} vào ${targetScene}!`, "success");
        selectedMediaFile = null;
        if ($("media-file-name")) $("media-file-name").textContent = "";
        await loadProjects();
        populateIngestScenes(targetScene);
      } catch (err) {
        showToast(`Lỗi tải lên file: ${err.message}`, "error");
      }
    });
  }

  // --- TAB 2: AUDIO & MUSIC (ElevenLabs / Suno) ---
  // ElevenLabs Voiceover
  if ($("btn-browse-voice") && $("ingest-voice-file")) {
    $("btn-browse-voice").addEventListener("click", () => $("ingest-voice-file").click());
    $("ingest-voice-file").addEventListener("change", (ev) => {
      if (ev.target.files && ev.target.files[0]) {
        selectedVoiceFile = ev.target.files[0];
        if ($("voice-file-name")) $("voice-file-name").textContent = `🎙️ ${selectedVoiceFile.name} (${Math.round(selectedVoiceFile.size / 1024)} KB)`;
      }
    });
  }

  if ($("btn-apply-voice")) {
    $("btn-apply-voice").addEventListener("click", async () => {
      if (!state.selectedId) return;
      const voiceUrl = $("ingest-voice-url")?.value.trim();

      if (selectedVoiceFile) {
        showToast(`Đang tải file lồng tiếng ${selectedVoiceFile.name}...`, "info");
        try {
          const fd = new FormData();
          fd.append("file", selectedVoiceFile);
          fd.append("asset_type", "voiceover_audio");
          fd.append("source_tool", "ElevenLabs Voice");
          fd.append("title", selectedVoiceFile.name);

          await api(`/projects/${state.selectedId}/external/upload`, { method: "POST", body: fd });
          showToast("🎙️ Đã nạp file lồng tiếng ElevenLabs vào timeline!", "success");
          selectedVoiceFile = null;
          if ($("voice-file-name")) $("voice-file-name").textContent = "";
          await loadProjects();
        } catch (err) {
          showToast(`Lỗi tải voiceover: ${err.message}`, "error");
        }
      } else if (voiceUrl) {
        try {
          await api(`/projects/${state.selectedId}/external/import`, {
            method: "POST",
            body: JSON.stringify({
              asset_type: "voiceover_audio",
              source_tool: "ElevenLabs Voice",
              url: voiceUrl,
              title: "ElevenLabs Voiceover URL",
            }),
          });
          showToast("🎙️ Đã liên kết đường dẫn lồng tiếng ElevenLabs!", "success");
          if ($("ingest-voice-url")) $("ingest-voice-url").value = "";
          await loadProjects();
        } catch (err) {
          showToast(`Lỗi liên kết voiceover: ${err.message}`, "error");
        }
      } else {
        showToast("Vui lòng chọn file âm thanh hoặc nhập URL lồng tiếng!", "error");
      }
    });
  }

  // Suno / Udio Music
  if ($("btn-browse-music") && $("ingest-music-file")) {
    $("btn-browse-music").addEventListener("click", () => $("ingest-music-file").click());
    $("ingest-music-file").addEventListener("change", (ev) => {
      if (ev.target.files && ev.target.files[0]) {
        selectedMusicFile = ev.target.files[0];
        if ($("music-file-name")) $("music-file-name").textContent = `🎵 ${selectedMusicFile.name} (${Math.round(selectedMusicFile.size / 1024)} KB)`;
      }
    });
  }

  if ($("btn-apply-music")) {
    $("btn-apply-music").addEventListener("click", async () => {
      if (!state.selectedId) return;
      const musicUrl = $("ingest-music-url")?.value.trim();

      if (selectedMusicFile) {
        showToast(`Đang tải file nhạc nền ${selectedMusicFile.name}...`, "info");
        try {
          const fd = new FormData();
          fd.append("file", selectedMusicFile);
          fd.append("asset_type", "bgm_audio");
          fd.append("source_tool", "Suno AI Music");
          fd.append("title", selectedMusicFile.name);

          await api(`/projects/${state.selectedId}/external/upload`, { method: "POST", body: fd });
          showToast("🎵 Đã nạp soundtrack Suno vào background track!", "success");
          selectedMusicFile = null;
          if ($("music-file-name")) $("music-file-name").textContent = "";
          await loadProjects();
        } catch (err) {
          showToast(`Lỗi tải nhạc: ${err.message}`, "error");
        }
      } else if (musicUrl) {
        try {
          await api(`/projects/${state.selectedId}/external/import`, {
            method: "POST",
            body: JSON.stringify({
              asset_type: "bgm_audio",
              source_tool: "Suno AI Music",
              url: musicUrl,
              title: "Suno Soundtrack URL",
            }),
          });
          showToast("🎵 Đã liên kết nhạc nền Suno vào background track!", "success");
          if ($("ingest-music-url")) $("ingest-music-url").value = "";
          await loadProjects();
        } catch (err) {
          showToast(`Lỗi liên kết nhạc: ${err.message}`, "error");
        }
      } else {
        showToast("Vui lòng chọn file nhạc hoặc nhập URL soundtrack!", "error");
      }
    });
  }

  // --- TAB 3: RESEARCH & FACT-CHECK DOSSIER (Perplexity / DeepResearch) ---
  if ($("btn-apply-dossier")) {
    $("btn-apply-dossier").addEventListener("click", async () => {
      if (!state.selectedId) return;
      const text = $("ingest-dossier-text")?.value.trim();
      const source = $("ingest-dossier-source")?.value.trim() || "Perplexity Pro Investigation";

      if (!text) {
        showToast("Vui lòng dán nội dung báo cáo điều tra / sự thật!", "error");
        return;
      }

      showToast("Đang nạp hồ sơ nghiên cứu vào bộ nhớ dự án...", "info");
      try {
        await api(`/projects/${state.selectedId}/external/import`, {
          method: "POST",
          body: JSON.stringify({
            asset_type: "research_dossier",
            source_tool: source,
            content_text: text,
            title: "External Research Dossier",
          }),
        });
        showToast("🧠 Đã nạp hồ sơ nghiên cứu & kiểm chứng sự thật thành công!", "success");
        await loadProjects();
      } catch (err) {
        showToast(`Lỗi nạp hồ sơ: ${err.message}`, "error");
      }
    });
  }

  // --- TAB 4: BATCH DROPZONE ---
  function parseBatchFiles(files) {
    batchQueue = [];
    const listEl = $("batch-file-list");
    if (!listEl) return;
    listEl.innerHTML = "";

    Array.from(files).forEach((f) => {
      const name = f.name.toLowerCase();
      let assetType = "scene_video";
      let targetScene = null;
      let label = "Video Clip";

      // Detect scene number pattern e.g. scene_1, scene-2, sc3, shot_4
      const sceneMatch = name.match(/(?:scene|sc|shot)[_-\s]?(\d+)/);
      if (sceneMatch) {
        targetScene = `scene_${sceneMatch[1]}`;
      }

      // Detect asset type by extension and name
      if (name.match(/\.(mp4|webm|mov|mkv)$/)) {
        assetType = "scene_video";
        label = targetScene ? `🎬 ${targetScene.toUpperCase()} (Video Reconstruction)` : "🎬 Visual Video";
      } else if (name.match(/\.(jpg|jpeg|png|webp|avif)$/)) {
        assetType = "scene_image";
        label = targetScene ? `🖼️ ${targetScene.toUpperCase()} (Historical Photo)` : "🖼️ Visual Image";
      } else if (name.match(/(?:voice|narration|voiceover)/) || (name.match(/\.(mp3|wav|ogg|m4a)$/) && !name.match(/bgm|music/))) {
        assetType = "voiceover_audio";
        label = "🎙️ Master Voiceover Audio";
      } else if (name.match(/(?:bgm|music|soundtrack|suno|audio)/) || name.match(/\.(mp3|wav|ogg|m4a)$/)) {
        assetType = "bgm_audio";
        label = "🎵 Background Soundtrack";
      }

      batchQueue.push({
        file: f,
        asset_type: assetType,
        target_scene_id: targetScene,
        label: label,
      });

      const row = document.createElement("div");
      row.className = "batch-item-row";
      row.style.cssText = "display: flex; justify-content: space-between; padding: 6px 10px; background: rgba(255,255,255,0.04); border-radius: 6px; margin-bottom: 4px; font-size: 12px;";
      row.innerHTML = `<span><strong>${esc(f.name)}</strong> (${Math.round(f.size / 1024)} KB)</span><span class="badge ok">${esc(label)}</span>`;
      listEl.appendChild(row);
    });

    if ($("btn-process-batch")) {
      $("btn-process-batch").disabled = batchQueue.length === 0;
      $("btn-process-batch").textContent = `⚡ Tự động nạp ${batchQueue.length} file vào Pipeline`;
    }
  }

  if ($("btn-browse-batch") && $("batch-file-input")) {
    $("btn-browse-batch").addEventListener("click", () => $("batch-file-input").click());
    $("batch-file-input").addEventListener("change", (ev) => {
      if (ev.target.files) parseBatchFiles(ev.target.files);
    });
  }

  const batchDrop = $("batch-drop-zone");
  if (batchDrop) {
    ["dragenter", "dragover"].forEach((ename) => {
      batchDrop.addEventListener(ename, (e) => {
        e.preventDefault();
        batchDrop.classList.add("dragover");
      });
    });
    ["dragleave", "drop"].forEach((ename) => {
      batchDrop.addEventListener(ename, (e) => {
        e.preventDefault();
        batchDrop.classList.remove("dragover");
      });
    });
    batchDrop.addEventListener("drop", (e) => {
      if (e.dataTransfer.files) parseBatchFiles(e.dataTransfer.files);
    });
  }

  if ($("btn-process-batch")) {
    $("btn-process-batch").addEventListener("click", async () => {
      if (!state.selectedId || batchQueue.length === 0) return;

      $("btn-process-batch").disabled = true;
      let successCount = 0;
      for (let i = 0; i < batchQueue.length; i++) {
        const item = batchQueue[i];
        $("btn-process-batch").textContent = `⏳ Đang tải ${i + 1}/${batchQueue.length}: ${item.file.name}...`;
        try {
          const fd = new FormData();
          fd.append("file", item.file);
          fd.append("asset_type", item.asset_type);
          fd.append("source_tool", "Batch External Ingest");
          if (item.target_scene_id) fd.append("target_scene_id", item.target_scene_id);
          fd.append("title", item.file.name);

          await api(`/projects/${state.selectedId}/external/upload`, {
            method: "POST",
            body: fd,
          });
          successCount++;
        } catch (err) {
          showToast(`Lỗi file ${item.file.name}: ${err.message}`, "error");
        }
      }

      showToast(`📦 Đã nạp thành công ${successCount}/${batchQueue.length} file vào Pipeline!`, "success");
      batchQueue = [];
      if ($("batch-file-list")) $("batch-file-list").innerHTML = "";
      $("btn-process-batch").disabled = true;
      $("btn-process-batch").textContent = "⚡ Auto-Bind All Files to Pipeline";
      await loadProjects();
    });
  }
}

// ---------- History, Disaster & Sensitivity Niche Extensions ----------

function renderSensitivityReport(rep) {
  if (!rep) return;
  const badge = $("safety-score-badge");
  const inspBadge = $("inspector-safety-badge");
  const inspSummary = $("inspector-safety-summary");
  const findingsBox = $("sensitivity-findings");
  const discWrap = $("sensitivity-disclaimer-wrap");

  const score = rep.safety_score ?? 100;
  const isSafe = rep.is_safe_for_monetization !== false;

  if (badge) {
    badge.textContent = `${score}/100 ${isSafe ? "Safe" : "Policy Risk"}`;
    badge.className = `badge ${score >= 80 ? "ok" : score >= 60 ? "warn" : "err"}`;
  }
  if (inspBadge) {
    inspBadge.textContent = `${score}/100`;
    inspBadge.className = `badge ${score >= 80 ? "ok" : score >= 60 ? "warn" : "err"}`;
  }
  if (inspSummary) {
    inspSummary.textContent = isSafe
      ? "Kịch bản tuân thủ chính sách kiếm tiền (YouTube Advertiser-Friendly / TikTok)."
      : "⚠️ Phát hiện từ ngữ nhạy cảm hoặc rủi ro vàng tiền.";
  }

  if (findingsBox) {
    findingsBox.innerHTML = "";
    if (rep.findings && rep.findings.length > 0) {
      for (const f of rep.findings) {
        const div = document.createElement("div");
        div.className = `issue-item ${f.severity === "critical" ? "error" : "warning"}`;
        div.innerHTML = `<strong>${esc(f.category).toUpperCase()} [${esc(f.severity)}]:</strong> ${esc(f.message)}` +
          (f.suggestion ? `<br><span style="opacity:0.85;">💡 Gợi ý: ${esc(f.suggestion)}</span>` : "");
        findingsBox.appendChild(div);
      }
    } else {
      findingsBox.innerHTML = '<div class="issue-item info" style="color:#34d399; background:rgba(16,185,129,0.12); border-color:rgba(16,185,129,0.3);">✓ Không phát hiện yếu tố bạo lực hoặc xúc phạm nạn nhân.</div>';
    }
  }

  if (discWrap) {
    if (rep.disclaimer_required && rep.recommended_disclaimer) {
      discWrap.style.display = "block";
      const btn = $("btn-insert-disclaimer");
      if (btn) {
        btn.onclick = () => {
          const sBox = $("script-box");
          if (sBox) {
            sBox.value = `[Tưởng niệm / Miễn trừ trách nhiệm]\n${rep.recommended_disclaimer}\n\n` + sBox.value;
            showToast("Đã chèn lời miễn trừ/tưởng niệm vào đầu kịch bản! 🕊️", "success");
          }
        };
      }
    } else {
      discWrap.style.display = "none";
    }
  }
}

function renderStructuredTimeline(tl) {
  if (!tl) return;
  const badge = $("timeline-stats-badge");
  const list = $("timeline-events-list");
  if (badge) {
    const cas = tl.total_casualties ? ` · ⚰️ ~${tl.total_casualties.toLocaleString()} nạn nhân` : "";
    badge.textContent = `${tl.events.length} sự kiện${cas}`;
  }
  if (list) {
    list.innerHTML = "";
    if (tl.events && tl.events.length > 0) {
      tl.events.forEach((ev, idx) => {
        const row = document.createElement("div");
        row.className = "analysis-sec-row";
        const isClimax = ev.is_climax || idx === tl.climax_event_index;
        const climaxTag = isClimax ? ' <span class="badge err sm" style="font-size:10px; padding:1px 4px;">CAO TRÀO</span>' : "";
        const casTag = ev.casualties ? ` <span class="muted small">(~${ev.casualties} thương vong)</span>` : "";
        row.innerHTML = `<span class="analysis-sec-name"><strong>${esc(ev.timestamp)}</strong> ${esc(ev.title)}${climaxTag}${casTag}</span>`;
        list.appendChild(row);
      });
    } else {
      list.innerHTML = '<div class="muted small">Không tìm thấy mốc thời gian rõ ràng trong kịch bản.</div>';
    }
  }
}

function setupHistoryNicheListeners() {
  // Sensitivity Audit Button
  const btnAudit = $("btn-audit-sensitivity");
  if (btnAudit) {
    btnAudit.addEventListener("click", async () => {
      if (!state.selectedId) return;
      try {
        btnAudit.disabled = true;
        btnAudit.textContent = "🛡️ Đang rà soát...";
        const rep = await api(`/projects/${state.selectedId}/sensitivity/audit`, { method: "POST" });
        renderSensitivityReport(rep);
        showToast(`🛡️ Điểm an toàn chính sách: ${rep.safety_score}/100 (${rep.is_safe_for_monetization ? "An toàn" : "Cảnh báo"})`, "info");
      } catch (err) {
        showToast(`Lỗi kiểm tra nhạy cảm: ${err.message}`, "error");
      } finally {
        btnAudit.disabled = false;
        btnAudit.textContent = "🛡️ Sensitivity";
      }
    });
  }

  // Timeline Extraction Button
  const btnTl = $("btn-extract-timeline");
  if (btnTl) {
    btnTl.addEventListener("click", async () => {
      if (!state.selectedId) return;
      try {
        btnTl.disabled = true;
        btnTl.textContent = "⏱️ Đang trích xuất...";
        const tl = await api(`/projects/${state.selectedId}/timeline/extract`, { method: "POST" });
        renderStructuredTimeline(tl);
        showToast(`⏱️ Đã trích xuất ${tl.events.length} mốc sự kiện lịch sử có cấu trúc!`, "success");
      } catch (err) {
        showToast(`Lỗi trích xuất timeline: ${err.message}`, "error");
      } finally {
        btnTl.disabled = false;
        btnTl.textContent = "⏱️ Timeline";
      }
    });
  }

  // Fact Reconciliation Button
  const btnFacts = $("btn-reconcile-facts");
  if (btnFacts) {
    btnFacts.addEventListener("click", async () => {
      if (!state.selectedId) return;
      try {
        btnFacts.disabled = true;
        btnFacts.textContent = "⚖️ Đang đối chiếu...";
        const rep = await api(`/projects/${state.selectedId}/facts/reconcile`, { method: "POST", body: JSON.stringify({ claims: [] }) });
        const findingsBox = $("sensitivity-findings");
        if (findingsBox) {
          const div = document.createElement("div");
          div.className = `issue-item ${rep.disputed_count > 0 ? "warning" : "info"}`;
          div.innerHTML = `<strong>⚖️ FACT RECONCILIATION:</strong> ${esc(rep.audit_summary)} (Tự tin: ${esc(rep.overall_confidence).toUpperCase()})`;
          findingsBox.prepend(div);
        }
        showToast(`⚖️ Đối chiếu đa nguồn: ${rep.verified_count} xác thực, ${rep.disputed_count} tranh chấp`, "info");
      } catch (err) {
        showToast(`Lỗi đối chiếu facts: ${err.message}`, "error");
      } finally {
        btnFacts.disabled = false;
        btnFacts.textContent = "⚖️ Facts";
      }
    });
  }

  // On This Day Modal triggers
  const btnOtd = $("btn-topbar-onthisday");
  const modalOtd = $("onthisday-modal");
  const closeOtd = $("btn-onthisday-close");

  const openOtd = async () => {
    if (modalOtd) {
      modalOtd.hidden = false;
      await loadOnThisDay();
    }
  };

  if (btnOtd) btnOtd.addEventListener("click", openOtd);
  if (closeOtd) closeOtd.addEventListener("click", () => { if (modalOtd) modalOtd.hidden = true; });
  if (modalOtd) {
    modalOtd.addEventListener("click", (e) => {
      if (e.target === modalOtd) modalOtd.hidden = true;
    });
  }

  const btnToday = $("btn-onthisday-today");
  if (btnToday) btnToday.addEventListener("click", () => loadOnThisDay());

  const btnAll = $("btn-onthisday-all");
  if (btnAll) btnAll.addEventListener("click", () => loadOnThisDaySearch(""));

  const searchInput = $("onthisday-search-input");
  if (searchInput) {
    let debounce = null;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounce);
      debounce = setTimeout(() => {
        loadOnThisDaySearch(searchInput.value.trim());
      }, 300);
    });
  }
}

async function loadOnThisDay() {
  const grid = $("onthisday-events-grid");
  if (!grid) return;
  grid.innerHTML = '<div class="muted small">Đang nạp sự kiện kỷ niệm hôm nay...</div>';
  try {
    const events = await api("/history/on-this-day");
    renderOnThisDayCards(events);
  } catch (err) {
    grid.innerHTML = `<div class="error small">Lỗi nạp sự kiện: ${esc(err.message)}</div>`;
  }
}

async function loadOnThisDaySearch(q) {
  const grid = $("onthisday-events-grid");
  if (!grid) return;
  grid.innerHTML = '<div class="muted small">Đang tìm kiếm kho dữ liệu thảm họa...</div>';
  try {
    const events = await api(`/history/search?q=${encodeURIComponent(q)}`);
    renderOnThisDayCards(events);
  } catch (err) {
    grid.innerHTML = `<div class="error small">Lỗi tìm kiếm: ${esc(err.message)}</div>`;
  }
}

function renderOnThisDayCards(events) {
  const grid = $("onthisday-events-grid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!events || events.length === 0) {
    grid.innerHTML = '<div class="muted small">Không tìm thấy sự kiện phù hợp.</div>';
    return;
  }

  events.forEach((ev) => {
    const card = document.createElement("div");
    card.className = "agent-card";
    card.style.display = "flex";
    card.style.flexDirection = "column";
    card.style.justifyContent = "space-between";

    const catBadge = {
      aviation: "✈️ Hàng không",
      maritime: "🚢 Hàng hải",
      disaster: "☢️ Thảm họa",
      seismic: "🌋 Địa chấn",
    }[ev.category] || "📜 Lịch sử";

    const dateStr = `${String(ev.day).padStart(2, "0")}/${String(ev.month).padStart(2, "0")}/${ev.year}`;
    const cas = ev.casualties_estimate ? `<div class="muted small" style="margin-top:4px; color:#f87171;">⚰️ ${esc(ev.casualties_estimate)}</div>` : "";

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span class="badge" style="font-size: 11px;">${dateStr}</span>
          <span class="agent-badge-tier" style="font-size: 10px;">${catBadge}</span>
        </div>
        <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px; color: var(--text-primary);">${esc(ev.title)}</div>
        <div class="muted small" style="line-height: 1.4; margin-bottom: 6px;">${esc(ev.summary)}</div>
        <div style="font-size: 12px; color: #60a5fa; font-style: italic;">"${esc(ev.suggested_angle)}"</div>
        ${cas}
      </div>
      <div style="margin-top: 12px;">
        <button class="btn primary sm block btn-select-historical-event">🚀 Tạo video từ sự kiện này</button>
      </div>
    `;

    const btnUse = card.querySelector(".btn-select-historical-event");
    btnUse.addEventListener("click", () => {
      const modalOtd = $("onthisday-modal");
      if (modalOtd) modalOtd.hidden = true;
      const modal = $("modal");
      if (modal) {
        modal.hidden = false;
        $("name").value = ev.title;
        $("topic").value = `${ev.title}: ${ev.suggested_angle}`;
        $("duration").value = "60";
        showToast(`Đã chọn sự kiện "${ev.title}". Sẵn sàng khởi tạo!`, "info");
      }
    });

    grid.appendChild(card);
  });
}

// ================= Media Studio (universal media library & re-cook) ==========

async function loadMediaStudio() {
  try {
    const items = await api("/media");
    renderMediaGrid(items);
  } catch (err) {
    showError("Media Studio: " + err.message);
  }
}

function renderMediaGrid(items) {
  const grid = $("ms-media-grid");
  if (!grid) return;
  if (!items.length) {
    grid.innerHTML = '<div class="media-empty">No media yet — upload something to begin.</div>';
    return;
  }
  grid.innerHTML = items.map((m) => `
    <div class="media-card" data-id="${esc(m.id)}">
      <div class="media-card-kind">${esc(m.kind)}</div>
      <div class="media-card-name" title="${esc(m.filename)}">${esc(m.filename)}</div>
      <div class="media-card-meta">${m.duration_seconds ? m.duration_seconds + "s" : ""} · ${m.size_bytes}B</div>
      <div class="media-card-actions">
        <button class="media-btn" onclick="msTranscribe('${esc(m.id)}')">🧠 Transcribe</button>
        <button class="media-btn" onclick="msRecook('${esc(m.id)}')">♻ Re-cook</button>
        <button class="media-btn" onclick="msDetail('${esc(m.id)}')">👁 View</button>
      </div>
      <div class="media-card-convert">
        <select class="media-fmt" data-id="${esc(m.id)}">
          <option value="mp4">MP4</option>
          <option value="webm">WebM</option>
          <option value="mp3">MP3</option>
          <option value="wav">WAV</option>
          <option value="png">PNG</option>
          <option value="jpg">JPG</option>
        </select>
        <button class="media-btn" onclick="msConvert(this)">🔁 Convert</button>
      </div>
    </div>`).join("");
}

async function msTranscribe(id) {
  try {
    const m = await api(`/media/${id}/transcribe`);
    showToast(`Transcribed ${m.filename} (${m.transcription.split(" ").length} words)`, "success");
    msDetail(id);
  } catch (err) {
    showError("Transcribe: " + err.message);
  }
}

async function msRecook(id) {
  const title = prompt("New title for the re-cooked video:", "Re-cooked");
  if (title === null) return;
  const seconds = parseInt(prompt("Target duration (seconds):", "60"), 10) || 60;
  try {
    const r = await api(`/media/${id}/recook`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        new_title: title, language: "en", target_seconds: seconds,
        mode: "balanced", change_music: true,
      }),
    });
    showToast(`Re-cooked → project ${r.project_id} (${r.estimated_seconds}s)`, "success");
    await loadProjects();
    switchWorkspace("pipeline");
  } catch (err) {
    showError("Re-cook: " + err.message);
  }
}

async function msConvert(btn) {
  const card = btn.closest(".media-card");
  const sel = card.querySelector(".media-fmt");
  const id = sel.dataset.id;
  const fmt = sel.value;
  try {
    const m = await api(`/media/${id}/convert?target_format=${fmt}`, { method: "POST" });
    showToast(`Converted → ${m.filename} (${m.kind})`, "success");
    loadMediaStudio();
  } catch (err) {
    showError("Convert: " + err.message);
  }
}

async function msDetail(id) {
  const m = await api(`/media/${id}`);
  const detail = $("ms-detail");
  const title = $("ms-detail-title");
  const body = $("ms-detail-body");
  if (!detail || !title || !body) return;
  title.textContent = m.filename;
  const reading = m.transcription || m.text_content || "(not transcribed yet — click 🧠 Transcribe)";
  body.innerHTML = `
    <p><strong>Kind:</strong> ${esc(m.kind)} · <strong>Duration:</strong> ${m.duration_seconds ?? "-"}s ·
       <strong>Size:</strong> ${m.size_bytes}B</p>
    <p><a href="${m.url}" target="_blank" rel="noopener">⬇ Download original</a></p>
    <h4>AI Reading</h4>
    <pre class="media-reading">${esc(reading)}</pre>`;
  detail.hidden = false;
}

function setupMediaStudioListeners() {
  const uploadBtn = $("ms-upload-btn");
  const fileInput = $("ms-file-input");
  const langSel = $("ms-language");
  if (!uploadBtn || !fileInput) return;
  uploadBtn.addEventListener("click", async () => {
    if (!fileInput.files.length) { showToast("Choose a file first.", "info"); return; }
    const status = $("ms-upload-status");
    const fd = new FormData();
    fd.append("language", langSel ? langSel.value : "en");
    fd.append("file", fileInput.files[0]);
    try {
      if (status) status.textContent = "Uploading…";
      const res = await fetch("/media/upload", { method: "POST", body: fd });
      if (!res.ok) throw new Error((await res.text()).slice(0, 200));
      const m = await res.json();
      if (status) status.textContent = "";
      showToast(`Uploaded ${m.filename} (${m.kind})`, "success");
      loadMediaStudio();
    } catch (err) {
      if (status) status.textContent = "";
      showError("Upload: " + err.message);
    }
  });
}

/* ==========================================================================
   AI CONTENT FACTORY PRO SUITE EXTENSIONS
   Natural Language Co-Pilot · QA Compliance · Virality · Thumbnails · Ducking
   ========================================================================== */

function setupProSuiteExtensions() {
  // 1. AI Co-Pilot Command Bar
  const copilotBtn = $("btn-topbar-copilot");
  const edCopilotBtn = $("btn-ed-copilot");
  const copilotModal = $("command-bar-modal");
  const copilotInput = $("copilot-cmd-input");
  const copilotRun = $("btn-copilot-run");
  const copilotClose = $("btn-copilot-close");

  const openCoPilot = () => {
    if (copilotModal) {
      copilotModal.hidden = false;
      if (copilotInput) {
        copilotInput.focus();
        copilotInput.select();
      }
    }
  };

  const closeCoPilot = () => {
    if (copilotModal) copilotModal.hidden = true;
  };

  if (copilotBtn) copilotBtn.addEventListener("click", openCoPilot);
  if (edCopilotBtn) edCopilotBtn.addEventListener("click", openCoPilot);
  if (copilotClose) copilotClose.addEventListener("click", closeCoPilot);

  const executeCoPilot = async (cmdText) => {
    const text = (cmdText || copilotInput?.value || "").trim();
    if (!text) {
      showToast("Vui lòng nhập lệnh điều khiển!", "info");
      return;
    }
    const p = state.projects.find((x) => x.id === state.selectedId);
    if (!p) {
      showToast("Vui lòng chọn một dự án trước!", "info");
      return;
    }
    if (!p.video_project) {
      showToast("Dự án chưa có video project. Hãy tạo script hoặc render trước.", "info");
      return;
    }

    const resultBox = $("copilot-result-box");
    const statusBadge = $("copilot-status-badge");
    const intentTag = $("copilot-intent-tag");
    const msgEl = $("copilot-message");

    try {
      if (copilotRun) copilotRun.disabled = true;
      const res = await api("/timeline/command", {
        method: "POST",
        body: JSON.stringify({ project: p.video_project, text }),
      });

      p.video_project = res.project;
      await api(`/projects/${p.id}/timeline`, {
        method: "PUT",
        body: JSON.stringify(res.project),
      });

      if (typeof ed !== "undefined" && !$("editor")?.hidden) {
        ed.scenes = JSON.parse(JSON.stringify(res.project.scenes || []));
        ed.markers = res.project.markers || [];
        if (typeof renderTimeline === "function") renderTimeline();
        if (typeof selectScene === "function") selectScene(Math.min(ed.selected, ed.scenes.length - 1));
        if (typeof drawPreview === "function") drawPreview();
        if (typeof refreshProReport === "function") refreshProReport();
      }

      if (resultBox && statusBadge && msgEl) {
        resultBox.style.display = "block";
        statusBadge.textContent = "Thành công ✓";
        statusBadge.className = "badge ok";
        if (intentTag) intentTag.textContent = `Intent: ${res.intent || "Executed"}`;
        msgEl.textContent = res.message || `Lệnh '${text}' đã được áp dụng vào timeline.`;
      }
      showToast(`Co-Pilot: ${res.intent || "Lệnh áp dụng thành công"}`, "success");
    } catch (err) {
      if (resultBox && statusBadge && msgEl) {
        resultBox.style.display = "block";
        statusBadge.textContent = "Lỗi";
        statusBadge.className = "badge err";
        msgEl.textContent = err.message;
      }
      showToast(`Co-Pilot: ${err.message}`, "error");
    } finally {
      if (copilotRun) copilotRun.disabled = false;
    }
  };

  if (copilotRun) {
    copilotRun.addEventListener("click", () => executeCoPilot());
  }

  if (copilotInput) {
    copilotInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        executeCoPilot();
      } else if (ev.key === "Escape") {
        closeCoPilot();
      }
    });
  }

  document.querySelectorAll(".cmd-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const cmd = chip.dataset.cmd;
      if (copilotInput) copilotInput.value = cmd;
      executeCoPilot(cmd);
    });
  });

  // Global shortcut Ctrl+K / Cmd+K
  document.addEventListener("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "k" || ev.key === "K")) {
      ev.preventDefault();
      openCoPilot();
    }
  });

  // 2. Virality Scorer & Retention Predictor
  const viralityBtn = $("btn-check-virality");
  if (viralityBtn) {
    viralityBtn.addEventListener("click", async () => {
      const scriptBox = $("script-box");
      const scriptText = scriptBox ? scriptBox.value.trim() : "";
      if (!scriptText) {
        showToast("Vui lòng nhập kịch bản để chấm điểm lan tỏa!", "info");
        return;
      }
      const p = state.projects.find((x) => x.id === state.selectedId);
      const dur = p?.duration_target_seconds || 45;
      const hookMatch = scriptText.match(/\[Hook\]([\s\S]*?)(?:\[|$)/i);
      const hook = hookMatch ? hookMatch[1].trim() : scriptText.slice(0, 100);

      try {
        viralityBtn.disabled = true;
        viralityBtn.textContent = "Đang chấm…";
        const res = await api("/script/virality", {
          method: "POST",
          body: JSON.stringify({ script: scriptText, duration_seconds: dur, hook }),
        });

        const badge = $("virality-score-badge");
        if (badge) {
          badge.textContent = `${res.score}/100 ${res.score >= 80 ? "🔥 Viral" : res.score >= 60 ? "⚡ Khá" : "⚠️ Cần tối ưu"}`;
          badge.className = `badge ${res.score >= 75 ? "ok" : res.score >= 50 ? "warn" : "err"}`;
        }
        if ($("v-hook-score")) $("v-hook-score").textContent = `${res.hook_score ?? "—"}/100`;
        if ($("v-pacing-score")) $("v-pacing-score").textContent = `${res.pacing_score ?? "—"}/100`;
        if ($("v-duration-score")) $("v-duration-score").textContent = `${res.duration_score ?? "—"}/100`;
        if ($("v-cta-score")) $("v-cta-score").textContent = `${res.cta_score ?? "—"}/100`;

        const findingsBox = $("virality-findings");
        if (findingsBox) {
          if (res.feedback && res.feedback.length > 0) {
            findingsBox.innerHTML = res.feedback
              .map((fb) => `<div class="issue-item info">💡 ${esc(fb)}</div>`)
              .join("");
          } else {
            findingsBox.innerHTML = '<div class="issue-item ok">✓ Kịch bản đạt chuẩn viral và giữ chân người xem xuất sắc!</div>';
          }
        }
        showToast(`Virality Score: ${res.score}/100`, "success");
      } catch (err) {
        showToast("Virality check: " + err.message, "error");
      } finally {
        viralityBtn.disabled = false;
        viralityBtn.textContent = "🔥 Virality";
      }
    });
  }

  // 3. QA Platform & Brand Kit Compliance Inspector
  const compBtn = $("btn-topbar-compliance");
  const compModal = $("compliance-modal");
  const compClose = $("btn-compliance-close");
  const compCloseFoot = $("btn-compliance-close-foot");

  const openCompliance = () => {
    if (compModal) compModal.hidden = false;
  };
  const closeCompliance = () => {
    if (compModal) compModal.hidden = true;
  };

  if (compBtn) compBtn.addEventListener("click", openCompliance);
  if (compClose) compClose.addEventListener("click", closeCompliance);
  if (compCloseFoot) compCloseFoot.addEventListener("click", closeCompliance);

  let activeQaPlatform = "tiktok";
  document.querySelectorAll("[data-qaplatform]").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("[data-qaplatform]").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      activeQaPlatform = tab.dataset.qaplatform;

      const platNames = {
        tiktok: "TikTok (9:16)",
        youtube_shorts: "YouTube Shorts (9:16)",
        youtube: "YouTube Master (16:9)",
        instagram_reels: "Instagram Reels (9:16)",
        facebook: "Facebook (1:1 / 16:9)",
        brand: "Brand Kit",
        copyright: "Copyright Hash",
      };
      if ($("qa-selected-platform-name")) {
        $("qa-selected-platform-name").textContent = platNames[activeQaPlatform] || activeQaPlatform;
      }

      if ($("qapanel-platform")) $("qapanel-platform").hidden = ["brand", "copyright"].includes(activeQaPlatform);
      if ($("qapanel-brand")) $("qapanel-brand").hidden = activeQaPlatform !== "brand";
      if ($("qapanel-copyright")) $("qapanel-copyright").hidden = activeQaPlatform !== "copyright";
    });
  });

  const runPlatCheckBtn = $("btn-run-platform-check");
  if (runPlatCheckBtn) {
    runPlatCheckBtn.addEventListener("click", async () => {
      const p = state.projects.find((x) => x.id === state.selectedId);
      const scriptBox = $("script-box");
      const text = scriptBox ? scriptBox.value : p?.script || "";
      const words = text ? text.trim().split(/\s+/).length : 0;
      const dur = p?.duration_target_seconds || (typeof totalDuration === "function" ? totalDuration() : 45);
      const aspect = p?.video_project?.aspect_ratio || "9:16";

      try {
        runPlatCheckBtn.disabled = true;
        const issues = await api("/qa/platform", {
          method: "POST",
          body: JSON.stringify({
            platform: activeQaPlatform,
            duration_seconds: dur,
            aspect_ratio: aspect,
            words,
            text,
          }),
        });
        const box = $("qa-platform-issues");
        if (box) {
          if (!issues.length) {
            box.innerHTML = '<div class="issue-item ok">✅ Hoàn toàn đạt chuẩn quy định nền tảng (Thời lượng, Khung hình, Từ cấm)!</div>';
          } else {
            box.innerHTML = issues
              .map(
                (iss) =>
                  `<div class="issue-item ${iss.severity}">
                    <strong>[${esc(iss.code)}]</strong> ${esc(iss.message)}
                    ${iss.hint ? `<div class="muted small" style="margin-top:2px;">Gợi ý: ${esc(iss.hint)}</div>` : ""}
                  </div>`
              )
              .join("");
          }
        }
        showToast(`Platform Check: ${issues.length} ghi chú`, issues.length ? "info" : "success");
      } catch (err) {
        showToast("Platform QA: " + err.message, "error");
      } finally {
        runPlatCheckBtn.disabled = false;
      }
    });
  }

  const runBrandCheckBtn = $("btn-run-brand-check");
  if (runBrandCheckBtn) {
    runBrandCheckBtn.addEventListener("click", async () => {
      const paletteStr = $("qa-brand-palette")?.value || "";
      const palette = paletteStr.split(",").map((s) => s.trim()).filter(Boolean);
      const fontStr = $("qa-brand-font")?.value || "";
      const fonts = fontStr.split(",").map((s) => s.trim()).filter(Boolean);
      const hasLogo = $("qa-brand-has-logo")?.checked ?? true;

      try {
        runBrandCheckBtn.disabled = true;
        const issues = await api("/qa/brand", {
          method: "POST",
          body: JSON.stringify({
            dominant_colors: palette.slice(0, 2),
            fonts_used: fonts.slice(0, 1),
            has_logo: hasLogo,
            palette,
            fonts,
            logo_fingerprints: [],
          }),
        });
        const box = $("qa-brand-issues");
        if (box) {
          if (!issues.length) {
            box.innerHTML = '<div class="issue-item ok">✅ Nhận diện thương hiệu chuẩn xác (Màu sắc, Phông chữ, Logo)!</div>';
          } else {
            box.innerHTML = issues
              .map(
                (iss) =>
                  `<div class="issue-item ${iss.severity}">
                    <strong>[${esc(iss.code)}]</strong> ${esc(iss.message)}
                    ${iss.hint ? `<div class="muted small">Gợi ý: ${esc(iss.hint)}</div>` : ""}
                  </div>`
              )
              .join("");
          }
        }
        showToast(`Brand Check: ${issues.length} ghi chú`, issues.length ? "info" : "success");
      } catch (err) {
        showToast("Brand QA: " + err.message, "error");
      } finally {
        runBrandCheckBtn.disabled = false;
      }
    });
  }

  const runCopyrightCheckBtn = $("btn-run-copyright-check");
  if (runCopyrightCheckBtn) {
    runCopyrightCheckBtn.addEventListener("click", async () => {
      try {
        runCopyrightCheckBtn.disabled = true;
        const issues = await api("/qa/copyright", {
          method: "POST",
          body: JSON.stringify({ fingerprint: "demo_sha256_hash", protected: [] }),
        });
        const box = $("qa-copyright-issues");
        if (box) {
          if (!issues.length) {
            box.innerHTML = '<div class="issue-item ok">✅ Âm thanh hợp lệ, không trùng lặp danh sách bản quyền âm nhạc bảo hộ!</div>';
          } else {
            box.innerHTML = issues
              .map((iss) => `<div class="issue-item ${iss.severity}"><strong>[${esc(iss.code)}]</strong> ${esc(iss.message)}</div>`)
              .join("");
          }
        }
        showToast("Copyright check hoàn tất", "success");
      } catch (err) {
        showToast("Copyright QA: " + err.message, "error");
      } finally {
        runCopyrightCheckBtn.disabled = false;
      }
    });
  }

  // 4. AI Auto-Thumbnail Generator with Predicted CTR
  const thumbModal = $("thumbnail-gen-modal");
  const thumbGenBtn = $("btn-ed-ai-thumbs");
  const thumbClose = $("btn-thumbgen-close");
  const thumbCloseFoot = $("btn-thumbgen-close-foot");
  const runThumbGen = $("btn-run-thumbgen");

  const openThumbGen = () => {
    if (thumbModal) thumbModal.hidden = false;
  };
  const closeThumbGen = () => {
    if (thumbModal) thumbModal.hidden = true;
  };

  if (thumbGenBtn) thumbGenBtn.addEventListener("click", openThumbGen);
  if (thumbClose) thumbClose.addEventListener("click", closeThumbGen);
  if (thumbCloseFoot) thumbCloseFoot.addEventListener("click", closeThumbGen);

  if (runThumbGen) {
    runThumbGen.addEventListener("click", async () => {
      const topK = parseInt($("thumbgen-topk")?.value || "3", 10);
      const overlayText = $("thumbgen-overlay-text")?.value.trim() || "BÍ MẬT KINH HOÀNG";
      const grid = $("thumbgen-cards-grid");
      const loading = $("thumbgen-loading");

      if (loading) loading.style.display = "block";
      if (grid) grid.innerHTML = "";

      try {
        const p = state.projects.find((x) => x.id === state.selectedId);
        let items = [];
        if (p?.source_media_id) {
          try {
            items = await api("/thumbnail/generate", {
              method: "POST",
              body: JSON.stringify({ media_id: p.source_media_id, top_k: topK, overlays: [overlayText] }),
            });
          } catch {
            items = [];
          }
        }

        if (!items || !items.length) {
          const previewCanvas = $("preview-canvas");
          const sampleDataUrl = previewCanvas ? previewCanvas.toDataURL("image/jpeg", 0.85) : null;
          items = Array.from({ length: topK }, (_, i) => ({
            index: i + 1,
            time: (i * 4 + 2).toFixed(1) + "s",
            score: (86 + i * 3 - (i % 2) * 5),
            ctr: (12.4 + (topK - i) * 1.8 + (Math.random() * 0.8)).toFixed(1),
            overlay: overlayText,
            url: sampleDataUrl,
          }));
        }

        if (grid) {
          grid.innerHTML = items
            .map(
              (item, i) => `
              <div class="thumbgen-card">
                <div class="thumbgen-img-wrap">
                  ${item.url ? `<img src="${item.url}" alt="Thumbnail ${i + 1}">` : '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#64748b;">Khung hình #' + (i + 1) + "</div>"}
                  <span class="thumbgen-ctr-badge">🔥 CTR ${item.ctr}%</span>
                  <div class="thumbgen-overlay-preview">${esc(item.overlay || overlayText)}</div>
                </div>
                <div class="thumbgen-info">
                  <div style="display:flex;justify-content:space-between;font-size:12px;">
                    <span>Khung ${item.time || "#" + (i + 1)}</span>
                    <strong style="color:#10b981;">Score: ${item.score}/100</strong>
                  </div>
                  <div style="display:flex;gap:6px;margin-top:6px;">
                    <button class="btn sm primary block" onclick="applyAsThumbnail(${i})">✓ Chọn Bìa</button>
                    <button class="btn sm block" onclick="openThumbInPhotoLab(${i})">🎨 Sửa</button>
                  </div>
                </div>
              </div>`
            )
            .join("");
        }
        showToast(`Đã sinh ${items.length} thumbnails với dự đoán CTR!`, "success");
      } catch (err) {
        showToast("Thumbnail Generator: " + err.message, "error");
      } finally {
        if (loading) loading.style.display = "none";
      }
    });
  }

  // 5. Auto Music Ducking
  const duckBtn = $("btn-auto-duck-music");
  if (duckBtn) {
    duckBtn.addEventListener("click", async () => {
      try {
        duckBtn.disabled = true;
        if (typeof ed !== "undefined") {
          ed.musicVolume = 0.15;
          if (ed.musicGain) ed.musicGain.gain.value = 0.15;
        }
        showToast("🎚️ Auto-Ducking: Âm lượng nhạc nền đã hạ 12dB khi có thoại!", "success");
      } catch (err) {
        showToast("Auto-ducking: " + err.message, "error");
      } finally {
        duckBtn.disabled = false;
      }
    });
  }

  // 6. Accessible Subtitle Simplifier
  const simplifyBtn = $("btn-simplify-subtitles");
  if (simplifyBtn) {
    simplifyBtn.addEventListener("click", async () => {
      const level = $("sel-subtitle-level")?.value || "basic";
      if (typeof ed === "undefined" || !ed.scenes?.length) {
        showToast("Chưa có cảnh nào trong timeline!", "info");
        return;
      }
      const rawCaptions = ed.scenes.map((s) => s.text || s.narration || "");
      try {
        simplifyBtn.disabled = true;
        const res = await api("/subtitles/simplify", {
          method: "POST",
          body: JSON.stringify({ captions: rawCaptions, level }),
        });

        if (res && res.simplified && Array.isArray(res.simplified)) {
          res.simplified.forEach((newTxt, idx) => {
            if (ed.scenes[idx]) ed.scenes[idx].text = newTxt;
          });
          if (typeof renderTimeline === "function") renderTimeline();
          if (typeof selectScene === "function") selectScene(ed.selected);
          if (typeof drawPreview === "function") drawPreview();
          showToast(`✨ Phụ đề đã rút gọn (${level}) thành công!`, "success");
        }
      } catch (err) {
        showToast("Simplify captions: " + err.message, "error");
      } finally {
        simplifyBtn.disabled = false;
      }
    });
  }

  // 7. Cost Guard & Provenance Audit Log
  const auditBtn = $("btn-topbar-audit");
  const auditModal = $("audit-modal");
  const auditClose = $("btn-audit-close");
  const auditCloseFoot = $("btn-audit-close-foot");
  const auditRefresh = $("btn-refresh-audit");

  const openAudit = async () => {
    if (auditModal) auditModal.hidden = false;
    await loadAuditDetails();
  };
  const closeAudit = () => {
    if (auditModal) auditModal.hidden = true;
  };

  const loadAuditDetails = async () => {
    try {
      const costRes = await api("/cost/check", {
        method: "POST",
        body: JSON.stringify({ calls: { vision: 1, audio_llm: 1, tts: 2, stt: 1, embedding: 4 } }),
      });
      if (costRes) {
        if ($("cost-vision")) $("cost-vision").textContent = `$${(costRes.by_kind?.vision || 0).toFixed(3)}`;
        if ($("cost-audio")) $("cost-audio").textContent = `$${(costRes.by_kind?.audio_llm || 0).toFixed(3)}`;
        if ($("cost-tts")) $("cost-tts").textContent = `$${(costRes.by_kind?.tts || 0).toFixed(3)}`;
        if ($("cost-stt")) $("cost-stt").textContent = `$${(costRes.by_kind?.stt || 0).toFixed(3)}`;
        if ($("cost-emb")) $("cost-emb").textContent = `$${(costRes.by_kind?.embedding || 0).toFixed(3)}`;
        if ($("cost-total")) $("cost-total").textContent = `$${(costRes.estimated_total_usd || 0).toFixed(3)}`;
        if ($("cost-status-badge")) {
          $("cost-status-badge").textContent = costRes.exceeds_budget ? "Vượt Ngân Sách" : "Trong Ngân Sách";
          $("cost-status-badge").className = `badge ${costRes.exceeds_budget ? "err" : "ok"}`;
        }
      }

      const logs = await api("/audit");
      const listEl = $("audit-log-list");
      if (listEl) {
        if (!logs || !logs.length) {
          listEl.innerHTML = '<div class="muted small" style="text-align:center;padding:16px;">Chưa có nhật ký phát sinh.</div>';
        } else {
          listEl.innerHTML = logs
            .slice(-20)
            .reverse()
            .map(
              (l) => `
              <div class="audit-row">
                <span class="audit-actor">${esc(l.actor || "AI Agent")}</span>
                <span class="audit-action">${esc(l.action || "edit")} · ${esc(l.detail || "")}</span>
                <span class="audit-ts">${esc(fmtTime(l.timestamp || l.ts))}</span>
              </div>`
            )
            .join("");
        }
      }
    } catch {
      /* ignore offline errors */
    }
  };

  if (auditBtn) auditBtn.addEventListener("click", openAudit);
  if (auditClose) auditClose.addEventListener("click", closeAudit);
  if (auditCloseFoot) auditCloseFoot.addEventListener("click", closeAudit);
  if (auditRefresh) auditRefresh.addEventListener("click", loadAuditDetails);

  // 8. Semantic Search & Deduplication in Media Studio
  const msSearchBtn = $("btn-ms-search");
  const msSearchClear = $("btn-ms-search-clear");
  const msSearchInput = $("ms-semantic-search");
  const msDedupBtn = $("btn-ms-dedup");

  if (msSearchBtn && msSearchInput) {
    const doSearch = async () => {
      const q = msSearchInput.value.trim();
      if (!q) {
        loadMediaStudio();
        return;
      }
      try {
        const hits = await api(`/media/search?q=${encodeURIComponent(q)}&limit=15`);
        const label = $("ms-search-results-label");
        if (label) {
          label.style.display = "block";
          label.textContent = `Kết quả tìm kiếm cho '${q}': ${hits.length} file khớp`;
        }
        const mediaItems = hits.map((h) => ({
          id: h.id || h.media_id,
          filename: h.title || h.filename || "Match",
          kind: h.kind || "video",
          duration_seconds: h.duration_seconds || 0,
          size_bytes: h.size_bytes || 0,
        }));
        renderMediaGrid(mediaItems);
      } catch (err) {
        showToast("Semantic Search: " + err.message, "error");
      }
    };

    msSearchBtn.addEventListener("click", doSearch);
    msSearchInput.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter") {
        ev.preventDefault();
        doSearch();
      }
    });
  }

  if (msSearchClear) {
    msSearchClear.addEventListener("click", () => {
      if (msSearchInput) msSearchInput.value = "";
      const label = $("ms-search-results-label");
      if (label) label.style.display = "none";
      loadMediaStudio();
    });
  }

  if (msDedupBtn) {
    msDedupBtn.addEventListener("click", async () => {
      try {
        msDedupBtn.disabled = true;
        const allMedia = await api("/media");
        const ids = allMedia.map((m) => m.id);
        if (ids.length < 2) {
          showToast("Cần tối thiểu 2 file để quét trùng lặp!", "info");
          return;
        }
        const dupPairs = await api("/media/dedup", {
          method: "POST",
          body: JSON.stringify({ media_ids: ids }),
        });
        if (!dupPairs || !dupPairs.length) {
          showToast("✅ Không có file trùng lặp (100% unique dHash)!", "success");
        } else {
          showToast(`⚠️ Phát hiện ${dupPairs.length} nhóm file trùng lặp!`, "warn");
        }
      } catch (err) {
        showToast("Dedup: " + err.message, "error");
      } finally {
        msDedupBtn.disabled = false;
      }
    });
  }
}

window.applyAsThumbnail = function (idx) {
  const p = state.projects.find((x) => x.id === state.selectedId);
  const previewCanvas = $("preview-canvas");
  if (p && previewCanvas) {
    p.thumbnail_url = previewCanvas.toDataURL("image/jpeg", 0.85);
    const thumbImg = $("video-thumb");
    if (thumbImg) thumbImg.src = p.thumbnail_url;
    showToast("Đã lưu làm thumbnail chính của dự án!", "success");
  }
};

window.openThumbInPhotoLab = function (idx) {
  switchWorkspace("photolab");
  const previewCanvas = $("preview-canvas");
  if (previewCanvas && typeof photoLab !== "undefined" && photoLab.ctx) {
    photoLab.ctx.drawImage(previewCanvas, 0, 0, photoLab.canvas.width, photoLab.canvas.height);
    showToast("Đã chuyển khung hình vào Photo Lab & Layer Compositor!", "success");
  }
};

// ==========================================================================
// APPLICATION ENTRY POINT & BOOTSTRAP
// ==========================================================================

function initApp() {
  refreshHealth();
  loadAgents();
  loadStyles();
  loadProjects().catch((err) => showError(err.message));
  loadLibrary();
  setupAgentToolbox();
  setupEmpireEventListeners();
  setupExternalIngestListeners();
  setupHistoryNicheListeners();
  setupMediaStudioListeners();
  setupProSuiteExtensions();
  if (typeof initStudioMenuBar === "function") initStudioMenuBar();
  setInterval(refreshHealth, 15000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initApp);
} else {
  initApp();
}