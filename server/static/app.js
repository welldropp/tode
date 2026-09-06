/* tode web UI */
"use strict";

const API = "";   // same origin

// ── state ────────────────────────────────────────────────────────────────────
let _projects     = [];
let _project      = null;   // currently open project
let _frames       = [];     // list of frame objects
let _frameIdx     = 0;      // index into _frames
let _annotations  = { boxes: [], polygons: [], classifications: [] };
let _annType      = "bbox"; // "bbox" | "seg" | "cls"
let _drawing      = false;
let _drawStart    = null;   // {x, y} normalised for bbox
let _polyPts      = [];     // normalised points for polygon-in-progress
let _classNames   = [];     // project class names list

const COLORS = ["#6c63ff","#ff6584","#43d9ad","#f9ca24","#f0932b","#eb4d4b","#6ab04c","#22a6b3"];

// ── helpers ──────────────────────────────────────────────────────────────────
function colorFor(classId) { return COLORS[classId % COLORS.length]; }

function toast(msg, type = "ok") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className   = "show " + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ""; }, 2800);
}

async function api(path, opts = {}) {
  const r = await fetch(API + path, opts);
  if (!r.ok) { const t = await r.text(); throw new Error(t || r.status); }
  const ct = r.headers.get("content-type") || "";
  return ct.includes("application/json") ? r.json() : r;
}

function showView(id) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

function esc(s) {
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function classIdFor(name) {
  const idx = _classNames.indexOf(name);
  if (idx !== -1) return idx;
  _classNames.push(name);
  return _classNames.length - 1;
}

// ── frame counter ─────────────────────────────────────────────────────────────
function updateFrameCounter() {
  const el = document.getElementById("frame-counter");
  if (!el) return;
  if (_frames.length === 0) {
    el.textContent = "Frame 0 / 0";
  } else {
    el.textContent = `Frame ${_frameIdx + 1} / ${_frames.length}`;
  }
}

// ── projects list ─────────────────────────────────────────────────────────────
async function loadProjects() {
  _projects = await api("/api/projects");
  renderProjects();
}

function renderProjects() {
  const grid = document.getElementById("projects-grid");
  grid.innerHTML = "";
  if (!_projects.length) {
    grid.innerHTML = '<p style="color:var(--text2);grid-column:1/-1">No projects yet — click + New Project.</p>';
    return;
  }
  _projects.forEach(p => {
    const card = document.createElement("div");
    card.className = "project-card";
    card.innerHTML = `
      <h3>${esc(p.name)}</h3>
      <p class="meta">${p.frame_count ?? 0} frames &nbsp;&middot;&nbsp; ${esc(p.annotation_type || "detection")}</p>
      <p class="meta">${new Date(p.created_at).toLocaleDateString()}</p>
    `;
    card.addEventListener("click", () => openProject(p));
    grid.appendChild(card);
  });
}

// ── new project modal ─────────────────────────────────────────────────────────
document.getElementById("new-project-btn").addEventListener("click", () => {
  document.getElementById("new-project-modal").classList.add("open");
});
document.getElementById("cancel-new-project").addEventListener("click", () => {
  document.getElementById("new-project-modal").classList.remove("open");
});
document.getElementById("create-project-form").addEventListener("submit", async e => {
  e.preventDefault();
  const name  = document.getElementById("proj-name").value.trim();
  const atype = document.getElementById("proj-type").value;
  const classesRaw = document.getElementById("proj-classes").value.trim();
  const classNames = classesRaw
    ? classesRaw.split(",").map(s => s.trim()).filter(Boolean)
    : [];
  if (!name) return;
  try {
    const p = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, annotation_type: atype, class_names: classNames }),
    });
    _projects.unshift(p);
    renderProjects();
    document.getElementById("new-project-modal").classList.remove("open");
    document.getElementById("proj-name").value = "";
    document.getElementById("proj-classes").value = "";
    toast("Project created");
  } catch (err) { toast(String(err), "err"); }
});

// ── open project ──────────────────────────────────────────────────────────────
async function openProject(p) {
  _project = p;
  _frames  = [];
  _frameIdx = 0;
  _annotations = { boxes: [], polygons: [], classifications: [] };
  _classNames = p.class_names || [];

  document.getElementById("detail-title").textContent = p.name;
  document.getElementById("ann-type-tabs").querySelector('[data-type="bbox"]').click();

  showView("detail-view");
  await loadFrames();
}

async function loadFrames() {
  try {
    _frames = await api(`/api/projects/${_project.id}/frames`);
    renderFrameStrip();
    updateFrameCounter();
    if (_frames.length) await selectFrame(0);
  } catch (err) { toast("Could not load frames: " + err, "err"); }
}

function renderFrameStrip() {
  const strip = document.getElementById("frame-strip");
  strip.innerHTML = "";
  _frames.forEach((f, i) => {
    const img = document.createElement("img");
    img.className = "frame-thumb";
    img.src = `/api/projects/${_project.id}/frames/${f.frame_index}/image`;
    img.title = `Frame ${f.frame_index}`;
    if (i === _frameIdx) img.classList.add("active");
    img.addEventListener("click", () => selectFrame(i));
    strip.appendChild(img);
  });
}

async function selectFrame(i) {
  _frameIdx = i;
  // highlight strip
  document.querySelectorAll(".frame-thumb").forEach((el, j) => {
    el.classList.toggle("active", j === i);
  });
  updateFrameCounter();
  // load annotations
  const f = _frames[i];
  try {
    _annotations = await api(`/api/projects/${_project.id}/frames/${f.frame_index}/annotations`);
  } catch (_) {
    _annotations = { boxes: [], polygons: [], classifications: [] };
  }
  renderCanvas();
  renderAnnList();
}

// ── prev / next frame buttons ─────────────────────────────────────────────────
document.getElementById("prev-frame-btn").addEventListener("click", () => {
  if (_frameIdx > 0) selectFrame(_frameIdx - 1);
});
document.getElementById("next-frame-btn").addEventListener("click", () => {
  if (_frameIdx < _frames.length - 1) selectFrame(_frameIdx + 1);
});

// ── canvas ────────────────────────────────────────────────────────────────────
const canvas = document.getElementById("annotation-canvas");
const ctx    = canvas.getContext("2d");
let _img     = null;

async function renderCanvas() {
  if (!_frames.length) return;
  const f = _frames[_frameIdx];
  const imgEl = new Image();
  imgEl.onload = () => {
    _img = imgEl;
    const container = document.getElementById("canvas-area");
    const maxW = container.clientWidth  - 16;
    const maxH = container.clientHeight - 16;
    const scale = Math.min(1, maxW / imgEl.naturalWidth, maxH / imgEl.naturalHeight);
    canvas.width  = Math.round(imgEl.naturalWidth  * scale);
    canvas.height = Math.round(imgEl.naturalHeight * scale);
    drawAll();
  };
  imgEl.src = `/api/projects/${_project.id}/frames/${f.frame_index}/image`;
}

function drawAll() {
  if (!_img) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(_img, 0, 0, canvas.width, canvas.height);

  const W = canvas.width, H = canvas.height;

  // bounding boxes
  (_annotations.boxes || []).forEach(b => {
    const col = colorFor(b.class_id);
    const x1  = (b.x_center - b.width  / 2) * W;
    const y1  = (b.y_center - b.height / 2) * H;
    const bw  = b.width  * W;
    const bh  = b.height * H;
    ctx.strokeStyle = col;
    ctx.lineWidth   = 2;
    ctx.strokeRect(x1, y1, bw, bh);
    ctx.fillStyle = col + "33";
    ctx.fillRect(x1, y1, bw, bh);
    ctx.fillStyle = col;
    ctx.font = "12px sans-serif";
    ctx.fillText(b.class_name, x1 + 3, y1 + 13);
  });

  // polygons
  (_annotations.polygons || []).forEach(poly => {
    const col = colorFor(poly.class_id);
    if (!poly.points.length) return;
    ctx.beginPath();
    poly.points.forEach(([px, py], i) => {
      const x = px * W, y = py * H;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.closePath();
    ctx.strokeStyle = col;
    ctx.lineWidth   = 2;
    ctx.stroke();
    ctx.fillStyle   = col + "44";
    ctx.fill();
  });

  // in-progress polygon
  if (_annType === "seg" && _polyPts.length) {
    ctx.beginPath();
    _polyPts.forEach(([px, py], i) => {
      const x = px * W, y = py * H;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = "#fff";
    ctx.setLineDash([4, 4]);
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.setLineDash([]);
    // dots
    _polyPts.forEach(([px, py]) => {
      ctx.beginPath();
      ctx.arc(px * W, py * H, 4, 0, Math.PI * 2);
      ctx.fillStyle = "#fff";
      ctx.fill();
    });
  }

  // in-progress bbox drawn live in mousemove handler
}

// canvas interaction
canvas.addEventListener("mousedown", e => {
  if (_annType === "bbox") {
    _drawing  = true;
    _drawStart = canvasNorm(e);
  } else if (_annType === "seg") {
    _polyPts.push(canvasNorm(e));
    drawAll();
  }
});

canvas.addEventListener("mousemove", e => {
  if (!_drawing || _annType !== "bbox") return;
  const {x, y} = canvasNorm(e);
  const {x: sx, y: sy} = _drawStart;
  drawAll();
  const W = canvas.width, H = canvas.height;
  ctx.strokeStyle = "#ffffff";
  ctx.lineWidth   = 1.5;
  ctx.strokeRect(sx * W, sy * H, (x - sx) * W, (y - sy) * H);
});

canvas.addEventListener("mouseup", e => {
  if (!_drawing || _annType !== "bbox") return;
  _drawing = false;
  const {x, y} = canvasNorm(e);
  const {x: sx, y: sy} = _drawStart;
  const x_c = (sx + x) / 2, y_c = (sy + y) / 2;
  const bw  = Math.abs(x - sx), bh = Math.abs(y - sy);
  if (bw < 0.005 || bh < 0.005) { drawAll(); return; }
  const cls = document.getElementById("class-input").value.trim() || "object";
  const cid = classIdFor(cls);
  _annotations.boxes.push({ class_id: cid, class_name: cls, x_center: x_c, y_center: y_c, width: bw, height: bh, confidence: 1 });
  drawAll();
  renderAnnList();
  saveAnnotations();
});

canvas.addEventListener("dblclick", e => {
  if (_annType !== "seg" || _polyPts.length < 3) return;
  const cls = document.getElementById("class-input").value.trim() || "object";
  const cid = classIdFor(cls);
  _annotations.polygons.push({ class_id: cid, class_name: cls, points: [..._polyPts], confidence: 1 });
  _polyPts = [];
  drawAll();
  renderAnnList();
  saveAnnotations();
});

canvas.addEventListener("contextmenu", e => {
  e.preventDefault();
  _polyPts = [];
  _drawing = false;
  drawAll();
});

function canvasNorm(e) {
  const r = canvas.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)),
    y: Math.max(0, Math.min(1, (e.clientY - r.top)  / r.height)),
  };
}

// ── annotation type tabs ──────────────────────────────────────────────────────
document.getElementById("ann-type-tabs").addEventListener("click", e => {
  const tab = e.target.closest("[data-type]");
  if (!tab) return;
  _annType = tab.dataset.type;
  _polyPts = [];
  _drawing = false;
  document.querySelectorAll(".type-tab").forEach(t => t.classList.toggle("active", t === tab));
  drawAll();
  renderAnnList();

  document.getElementById("cls-panel").style.display  = _annType === "cls"  ? "" : "none";
  document.getElementById("draw-hint").style.display  = _annType === "cls"  ? "none" : "";
});

// ── classification ────────────────────────────────────────────────────────────
document.getElementById("apply-cls-btn").addEventListener("click", () => {
  const cls = document.getElementById("class-input").value.trim() || "object";
  const cid = classIdFor(cls);
  _annotations.classifications = [{ class_id: cid, class_name: cls, confidence: 1 }];
  renderAnnList();
  saveAnnotations();
  toast("Classification saved");
});

// ── ann list ──────────────────────────────────────────────────────────────────
function renderAnnList() {
  const ul = document.getElementById("ann-list");
  ul.innerHTML = "";
  const items = _annType === "bbox"
    ? (_annotations.boxes || []).map((b, i) => ({ label: `${b.class_name} (box)`, i, type: "box", color: colorFor(b.class_id) }))
    : _annType === "seg"
    ? (_annotations.polygons || []).map((p, i) => ({ label: `${p.class_name} (poly, ${p.points.length}pts)`, i, type: "poly", color: colorFor(p.class_id) }))
    : (_annotations.classifications || []).map((c, i) => ({ label: c.class_name, i, type: "cls", color: colorFor(c.class_id) }));

  items.forEach(({ label, i, type, color }) => {
    const li  = document.createElement("li");
    const dot = document.createElement("span");
    dot.className = "dot";
    dot.style.background = color;
    const lbl = document.createElement("span");
    lbl.textContent = label;
    const del = document.createElement("button");
    del.textContent = "✕";
    del.className = "btn btn-sm btn-danger";
    del.addEventListener("click", () => {
      if (type === "box")  _annotations.boxes.splice(i, 1);
      if (type === "poly") _annotations.polygons.splice(i, 1);
      if (type === "cls")  _annotations.classifications.splice(i, 1);
      drawAll();
      renderAnnList();
      saveAnnotations();
    });
    li.append(dot, lbl, del);
    ul.appendChild(li);
  });
}

// ── save annotations ──────────────────────────────────────────────────────────
async function saveAnnotations() {
  if (!_frames.length) return;
  const f = _frames[_frameIdx];
  try {
    await api(`/api/projects/${_project.id}/frames/${f.frame_index}/annotations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(_annotations),
    });
  } catch (err) { toast("Save failed: " + err, "err"); }
}

// ── YOLO auto-annotate ────────────────────────────────────────────────────────
const yoloBtn  = document.getElementById("yolo-btn");
const yoloConf = document.getElementById("yolo-conf");
const yoloVal  = document.getElementById("yolo-conf-val");

yoloConf.addEventListener("input", () => {
  yoloVal.textContent = parseFloat(yoloConf.value).toFixed(2);
});

yoloBtn.addEventListener("click", async () => {
  if (!_project || !_frames.length) return;
  const f    = _frames[_frameIdx];
  const conf = parseFloat(yoloConf.value).toFixed(2);
  yoloBtn.disabled  = true;
  yoloBtn.textContent = "Running…";
  try {
    const result = await api(
      `/api/projects/${_project.id}/frames/${f.frame_index}/auto-annotate?conf=${conf}`,
      { method: "POST" }
    );
    if (result.error) {
      toast("YOLO: " + result.error, "err");
    } else {
      const boxes = result.boxes || [];
      boxes.forEach(b => {
        _annotations.boxes.push({
          class_id:   classIdFor(b.class_name),
          class_name: b.class_name,
          x_center:   b.x_center,
          y_center:   b.y_center,
          width:      b.width,
          height:     b.height,
          confidence: b.confidence,
        });
      });
      drawAll();
      renderAnnList();
      saveAnnotations();
      toast(`Auto-annotated: ${boxes.length} box(es)`);
    }
  } catch (err) { toast("YOLO failed: " + err, "err"); }
  yoloBtn.disabled    = false;
  yoloBtn.textContent = "⚡ Auto YOLO";
});

// ── export ────────────────────────────────────────────────────────────────────
document.getElementById("export-btn").addEventListener("click", async () => {
  if (!_project) return;
  try {
    const fmtEl = document.getElementById("export-fmt");
    const fmt   = fmtEl ? fmtEl.value : "yolo";
    const resp = await fetch(`/api/projects/${_project.id}/export?fmt=${fmt}`);
    if (!resp.ok) throw new Error(await resp.text());
    const blob = await resp.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href     = url;
    a.download = `${_project.name}_export.zip`;
    a.click();
    URL.revokeObjectURL(url);
    toast("Export downloaded");
  } catch (err) { toast("Export failed: " + err, "err"); }
});

// ── upload frames ─────────────────────────────────────────────────────────────
document.getElementById("upload-btn").addEventListener("click", () => {
  document.getElementById("upload-input").click();
});
document.getElementById("upload-input").addEventListener("change", async e => {
  const files = [...e.target.files];
  if (!files.length || !_project) return;
  const fd = new FormData();
  files.forEach(f => fd.append("files", f));
  try {
    const result = await api(`/api/projects/${_project.id}/upload`, { method: "POST", body: fd });
    const count = result && result.uploaded != null ? result.uploaded : files.length;
    toast(`Uploaded ${count} frame(s)`);
    await loadFrames();
  } catch (err) { toast("Upload failed: " + err, "err"); }
  e.target.value = "";
});

// ── back button ───────────────────────────────────────────────────────────────
document.getElementById("back-btn").addEventListener("click", () => {
  _project = null;
  showView("projects-view");
});

// ── delete project ────────────────────────────────────────────────────────────
document.getElementById("delete-project-btn").addEventListener("click", async () => {
  if (!_project || !confirm(`Delete project "${_project.name}"?`)) return;
  try {
    await api(`/api/projects/${_project.id}`, { method: "DELETE" });
    _projects = _projects.filter(p => p.id !== _project.id);
    renderProjects();
    showView("projects-view");
    toast("Project deleted");
  } catch (err) { toast("Delete failed: " + err, "err"); }
});

// ── keyboard shortcuts ─────────────────────────────────────────────────────────
document.addEventListener("keydown", e => {
  if (e.key === "ArrowRight") { if (_frameIdx < _frames.length - 1) selectFrame(_frameIdx + 1); }
  if (e.key === "ArrowLeft")  { if (_frameIdx > 0) selectFrame(_frameIdx - 1); }
  if (e.key === "Escape")     { _polyPts = []; _drawing = false; drawAll(); }
});

// ── init ──────────────────────────────────────────────────────────────────────
(async () => {
  showView("projects-view");
  await loadProjects();
})();
