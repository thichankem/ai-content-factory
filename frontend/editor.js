"use strict";

/* Video editor engine: multitrack timeline, keyframe-style animations,
   transitions library, filters, text styles, undo/redo, and real export. */

const ed = {
  scenes: [],
  selected: 0,
  playing: false,
  t: 0,
  raf: null,
  lastTs: 0,
  W: 480,
  H: 854,
  fps: 30,
  captions: true,
  music: false,
  musicVolume: 0,
  quality: "high",
  aspect: "9:16",
  bpm: 120,
  undoStack: [],
  redoStack: [],
  dirty: false,
  voiceover: null,
  audioCtx: null,
  audioDest: null,
  audioEl: null,
  audioSrc: null,
  audioScene: -1,
  musicSrc: null,
  musicGain: null,
};

const ED = {
  WIPE_DURATION: 0.45,
};

const FILTERS = {
  none: "none",
  grayscale: "grayscale(1)",
  sepia: "sepia(1)",
  invert: "invert(1)",
  blur: "blur(6px)",
  warm: "sepia(0.35) saturate(1.5)",
  cool: "hue-rotate(180deg) saturate(1.3)",
  contrast: "contrast(1.45)",
  brightness: "brightness(1.35)",
};

function canvasSize(aspect) {
  const [w, h] = aspect.split(":").map(Number);
  const maxW = 480;
  const maxH = 840;
  let W = maxW;
  let H = Math.round((maxW * h) / w);
  if (H > maxH) {
    H = maxH;
    W = Math.round((maxH * w) / h);
  }
  return { W, H };
}

function totalDuration() {
  return ed.scenes.reduce((sum, s) => sum + s.duration_seconds, 0);
}

function fmtClock(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

function sceneAt(t) {
  let acc = 0;
  for (let i = 0; i < ed.scenes.length; i++) {
    const dur = ed.scenes[i].duration_seconds;
    if (t < acc + dur) return { index: i, local: t - acc };
    acc += dur;
  }
  return { index: ed.scenes.length - 1, local: ed.scenes[ed.scenes.length - 1].duration_seconds };
}

// ---------- open / close ----------

async function openEditor() {
  const project = state.projects.find((p) => p.id === state.selectedId);
  if (!project || !project.video_project) {
    showError("No video project yet — run generation first.");
    return;
  }
  const vp = project.video_project;
  ed.scenes = JSON.parse(JSON.stringify(vp.scenes || []));
  ed.aspect = vp.aspect_ratio || "9:16";
  ed.fps = vp.fps || 30;
  ed.captions = vp.captions !== false;
  ed.music = !!vp.background_music;
  ed.musicVolume = vp.music_volume || 0;
  ed.quality = vp.export_quality || "high";
  ed.bpm = vp.bpm || 120;
  ed.selected = 0;
  ed.t = 0;
  ed.undoStack = [];
  ed.redoStack = [];
  ed.dirty = false;
  ed.voiceover = project.voiceover || null;
  ed.audioScene = -1;

  $("ed-aspect").value = ed.aspect;
  $("ed-fps").value = String(ed.fps);
  $("ed-quality").value = ed.quality;
  $("prop-bpm").value = ed.bpm;
  $("prop-bpm-val").textContent = ed.bpm;
  $("prop-captions").checked = ed.captions;
  $("prop-music").checked = ed.music;

  setupAudio();
  resizeCanvas();
  renderTimeline();
  selectScene(0);
  $("editor").hidden = false;
  setEdStatus(ed.voiceover ? `Voiceover ready (${ed.voiceover.engine})` : "Editing");
  pausePlayback();
}

function setupAudio() {
  if (ed.audioCtx) return;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    ed.audioCtx = new AC();
    ed.audioDest = ed.audioCtx.createMediaStreamDestination();
    ed.audioEl = new Audio();
    ed.audioEl.crossOrigin = "anonymous";
    ed.audioSrc = ed.audioCtx.createMediaElementSource(ed.audioEl);
    ed.audioSrc.connect(ed.audioDest);
  } catch (err) {
    ed.audioCtx = null;
  }
}

function buildBeatBuffer(bpm, seconds) {
  const sr = ed.audioCtx.sampleRate;
  const beat = 60 / bpm;
  const total = Math.max(beat, Math.ceil(seconds / beat) * beat);
  const buf = ed.audioCtx.createBuffer(1, Math.ceil(total * sr), sr);
  const data = buf.getChannelData(0);
  for (let t = 0; t < total; t += beat) {
    const kickLen = 0.055 * sr;
    for (let i = 0; i < kickLen; i++) {
      const idx = Math.round((t + i / sr) * sr);
      if (idx < data.length) {
        const env = Math.exp(-i / (sr * 0.035));
        data[idx] += Math.sin(2 * Math.PI * 60 * (i / sr)) * env * 0.5;
      }
    }
    const hat = t + beat / 2;
    const hatLen = 0.028 * sr;
    for (let i = 0; i < hatLen; i++) {
      const idx = Math.round((hat + i / sr) * sr);
      if (idx < data.length) {
        data[idx] += (Math.random() * 2 - 1) * 0.12 * (1 - i / hatLen);
      }
    }
  }
  return buf;
}

function startMusic() {
  if (!ed.music || !ed.audioCtx || ed.musicSrc) return;
  try {
    const buf = buildBeatBuffer(ed.bpm, totalDuration());
    const src = ed.audioCtx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const gain = ed.audioCtx.createGain();
    gain.gain.value = ed.musicVolume || 0.25;
    src.connect(gain);
    gain.connect(ed.audioDest);
    src.start(0);
    ed.musicSrc = src;
    ed.musicGain = gain;
  } catch (err) {
    ed.musicSrc = null;
  }
}

function stopMusic() {
  if (ed.musicSrc) {
    try { ed.musicSrc.stop(); } catch (err) { /* noop */ }
    try { ed.musicSrc.disconnect(); } catch (err) { /* noop */ }
    ed.musicSrc = null;
  }
}

function updatePlaybackAudio(index, forcePlay) {
  if (!ed.audioEl) return;
  if (index === ed.audioScene && !forcePlay) return;
  ed.audioScene = index;
  const track = ed.voiceover?.tracks?.find((t) => t.scene_id === ed.scenes[index]?.id);
  if (track && (forcePlay || ed.playing)) {
    if (ed.audioEl.src !== track.audio_url) ed.audioEl.src = track.audio_url;
    ed.audioEl.play().catch(() => {});
  } else {
    ed.audioEl.pause();
  }
}

async function generateVoiceover() {
  setEdStatus("Generating voiceover…");
  await api(`/projects/${state.selectedId}/voiceover/generate`, { method: "POST" });
  for (let i = 0; i < 180; i++) {
    await new Promise((r) => setTimeout(r, 1000));
    const p = await api(`/projects/${state.selectedId}`);
    if (p.voiceover) {
      ed.scenes = JSON.parse(JSON.stringify(p.video_project.scenes));
      ed.voiceover = p.voiceover;
      ed.audioScene = -1;
      renderTimeline();
      selectScene(ed.selected);
      setEdStatus(`Voiceover ready (${p.voiceover.engine}) — durations synced`);
      return;
    }
    if (p.error && p.error.includes("Voiceover")) {
      setEdStatus("Voiceover failed: " + p.error);
      return;
    }
  }
  setEdStatus("Voiceover generation timed out");
}

function closeEditor() {
  pausePlayback();
  $("editor").hidden = true;
}

// ---------- AI assist ----------

async function aiAutoEdit() {
  pushHistory();
  setEdStatus("✨ AI is editing…");
  const p = await api(`/projects/${state.selectedId}/video-project/ai-assist`, {
    method: "POST",
    body: JSON.stringify({ fit: true, beat: false, bpm: ed.bpm }),
  });
  ed.scenes = JSON.parse(JSON.stringify(p.video_project.scenes));
  renderTimeline();
  selectScene(ed.selected);
  setEdStatus("✨ AI auto-edit applied (durations, looks, text)");
}

async function aiBeatSync() {
  pushHistory();
  const p = await api(`/projects/${state.selectedId}/video-project/ai-assist`, {
    method: "POST",
    body: JSON.stringify({ fit: false, beat: true, bpm: ed.bpm }),
  });
  ed.scenes = JSON.parse(JSON.stringify(p.video_project.scenes));
  renderTimeline();
  selectScene(ed.selected);
  setEdStatus(`🎵 Scenes snapped to ${ed.bpm} BPM grid`);
}

async function aiSuggestLook() {
  const sc = ed.scenes[ed.selected];
  if (!sc) return;
  setEdStatus("💡 Asking the AI…");
  const s = await api(`/projects/${state.selectedId}/video-project/scenes/${sc.id}/suggest`);
  pushHistory();
  sc.filter = s.filter;
  sc.effect = s.effect;
  sc.grade = s.grade;
  sc.transition = s.transition;
  renderTimeline();
  selectScene(ed.selected);
  setEdStatus(`💡 Suggested: ${s.filter || "no filter"} · ${s.effect || "no effect"} · ${s.grade || "no grade"} · ${s.transition}`);
}

async function aiPolishText() {
  const sc = ed.scenes[ed.selected];
  if (!sc) return;
  setEdStatus("✨ Polishing text…");
  const p = await api(`/projects/${state.selectedId}/video-project/scenes/${sc.id}/polish`, {
    method: "POST",
  });
  ed.scenes = JSON.parse(JSON.stringify(p.video_project.scenes));
  renderTimeline();
  selectScene(ed.selected);
  setEdStatus("✨ Text polished");
}

function aiCaptions() {
  ed.captions = true;
  $("prop-captions").checked = true;
  ed.dirty = true;
  renderTimeline();
  drawFrame(ed.t);
  setEdStatus("📝 Captions on — shown from scene text/narration");
}

function resizeCanvas() {
  const size = canvasSize(ed.aspect);
  ed.W = size.W;
  ed.H = size.H;
  const canvas = $("preview-canvas");
  canvas.width = ed.W;
  canvas.height = ed.H;
  const frame = $("canvas-frame");
  frame.style.width = `${ed.W}px`;
  frame.style.height = `${ed.H}px`;
  drawFrame(ed.t);
}

// ---------- undo / redo ----------

function pushHistory() {
  ed.undoStack.push(JSON.stringify(ed.scenes));
  if (ed.undoStack.length > 50) ed.undoStack.shift();
  ed.redoStack = [];
  ed.dirty = true;
  setEdStatus("Unsaved changes");
}

function undo() {
  if (!ed.undoStack.length) return;
  ed.redoStack.push(JSON.stringify(ed.scenes));
  ed.scenes = JSON.parse(ed.undoStack.pop());
  if (ed.selected >= ed.scenes.length) ed.selected = ed.scenes.length - 1;
  renderTimeline();
  selectScene(ed.selected);
  drawFrame(ed.t);
  setEdStatus("Undone");
}

function redo() {
  if (!ed.redoStack.length) return;
  ed.undoStack.push(JSON.stringify(ed.scenes));
  ed.scenes = JSON.parse(ed.redoStack.pop());
  if (ed.selected >= ed.scenes.length) ed.selected = ed.scenes.length - 1;
  renderTimeline();
  selectScene(ed.selected);
  drawFrame(ed.t);
  setEdStatus("Redone");
}

// ---------- timeline ----------

function renderTimeline() {
  const tl = $("timeline");
  const tlText = $("timeline-text");
  const tlMusic = $("timeline-music");
  tl.innerHTML = "";
  tlText.innerHTML = "";
  tlMusic.innerHTML = "";

  ed.scenes.forEach((sc, i) => {
    const seg = document.createElement("div");
    seg.className = `tl-seg${i === ed.selected ? " active" : ""}`;
    seg.style.flexGrow = sc.duration_seconds;
    seg.innerHTML = `<div class="tl-label">${esc(sc.label || "Scene " + (i + 1))}</div>` +
      `<div class="tl-dur">${sc.duration_seconds}s${sc.speed !== 1 ? " · " + sc.speed + "x" : ""}</div>`;
    seg.addEventListener("click", () => selectScene(i));
    tl.appendChild(seg);

    const textSeg = document.createElement("div");
    textSeg.className = `tl-seg${i === ed.selected ? " active" : ""}`;
    textSeg.style.flexGrow = sc.duration_seconds;
    textSeg.innerHTML = `<div class="tl-label">${esc((sc.text || "Text").slice(0, 18))}</div>`;
    textSeg.addEventListener("click", () => selectScene(i));
    tlText.appendChild(textSeg);

    const musicSeg = document.createElement("div");
    musicSeg.className = `tl-seg${i === ed.selected ? " active" : ""}`;
    musicSeg.style.flexGrow = sc.duration_seconds;
    musicSeg.innerHTML = `<div class="tl-label">${ed.music ? "♪ music" : "—"}</div>`;
    musicSeg.addEventListener("click", () => selectScene(i));
    tlMusic.appendChild(musicSeg);
  });
}

function selectScene(i) {
  if (i < 0 || i >= ed.scenes.length) return;
  ed.selected = i;
  const sc = ed.scenes[i];
  $("prop-text").value = sc.text || "";
  $("prop-duration").value = sc.duration_seconds;
  $("prop-duration-val").textContent = sc.duration_seconds + "s";
  $("prop-speed").value = sc.speed || 1;
  $("prop-speed-val").textContent = (sc.speed || 1) + "x";
  $("prop-bg").value = typeof sc.background === "string" && sc.background.startsWith("#") ? sc.background : "#1a1d27";
  $("prop-color").value = sc.text_color || "#ffffff";
  $("prop-transition").value = sc.transition || "fade";
  $("prop-position").value = sc.text_position || "center";
  $("prop-style").value = sc.text_style || "normal";
  $("prop-font").value = sc.font_size || 44;
  $("prop-font-val").textContent = sc.font_size || 44;
  $("prop-filter").value = sc.filter || "none";
  $("prop-kenburns").value = sc.ken_burns || "none";
  $("prop-entrance").value = sc.entrance || "fade";
  $("prop-exit").value = sc.exit || "none";
  $("prop-effect").value = sc.effect || "none";
  $("prop-grade").value = sc.grade || "none";
  const m = sc.motion || {};
  $("prop-scale").value = m.scale ?? 1;
  $("prop-scale-val").textContent = m.scale ?? 1;
  $("prop-rot").value = m.rotation ?? 0;
  $("prop-rot-val").textContent = (m.rotation ?? 0) + "°";
  $("prop-opacity").value = m.opacity ?? 1;
  $("prop-opacity-val").textContent = Math.round((m.opacity ?? 1) * 100) + "%";
  $("prop-posx").value = m.pos_x ?? 0;
  $("prop-posx-val").textContent = m.pos_x ?? 0;
  $("prop-posy").value = m.pos_y ?? 0;
  $("prop-posy-val").textContent = m.pos_y ?? 0;
  $("prop-easing").value = m.easing || "ease-in-out";
  $("prop-overlay-emoji").value = sc.overlay_emoji || "";
  $("prop-overlay-pos").value = sc.overlay_pos || "top-right";
  $("prop-overlay-size").value = sc.overlay_size || 48;
  $("prop-overlay-size-val").textContent = sc.overlay_size || 48;
  $("prop-pitch").value = sc.pitch || 1;
  $("prop-pitch-val").textContent = (sc.pitch || 1) + "x";
  renderTimeline();
  drawFrame(ed.t);
}

function motionOrDefault(sc) {
  return sc.motion || { scale: 1, rotation: 0, opacity: 1, pos_x: 0, pos_y: 0, easing: "ease-in-out" };
}

function applyProps() {
  const sc = ed.scenes[ed.selected];
  if (!sc) return;
  sc.text = $("prop-text").value;
  sc.duration_seconds = parseFloat($("prop-duration").value);
  sc.speed = parseFloat($("prop-speed").value);
  sc.background = $("prop-bg").value;
  sc.text_color = $("prop-color").value;
  sc.transition = $("prop-transition").value;
  sc.text_position = $("prop-position").value;
  sc.text_style = $("prop-style").value;
  sc.font_size = parseInt($("prop-font").value, 10);
  sc.filter = $("prop-filter").value;
  sc.ken_burns = $("prop-kenburns").value;
  sc.entrance = $("prop-entrance").value;
  sc.exit = $("prop-exit").value;
  sc.effect = $("prop-effect").value;
  sc.grade = $("prop-grade").value;
  const m = motionOrDefault(sc);
  m.scale = parseFloat($("prop-scale").value);
  m.rotation = parseFloat($("prop-rot").value);
  m.opacity = parseFloat($("prop-opacity").value);
  m.pos_x = parseFloat($("prop-posx").value);
  m.pos_y = parseFloat($("prop-posy").value);
  m.easing = $("prop-easing").value;
  sc.motion = m;
  sc.overlay_emoji = $("prop-overlay-emoji").value.trim() || null;
  sc.overlay_pos = $("prop-overlay-pos").value;
  sc.overlay_size = parseInt($("prop-overlay-size").value, 10);
  sc.pitch = parseFloat($("prop-pitch").value);
  ed.dirty = true;
  renderTimeline();
  drawFrame(ed.t);
}

function addScene() {
  const template = ed.scenes[ed.selected] || {};
  const sc = {
    id: "s" + Date.now().toString(36),
    label: "Scene " + (ed.scenes.length + 1),
    text: "New scene text",
    narration: null,
    duration_seconds: 3,
    speed: 1,
    background: template.background || "#1a1d27",
    image_url: null,
    transition: "fade",
    text_position: "center",
    text_color: "#ffffff",
    font_size: 44,
    text_style: "normal",
    filter: "none",
    ken_burns: "none",
    entrance: "fade",
    exit: "none",
    effect: "none",
    grade: "none",
    motion: null,
    overlay_emoji: null,
    overlay_pos: "top-right",
    overlay_size: 48,
    pitch: 1,
  };
  pushHistory();
  ed.scenes.splice(ed.selected + 1, 0, sc);
  ed.selected += 1;
  renderTimeline();
  selectScene(ed.selected);
}

function duplicateScene() {
  const sc = ed.scenes[ed.selected];
  if (!sc) return;
  pushHistory();
  const copy = JSON.parse(JSON.stringify(sc));
  copy.id = "s" + Date.now().toString(36);
  copy.label = sc.label + " copy";
  ed.scenes.splice(ed.selected + 1, 0, copy);
  ed.selected += 1;
  renderTimeline();
  selectScene(ed.selected);
}

function deleteScene() {
  if (ed.scenes.length <= 1) return;
  pushHistory();
  ed.scenes.splice(ed.selected, 1);
  if (ed.selected >= ed.scenes.length) ed.selected = ed.scenes.length - 1;
  renderTimeline();
  selectScene(ed.selected);
}

// ---------- playback ----------

function play() {
  if (ed.playing) return;
  ed.playing = true;
  ed.lastTs = performance.now();
  $("btn-play").textContent = "❚❚";
  startMusic();
  ed.raf = requestAnimationFrame(loop);
}

function pausePlayback() {
  ed.playing = false;
  if (ed.raf) cancelAnimationFrame(ed.raf);
  ed.raf = null;
  $("btn-play").textContent = "▶";
  stopMusic();
  if (ed.audioEl) ed.audioEl.pause();
}

function loop(ts) {
  const dt = (ts - ed.lastTs) / 1000;
  ed.lastTs = ts;
  ed.t += dt;
  const total = totalDuration();
  if (ed.t >= total) {
    ed.t = 0;
    ed.audioScene = -1;
    pausePlayback();
    drawFrame(0);
    updateSeek();
    return;
  }
  drawFrame(ed.t);
  updatePlaybackAudio(sceneAt(ed.t).index, false);
  updateSeek();
  ed.raf = requestAnimationFrame(loop);
}

function updateSeek() {
  const total = totalDuration();
  $("seek").value = total ? Math.round((ed.t / total) * 1000) : 0;
  $("play-time").textContent = `${fmtClock(ed.t)} / ${fmtClock(total)}`;
}

// ---------- rendering ----------

function drawFrame(t) {
  const ctx = $("preview-canvas").getContext("2d");
  if (!ed.scenes.length) {
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, ed.W, ed.H);
    return;
  }
  const { index, local } = sceneAt(t);
  const sc = ed.scenes[index];
  const prev = index > 0 ? ed.scenes[index - 1] : null;
  drawComposite(ctx, sc, prev, local, sc.duration_seconds, ed.W, ed.H);
}

function drawComposite(ctx, sc, prev, local, dur, W, H) {
  const tr = sc.transition || "cut";
  const td = ED.WIPE_DURATION;
  if (prev && tr !== "cut" && local < td) {
    const p = local / td;
    if (tr === "fade") {
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.save();
      ctx.globalAlpha = p;
      drawContent(ctx, sc, 1, dur, W, H);
      ctx.restore();
    } else if (tr === "slide") {
      ctx.save();
      ctx.translate(-p * W, 0);
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.restore();
      ctx.save();
      ctx.translate((1 - p) * W, 0);
      drawContent(ctx, sc, 1, dur, W, H);
      ctx.restore();
    } else if (tr === "zoom") {
      ctx.save();
      const s1 = 1 + (1 - p) * 0.12;
      ctx.translate(W / 2, H / 2);
      ctx.scale(s1, s1);
      ctx.translate(-W / 2, -H / 2);
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.restore();
      ctx.save();
      const s2 = 0.88 + p * 0.12;
      ctx.translate(W / 2, H / 2);
      ctx.scale(s2, s2);
      ctx.translate(-W / 2, -H / 2);
      drawContent(ctx, sc, 1, dur, W, H);
      ctx.restore();
    } else if (tr === "wipe") {
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, W * p, H);
      ctx.clip();
      drawContent(ctx, sc, 1, dur, W, H);
      ctx.restore();
      ctx.save();
      ctx.beginPath();
      ctx.rect(W * p, 0, W, H);
      ctx.clip();
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.restore();
    } else if (tr === "circle") {
      const r = Math.hypot(W, H) / 2 * p;
      ctx.save();
      ctx.beginPath();
      ctx.arc(W / 2, H / 2, r, 0, Math.PI * 2);
      ctx.clip();
      drawContent(ctx, sc, 1, dur, W, H);
      ctx.restore();
      ctx.save();
      ctx.globalAlpha = 1 - p;
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.restore();
    } else if (tr === "dissolve") {
      drawContent(ctx, sc, p, dur, W, H);
      ctx.save();
      ctx.globalAlpha = 1 - p;
      drawContent(ctx, prev, 1, dur, W, H);
      ctx.restore();
    } else {
      drawContent(ctx, sc, 1, dur, W, H);
    }
  } else {
    drawContent(ctx, sc, 1, dur, W, H);
  }
}

function easingFn(name) {
  switch (name) {
    case "linear": return (t) => t;
    case "ease-in": return (t) => t * t;
    case "ease-out": return (t) => 1 - (1 - t) * (1 - t);
    default: return (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
  }
}

function canvasCopy(ctx, W, H) {
  const off = document.createElement("canvas");
  off.width = W;
  off.height = H;
  off.getContext("2d").drawImage(ctx.canvas, 0, 0);
  return off;
}

function applyGrade(ctx, grade, W, H) {
  if (!grade || grade === "none") return;
  ctx.save();
  if (grade === "teal-orange") {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, "rgba(0,120,130,0.22)");
    g.addColorStop(0.5, "rgba(255,140,40,0.16)");
    g.addColorStop(1, "rgba(255,90,20,0.25)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.filter = "contrast(1.15) saturate(1.25)";
    ctx.fillStyle = "rgba(255,255,255,0.04)";
    ctx.fillRect(0, 0, W, H);
  } else if (grade === "noir") {
    ctx.filter = "grayscale(1) contrast(1.4) brightness(0.95)";
    ctx.fillStyle = "rgba(0,0,0,0.15)";
    ctx.fillRect(0, 0, W, H);
  } else if (grade === "vintage") {
    ctx.filter = "sepia(0.6) contrast(0.95) brightness(1.05)";
    ctx.fillStyle = "rgba(255,220,170,0.15)";
    ctx.fillRect(0, 0, W, H);
  } else if (grade === "cyberpunk") {
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, "rgba(255,0,128,0.25)");
    g.addColorStop(1, "rgba(0,229,255,0.25)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    ctx.filter = "contrast(1.3) saturate(1.6)";
    ctx.fillStyle = "rgba(255,255,255,0.05)";
    ctx.fillRect(0, 0, W, H);
  } else if (grade === "pastel") {
    ctx.filter = "saturate(0.85) brightness(1.12)";
    ctx.fillStyle = "rgba(255,200,220,0.12)";
    ctx.fillRect(0, 0, W, H);
  }
  ctx.restore();
}

function applyScanlines(ctx, W, H) {
  ctx.save();
  ctx.fillStyle = "rgba(0,0,0,0.22)";
  for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 1);
  ctx.restore();
}

function applyFilmGrain(ctx, W, H) {
  ctx.save();
  for (let i = 0; i < 140; i++) {
    ctx.fillStyle = Math.random() > 0.5 ? "rgba(255,255,255,0.09)" : "rgba(0,0,0,0.09)";
    ctx.fillRect(Math.random() * W, Math.random() * H, 1.5, 1.5);
  }
  ctx.restore();
}

function applyOldFilm(ctx, W, H) {
  ctx.save();
  ctx.filter = "sepia(0.55) contrast(1.1)";
  ctx.fillStyle = "rgba(255,230,180,0.12)";
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
  applyFilmGrain(ctx, W, H);
  const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.3, W / 2, H / 2, Math.max(W, H) * 0.75);
  g.addColorStop(0, "rgba(0,0,0,0)");
  g.addColorStop(1, "rgba(0,0,0,0.5)");
  ctx.save();
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);
  ctx.restore();
}

function applyDreamy(ctx, W, H) {
  const off = canvasCopy(ctx, W, H);
  ctx.save();
  ctx.filter = "blur(6px) brightness(1.15) saturate(1.2)";
  ctx.globalAlpha = 0.55;
  ctx.drawImage(off, 0, 0);
  ctx.restore();
}

function applyGlitch(ctx, W, H, p) {
  const off = canvasCopy(ctx, W, H);
  const shift = 8 + Math.sin(p * 977) * 4;
  ctx.save();
  ctx.globalCompositeOperation = "screen";
  ctx.globalAlpha = 0.5;
  ctx.filter = "sepia(1) hue-rotate(-40deg)";
  ctx.drawImage(off, -shift, 0);
  ctx.filter = "hue-rotate(140deg)";
  ctx.drawImage(off, shift, 0);
  ctx.restore();
}

function applyPixelate(ctx, W, H, amount) {
  const off = document.createElement("canvas");
  off.width = Math.max(1, Math.round(W / amount));
  off.height = Math.max(1, Math.round(H / amount));
  const octx = off.getContext("2d");
  octx.drawImage(ctx.canvas, 0, 0, off.width, off.height);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(off, 0, 0, W, H);
  ctx.imageSmoothingEnabled = true;
}

function applyEffect(ctx, sc, p, W, H) {
  const fx = sc.effect || "none";
  if (fx === "scanlines") applyScanlines(ctx, W, H);
  else if (fx === "film-grain") applyFilmGrain(ctx, W, H);
  else if (fx === "old-film") applyOldFilm(ctx, W, H);
  else if (fx === "dreamy") applyDreamy(ctx, W, H);
  else if (fx === "glitch") applyGlitch(ctx, W, H, p);
  else if (fx === "sharpen") {
    ctx.save();
    ctx.filter = "contrast(1.25) saturate(1.15)";
    ctx.fillStyle = "rgba(255,255,255,0.03)";
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
  }
}

function drawOverlay(ctx, sc, W, H) {
  const emoji = sc.overlay_emoji;
  if (!emoji) return;
  const size = (sc.overlay_size || 48) * (W / 480);
  ctx.save();
  ctx.font = `${size}px serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const pad = size * 0.8;
  let x = W / 2;
  let y = H / 2;
  if (sc.overlay_pos === "top-left") { x = pad; y = pad; }
  else if (sc.overlay_pos === "top-right") { x = W - pad; y = pad; }
  else if (sc.overlay_pos === "bottom-left") { x = pad; y = H - pad; }
  else if (sc.overlay_pos === "bottom-right") { x = W - pad; y = H - pad; }
  ctx.globalAlpha = 0.9;
  ctx.fillText(emoji, x, y);
  ctx.restore();
}

function drawCaptions(ctx, sc, W, H) {
  const text = (sc.narration || sc.text || "").trim();
  if (!text) return;
  ctx.save();
  ctx.font = "600 26px Roboto, 'Segoe UI', sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const maxWidth = W * 0.9;
  const lines = wrapText(ctx, text, maxWidth).slice(0, 2);
  const lineH = 34;
  const blockH = lines.length * lineH;
  const y0 = H - 70 - blockH;
  const tw = Math.max(...lines.map((l) => ctx.measureText(l).width)) + 28;
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.beginPath();
  ctx.roundRect(W / 2 - tw / 2, y0 - 10, tw, blockH + 20, 10);
  ctx.fill();
  ctx.fillStyle = "#fff";
  lines.forEach((l, i) => ctx.fillText(l, W / 2, y0 + i * lineH + lineH / 2));
  ctx.restore();
}

function drawContent(ctx, sc, alpha, dur, W, H) {
  const p = Math.min(1, alpha);
  ctx.save();
  ctx.globalAlpha = p;

  // keyframe-style motion animation (neutral → target with easing)
  const m = sc.motion || null;
  if (m) {
    const k = easingFn(m.easing || "ease-in-out")(p);
    const mscale = 1 + (m.scale - 1) * k;
    const mrot = (m.rotation * k) * Math.PI / 180;
    const mop = 1 + (m.opacity - 1) * k;
    const mx = (m.pos_x * k / 100) * W;
    const my = (m.pos_y * k / 100) * H;
    ctx.translate(W / 2 + mx, H / 2 + my);
    ctx.rotate(mrot);
    ctx.scale(mscale, mscale);
    ctx.translate(-W / 2, -H / 2);
    ctx.globalAlpha *= mop;
  }

  // background (oversized so rotation/scale never reveal edges)
  if (typeof sc.background === "string" && sc.background.startsWith("linear-gradient")) {
    const gm = sc.background.match(/linear-gradient\(([^,]+),([^)]+)\)/);
    const g = ctx.createLinearGradient(0, 0, W, H);
    g.addColorStop(0, gm ? gm[1].trim() : "#1a1d27");
    g.addColorStop(1, gm ? gm[2].trim() : "#312e81");
    ctx.fillStyle = g;
  } else {
    ctx.fillStyle = sc.background || "#1a1d27";
  }
  ctx.fillRect(-W * 0.5, -H * 0.5, W * 2, H * 2);

  // ken burns (subtle pan/zoom)
  const kb = sc.ken_burns || "none";
  if (kb !== "none") {
    const scale = 1.06 + 0.08 * (kb === "zoom-in" ? p : kb === "zoom-out" ? 1 - p : 0.5);
    const dx = kb === "pan-left" ? -0.04 * p * W : kb === "pan-right" ? 0.04 * p * W : 0;
    ctx.save();
    ctx.translate(dx, 0);
    ctx.translate(W / 2, H / 2);
    ctx.scale(scale, scale);
    ctx.translate(-W / 2, -H / 2);
    ctx.fillStyle = "rgba(255,255,255,0.015)";
    ctx.fillRect(0, 0, W, H);
    ctx.restore();
  }

  // filter
  const filter = FILTERS[sc.filter] || "none";
  if (filter !== "none") ctx.filter = filter;

  // cinematic color grade
  applyGrade(ctx, sc.grade, W, H);

  // vignette overlay
  if (sc.filter === "vignette") {
    const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.35, W / 2, H / 2, Math.max(W, H) * 0.72);
    g.addColorStop(0, "rgba(0,0,0,0)");
    g.addColorStop(1, "rgba(0,0,0,0.55)");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }

  drawText(ctx, sc, p, dur, W, H);
  drawOverlay(ctx, sc, W, H);
  if (ed.captions) drawCaptions(ctx, sc, W, H);
  ctx.restore();

  // post-process effects that need the full frame
  const fx = sc.effect || "none";
  if (fx === "pixelate") applyPixelate(ctx, W, H, 10);
  else if (fx === "mosaic") applyPixelate(ctx, W, H, 24);
}

function wrapText(ctx, text, maxWidth) {
  const words = String(text || "").split(/\s+/).filter(Boolean);
  const lines = [];
  let line = "";
  for (const word of words) {
    const test = line ? line + " " + word : word;
    if (ctx.measureText(test).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines.length ? lines : [""];
}

function drawText(ctx, sc, p, dur, W, H) {
  const base = Math.round((sc.font_size || 44) * (W / 480));
  const style = sc.text_style || "normal";
  let fontSize = base;
  let fontWeight = 600;
  if (style === "title") {
    fontSize = Math.round(base * 1.25);
    fontWeight = 800;
  } else if (style === "subtitle") {
    fontSize = Math.round(base * 0.85);
    fontWeight = 500;
  } else if (style === "caption") {
    fontSize = Math.round(base * 0.7);
    fontWeight = 500;
  }

  ctx.font = `${fontWeight} ${fontSize}px Roboto, "Segoe UI", sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const maxWidth = W * 0.86;
  const lines = wrapText(ctx, sc.text || "", maxWidth);
  const lineH = fontSize * 1.3;
  const blockH = lines.length * lineH;

  let cy;
  if (sc.text_position === "top") cy = H * 0.2;
  else if (sc.text_position === "bottom") cy = H * 0.8;
  else cy = H / 2;
  const startY = cy - blockH / 2;

  // entrance / exit animation
  let alpha = 1;
  let dy = 0;
  let scale = 1;
  const ent = sc.entrance || "none";
  const ex = sc.exit || "none";
  const prog = p;
  if (ent === "fade") alpha *= Math.min(1, prog / 0.3);
  else if (ent === "slide-up") dy = (1 - Math.min(1, prog / 0.35)) * 40;
  else if (ent === "zoom") scale = Math.max(0.6, 1 - (1 - Math.min(1, prog / 0.35)) * 0.4);
  else if (ent === "bounce") {
    const q = Math.min(1, prog / 0.5);
    scale = 1 + Math.abs(Math.sin(q * Math.PI * 2.2)) * (1 - q) * 0.15;
  } else if (ent === "blur-in") {
    ctx.filter = `blur(${(1 - Math.min(1, prog / 0.4)) * 12}px)`;
  }
  if (ex === "fade") alpha *= Math.min(1, (1 - prog) / 0.3);
  else if (ex === "slide-down") dy = Math.max(0, (prog - 0.7) / 0.3) * 40;
  else if (ex === "zoom") scale *= Math.max(0.6, 1 - Math.max(0, (prog - 0.7) / 0.3) * 0.4);

  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.translate(W / 2, startY + blockH / 2 + dy);
  ctx.scale(scale, scale);
  ctx.translate(-W / 2, -(startY + blockH / 2));

  for (let i = 0; i < lines.length; i++) {
    const y = startY + i * lineH + lineH / 2;
    if (style === "caption") {
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      const tw = ctx.measureText(lines[i]).width + 24;
      const r = 8;
      ctx.beginPath();
      ctx.roundRect(W / 2 - tw / 2, y - lineH / 2 - 4, tw, lineH + 8, r);
      ctx.fill();
    }
    if (style === "neon") {
      ctx.shadowColor = sc.text_color || "#fff";
      ctx.shadowBlur = 18;
    }
    if (style === "shadow") {
      ctx.shadowColor = "rgba(0,0,0,0.7)";
      ctx.shadowBlur = 8;
      ctx.shadowOffsetY = 4;
    }
    if (style === "outline") {
      ctx.lineWidth = Math.max(3, fontSize / 12);
      ctx.strokeStyle = "rgba(0,0,0,0.85)";
      ctx.strokeText(lines[i], W / 2, y);
    }
    ctx.fillStyle = sc.text_color || "#ffffff";
    ctx.fillText(lines[i], W / 2, y);
    ctx.shadowBlur = 0;
    ctx.shadowOffsetY = 0;
  }
  ctx.restore();
}

// ---------- save ----------

async function saveEditor() {
  const project = {
    scenes: ed.scenes,
    aspect_ratio: ed.aspect,
    fps: ed.fps,
    captions: ed.captions,
    background_music: ed.music,
    music_volume: ed.musicVolume,
    export_quality: ed.quality,
    bpm: ed.bpm,
  };
  const p = await api(`/projects/${state.selectedId}/video-project`, {
    method: "PUT",
    body: JSON.stringify({ project }),
  });
  await loadProjects();
  renderProject(p);
  ed.dirty = false;
  setEdStatus("Saved ✓");
}

// ---------- export ----------

async function exportVideo() {
  const canvas = $("preview-canvas");
  const fps = ed.fps;
  const mime = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
    ? "video/webm;codecs=vp9"
    : "video/webm";
  const bits = ed.quality === "low" ? 850_000 : ed.quality === "medium" ? 1_800_000 : 3_500_000;
  const stream = canvas.captureStream(fps);
  if (ed.audioDest) {
    ed.audioDest.stream.getAudioTracks().forEach((track) => stream.addTrack(track));
  }
  const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: bits });
  const chunks = [];
  rec.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data);
  };
  const stopped = new Promise((res) => (rec.onstop = res));

  const total = totalDuration();
  const start = performance.now();
  setEdStatus("Exporting…");
  ed.audioScene = -1;
  startMusic();

  rec.start(100);
  await new Promise((resolve) => {
    const t0 = performance.now();
    const step = () => {
      const elapsed = (performance.now() - t0) / 1000;
      if (elapsed >= total) {
        resolve();
        return;
      }
      ed.t = elapsed;
      drawFrame(ed.t);
      updatePlaybackAudio(sceneAt(ed.t).index, true);
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
  rec.stop();
  await stopped;
  stopMusic();
  if (ed.audioEl) ed.audioEl.pause();
  const encodeMs = performance.now() - start;

  const blob = new Blob(chunks, { type: "video/webm" });
  const form = new FormData();
  form.append("file", blob, "video.webm");
  const p = await api(`/projects/${state.selectedId}/video/upload`, {
    method: "POST",
    body: form,
  });
  await loadProjects();
  renderProject(p);

  const sizeMb = (blob.size / 1e6).toFixed(2);
  const effFps = ((total * fps) / (encodeMs / 1000)).toFixed(1);
  setEdStatus(
    `Exported ✓ ${sizeMb} MB · ${(encodeMs / 1000).toFixed(1)}s encode · ~${effFps} fps effective`
  );
  ed.dirty = false;
}

function setEdStatus(text) {
  $("ed-status").textContent = text;
}

// ---------- wiring ----------

$("btn-ed-open-editor") && $("btn-ed-open-editor").addEventListener("click", openEditor);
$("btn-open-editor").addEventListener("click", openEditor);
$("btn-ed-close").addEventListener("click", closeEditor);
$("btn-ed-save").addEventListener("click", () => run(saveEditor));
$("btn-ed-export").addEventListener("click", () => run(exportVideo));
$("btn-ed-voice").addEventListener("click", () => run(generateVoiceover));
$("btn-ed-undo").addEventListener("click", undo);
$("btn-ed-redo").addEventListener("click", redo);
$("btn-ai-auto").addEventListener("click", () => run(aiAutoEdit));
$("btn-ai-beat").addEventListener("click", () => run(aiBeatSync));
$("btn-ai-suggest").addEventListener("click", () => run(aiSuggestLook));
$("btn-ai-polish").addEventListener("click", () => run(aiPolishText));
$("btn-ai-captions").addEventListener("click", aiCaptions);

$("btn-play").addEventListener("click", () => (ed.playing ? pausePlayback() : play()));
$("seek").addEventListener("input", () => {
  const total = totalDuration();
  ed.t = (parseInt($("seek").value, 10) / 1000) * total;
  drawFrame(ed.t);
});

$("ed-aspect").addEventListener("change", () => {
  ed.aspect = $("ed-aspect").value;
  pushHistory();
  resizeCanvas();
});
$("ed-fps").addEventListener("change", () => (ed.fps = parseInt($("ed-fps").value, 10)));
$("ed-quality").addEventListener("change", () => (ed.quality = $("ed-quality").value));
$("prop-captions").addEventListener("change", () => (ed.captions = $("prop-captions").checked));
$("prop-music").addEventListener("change", () => {
  ed.music = $("prop-music").checked;
  if (ed.music && !ed.musicVolume) ed.musicVolume = 0.25;
  renderTimeline();
});
$("prop-bpm").addEventListener("input", () => {
  ed.bpm = parseInt($("prop-bpm").value, 10);
  $("prop-bpm-val").textContent = ed.bpm;
});

$("prop-text").addEventListener("input", () => { applyProps(); ed.dirty = true; });
$("prop-duration").addEventListener("input", () => {
  $("prop-duration-val").textContent = $("prop-duration").value + "s";
  applyProps();
});
$("prop-speed").addEventListener("input", () => {
  $("prop-speed-val").textContent = $("prop-speed").value + "x";
  applyProps();
});
$("prop-font").addEventListener("input", () => {
  $("prop-font-val").textContent = $("prop-font").value;
  applyProps();
});
["prop-bg", "prop-color", "prop-transition", "prop-position", "prop-style", "prop-filter", "prop-kenburns", "prop-entrance", "prop-exit", "prop-effect", "prop-grade", "prop-easing", "prop-overlay-pos"].forEach((id) => {
  $(id).addEventListener("change", applyProps);
});
$("prop-scale").addEventListener("input", () => {
  $("prop-scale-val").textContent = $("prop-scale").value;
  applyProps();
});
$("prop-rot").addEventListener("input", () => {
  $("prop-rot-val").textContent = $("prop-rot").value + "°";
  applyProps();
});
$("prop-opacity").addEventListener("input", () => {
  $("prop-opacity-val").textContent = Math.round($("prop-opacity").value * 100) + "%";
  applyProps();
});
$("prop-posx").addEventListener("input", () => {
  $("prop-posx-val").textContent = $("prop-posx").value;
  applyProps();
});
$("prop-posy").addEventListener("input", () => {
  $("prop-posy-val").textContent = $("prop-posy").value;
  applyProps();
});
$("prop-overlay-emoji").addEventListener("input", applyProps);
$("prop-overlay-size").addEventListener("input", () => {
  $("prop-overlay-size-val").textContent = $("prop-overlay-size").value;
  applyProps();
});
$("prop-pitch").addEventListener("input", () => {
  $("prop-pitch-val").textContent = $("prop-pitch").value + "x";
  applyProps();
});

$("btn-scene-add").addEventListener("click", addScene);
$("btn-scene-dup").addEventListener("click", duplicateScene);
$("btn-scene-del").addEventListener("click", deleteScene);

document.addEventListener("keydown", (ev) => {
  if ($("editor").hidden) return;
  if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {
    ev.preventDefault();
    ev.shiftKey ? redo() : undo();
  }
  if (ev.code === "Space") {
    ev.preventDefault();
    ed.playing ? pausePlayback() : play();
  }
});