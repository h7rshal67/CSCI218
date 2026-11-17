"use strict";

const byId = (id) => document.getElementById(id);
const state = {kind: "road", scene: null, result: null, busy: false, fitAfterRun: true, animation: 0};
const palette = ["#c9e3ec", "#f2d8bb", "#d4dfb6", "#d9cceb", "#c6e4dc", "#f1d2ca", "#c9d6ea", "#e6ddbc"];
const number = (x, digits = 0) => x.toLocaleString("en-GB", {maximumFractionDigits: digits, minimumFractionDigits: digits});
const timeText = (x) => number(x, x < 10 ? 2 : 1) + " ms";

function status(message, kind = "") {
  byId("status").textContent = message;
  byId("status").className = "status " + kind;
}

function busy(value, message) {
  state.busy = value;
  document.querySelectorAll(".controls button,.controls select,#benchmark-btn").forEach((el) => { el.disabled = value; });
  byId("replay-btn").disabled = value || !state.result;
  if (message) status(message, value ? "loading" : "");
}

function options() {
  return {
    kind: state.kind, size: Number(byId("size").value), seed: Number(byId("seed").value),
    start: byId("start").value || "Boxpark", goal: byId("goal").value || "Port de La Mer",
    scenario: byId("scenario").value,
  };
}

async function request(url, data) {
  const response = await fetch(url, data === undefined ? {} : {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The local server could not complete the request.");
  return result;
}

class MapView {
  constructor(canvas, method) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.base = document.createElement("canvas");
    this.method = method;
    this.scene = null;
    this.result = null;
    this.closed = [];
    this.allowed = new Set();
    this.progress = 1;
    this.dirty = true;
    this.scale = 1;
    this.tx = 0;
    this.ty = 0;
    this.drag = null;
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(canvas);
    canvas.addEventListener("wheel", (event) => {
      if (!this.scene) return;
      event.preventDefault();
      const box = canvas.getBoundingClientRect();
      const x = event.clientX - box.left, y = event.clientY - box.top;
      const factor = Math.exp(-event.deltaY * .0015);
      const next = Math.max(this.fitScale * .3, Math.min(this.fitScale * 25, this.scale * factor));
      const ratio = next / this.scale;
      this.tx = x - (x - this.tx) * ratio;
      this.ty = y - (y - this.ty) * ratio;
      this.scale = next;
      this.dirty = true;
      this.draw();
    }, {passive: false});
    canvas.addEventListener("pointerdown", (event) => {
      this.drag = [event.clientX, event.clientY, this.tx, this.ty];
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!this.drag) return;
      this.tx = this.drag[2] + event.clientX - this.drag[0];
      this.ty = this.drag[3] + event.clientY - this.drag[1];
      this.dirty = true;
      this.draw();
    });
    canvas.addEventListener("pointerup", () => { this.drag = null; });
    canvas.addEventListener("pointercancel", () => { this.drag = null; });
    canvas.addEventListener("dblclick", () => this.fitMap());
  }

  resize() {
    const box = this.canvas.getBoundingClientRect();
    this.w = box.width; this.h = box.height;
    this.dpr = window.devicePixelRatio || 1;
    this.canvas.width = Math.round(this.w * this.dpr);
    this.canvas.height = Math.round(this.h * this.dpr);
    this.base.width = this.canvas.width;
    this.base.height = this.canvas.height;
    if (this.scene) this.fitMap();
    else this.draw();
  }

  setScene(scene) {
    this.scene = scene;
    this.result = null; this.closed = []; this.allowed.clear();
    this.fitMap();
  }

  fitMap() {
    if (!this.scene) return;
    if (this.scene.kind === "grid") {
      this.fitBounds(0, 0, this.scene.size, this.scene.size);
    } else {
      this.fitNodes(this.scene.nodes.map((_, i) => i));
    }
  }

  fitNodes(indices) {
    if (!this.scene || !indices.length) { this.fitMap(); return; }
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const i of indices) {
      const n = this.scene.nodes[i];
      x0 = Math.min(x0, n[0]); x1 = Math.max(x1, n[0]);
      y0 = Math.min(y0, n[1]); y1 = Math.max(y1, n[1]);
    }
    const padding = Math.max(x1 - x0, y1 - y0) * .08 + (this.scene.kind === "road" ? 80 : 1);
    this.fitBounds(x0 - padding, y0 - padding, x1 + padding, y1 + padding);
  }

  fitBounds(x0, y0, x1, y1) {
    const w = this.w || this.canvas.clientWidth, h = this.h || this.canvas.clientHeight;
    this.scale = Math.min((w - 64) / Math.max(1, x1 - x0), (h - 52) / Math.max(1, y1 - y0));
    this.fitScale = this.scale;
    this.tx = (w - (x1 - x0) * this.scale) / 2 - x0 * this.scale;
    this.ty = (h - (y1 - y0) * this.scale) / 2 + y1 * this.scale;
    this.dirty = true;
    this.draw();
  }

  point(i) {
    const node = this.scene.nodes[i];
    return [this.tx + node[0] * this.scale, this.ty - node[1] * this.scale];
  }

  setResult(result, comparison) {
    this.result = result; this.comparison = comparison;
    this.closed = comparison.blocked;
    this.allowed = new Set(result.allowed);
    this.progress = 1;
    this.dirty = true;
    this.draw();
  }

  drawBase() {
    const ctx = this.base.getContext("2d");
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    ctx.fillStyle = "#fcfdfb"; ctx.fillRect(0, 0, this.w, this.h);
    const scene = this.scene;
    if (!scene) return;
    const regions = byId("show-regions").checked;
    const restricted = this.method === "tier" && this.result && this.allowed.size > 0 && this.allowed.size < scene.nodes.length;
    if (scene.kind === "grid") {
      ctx.fillStyle = "#33464d";
      ctx.fillRect(this.tx, this.ty - scene.size * this.scale, scene.size * this.scale, scene.size * this.scale);
      for (let i = 0; i < scene.nodes.length; i++) {
        const p = this.point(i);
        const muted = restricted && !this.allowed.has(i);
        ctx.fillStyle = muted ? "#e8ece8" : regions ? palette[scene.nodes[i][2] % palette.length] : "#f5f8f1";
        const side = Math.max(.7, this.scale - Math.min(.4, this.scale * .035));
        ctx.fillRect(p[0] - side / 2, p[1] - side / 2, side, side);
      }
    } else {
      ctx.strokeStyle = "#d3ddd7"; ctx.lineWidth = .75;
      ctx.beginPath();
      for (const edge of scene.edges) {
        const a = this.point(edge[0]), b = this.point(edge[1]);
        ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
      }
      ctx.stroke();
      if (regions) {
        for (let i = 0; i < scene.nodes.length; i++) {
          if (restricted && !this.allowed.has(i)) continue;
          const p = this.point(i);
          if (p[0] < 0 || p[0] > this.w || p[1] < 0 || p[1] > this.h) continue;
          ctx.fillStyle = palette[scene.nodes[i][2] % palette.length];
          ctx.fillRect(p[0] - .75, p[1] - .75, 1.5, 1.5);
        }
      }
    }
    this.dirty = false;
  }

  draw() {
    if (!this.w || !this.h) return;
    if (this.dirty) this.drawBase();
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    ctx.drawImage(this.base, 0, 0, this.w, this.h);
    if (!this.scene) return;
    const isGrid = this.scene.kind === "grid";
    const color = this.method === "flat" ? "#087f9d" : "#bf663d";
    if (this.result && byId("show-explored").checked) {
      const end = Math.floor(this.result.trace.length * this.progress);
      const radius = isGrid ? Math.max(.6, this.scale * .29) : 1.4;
      ctx.fillStyle = this.method === "flat" ? "#087f9d38" : "#bf663d38";
      ctx.beginPath();
      for (let j = 0; j < end; j++) {
        const p = this.point(this.result.trace[j]);
        if (p[0] < -5 || p[0] > this.w + 5 || p[1] < -5 || p[1] > this.h + 5) continue;
        ctx.moveTo(p[0] + radius, p[1]); ctx.arc(p[0], p[1], radius, 0, Math.PI * 2);
      }
      ctx.fill();
    }
    ctx.strokeStyle = "#ce3c9c"; ctx.lineWidth = isGrid ? Math.max(2, this.scale * .2) : 3;
    ctx.beginPath();
    for (const edge of this.closed) {
      const a = this.point(edge[0]), b = this.point(edge[1]);
      ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]);
    }
    ctx.stroke();
    if (this.result && this.progress >= 1 && this.result.path.length) {
      ctx.lineJoin = "round"; ctx.lineCap = "round"; ctx.lineWidth = isGrid ? Math.max(1.7, this.scale * .3) : 4;
      ctx.strokeStyle = "#ffffffdd"; ctx.lineWidth += 2; ctx.beginPath();
      this.result.path.forEach((index, j) => { const p = this.point(index); if (j) ctx.lineTo(...p); else ctx.moveTo(...p); });
      ctx.stroke(); ctx.lineWidth -= 2; ctx.strokeStyle = color; ctx.stroke();
    }
    if (this.scene.hubs) {
      ctx.font = "10px Segoe UI,Arial"; ctx.lineWidth = 3; ctx.lineJoin = "round";
      for (const hub of this.scene.hubs) {
        const p = this.point(hub.node);
        if (p[0] < 0 || p[0] > this.w || p[1] < 0 || p[1] > this.h) continue;
        ctx.beginPath(); ctx.arc(p[0], p[1], 3, 0, Math.PI * 2); ctx.fillStyle = "#fff"; ctx.fill(); ctx.strokeStyle = "#576c60"; ctx.lineWidth = 1; ctx.stroke();
        ctx.strokeStyle = "#fffffff0"; ctx.lineWidth = 3; ctx.strokeText(hub.name, p[0] + 7, p[1] - 7);
        ctx.fillStyle = "#506459"; ctx.fillText(hub.name, p[0] + 7, p[1] - 7);
      }
    }
    if (this.comparison && this.result) {
      this.marker(this.comparison.start, "S", "#20343b");
      this.marker(this.comparison.goal, this.comparison.start === this.comparison.goal ? "S/G" : "G", color);
    } else if (this.scene.start !== null) {
      this.marker(this.scene.start, "S", "#20343b");
      this.marker(this.scene.goal, "G", color);
    }
  }

  marker(index, text, color) {
    const p = this.point(index);
    this.ctx.beginPath(); this.ctx.arc(p[0], p[1], text.length > 1 ? 14 : 10, 0, Math.PI * 2);
    this.ctx.fillStyle = color; this.ctx.fill(); this.ctx.strokeStyle = "#fff"; this.ctx.lineWidth = 2; this.ctx.stroke();
    this.ctx.fillStyle = "#fff"; this.ctx.textAlign = "center"; this.ctx.textBaseline = "middle"; this.ctx.font = "bold 10px Segoe UI,Arial";
    this.ctx.fillText(text, p[0], p[1] + .5); this.ctx.textAlign = "start"; this.ctx.textBaseline = "alphabetic";
  }
}

const views = {flat: new MapView(byId("flat-map"), "flat"), tier: new MapView(byId("tier-map"), "tier")};
for (const name of ["flat", "tier"]) {
  byId(name + "-fit").addEventListener("click", () => views[name].fitMap());
  byId(name + "-route-fit").addEventListener("click", () => {
    if (state.result) views[name].fitNodes(state.result[name].path);
  });
}
for (const id of ["show-regions", "show-explored"]) byId(id).addEventListener("change", () => {
  for (const view of Object.values(views)) { view.dirty = true; view.draw(); }
});

async function loadScene() {
  busy(true, "Loading the packaged " + (state.kind === "road" ? "Jumeirah road map" : "obstacle grid") + "…");
  state.animation++;
  state.result = null;
  try {
    const params = new URLSearchParams({kind: state.kind, size: byId("size").value, seed: byId("seed").value});
    const scene = await request("/api/scene?" + params);
    state.scene = scene;
    state.fitAfterRun = true;
    if (scene.kind === "road") {
      for (const id of ["start", "goal"]) {
        const old = byId(id).value;
        byId(id).replaceChildren(...scene.hubs.map((hub) => {
          const option = document.createElement("option"); option.value = hub.name; option.textContent = hub.name; return option;
        }));
        byId(id).value = scene.hubs.some((h) => h.name === old) ? old : id === "start" ? "Boxpark" : "Port de La Mer";
      }
    }
    for (const view of Object.values(views)) { view.comparison = null; view.setScene(scene); }
    byId("scene-info").textContent = scene.kind === "road"
      ? number(scene.node_count) + " road nodes · " + number(scene.directed_edge_count) + " directed edges · 8 hubs · map build " + timeText(scene.load_ms)
      : scene.size + " × " + scene.size + " · " + number(scene.node_count) + " open cells · connected regions · seed " + scene.seed + " · map build " + timeText(scene.load_ms);
    await runComparison();
  } catch (error) {
    status(error.message + " Keep the Python terminal open and try again.", "error");
    busy(false);
  }
}

function metric(id, value, suffix, digits = 0) {
  const el = byId(id); el.replaceChildren();
  el.append(document.createTextNode(value === null ? "—" : number(value, digits)));
  if (value !== null && suffix) { const small = document.createElement("small"); small.textContent = suffix; el.append(small); }
}

async function runComparison() {
  busy(true, "Running both algorithms on identical inputs and validating the paths…");
  state.animation++;
  try {
    const result = await request("/api/run", options());
    state.result = result;
    for (const name of ["flat", "tier"]) {
      const r = result[name];
      metric(name + "-cost", r.cost, result.unit, result.unit === "m" ? 1 : 0);
      metric(name + "-nodes", r.nodes);
      metric(name + "-time", r.runtime_ms, "ms", r.runtime_ms < 10 ? 2 : 1);
      const badge = byId(name + "-status");
      badge.textContent = r.found ? "Path found" : "No route";
      badge.className = "result-badge " + (r.found ? "found" : "unreachable");
      views[name].setResult(r, result);
    }
    if (state.fitAfterRun && state.kind === "road" && result.flat.found) {
      const all = result.flat.path.concat(result.tier.path);
      Object.values(views).forEach((v) => v.fitNodes(all));
      state.fitAfterRun = false;
    }
    byId("flat-detail").textContent = "Full map · " + number(result.flat.total_nodes) + " total expansions";
    byId("tier-detail").textContent = result.tier.mode + " · " + result.tier.attempts + " attempt" + (result.tier.attempts === 1 ? "" : "s") + " · " + number(result.tier.total_nodes) + " total expansions";
    byId("abstract-count").textContent = number(result.tier.abstract_nodes);
    byId("prep-time").textContent = timeText(result.tier.preprocess_ms);
    byId("closed-count").textContent = number(result.blocked_count);
    byId("validation-state").textContent = "Passed";
    byId("corridor-plan").textContent = result.tier.region_path.length
      ? state.kind === "road"
        ? "Abstract region plan: " + result.tier.region_path.join(" → ") + "."
        : "Abstract region plan: " + result.tier.region_path.length + " connected areas before any widening. Final corridor permits " + number(result.tier.allowed.length) + " open cells."
      : "No abstract region path was found; the detailed search uses its whole-map fallback.";
    byId("scenario-note").textContent = result.scenario_note + " Region graph: " + number(result.region_count) + " areas. Magenta lines mark closures.";
    if (!result.flat.found) {
      byId("finding-title").textContent = "Both searches agree: the destination is unreachable.";
      byId("finding-text").textContent = "The closure set is identical for both methods. Widening and fallback cannot create a route through closed edges.";
    } else {
      const extra = result.tier.cost - result.flat.cost;
      const gap = result.flat.cost ? 100 * extra / result.flat.cost : 0;
      const difference = result.tier.nodes - result.flat.nodes;
      byId("finding-title").textContent = Math.abs(extra) < .000001
        ? "Both methods found the same shortest route cost."
        : "Two-tier found a valid route " + number(gap, 1) + "% longer than the optimum.";
      byId("finding-text").textContent =
        "Two-tier expanded " + number(Math.abs(difference)) + (difference > 0 ? " more" : difference < 0 ? " fewer" : " extra") +
        " detailed nodes, plus " + number(result.tier.abstract_nodes) + " abstract nodes. " +
        (result.tier.mode === "Whole-map fallback" ? "It used the whole-map fallback. " : "") +
        "A smaller search corridor does not guarantee a faster query or the shortest route.";
    }
    status("Path checks passed · same map, same endpoints, same directed closures.");
  } catch (error) {
    status(error.message, "error");
  } finally { busy(false); }
}

for (const id of ["start", "goal", "scenario"]) byId(id).addEventListener("change", runComparison);
for (const id of ["size", "seed"]) byId(id).addEventListener("change", loadScene);
byId("run-btn").addEventListener("click", runComparison);
for (const kind of ["road", "grid"]) byId(kind + "-btn").addEventListener("click", () => {
  state.kind = kind;
  byId("road-fields").hidden = kind !== "road";
  byId("grid-fields").hidden = kind !== "grid";
  byId("hub-option").disabled = kind !== "road";
  if (kind !== "road" && byId("scenario").value === "hub") byId("scenario").value = "none";
  for (const name of ["road", "grid"]) {
    byId(name + "-btn").classList.toggle("selected", kind === name);
    byId(name + "-btn").setAttribute("aria-pressed", String(kind === name));
  }
  loadScene();
});

byId("replay-btn").addEventListener("click", () => {
  if (!state.result) return;
  const token = ++state.animation, start = performance.now();
  function frame(now) {
    if (state.animation !== token) return;
    const progress = Math.min(1, (now - start) / 2600);
    for (const view of Object.values(views)) { view.progress = progress; view.draw(); }
    if (progress < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
});

byId("benchmark-btn").addEventListener("click", async () => {
  busy(true, "Running the reproducible 600-search grid benchmark…");
  byId("benchmark-progress").hidden = false;
  try {
    const data = await request("/api/benchmark", {});
    const body = byId("benchmark-body"); body.replaceChildren();
    for (const row of data.summary) {
      const tr = document.createElement("tr");
      const values = [row.size + " × " + row.size, row.method,
        number(row.detailed_nodes_mean, 1) + " ± " + number(row.detailed_nodes_sd, 1),
        number(row.abstract_nodes_mean, 1),
        number(row.runtime_ms_mean, 3) + " ± " + number(row.runtime_ms_sd, 3) + " ms",
        number(row.cost_mean, 1) + " moves", timeText(row.preprocessing_ms_mean)];
      for (const value of values) { const td = document.createElement("td"); td.textContent = value; tr.append(td); }
      body.append(tr);
    }
    byId("benchmark-results").hidden = false;
    byId("benchmark-caption").textContent = data.metadata.trial_count +
      " validated searches · ± sample SD across 10 map means · Python " + data.metadata.python;
    status("Benchmark complete. Trials, summary and environment metadata were saved in results/integrated.");
  } catch (error) { status(error.message, "error"); }
  finally { byId("benchmark-progress").hidden = true; busy(false); }
});

loadScene();
