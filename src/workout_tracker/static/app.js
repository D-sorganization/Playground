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
      _lastActive = w;
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
    stopTimers();
    releaseWakeLock();
  }

  async function refreshActiveWorkout() {
    if (!state.activeWorkoutId) return;
    const w = await api.get(`/api/workouts/${state.activeWorkoutId}`);
    _lastActive = w;
    renderActive(w);
  }

  function renderActive(w) {
    $("#active-empty").classList.add("hidden");
    $("#active-workout").classList.remove("hidden");
    $("#today-date").textContent = w.date;
    $("#today-title").textContent = w.title || "Today's Workout";
    startTimers();
    acquireWakeLock();

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
              startRestTimer();
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
    scheduleRecall();
    $("#reps-input").focus();
  }

  function bindAutocomplete() {
    const input = $("#ex-input");
    const ul = $("#ex-suggest");
    let lastTimer;
    input.addEventListener("input", () => {
      clearTimeout(lastTimer);
      lastTimer = setTimeout(() => refreshSuggestions(input.value), 80);
      scheduleRecall();
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
    if (executed) startRestTimer();
    invalidateRecallFor(name);
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
    stopTimers();
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

  // ---------- Voice input (#295) ----------
  // Progressive enhancement: the button stays hidden on browsers without
  // webkitSpeechRecognition / SpeechRecognition. On supported browsers,
  // a tap starts a single-utterance listen; transcript is parsed by
  // WorkoutLib.parseVoiceCommand and used to populate the set form
  // (and submit immediately if fully specified).
  const voice = { rec: null, active: false };

  function getSpeechRecognition() {
    return (
      window.SpeechRecognition ||
      window.webkitSpeechRecognition ||
      null
    );
  }

  function bindVoiceInput() {
    const btn = $("#voice-btn");
    if (!btn) return;
    const Ctor = getSpeechRecognition();
    if (!Ctor) {
      // Leave button hidden; feature unavailable.
      return;
    }
    btn.classList.remove("hidden");
    btn.addEventListener("click", () => {
      if (voice.active) {
        stopListening();
      } else {
        startListening(Ctor);
      }
    });
  }

  function startListening(Ctor) {
    const btn = $("#voice-btn");
    const label = $("#voice-label");
    try {
      const rec = new Ctor();
      rec.lang = navigator.language || "en-US";
      rec.interimResults = false;
      rec.maxAlternatives = 3;
      rec.continuous = false;
      rec.onstart = () => {
        voice.active = true;
        btn.setAttribute("aria-pressed", "true");
        if (label) label.textContent = "Listening…";
      };
      rec.onerror = (e) => {
        toast(`Voice error: ${e.error || "unknown"}`, "danger");
      };
      rec.onend = () => {
        voice.active = false;
        voice.rec = null;
        btn.setAttribute("aria-pressed", "false");
        if (label) label.textContent = "Voice";
      };
      rec.onresult = (e) => {
        const lib = window.WorkoutLib;
        let parsed = null;
        let transcript = "";
        const alts = e.results[0] || [];
        for (let i = 0; i < alts.length; i++) {
          transcript = alts[i].transcript;
          if (!lib) break;
          parsed = lib.parseVoiceCommand(transcript);
          if (parsed) break;
        }
        if (!parsed) {
          // Populate exercise field with raw transcript so user can finish by hand.
          if (transcript) {
            $("#ex-input").value = transcript.trim();
            scheduleRecall();
            toast(`Heard: "${transcript}" — finish manually`, "danger");
          } else {
            toast("Didn't catch that", "danger");
          }
          return;
        }
        applyVoiceResult(parsed);
      };
      voice.rec = rec;
      rec.start();
    } catch (err) {
      toast(`Voice unavailable: ${err.message || err}`, "danger");
    }
  }

  function stopListening() {
    if (voice.rec) {
      try {
        voice.rec.stop();
      } catch {
        /* ignore */
      }
    }
  }

  function applyVoiceResult(parsed) {
    $("#ex-input").value = parsed.exercise;
    if (parsed.reps != null) $("#reps-input").value = String(parsed.reps);
    if (parsed.weight != null) $("#weight-input").value = String(parsed.weight);
    if (parsed.unit) $("#unit-input").value = parsed.unit;
    scheduleRecall();
    // If we got a full triple, auto-log it.
    if (parsed.exercise && parsed.reps != null && parsed.weight != null) {
      addSet(true);
    }
  }

  // ---------- Last-session recall strip (#295) ----------

  let _recallTimer = null;
<<<<<<< HEAD
  const _recallCache = new Map(); // normalized-name → payload
=======
  const _recallCache = new Map(); // active-workout-id::normalized-name → payload

  function recallCacheKey(name) {
    const workoutKey = state.activeWorkoutId ? String(state.activeWorkoutId) : "none";
    return `${workoutKey}::${name.trim().toLowerCase()}`;
  }
>>>>>>> origin/main

  function daysAgo(iso) {
    if (!iso) return null;
    const then = new Date(iso + "T00:00:00");
    const now = new Date();
    const midnightNow = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const diffMs = midnightNow - then;
    return Math.max(0, Math.round(diffMs / 86400000));
  }

  function renderRecall(payload) {
    const strip = $("#recall-strip");
    if (!strip) return;
    if (!payload || !payload.sets || !payload.sets.length) {
      strip.classList.add("hidden");
      strip.innerHTML = "";
      return;
    }
    const lib = window.WorkoutLib;
    const line = lib
      ? lib.formatRecall(payload.sets)
      : payload.sets
          .map((s) => `${s.reps}×${s.weight}`)
          .join(", ");
    strip.innerHTML = "";
    strip.appendChild(el("span", { class: "tag" }, "Last"));
    strip.appendChild(el("span", { class: "name" }, payload.exercise_name));
    strip.appendChild(document.createTextNode(line));
    const d = daysAgo(payload.date);
    if (d != null) {
      strip.appendChild(
        el("span", { class: "when" }, d === 0 ? "today" : `${d}d ago`)
      );
    }
    strip.classList.remove("hidden");
  }

  async function refreshRecall() {
    const name = $("#ex-input").value.trim();
    const strip = $("#recall-strip");
    if (!strip) return;
    if (!name) {
      strip.classList.add("hidden");
      strip.innerHTML = "";
      return;
    }
<<<<<<< HEAD
    const key = name.toLowerCase();
=======
    const key = recallCacheKey(name);
    const normalizedName = name.toLowerCase();
>>>>>>> origin/main
    if (_recallCache.has(key)) {
      renderRecall(_recallCache.get(key));
      return;
    }
    try {
      const params = new URLSearchParams({ q: name });
      if (state.activeWorkoutId) {
        params.set("exclude", String(state.activeWorkoutId));
      }
      const payload = await api.get(
        `/api/exercises/last_session?${params.toString()}`,
      );
      _recallCache.set(key, payload);
      // Only render if the user hasn't typed ahead.
<<<<<<< HEAD
      if ($("#ex-input").value.trim().toLowerCase() === key) {
=======
      if ($("#ex-input").value.trim().toLowerCase() === normalizedName) {
>>>>>>> origin/main
        renderRecall(payload);
      }
    } catch {
      strip.classList.add("hidden");
    }
  }

  function scheduleRecall() {
    clearTimeout(_recallTimer);
    _recallTimer = setTimeout(refreshRecall, 200);
  }

  function invalidateRecallFor(name) {
<<<<<<< HEAD
    if (name) _recallCache.delete(name.trim().toLowerCase());
=======
    if (!name) return;
    const suffix = `::${name.trim().toLowerCase()}`;
    for (const key of _recallCache.keys()) {
      if (key.endsWith(suffix)) _recallCache.delete(key);
    }
>>>>>>> origin/main
  }

  // ---------- Screen Wake Lock (#295) ----------
  // Progressive enhancement: no-op on browsers without navigator.wakeLock.
  // Acquired when an active workout renders, released on finish / tab hide.
  // Re-acquired automatically on visibilitychange (the Wake Lock API
  // releases the sentinel when the tab is backgrounded).
  const wake = { sentinel: null, wanted: false };

  async function acquireWakeLock() {
    wake.wanted = true;
    if (!("wakeLock" in navigator)) return;
    if (wake.sentinel) return;
    try {
      wake.sentinel = await navigator.wakeLock.request("screen");
      wake.sentinel.addEventListener("release", () => {
        wake.sentinel = null;
      });
    } catch (err) {
      // Permission denied / not allowed — silently fall back.
      console.debug("wakeLock.request failed:", err && err.message);
    }
  }

  async function releaseWakeLock() {
    wake.wanted = false;
    if (wake.sentinel) {
      try {
        await wake.sentinel.release();
      } catch {
        /* ignore */
      }
      wake.sentinel = null;
    }
  }

  function bindWakeLockLifecycle() {
    if (!("wakeLock" in navigator)) return;
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible" && wake.wanted) {
        acquireWakeLock();
      }
    });
  }

  // ---------- Timers (#295) ----------
  // Session: counts UP from when active workout became visible.
  // Rest: counts UP from the last ✓ executed set (or manual reset).
  const timers = {
    sessionStart: null, // ms
    restStart: null,    // ms (null = idle)
    tick: null,         // setInterval handle
  };

  function fmtMMSS(totalSec) {
    // Prefer shared lib; fallback keeps timer UI alive if lib.js 404's.
    if (window.WorkoutLib && window.WorkoutLib.fmtMMSS) {
      return window.WorkoutLib.fmtMMSS(totalSec);
    }
    const s = Math.max(0, Math.floor(totalSec));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  }

  function startTimers() {
    if (timers.sessionStart == null) timers.sessionStart = Date.now();
    if (timers.tick == null) {
      timers.tick = setInterval(renderTimers, 1000);
    }
    renderTimers();
  }

  function stopTimers() {
    if (timers.tick != null) {
      clearInterval(timers.tick);
      timers.tick = null;
    }
    timers.sessionStart = null;
    timers.restStart = null;
    const s = $("#session-timer");
    const r = $("#rest-timer");
    if (s) s.textContent = "00:00";
    if (r) {
      r.textContent = "—";
      $(".timers .timer.rest")?.classList.remove("running");
    }
  }

  function renderTimers() {
    const now = Date.now();
    const sessEl = $("#session-timer");
    const restEl = $("#rest-timer");
    const restBox = $(".timers .timer.rest");
    if (sessEl && timers.sessionStart != null) {
      sessEl.textContent = fmtMMSS((now - timers.sessionStart) / 1000);
    }
    if (restEl) {
      if (timers.restStart != null) {
        restEl.textContent = fmtMMSS((now - timers.restStart) / 1000);
        restBox?.classList.add("running");
      } else {
        restEl.textContent = "—";
        restBox?.classList.remove("running");
      }
    }
  }

  function startRestTimer() {
    timers.restStart = Date.now();
    renderTimers();
  }

  function resetRestTimer() {
    timers.restStart = null;
    renderTimers();
  }

  // ---------- Repeat last set (#295) ----------

  // Cache of the most recent active-workout payload, so Repeat Last Set
  // can read `sets` without a round-trip.
  let _lastActive = null;

  function pickLastSet(workout, exerciseName) {
    if (!workout || !workout.sets || !workout.sets.length) return null;
    const sets = workout.sets;
    if (exerciseName) {
      const needle = exerciseName.trim().toLowerCase();
      for (let i = sets.length - 1; i >= 0; i--) {
        const s = sets[i];
        if ((s.exercise_name || "").toLowerCase() === needle) return s;
      }
    }
    // Fallback: most recent set in the workout, regardless of exercise.
    return sets[sets.length - 1];
  }

  async function repeatLastSet() {
    const wid = state.activeWorkoutId;
    if (!wid) return toast("Start a workout first", "danger");
    const workout = _lastActive || (await api.get(`/api/workouts/${wid}`));
    _lastActive = workout;
    const nameHint = $("#ex-input").value.trim();
    const last = pickLastSet(workout, nameHint);
    if (!last) return toast("No previous set to repeat", "danger");
    const body = {
      exercise_name: last.exercise_name,
      unit: last.unit || "lbs",
      executed: true,
      actual_reps: last.actual_reps ?? last.planned_reps ?? null,
      actual_weight: last.actual_weight ?? last.planned_weight ?? null,
      rpe: last.rpe ?? null,
    };
    await api.post(`/api/workouts/${wid}/sets`, body);
    startRestTimer();
    toast(
      `Repeated ${body.exercise_name}: ${body.actual_reps ?? "?"}` +
        (body.actual_weight != null ? ` × ${body.actual_weight}${body.unit}` : ""),
    );
    refreshActiveWorkout();
  }

  // ---------- Quick weight ± steppers (#295) ----------

  function bindWeightSteppers() {
    const input = $("#weight-input");
    if (!input) return;
    $$(".weight-steps .step").forEach((btn) => {
      btn.addEventListener("click", () => {
        const lib = window.WorkoutLib;
        const delta = Number(btn.dataset.step);
        const current = input.value === "" ? 0 : Number(input.value);
        const next = lib
          ? lib.stepWeight(current, delta)
          : Math.max(0, Math.round((current + delta) * 4) / 4);
        input.value = String(next);
        // Fire input event so any listeners (e.g. plate modal when open) update.
        input.dispatchEvent(new Event("input", { bubbles: true }));
      });
    });
  }

  // ---------- Plate calculator modal (#295) ----------

  function openPlateModal() {
    const modal = $("#plate-modal");
    if (!modal) return;
    // Seed target with the current weight-input value and unit.
    const w = $("#weight-input").value;
    const unit = $("#unit-input").value || "lbs";
    $("#plate-target").value = w || "";
    $("#plate-unit").value = unit;
    // Default bar: 45 lbs, 20 kg. Preserve user override via localStorage.
    const savedBar = localStorage.getItem(`plate_bar_${unit}`);
    $("#plate-bar").value = savedBar || (unit === "kg" ? 20 : 45);
    modal.classList.remove("hidden");
    renderPlateResult();
    $("#plate-target").focus();
  }

  function closePlateModal() {
    const modal = $("#plate-modal");
    if (modal) modal.classList.add("hidden");
  }

  function renderPlateResult() {
    const lib = window.WorkoutLib;
    const out = $("#plate-result");
    if (!lib || !out) return;
    const target = Number($("#plate-target").value);
    const bar = Number($("#plate-bar").value);
    const unit = $("#plate-unit").value || "lbs";
    localStorage.setItem(`plate_bar_${unit}`, String(bar));
    if (!target) {
      out.innerHTML = "";
      return;
    }
    const plates = unit === "kg" ? lib.DEFAULT_PLATES_KG : lib.DEFAULT_PLATES_LBS;
    const r = lib.platesFor(target, bar, plates);
    out.innerHTML = "";
    out.appendChild(
      el("div", { class: "headline" }, lib.formatPlates(r))
    );
    if (r.perSide && r.perSide.length) {
      const chips = el("div", { class: "plates" });
      for (const p of r.perSide) {
        chips.appendChild(
          el("span", { class: "chip" }, `${p.count} × ${p.plate}${unit}`)
        );
      }
      out.appendChild(chips);
    }
    if (r.warning === "below_bar") {
      out.appendChild(
        el("div", { class: "warn" }, `Target is below bar weight (${bar}${unit}).`)
      );
    } else if (r.leftover && r.leftover > 0) {
      out.appendChild(
        el(
          "div",
          { class: "warn" },
          `Short by ${r.leftover}${unit} (achievable: ${r.achievable}${unit}).`
        )
      );
    }
  }

  function bindPlateModal() {
    const btn = $("#plate-open");
    if (!btn) return;
    btn.addEventListener("click", openPlateModal);
    $("#plate-close").addEventListener("click", closePlateModal);
    $("#plate-modal").addEventListener("click", (e) => {
      if (e.target === $("#plate-modal")) closePlateModal();
    });
    ["input", "change"].forEach((evt) => {
      $("#plate-target").addEventListener(evt, renderPlateResult);
      $("#plate-bar").addEventListener(evt, renderPlateResult);
      $("#plate-unit").addEventListener(evt, renderPlateResult);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !$("#plate-modal").classList.contains("hidden")) {
        closePlateModal();
      }
    });
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
    // Sort by completed_at descending so we pick the most recently *executed*
    // set, not just the highest-position one (issue #336: sets checked out of
    // order would otherwise repeat the wrong set).
    executed.sort((a, b) => {
      const ta = a.completed_at || "";
      const tb = b.completed_at || "";
      return tb < ta ? -1 : tb > ta ? 1 : b.position - a.position;
    });
    const last = executed[0];
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
    $("#repeat-set").addEventListener("click", repeatLastSet);
    $("#add-planned").addEventListener("click", () => addSet(false));
    $("#finish-workout").addEventListener("click", finishWorkout);
    $("#rest-reset").addEventListener("click", resetRestTimer);
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
    bindWeightSteppers();
    bindPlateModal();
    bindWakeLockLifecycle();
    bindVoiceInput();
    tryResumeActive();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
