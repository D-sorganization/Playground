/* Workout tracker frontend - vanilla JS, no build step. */
(() => {
  "use strict";

  // ---------- API helpers ----------
  const api = {
    async get(path) {
      const r = await fetch(path);
      if (!r.ok) throw new Error(`${r.status} ${path}`);
      return r.json();
    },
    async send(method, path, body) {
      const r = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: body == null ? undefined : JSON.stringify(body),
      });
      if (!r.ok) {
        const t = await r.text().catch(() => "");
        throw new Error(`${r.status} ${path}: ${t}`);
      }
      const txt = await r.text();
      return txt ? JSON.parse(txt) : {};
    },
    post(p, b) { return this.send("POST", p, b); },
    put(p, b) { return this.send("PUT", p, b); },
    delete(p) { return this.send("DELETE", p); },
  };

  // ---------- DOM helpers ----------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const el = (tag, attrs = {}, kids = []) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") e.className = v;
      else if (k === "html") e.innerHTML = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (v === true) e.setAttribute(k, "");
      else if (v != null && v !== false) e.setAttribute(k, v);
    }
    for (const k of [].concat(kids)) {
      if (k == null) continue;
      e.appendChild(typeof k === "string" ? document.createTextNode(k) : k);
    }
    return e;
  };

  function toast(msg, type = "ok") {
    const t = $("#toast");
    t.textContent = msg;
    t.className = `toast ${type === "danger" ? "danger" : ""}`;
    setTimeout(() => t.classList.add("hidden"), 10);
    requestAnimationFrame(() => {
      t.classList.remove("hidden");
      clearTimeout(t._tm);
      t._tm = setTimeout(() => t.classList.add("hidden"), 2200);
    });
  }

  function fmtSet(s) {
    const r = s.actual_reps ?? s.planned_reps ?? "?";
    const w = s.actual_weight ?? s.planned_weight;
    const unit = s.unit || "lbs";
    const main = w == null ? `${r}` : `${r} × ${w}${unit}`;
    const rpe = s.rpe ? ` · RPE ${s.rpe}` : "";
    return main + rpe;
  }

  // ---------- State ----------
  const state = {
    activeWorkoutId: null,
    catalog: [],          // [Exercise]
    pendingExercise: null,
    suggestFocus: -1,
  };

  // ---------- Tabs ----------
  function bindTabs() {
    $$(".tab").forEach((t) =>
      t.addEventListener("click", () => {
        $$(".tab").forEach((x) => x.classList.remove("active"));
        $$(".panel").forEach((x) => x.classList.remove("active"));
        t.classList.add("active");
        $(`#tab-${t.dataset.tab}`).classList.add("active");
        if (t.dataset.tab === "history") loadHistory();
        if (t.dataset.tab === "stats") loadStats();
        if (t.dataset.tab === "plans") loadPlans();
        if (t.dataset.tab === "catalog") loadCatalog();
      })
    );
  }

  // Local YYYY-MM-DD (avoids UTC date drift near midnight).
  function localDateISO(d = new Date()) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  // ---------- Today / active workout ----------

  async function startWorkout() {
    const today = localDateISO();
    const w = await api.post("/api/workouts", {
      date: today,
      status: "in_progress",
      title: null,
    });
    state.activeWorkoutId = w.id;
    localStorage.setItem("active_workout_id", String(w.id));
    await refreshActiveWorkout();
  }

  async function tryResumeActive() {
    const sid = localStorage.getItem("active_workout_id");
    if (!sid) return showEmpty();
    try {
      const w = await api.get(`/api/workouts/${sid}`);
      if (w.status === "completed") {
        localStorage.removeItem("active_workout_id");
        return showEmpty();
      }
      state.activeWorkoutId = w.id;
      renderActive(w);
    } catch {
      localStorage.removeItem("active_workout_id");
      showEmpty();
    }
  }

  function showEmpty() {
    $("#active-empty").classList.remove("hidden");
    $("#active-workout").classList.add("hidden");
    $("#today-date").textContent = new Date().toLocaleDateString();
  }

  async function refreshActiveWorkout() {
    if (!state.activeWorkoutId) return;
    const w = await api.get(`/api/workouts/${state.activeWorkoutId}`);
    renderActive(w);
  }

  function renderActive(w) {
    $("#active-empty").classList.add("hidden");
    $("#active-workout").classList.remove("hidden");
    $("#today-date").textContent = w.date;
    $("#today-title").textContent = w.title || "Today's Workout";

    const list = $("#set-list");
    list.innerHTML = "";
    const grouped = groupByExercise(w.sets);
    for (const [exName, sets] of grouped) {
      list.appendChild(el("h3", {}, exName));
      sets.forEach((s, idx) => list.appendChild(renderSetRow(s, idx + 1)));
    }
  }

  function groupByExercise(sets) {
    const byEx = new Map();
    for (const s of sets) {
      const k = s.exercise_name || `#${s.exercise_id}`;
      if (!byEx.has(k)) byEx.set(k, []);
      byEx.get(k).push(s);
    }
    return byEx;
  }

  function renderSetRow(s, n) {
    const cls = "set-row" + (s.executed ? " exec" : " planned");
    const meta = el("div", { class: "meta" }, [
      el("span", { class: "pill" }, `Set ${n}`),
      el("span", {}, fmtSet(s)),
      s.executed ? null : el("span", { class: "pill" }, "planned"),
    ]);
    const actions = el("div", { class: "actions" });
    if (!s.executed) {
      actions.appendChild(
        el(
          "button",
          {
            class: "btn icon primary",
            onclick: async () => {
              await api.put(`/api/sets/${s.id}`, {
                executed: true,
                actual_reps: s.actual_reps ?? s.planned_reps,
                actual_weight: s.actual_weight ?? s.planned_weight,
              });
              refreshActiveWorkout();
            },
          },
          "✓"
        )
      );
    }
    actions.appendChild(
      el(
        "button",
        {
          class: "btn icon",
          onclick: () => editSetInline(s),
        },
        "✎"
      )
    );
    actions.appendChild(
      el(
        "button",
        {
          class: "btn icon danger",
          onclick: async () => {
            if (!confirm("Delete this set?")) return;
            await api.delete(`/api/sets/${s.id}`);
            refreshActiveWorkout();
          },
        },
        "✕"
      )
    );
    return el("div", { class: cls }, [meta, actions]);
  }

  async function editSetInline(s) {
    const reps = prompt("Reps:", s.actual_reps ?? s.planned_reps ?? "");
    if (reps == null) return;
    const weight = prompt("Weight:", s.actual_weight ?? s.planned_weight ?? "");
    if (weight == null) return;
    const body = {
      actual_reps: reps === "" ? null : Number(reps),
      actual_weight: weight === "" ? null : Number(weight),
      executed: true,
    };
    await api.put(`/api/sets/${s.id}`, body);
    refreshActiveWorkout();
  }

  // ---------- Autocomplete ----------

  let suggestionItems = [];

  async function refreshSuggestions(q) {
    const ul = $("#ex-suggest");
    ul.innerHTML = "";
    suggestionItems = [];
    state.suggestFocus = -1;
    let results = await api.get(
      `/api/exercises/suggest?q=${encodeURIComponent(q)}&limit=8`
    );
    for (const r of results) {
      const li = el(
        "li",
        {
          onclick: () => pickSuggestion(r.name),
          onmousedown: (e) => e.preventDefault(),
        },
        [el("span", {}, r.name), el("span", { class: "badge" }, `×${r.use_count}`)]
      );
      suggestionItems.push({ el: li, name: r.name });
      ul.appendChild(li);
    }
    const trimmed = (q || "").trim();
    const exact = results.find(
      (r) => r.name.toLowerCase() === trimmed.toLowerCase()
    );
    if (trimmed && !exact) {
      const li = el(
        "li",
        {
          class: "create",
          onclick: () => pickSuggestion(trimmed),
          onmousedown: (e) => e.preventDefault(),
        },
        `+ Create "${trimmed}"`
      );
      suggestionItems.push({ el: li, name: trimmed });
      ul.appendChild(li);
    }
    if (suggestionItems.length) ul.classList.remove("hidden");
    else ul.classList.add("hidden");
  }

  function pickSuggestion(name) {
    $("#ex-input").value = name;
    $("#ex-suggest").classList.add("hidden");
    $("#reps-input").focus();
  }

  function bindAutocomplete() {
    const input = $("#ex-input");
    const ul = $("#ex-suggest");
    let lastTimer;
    input.addEventListener("input", () => {
      clearTimeout(lastTimer);
      lastTimer = setTimeout(() => refreshSuggestions(input.value), 80);
    });
    input.addEventListener("focus", () => refreshSuggestions(input.value));
    input.addEventListener("blur", () =>
      setTimeout(() => ul.classList.add("hidden"), 150)
    );
    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        moveSuggest(1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        moveSuggest(-1);
      } else if (e.key === "Enter") {
        if (state.suggestFocus >= 0 && suggestionItems[state.suggestFocus]) {
          e.preventDefault();
          pickSuggestion(suggestionItems[state.suggestFocus].name);
        }
      } else if (e.key === "Escape") {
        ul.classList.add("hidden");
      }
    });
  }

  function moveSuggest(d) {
    if (!suggestionItems.length) return;
    state.suggestFocus =
      (state.suggestFocus + d + suggestionItems.length) % suggestionItems.length;
    suggestionItems.forEach((s, i) =>
      s.el.classList.toggle("focus", i === state.suggestFocus)
    );
  }

  // ---------- Add set ----------

  async function ensureActiveWorkout() {
    if (state.activeWorkoutId) return state.activeWorkoutId;
    await startWorkout();
    return state.activeWorkoutId;
  }

  async function addSet(executed) {
    const name = $("#ex-input").value.trim();
    const reps = $("#reps-input").value;
    const weight = $("#weight-input").value;
    const unit = $("#unit-input").value;
    const rpe = $("#rpe-input").value;
    if (!name) return toast("Pick an exercise", "danger");
    if (!reps && executed) return toast("Reps required", "danger");
    const wid = await ensureActiveWorkout();
    const body = {
      exercise_name: name,
      unit,
      executed,
      rpe: rpe ? Number(rpe) : null,
    };
    if (executed) {
      body.actual_reps = reps ? Number(reps) : null;
      body.actual_weight = weight ? Number(weight) : null;
    } else {
      body.planned_reps = reps ? Number(reps) : null;
      body.planned_weight = weight ? Number(weight) : null;
    }
    await api.post(`/api/workouts/${wid}/sets`, body);
    $("#reps-input").value = "";
    // Keep weight + exercise to make repeated sets fast
    toast(executed ? "Set logged ✓" : "Set planned");
    refreshActiveWorkout();
  }

  async function finishWorkout() {
    if (!state.activeWorkoutId) return;
    if (!confirm("Finish this workout?")) return;
    await api.put(`/api/workouts/${state.activeWorkoutId}`, {
      status: "completed",
    });
    localStorage.removeItem("active_workout_id");
    state.activeWorkoutId = null;
    showEmpty();
    toast("Workout saved ✓");
  }

  // ---------- Plans ----------

  async function previewPlan() {
    const text = $("#plan-text").value;
    const parsed = await api.post("/api/parse", { text });
    const out = parsed
      .map(
        (e) =>
          `${e.exercise_name}\n` +
          e.sets
            .map(
              (s) =>
                `  · ${s.reps}${
                  s.weight != null ? ` × ${s.weight}${s.unit}` : ""
                }${s.rpe ? ` @RPE${s.rpe}` : ""}`
            )
            .join("\n")
      )
      .join("\n\n");
    $("#plan-preview").textContent = out || "(nothing parsed)";
  }

  async function savePlan() {
    const text = $("#plan-text").value.trim();
    if (!text) return toast("Plan is empty", "danger");
    const date =
      $("#plan-date").value || localDateISO();
    const title = $("#plan-title").value || null;
    const w = await api.post("/api/workouts", {
      date,
      title,
      status: "planned",
      notes: text,
    });
    await api.post(`/api/workouts/${w.id}/import`, { text, executed: false });
    toast("Plan saved ✓");
    $("#plan-text").value = "";
    $("#plan-title").value = "";
    $("#plan-preview").textContent = "";
    loadPlans();
  }

  async function loadPlans() {
    const ws = await api.get("/api/workouts?limit=200");
    const plans = ws.filter((w) => w.status === "planned");
    const list = $("#plans-list");
    list.innerHTML = "";
    if (!plans.length) {
      list.appendChild(
        el("p", { class: "muted small" }, "No saved plans yet.")
      );
      return;
    }
    for (const w of plans) list.appendChild(renderWorkoutItem(w, true));
  }

  // ---------- History ----------

  async function loadHistory() {
    const ws = await api.get("/api/workouts?limit=200");
    const list = $("#history-list");
    list.innerHTML = "";
    if (!ws.length) {
      list.appendChild(el("p", { class: "muted small" }, "No workouts yet."));
      return;
    }
    for (const w of ws) list.appendChild(renderWorkoutItem(w, false));
  }

  function renderWorkoutItem(w, isPlan) {
    const sub =
      `${w.sets.length} sets · status: ${w.status}` +
      (w.title ? ` · ${w.title}` : "");
    const meta = el("div", { class: "meta" }, [
      el("span", { class: "title" }, `${w.date}`),
      el("span", { class: "sub" }, sub),
    ]);
    const actions = el("div", { class: "actions" });
    if (isPlan) {
      actions.appendChild(
        el(
          "button",
          {
            class: "btn primary icon",
            onclick: async () => {
              await api.put(`/api/workouts/${w.id}`, {
                status: "in_progress",
              });
              state.activeWorkoutId = w.id;
              localStorage.setItem("active_workout_id", String(w.id));
              $$(".tab").forEach((t) => t.classList.remove("active"));
              $('.tab[data-tab="today"]').classList.add("active");
              $$(".panel").forEach((p) => p.classList.remove("active"));
              $("#tab-today").classList.add("active");
              refreshActiveWorkout();
            },
          },
          "Start"
        )
      );
    }
    actions.appendChild(
      el(
        "button",
        {
          class: "btn icon danger",
          onclick: async () => {
            if (!confirm("Delete this workout?")) return;
            await api.delete(`/api/workouts/${w.id}`);
            isPlan ? loadPlans() : loadHistory();
          },
        },
        "✕"
      )
    );
    return el("div", { class: "item" }, [meta, actions]);
  }

  // ---------- Stats ----------

  async function loadStats() {
    const [data, adv] = await Promise.all([
      api.get("/api/stats/overview"),
      api.get("/api/stats/advanced"),
    ]);
    const ov = data.overview;
    const tiles = $("#stats-overview");
    tiles.innerHTML = "";
    const stat = (n, l) =>
      el("div", { class: "stat-tile" }, [
        el("div", { class: "num" }, String(n)),
        el("div", { class: "lbl" }, l),
      ]);
    tiles.appendChild(stat(ov.total_workouts, "Workouts"));
    tiles.appendChild(stat(ov.total_sets, "Sets"));
    tiles.appendChild(stat(round(ov.total_volume), "Volume"));
    tiles.appendChild(stat(ov.distinct_exercises, "Exercises"));
    tiles.appendChild(stat(ov.last_workout_date || "—", "Last"));

    renderStreak(adv.streak);
    renderHeatmap(adv.heatmap);

    const prs = $("#stats-prs");
    prs.innerHTML = "";
    if (!data.personal_records.length) {
      prs.appendChild(el("p", { class: "muted small" }, "No PRs yet."));
    }
    for (const pr of data.personal_records) {
      const sub =
        pr.metric === "max_weight"
          ? `Heaviest: ${pr.weight} × ${pr.reps} on ${pr.date}`
          : pr.metric === "max_reps"
          ? `Most reps: ${pr.reps} × ${pr.weight} on ${pr.date}`
          : `Best e1RM: ${round(pr.value)} (${pr.weight}×${pr.reps}) on ${pr.date}`;
      prs.appendChild(
        el("div", { class: "item" }, [
          el("div", { class: "meta" }, [
            el("span", { class: "title" }, pr.exercise_name),
            el("span", { class: "sub" }, sub),
          ]),
        ])
      );
    }

    const sum = $("#stats-summary");
    sum.innerHTML = "";
    // Close detail panel on re-load
    $("#stats-exercise-detail").classList.add("hidden");
    for (const s of data.per_exercise) {
      const row = el("div", { class: "item" }, [
        el("div", { class: "meta" }, [
          el("span", { class: "title" }, s.exercise_name),
          el(
            "span",
            { class: "sub" },
            `${s.total_sets} sets · ${s.total_reps} reps · vol ${round(s.total_volume)} · top ${s.max_weight}×${s.max_reps_at_max_weight} · e1RM ${round(s.best_e1rm)}`
          ),
        ]),
      ]);
      row.style.cursor = "pointer";
      row.addEventListener("click", () =>
        loadExerciseDetail(s.exercise_id, s.exercise_name)
      );
      sum.appendChild(row);
    }

    renderSessions(adv.sessions);

    const fr = $("#stats-frequency");
    fr.innerHTML = "";
    for (const f of data.frequency) {
      fr.appendChild(
        el("div", { class: "item" }, [
          el("div", { class: "meta" }, [
            el("span", { class: "title" }, f.exercise_name),
            el(
              "span",
              { class: "sub" },
              `${f.sessions} sessions · ${f.days_since_last} days ago`
            ),
          ]),
        ])
      );
    }

    await populateRatioPicker();
  }

  // ---------- Streak ----------

  function renderStreak(streak) {
    const wrap = $("#stats-streak");
    wrap.innerHTML = "";
    const badge = (num, lbl) =>
      el("div", { class: "streak-badge" }, [
        el("div", { class: "streak-num" }, String(num)),
        el("div", { class: "streak-lbl" }, lbl),
      ]);
    wrap.appendChild(badge(streak.current_streak, "Current streak (days)"));
    wrap.appendChild(badge(streak.longest_streak, "Longest streak (days)"));
    if (streak.last_training_date) {
      wrap.appendChild(badge(streak.last_training_date, "Last trained"));
    }
  }

  // ---------- Heatmap ----------

  function renderHeatmap(heatmap) {
    const wrap = $("#stats-heatmap");
    wrap.innerHTML = "";
    if (!heatmap.length) {
      wrap.appendChild(
        el("p", { class: "muted small" }, "No training days yet.")
      );
      return;
    }

    const counts = {};
    let maxCount = 0;
    for (const d of heatmap) {
      counts[d.date] = d.count;
      if (d.count > maxCount) maxCount = d.count;
    }

    const WEEKS = 26;
    const today = new Date();
    const startDate = new Date(today);
    startDate.setDate(
      startDate.getDate() - today.getDay() - (WEEKS - 1) * 7
    );

    const cellSize = 13;
    const gap = 2;
    const step = cellSize + gap;
    const svgW = WEEKS * step;
    const svgH = 7 * step;

    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${svgW} ${svgH}`);
    svg.setAttribute("class", "heatmap-svg");
    svg.style.width = "100%";
    svg.style.maxWidth = `${svgW}px`;

    const colors = [
      "#1d2230", "#1a4a3a", "#1f6b53", "#25a27a", "#6ee7b7",
    ];
    const cur = new Date(startDate);
    for (let col = 0; col < WEEKS; col++) {
      for (let row = 0; row < 7; row++) {
        const iso = cur.toISOString().slice(0, 10);
        const cnt = counts[iso] || 0;
        let colorIdx = 0;
        if (cnt > 0 && maxCount > 0) {
          colorIdx = Math.min(4, Math.ceil((cnt / maxCount) * 4));
        }
        const rect = document.createElementNS(NS, "rect");
        rect.setAttribute("x", col * step);
        rect.setAttribute("y", row * step);
        rect.setAttribute("width", cellSize);
        rect.setAttribute("height", cellSize);
        rect.setAttribute("rx", 2);
        rect.setAttribute("fill", colors[colorIdx]);
        const title = document.createElementNS(NS, "title");
        title.textContent = `${iso}: ${cnt} sets`;
        rect.appendChild(title);
        svg.appendChild(rect);
        cur.setDate(cur.getDate() + 1);
      }
    }
    wrap.appendChild(svg);
  }

  // ---------- Exercise detail (sparklines) ----------

  async function loadExerciseDetail(exId, exName) {
    const panel = $("#stats-exercise-detail");
    const charts = $("#stats-detail-charts");
    $("#stats-detail-name").textContent = exName;
    charts.innerHTML = '<p class="muted small">Loading\u2026</p>';
    panel.classList.remove("hidden");

    const data = await api.get(
      `/api/stats/exercise/${exId}/trend?period=weekly`
    );
    charts.innerHTML = "";

    if (data.trend.length > 0) {
      charts.appendChild(el("p", { class: "lbl" }, "Weekly Volume"));
      charts.appendChild(
        renderSparkline(
          data.trend.map((p) => ({ x: p.period_label, y: p.volume })),
          { color: "var(--accent)", prDates: [] }
        )
      );
    }

    if (data.timeseries.length > 0) {
      const prDates = data.personal_records
        .filter((p) => p.metric === "best_e1rm")
        .map((p) => p.date);
      charts.appendChild(el("p", { class: "lbl" }, "e1RM Progression"));
      charts.appendChild(
        renderSparkline(
          data.timeseries.map((p) => ({ x: p.date, y: p.best_e1rm })),
          { color: "var(--accent-2)", prDates }
        )
      );
    }

    if (!data.trend.length && !data.timeseries.length) {
      charts.appendChild(
        el("p", { class: "muted small" }, "No data yet.")
      );
    }
  }

  function renderSparkline(points, { color, prDates }) {
    if (!points.length) return el("p", { class: "muted small" }, "No data.");

    const W = 300,
      H = 80,
      PAD = { t: 8, r: 8, b: 20, l: 40 };
    const iW = W - PAD.l - PAD.r;
    const iH = H - PAD.t - PAD.b;

    const ys = points.map((p) => p.y);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const rangeY = maxY - minY || 1;
    const n = points.length;

    const px = (i) => PAD.l + (i / Math.max(n - 1, 1)) * iW;
    const py = (v) => PAD.t + iH - ((v - minY) / rangeY) * iH;

    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.setAttribute("class", "sparkline-svg");

    const makeL = (x1, y1, x2, y2) => {
      const line = document.createElementNS(NS, "line");
      line.setAttribute("x1", x1); line.setAttribute("y1", y1);
      line.setAttribute("x2", x2); line.setAttribute("y2", y2);
      line.setAttribute("class", "sparkline-axis");
      return line;
    };
    svg.appendChild(makeL(PAD.l, PAD.t, PAD.l, PAD.t + iH));
    svg.appendChild(makeL(PAD.l, PAD.t + iH, PAD.l + iW, PAD.t + iH));

    const lblY = (v, y) => {
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", PAD.l - 4);
      t.setAttribute("y", y + 4);
      t.setAttribute("text-anchor", "end");
      t.setAttribute("class", "sparkline-label");
      t.textContent = Math.round(v);
      return t;
    };
    svg.appendChild(lblY(minY, PAD.t + iH));
    svg.appendChild(lblY(maxY, PAD.t));

    const pts = points.map((p, i) => `${px(i)},${py(p.y)}`).join(" ");
    const poly = document.createElementNS(NS, "polyline");
    poly.setAttribute("points", pts);
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke", color);
    poly.setAttribute("stroke-width", "2");
    svg.appendChild(poly);

    const prSet = new Set(prDates);
    points.forEach((p, i) => {
      if (prSet.has(p.x.slice(0, 10))) {
        const c = document.createElementNS(NS, "circle");
        c.setAttribute("cx", px(i));
        c.setAttribute("cy", py(p.y));
        c.setAttribute("r", 4);
        c.setAttribute("fill", "var(--warn)");
        const title = document.createElementNS(NS, "title");
        title.textContent = `PR: ${Math.round(p.y)} on ${p.x}`;
        c.appendChild(title);
        svg.appendChild(c);
      }
    });

    const xlbl = (text, x) => {
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", x);
      t.setAttribute("y", H - 2);
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("class", "sparkline-label");
      t.textContent = text;
      return t;
    };
    svg.appendChild(xlbl(points[0].x, px(0)));
    if (n > 1) svg.appendChild(xlbl(points[n - 1].x, px(n - 1)));

    return svg;
  }

  // ---------- Session metrics ----------

  function renderSessions(sessions) {
    const wrap = $("#stats-sessions");
    wrap.innerHTML = "";
    if (!sessions.length) {
      wrap.appendChild(
        el("p", { class: "muted small" }, "No sessions yet.")
      );
      return;
    }
    const rows = sessions
      .slice(0, 10)
      .map(
        (s) =>
          `<tr><td>${s.date}</td><td>${round(s.tonnage)}</td><td>${s.sets}</td><td>${s.exercises}</td></tr>`
      )
      .join("");
    wrap.innerHTML = `<table class="sessions-table">
      <thead><tr><th>Date</th><th>Tonnage</th><th>Sets</th><th>Exercises</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
  }

  // ---------- Strength ratio picker ----------

  async function populateRatioPicker() {
    const exs = await api.get("/api/exercises");
    const opts = exs
      .map((e) => `<option value="${e.id}">${e.name}</option>`)
      .join("");
    const selA = $("#ratio-a");
    const selB = $("#ratio-b");
    selA.innerHTML = '<option value="">Exercise A</option>' + opts;
    selB.innerHTML = '<option value="">Exercise B</option>' + opts;

    const compute = async () => {
      const aId = selA.value;
      const bId = selB.value;
      const disp = $("#stats-ratio");
      if (!aId || !bId || aId === bId) {
        disp.classList.add("hidden");
        return;
      }
      try {
        const r = await api.post("/api/stats/ratio", {
          exercise_a_id: Number(aId),
          exercise_b_id: Number(bId),
        });
        disp.classList.remove("hidden");
        disp.innerHTML =
          r.ratio != null
            ? `<div class="ratio-num">${round(r.ratio)}</div>
               <div class="ratio-sub">${r.name_a} (e1RM ${round(r.e1rm_a)}) &divide; ${r.name_b} (e1RM ${round(r.e1rm_b)})</div>`
            : `<div class="ratio-sub">Not enough data for one or both exercises.</div>`;
      } catch {
        // ignore
      }
    };

    // Avoid duplicate listeners on re-population by cloning
    const newA = selA.cloneNode(true);
    const newB = selB.cloneNode(true);
    selA.parentNode.replaceChild(newA, selA);
    selB.parentNode.replaceChild(newB, selB);
    newA.innerHTML = '<option value="">Exercise A</option>' + opts;
    newB.innerHTML = '<option value="">Exercise B</option>' + opts;
    newA.addEventListener("change", compute);
    newB.addEventListener("change", compute);
  }

  function round(n) {
    if (n == null) return "—";
    return Math.round(Number(n) * 10) / 10;
  }

  // ---------- Catalog (manage exercises / fix typos) ----------

  async function loadCatalog() {
    const list = $("#catalog-list");
    list.innerHTML = "";
    const exs = await api.get("/api/exercises");
    if (!exs.length) {
      list.appendChild(
        el("p", { class: "muted small" }, "No exercises yet — add one in Today.")
      );
      return;
    }
    for (const e of exs) list.appendChild(renderExerciseItem(e, exs));
  }

  function renderExerciseItem(e, all) {
    const meta = el("div", { class: "meta" }, [
      el("span", { class: "title" }, e.name),
      el(
        "span",
        { class: "sub" },
        `used ${e.use_count}× · last ${e.last_used_at || "never"}`
      ),
    ]);
    const actions = el("div", { class: "actions" }, [
      el(
        "button",
        {
          class: "btn icon",
          onclick: async () => {
            const n = prompt("Rename to:", e.name);
            if (!n || n.trim() === e.name) return;
            try {
              await api.put(`/api/exercises/${e.id}`, { name: n.trim() });
              loadCatalog();
              toast("Renamed ✓");
            } catch (err) {
              toast(err.message, "danger");
            }
          },
        },
        "Rename"
      ),
      el(
        "button",
        {
          class: "btn icon",
          onclick: async () => {
            const others = all.filter((x) => x.id !== e.id);
            const choices = others
              .map((x, i) => `${i + 1}. ${x.name}`)
              .join("\n");
            const idx = prompt(
              `Merge "${e.name}" into which? (number)\n\n${choices}`
            );
            if (!idx) return;
            const target = others[Number(idx) - 1];
            if (!target) return toast("Invalid choice", "danger");
            await api.post(`/api/exercises/${e.id}/merge_into/${target.id}`);
            loadCatalog();
            toast("Merged ✓");
          },
        },
        "Merge"
      ),
      el(
        "button",
        {
          class: "btn icon danger",
          onclick: async () => {
            if (
              !confirm(
                `Delete "${e.name}" and ALL its set history? This cannot be undone.`
              )
            )
              return;
            await api.delete(`/api/exercises/${e.id}`);
            loadCatalog();
            toast("Deleted");
          },
        },
        "✕"
      ),
    ]);
    return el("div", { class: "item" }, [meta, actions]);
  }

  // ---------- Init ----------

  function bindButtons() {
    $("#start-workout").addEventListener("click", startWorkout);
    $("#add-set").addEventListener("click", () => addSet(true));
    $("#add-planned").addEventListener("click", () => addSet(false));
    $("#finish-workout").addEventListener("click", finishWorkout);
    $("#preview-plan").addEventListener("click", previewPlan);
    $("#save-plan").addEventListener("click", savePlan);
    $("#plan-date").value = localDateISO();
    $("#stats-detail-close").addEventListener("click", () => {
      $("#stats-exercise-detail").classList.add("hidden");
    });
  }

  function init() {
    bindTabs();
    bindAutocomplete();
    bindButtons();
    tryResumeActive();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
