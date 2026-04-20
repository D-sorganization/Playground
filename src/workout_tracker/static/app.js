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
    const data = await api.get("/api/stats/overview");
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
    for (const s of data.per_exercise) {
      sum.appendChild(
        el("div", { class: "item" }, [
          el("div", { class: "meta" }, [
            el("span", { class: "title" }, s.exercise_name),
            el(
              "span",
              { class: "sub" },
              `${s.total_sets} sets · ${s.total_reps} reps · vol ${round(s.total_volume)} · top ${s.max_weight}×${s.max_reps_at_max_weight} · e1RM ${round(s.best_e1rm)}`
            ),
          ]),
        ])
      );
    }

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

  // Adjust the weight input by a delta (quick ± buttons). Treats an empty
  // input as 0. Rounds to 2 decimals to avoid float-noise like 137.50000001.
  function adjustWeight(delta) {
    const inp = $("#weight-input");
    const cur = inp.value === "" ? 0 : Number(inp.value);
    if (!Number.isFinite(cur)) return;
    let next = cur + Number(delta);
    if (next < 0) next = 0;
    inp.value = String(Math.round(next * 100) / 100);
  }

  // Repeat the most recent logged (executed) set in the active workout.
  // Clones exercise/reps/weight/unit/rpe into a new executed set so the
  // user can keep logging at-pace between work sets.
  async function repeatLastSet() {
    if (!state.activeWorkoutId) return toast("Start a workout first", "danger");
    const w = await api.get(`/api/workouts/${state.activeWorkoutId}`);
    const executed = (w.sets || []).filter((s) => s.executed);
    if (!executed.length) return toast("No logged sets to repeat", "danger");
    const last = executed[executed.length - 1];
    const body = {
      exercise_name: last.exercise_name,
      unit: last.unit || "lbs",
      executed: true,
      actual_reps: last.actual_reps ?? null,
      actual_weight: last.actual_weight ?? null,
      rpe: last.rpe ?? null,
    };
    await api.post(`/api/workouts/${state.activeWorkoutId}/sets`, body);
    toast("Set repeated ✓");
    refreshActiveWorkout();
  }

  function bindButtons() {
    $("#start-workout").addEventListener("click", startWorkout);
    $("#add-set").addEventListener("click", () => addSet(true));
    $("#add-planned").addEventListener("click", () => addSet(false));
    $("#finish-workout").addEventListener("click", finishWorkout);
    $("#preview-plan").addEventListener("click", previewPlan);
    $("#save-plan").addEventListener("click", savePlan);
    $("#plan-date").value = localDateISO();
    const repeatBtn = $("#repeat-last-set");
    if (repeatBtn) repeatBtn.addEventListener("click", repeatLastSet);
    $$(".weight-quick .wq").forEach((b) =>
      b.addEventListener("click", () => adjustWeight(b.dataset.delta))
    );
  }

  function init() {
    bindTabs();
    bindAutocomplete();
    bindButtons();
    tryResumeActive();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
