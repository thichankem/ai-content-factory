"use strict";

const state = { projects: [], selectedId: null, pollTimer: null, activeTab: "sources" };

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const isForm = options.body instanceof FormData;
  const res = await fetch(path, {
    ...(isForm ? {} : { headers: { "Content-Type": "application/json" } }),
    ...options,
  });
  let body = null;
  try {
    body = await res.json();
  } catch {
    /* no JSON body */
  }
  if (!res.ok) {
    const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
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
  return status.replace(/_/g, " ");
}

// ---------- health ----------

async function refreshHealth() {
  try {
    const h = await api("/health");
    const badge = $("health");
    badge.textContent = `${h.status} · v${h.version}`;
    badge.className = `badge ${h.status === "ok" ? "ok" : "err"}`;
  } catch {
    const badge = $("health");
    badge.textContent = "offline";
    badge.className = "badge err";
  }
}

// ---------- projects ----------

async function loadProjects() {
  state.projects = await api("/projects");
  renderSidebar();
  if (state.selectedId) {
    const found = state.projects.find((p) => p.id === state.selectedId);
    if (found) renderProject(found);
  }
}

function renderSidebar() {
  const box = $("projects");
  box.innerHTML = "";
  if (state.projects.length === 0) {
    box.innerHTML = '<div class="muted small" style="padding:8px;">No projects yet.</div>';
    return;
  }
  for (const p of state.projects) {
    const item = document.createElement("div");
    item.className = `project-item${p.id === state.selectedId ? " active" : ""}`;
    const info = document.createElement("div");
    info.className = "pi-info";
    const name = document.createElement("div");
    name.className = "pi-name";
    name.textContent = p.name;
    const topic = document.createElement("div");
    topic.className = "pi-topic";
    topic.textContent = p.topic;
    info.append(name, topic);
    item.append(info, statusBadge(p.status));
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

// ---------- project rendering ----------

function renderProject(p) {
  $("empty-state").hidden = true;
  $("notebook").hidden = false;
  $("inspector-empty").hidden = true;
  $("inspector-content").hidden = false;

  $("nb-title").textContent = p.name;
  $("nb-subtitle").textContent = p.topic;

  renderInspector(p);
  renderSources(p);
  renderFacts(p);
  renderScript(p);
  renderAttachedDocs(p);
  schedulePolling(p);
  renderSidebar();
}

function renderInspector(p) {
  const badge = $("status-badge");
  badge.className = `status ${p.status}`;
  badge.textContent = statusLabel(p.status);

  $("detail-meta").innerHTML =
    `<div>Language<strong>${esc(p.target_language)}</strong></div>` +
    `<div>Duration<strong>${p.duration_target_seconds}s</strong></div>` +
    `<div>Provider<strong>${esc(p.provider_used || "—")}</strong></div>` +
    `<div>Created<strong>${fmtTime(p.created_at)}</strong></div>` +
    `<div>Updated<strong>${fmtTime(p.updated_at)}</strong></div>` +
    (p.published_at ? `<div>Published<strong>${fmtTime(p.published_at)}</strong></div>` : "") +
    (p.platforms.length ? `<div>Platforms<strong>${esc(p.platforms.join(", "))}</strong></div>` : "");

  $("btn-approve-script").disabled = p.status !== "script_review";

  const canStart = ["script_approved", "failed", "video_review"].includes(p.status);
  $("btn-start").disabled = !canStart;
  $("btn-start").textContent =
    p.status === "failed" ? "Retry generation"
    : p.status === "video_review" ? "Re-render"
    : "Start generation";

  const hasVideo = !!p.video;
  $("video-card").hidden = !hasVideo;
  if (hasVideo) {
    $("video-thumb").src = p.video.thumbnail_url;
    $("video-meta").textContent =
      `${p.video.format.toUpperCase()} · ${p.video.duration_seconds}s · ` +
      `${Math.round((p.video.size_bytes || 0) / 1e6)} MB`;
  }
  const editableVideo = ["generating", "video_review", "video_approved"].includes(p.status) && !!p.video_project;
  $("btn-open-editor").hidden = !editableVideo;

  const reviewing = p.status === "video_review";
  $("btn-approve-video").disabled = !reviewing;
  $("btn-reject-video").disabled = !reviewing;
  $("btn-publish").disabled = p.status !== "video_approved";

  const generating = p.status === "generating";
  $("progress-wrap").hidden = !generating;
  if (generating) {
    $("progress-bar").style.width = `${p.progress ?? 0}%`;
    $("progress-label").textContent = `Rendering video… ${p.progress ?? 0}%`;
  }

  const published = p.status === "published";
  $("published-box").hidden = !published;
  if (published) {
    $("published-box").textContent =
      `Published to ${p.platforms.join(", ")} on ${fmtTime(p.published_at)}.`;
  }

  const failed = p.status === "failed";
  $("error-box").hidden = !failed;
  if (failed) {
    $("error-box").textContent = `Production failed: ${p.error || "unknown error"}`;
  }

  const approvals = $("approvals");
  approvals.innerHTML = "";
  if (p.approvals.length === 0) {
    approvals.innerHTML = '<div class="muted small">No review decisions yet.</div>';
  } else {
    for (const a of p.approvals) {
      const div = document.createElement("div");
      div.className = "approval-item";
      const verdict = document.createElement("span");
      verdict.className = `verdict ${a.verdict}`;
      verdict.textContent = a.verdict;
      div.append(
        `${a.stage} · `,
        verdict,
        ` · ${fmtTime(a.created_at)}`,
        a.comment ? ` — ${esc(a.comment)}` : ""
      );
      approvals.appendChild(div);
    }
  }
  hideError();
}

function renderScript(p) {
  $("script-box").value = p.script || "";
  $("rights-box").checked = !!p.source_rights_confirmed;
  const editable = p.status === "draft" || p.status === "script_review";
  $("script-box").disabled = !editable;
  $("rights-box").disabled = !editable;
  $("btn-save").disabled = !editable;
  $("btn-generate").disabled = !editable;
}

function renderSources(p) {
  const statusEl = $("research-status");
  const sourcesEl = $("sources");
  sourcesEl.innerHTML = "";
  $("btn-research").disabled = !["draft", "script_review"].includes(p.status);

  if (!p.research || p.research.sources.length === 0) {
    statusEl.textContent =
      "No research yet. Run research or generate a script to gather reference sources.";
    return;
  }
  statusEl.textContent =
    `${p.research.sources.length} sources gathered · ${fmtTime(p.research.generated_at)}` +
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
    relevance.textContent = `${Math.round(source.relevance * 100)}%`;
    head.append(chevron, info, type, relevance);

    const body = document.createElement("div");
    body.className = "source-body";
    if (source.highlights.length) {
      const h4 = document.createElement("h4");
      h4.textContent = "Highlights";
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
  if (!p.research || p.research.key_facts.length === 0) {
    box.innerHTML = '<div class="muted small">No key facts yet — run research first.</div>';
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
  if (p.documents.length === 0) {
    box.innerHTML = '<div class="muted small">No documents attached.</div>';
    return;
  }
  for (const doc of p.documents) {
    const div = document.createElement("div");
    div.className = "attached-item";
    div.innerHTML = `<strong>${esc(doc.title)}</strong> · ${esc(doc.source)}` +
      (doc.doi ? ` · doi:${esc(doc.doi)}` : "") +
      (doc.url ? ` · <a href="${esc(doc.url)}" target="_blank" rel="noopener">link</a>` : "");
    box.appendChild(div);
  }
}

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
      } catch {
        /* transient — keep polling */
      }
    }, 700);
  }
}

// ---------- tabs ----------

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

// ---------- errors ----------

function showError(message) {
  const el = $("error");
  el.textContent = message;
  el.hidden = false;
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

// ---------- modal ----------

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
  });
});

// ---------- notebook actions ----------

$("btn-research").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/research?web=true`, { method: "POST" });
    await loadProjects();
    renderProject(p);
  })
);

$("btn-generate").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/script/generate`, { method: "POST" });
    await loadProjects();
    renderProject(p);
    switchTab("script");
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
  })
);

$("btn-approve-script").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "script", verdict: "approved", comment: "Approved via UI" }),
    });
    await loadProjects();
    renderProject(p);
  })
);

$("btn-start").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/generate`, { method: "POST" });
    await loadProjects();
    renderProject(p);
  })
);

$("btn-approve-video").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "video", verdict: "approved", comment: "Approved via UI" }),
    });
    await loadProjects();
    renderProject(p);
  })
);

$("btn-reject-video").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/approvals`, {
      method: "POST",
      body: JSON.stringify({ stage: "video", verdict: "rejected", comment: "Rejected via UI" }),
    });
    await loadProjects();
    renderProject(p);
  })
);

$("btn-publish").addEventListener("click", () =>
  run(async () => {
    const p = await api(`/projects/${state.selectedId}/publish`, {
      method: "POST",
      body: JSON.stringify({ platforms: ["youtube"] }),
    });
    await loadProjects();
    renderProject(p);
  })
);

// ---------- document explorer ----------

async function searchDocuments(query) {
  const box = $("doc-results");
  box.innerHTML = '<div class="muted small">Searching federated sources…</div>';
  const results = await api(`/documents/search?q=${encodeURIComponent(query)}&limit=10`);
  box.innerHTML = "";
  if (!results.length) {
    box.innerHTML = '<div class="muted small">No results found.</div>';
    return;
  }
  for (const r of results) {
    const card = document.createElement("div");
    card.className = "doc-card";
    const authors = (r.authors || []).slice(0, 4).join(", ") + (r.authors.length > 4 ? " et al." : "");
    const year = r.year ? ` (${r.year})` : "";
    const oa = r.is_open_access ? ' <span class="source-badge oa">Open Access</span>' : "";
    const citations = r.citations != null ? ` · ${r.citations} citations` : "";
    const links = [];
    if (r.landing_url) links.push(`<a href="${esc(r.landing_url)}" target="_blank" rel="noopener">landing</a>`);
    if (r.pdf_url) links.push(`<a href="${esc(r.pdf_url)}" target="_blank" rel="noopener">pdf</a>`);
    card.innerHTML =
      `<div class="doc-title">${esc(r.title)}</div>` +
      `<div class="doc-meta">${esc(authors)}${year} · ` +
      `<span class="source-badge">${esc(r.source)}</span>${oa}${citations}` +
      (r.venue ? ` · ${esc(r.venue)}` : "") + `</div>` +
      (r.abstract ? `<div class="doc-abstract">${esc(r.abstract.slice(0, 300))}${r.abstract.length > 300 ? "…" : ""}</div>` : "") +
      `<div class="doc-foot"><span class="doc-links">${links.join(" · ")}</span>` +
      `<button class="btn" data-add="${r.id}">Download &amp; add</button></div>`;
    card.querySelector(`[data-add="${r.id}"]`).addEventListener("click", () =>
      run(async () => {
        const p = await api(`/projects/${state.selectedId}/documents`, {
          method: "POST",
          body: JSON.stringify(r),
        });
        await loadProjects();
        renderProject(p);
        loadLibrary();
      })
    );
    box.appendChild(card);
  }
}

async function searchLibrary(query) {
  const box = $("lib-hits");
  box.innerHTML = '<div class="muted small">Searching library…</div>';
  const hits = await api(`/library/search?q=${encodeURIComponent(query)}&limit=20`);
  box.innerHTML = "";
  if (!hits.length) {
    box.innerHTML = '<div class="muted small">No matches in the library.</div>';
    return;
  }
  for (const hit of hits) {
    const div = document.createElement("div");
    div.className = "lib-hit";
    const snippet = esc(hit.snippet).replace(/\[\[/g, "<b>").replace(/\]\]/g, "</b>");
    div.innerHTML =
      `<div class="hit-title">${esc(hit.title)}</div>` +
      `<div class="hit-snippet">${snippet}</div>` +
      `<div class="hit-meta">${esc(hit.path)} · page ${hit.page} · score ${hit.score.toFixed(3)}</div>`;
    box.appendChild(div);
  }
}

async function loadLibrary() {
  try {
    const data = await api("/library");
    const stats = data.stats;
    $("lib-stats").textContent =
      `${stats.documents} documents · ${stats.pages} pages · ` +
      `${(stats.size_bytes / 1024).toFixed(0)} KB (${stats.fts5 ? "BM25" : "LIKE"})`;
  } catch {
    $("lib-stats").textContent = "Library unavailable.";
  }
}

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

// ---------- init ----------

refreshHealth();
loadProjects().catch((err) => showError(err.message));
loadLibrary();
setInterval(refreshHealth, 15000);