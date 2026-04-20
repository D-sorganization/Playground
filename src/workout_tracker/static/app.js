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

  function toast(msg, type = "ok", undoFn = null) {
    const t = $("#toast");
    t.innerHTML = "";
    t.appendChild(document.createTextNode(msg));
    if (undoFn) {
      const btn = el(
        "button",
        {
          class: "toast-undo",
          onclick: () => {
            clearTimeout(t._tm);
            t.classList.add("hidden");
            undoFn();
          },
        },
        "Undo"
      );
      t.appendChild(btn);
    }
    t.className = `toast${type === "danger" ? " danger" : ""}`;
    setTimeout(() => t.classList.add("hidden"), 10);
    requestAnimationFrame(() => {
      t.classList.remove("hidden");
      clearTimeout(t._tm);
      const delay = undoFn ? 5000 : 2200;
      t._tm = setTimeout(() => t.classList.add("hidden"), delay);
    });
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    const btn = $("#theme-toggle");
    if (btn) btn.textContent = theme === "light" ? "☽" : "☀";
  }

  function initTheme() {
    const stored = localStorage.getItem("theme");
    if (stored) {
      applyTheme(stored);
    } else {
      const preferLight = window.matchMedia("(prefers-color-scheme: light)").matches;
      applyTheme(preferLight ? "light" : "dark");
    }
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem("theme", next);
    applyTheme(next);
  }

  function switchToTab(tabName) {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    $$(".panel").forEach((x) => x.classList.remove("active"));
    const tabBtn = $(`.tab[data-tab="${tabName}"]`);
    if (tabBtn) tabBtn.classList.add("active");
    const panel = $(`#tab-${tabName}`);
    if (panel) panel.classList.add("active");
    if (tabName === "history") loadHistory();
    if (tabName === "stats") loadStats();
    if (tabName === "plans") loadPlans();
    if (tabName === "catalog") loadCatalog();
  }

  function fmtWeight(s) {
    const w = s.actual_weight ?? s.planned_weight;
    const unit = s.unit || "lbs";
    if (s.is_bodyweight) {
      return w != null ? `BW+${w}${unit}` : "BW";
    }
    return w != null ? `${w}${unit}` : null;
  }

  function fmtSet(s) {
    const r = s.actual_reps ?? s.planned_reps ?? "?";
    const wStr = fmtWeight(s);
    const main = wStr == null ? `${r}` : `${r} × ${wStr}`;
    const rpe = s.rpe ? ` · RPE ${s.rpe}` : "";
    return main + rpe;
  }

  const PROTOCOL_LABELS = {
    amrap: "AMRAP",
    emom: "EMOM",
    drop_set: "DROP",
    failure: "FAIL",
    partials: "PART",
  };

  // ---------- State ----------
  const state = {
    activeWorkoutId: null,
    catalog: [],          // [Exercise]
    pendingExercise: null,
    suggestFocus: -1,
    // Timers (GH295)
    sessionStart: null,     // Date — when current workout started
    sessionTimerHandle: null,
    restStart: null,        // Date — when last rest started
    restTimerHandle: null,
    // Wake lock (GH295)
    wakeLock: null,
  };

  // ---------- Tabs ----------
  function bindTabs() {
    $$(".tab").forEach((t) =>
      t.addEventListener("click", () => switchToTab(t.dataset.tab))
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
    startSessionTimer();
    await acquireWakeLock();
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
      startSessionTimer();
      await acquireWakeLock();
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
    const groupBadge = s.group_id
      ? el("span", { class: "pill group-badge" }, s.group_id)
      : null;
    const protoBadge = s.protocol
      ? el("span", { class: "pill proto-badge" }, PROTOCOL_LABELS[s.protocol] || s.protocol)
      : null;
    const meta = el("div", { class: "meta" }, [
      el("span", { class: "pill" }, `Set ${n}`),
      groupBadge,
      el("span", {}, fmtSet(s)),
      protoBadge,
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
    // Repeat last set button (GH295) — clone this set's reps/weight into the form
    actions.appendChild(
      el(
        "button",
        {
          class: "btn icon repeat-set",
          title: "Repeat this set",
          onclick: () => {
            const reps = s.actual_reps ?? s.planned_reps;
            const weight = s.actual_weight ?? s.planned_weight;
            if (reps != null) $("#reps-input").value = reps;
            if (weight != null) $("#weight-input").value = weight;
            const exName = s.exercise_name;
            if (exName) {
              $("#ex-input").value = exName;
              refreshLastSession(exName);
            }
            toast("Set pre-filled ⟳");
          },
        },
        "⟳"
      )
    );
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
            toast("Set deleted", "ok", async () => {
              await api.post(`/api/sets/${s.id}/restore`);
              refreshActiveWorkout();
            });
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
    refreshLastSession(name);
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
    if (executed) startRestTimer();
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
    stopSessionTimer();
    stopRestTimer();
    releaseWakeLock();
    showEmpty();
    toast("Workout saved ✓");
  }

  // ---------- Session timer (GH295) ----------

  function startSessionTimer() {
    state.sessionStart = Date.now();
    clearInterval(state.sessionTimerHandle);
    state.sessionTimerHandle = setInterval(tickSessionTimer, 1000);
    tickSessionTimer();
  }

  function stopSessionTimer() {
    clearInterval(state.sessionTimerHandle);
    state.sessionTimerHandle = null;
    state.sessionStart = null;
    const el = $("#session-timer");
    if (el) el.textContent = "0:00";
  }

  function tickSessionTimer() {
    if (!state.sessionStart) return;
    const el = $("#session-timer");
    if (!el) return;
    const secs = Math.floor((Date.now() - state.sessionStart) / 1000);
    el.textContent = fmtDuration(secs);
  }

  // ---------- Rest timer (GH295) ----------

  function startRestTimer() {
    state.restStart = Date.now();
    clearInterval(state.restTimerHandle);
    state.restTimerHandle = setInterval(tickRestTimer, 1000);
    tickRestTimer();
  }

  function stopRestTimer() {
    clearInterval(state.restTimerHandle);
    state.restTimerHandle = null;
    state.restStart = null;
    const el = $("#rest-timer");
    if (el) {
      el.textContent = "—";
      el.className = "timer-val rest-idle";
    }
  }

  function tickRestTimer() {
    if (!state.restStart) return;
    const el = $("#rest-timer");
    if (!el) return;
    const secs = Math.floor((Date.now() - state.restStart) / 1000);
    el.textContent = fmtDuration(secs);
    el.className = "timer-val rest-active";
  }

  function fmtDuration(secs) {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  // ---------- Screen Wake Lock (GH295) ----------

  async function acquireWakeLock() {
    if (!("wakeLock" in navigator)) return;
    try {
      state.wakeLock = await navigator.wakeLock.request("screen");
      state.wakeLock.addEventListener("release", () => {
        state.wakeLock = null;
      });
    } catch {
      // Wake lock not available — silently ignore
    }
  }

  function releaseWakeLock() {
    if (state.wakeLock) {
      state.wakeLock.release().catch(() => {});
      state.wakeLock = null;
    }
  }

  // Re-acquire wake lock when page becomes visible again (browser may revoke on hide)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && state.activeWorkoutId && !state.wakeLock) {
      acquireWakeLock();
    }
  });

  // ---------- Last-session recall (GH295) ----------

  async function refreshLastSession(exerciseName) {
    const strip = $("#last-session-strip");
    if (!strip) return;
    strip.classList.add("hidden");
    strip.innerHTML = "";
    if (!exerciseName || !exerciseName.trim()) return;
    try {
      const sets = await api.get(
        `/api/last_session_sets?exercise_name=${encodeURIComponent(exerciseName)}&limit=10`
      );
      if (!sets.length) return;
      const lbl = el("span", { class: "lss-label" }, "Last:");
      strip.appendChild(lbl);
      sets.forEach((s) => {
        const txt = fmtSet(s);
        const chip = el("span", {
          class: "lss-set",
          title: "Click to fill weight/reps",
          onclick: () => {
            const reps = s.actual_reps ?? s.planned_reps;
            const weight = s.actual_weight ?? s.planned_weight;
            if (reps != null) $("#reps-input").value = reps;
            if (weight != null) $("#weight-input").value = weight;
          },
        }, txt);
        strip.appendChild(chip);
      });
      strip.classList.remove("hidden");
    } catch {
      // silently ignore
    }
  }

  // ---------- Quick weight ± (GH295) ----------

  function bindWeightAdj() {
    $$(".adj-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const delta = parseFloat(btn.dataset.delta);
        const input = $("#weight-input");
        const cur = parseFloat(input.value) || 0;
        const next = Math.max(0, Math.round((cur + delta) * 100) / 100);
        input.value = next;
      });
    });
  }

  // ---------- Plate calculator modal (GH295) ----------

  const PLATE_SIZES_LBS = [45, 35, 25, 10, 5, 2.5];
  const PLATE_SIZES_KG = [20, 15, 10, 5, 2.5, 1.25];

  function calcPlates(targetWeight, barWeight, unit) {
    const sizes = unit === "kg" ? PLATE_SIZES_KG : PLATE_SIZES_LBS;
    const perSide = (targetWeight - barWeight) / 2;
    if (perSide < 0) return null; // impossible
    let remaining = perSide;
    const result = [];
    for (const size of sizes) {
      const count = Math.floor(remaining / size + 1e-9);
      if (count > 0) {
        result.push({ size, count });
        remaining -= count * size;
      }
    }
    if (remaining > 0.01) return null; // can't make it exactly
    return result;
  }

  function renderPlateResult() {
    const target = parseFloat($("#plate-target").value) || 0;
    const bar = parseFloat($("#plate-bar").value) || 45;
    const unit = $("#plate-unit").value;
    const div = $("#plate-result");
    if (!target) { div.innerHTML = ""; return; }
    const plates = calcPlates(target, bar, unit);
    if (plates === null) {
      div.innerHTML = `<span class="plate-err">Cannot make ${target}${unit} with standard plates + ${bar}${unit} bar.</span>`;
      return;
    }
    if (plates.length === 0) {
      div.innerHTML = `<span style="color:var(--fg-muted)">Just the bar (${bar}${unit})</span>`;
      return;
    }
    div.innerHTML = plates
      .map(
        (p) =>
          `<div class="plate-each">
            <span class="plate-weight">${p.size}${unit}</span>
            <span class="plate-count">× ${p.count} per side</span>
           </div>`
      )
      .join("");
  }

  function bindPlateCalc() {
    const btn = $("#plate-calc-btn");
    const modal = $("#plate-modal");
    const close = $("#plate-modal-close");
    if (!btn || !modal) return;

    btn.addEventListener("click", () => {
      // Pre-fill from current weight input
      const w = parseFloat($("#weight-input").value);
      if (w > 0) $("#plate-target").value = w;
      $("#plate-unit").value = $("#unit-input").value;
      modal.classList.remove("hidden");
      renderPlateResult();
      $("#plate-target").focus();
    });
    close.addEventListener("click", () => modal.classList.add("hidden"));
    modal.addEventListener("click", (e) => {
      if (e.target === modal) modal.classList.add("hidden");
    });
    ["plate-target", "plate-bar", "plate-unit"].forEach((id) =>
      $(`#${id}`).addEventListener("input", renderPlateResult)
    );
  }

  // ---------- Voice input (GH295) ----------

  function bindVoiceInput() {
    const btn = $("#voice-btn");
    const status = $("#voice-status");
    if (!btn) return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      btn.title = "Voice input not supported in this browser";
      btn.disabled = true;
      return;
    }

    let recognition = null;

    btn.addEventListener("click", () => {
      if (recognition) {
        recognition.stop();
        return;
      }
      recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        btn.classList.add("active");
        status.classList.remove("hidden");
      };

      recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript.toLowerCase().trim();
        parseVoiceInput(transcript);
      };

      recognition.onerror = () => {
        toast("Voice input failed", "danger");
      };

      recognition.onend = () => {
        recognition = null;
        btn.classList.remove("active");
        status.classList.add("hidden");
      };

      recognition.start();
    });
  }

  /**
   * Parse voice transcript like "bench press 5 by 135" or "squat 3 reps 225".
   * Fills exercise name, reps, weight fields.
   */
  function parseVoiceInput(transcript) {
    // Patterns: "exercise N by W", "exercise N x W", "exercise N reps W"
    const match = transcript.match(
      /^(.+?)\s+(\d+)\s+(?:by|x|reps?|×)\s+([\d.]+)/i
    );
    if (match) {
      const exName = match[1].trim();
      const reps = match[2];
      const weight = match[3];
      if (exName) $("#ex-input").value = toTitleCase(exName);
      if (reps) $("#reps-input").value = reps;
      if (weight) $("#weight-input").value = weight;
      refreshLastSession(toTitleCase(exName));
      toast(`Voice: "${transcript}"`);
      return;
    }
    // Fallback: just set exercise name
    $("#ex-input").value = toTitleCase(transcript);
    refreshLastSession(toTitleCase(transcript));
    toast(`Voice: "${transcript}"`);
  }

  function toTitleCase(str) {
    return str.replace(/\b\w/g, (c) => c.toUpperCase());
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
            .map((s) => {
              const wStr = s.is_bodyweight
                ? (s.weight != null ? `BW+${s.weight}${s.unit}` : "BW")
                : (s.weight != null ? `${s.weight}${s.unit}` : "");
              const proto = s.protocol ? ` [${s.protocol.toUpperCase()}]` : "";
              return `  · ${s.reps}${wStr ? ` × ${wStr}` : ""}${s.rpe ? ` @RPE${s.rpe}` : ""}${proto}`;
            })
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
            toast("Workout deleted", "ok", async () => {
              await api.post(`/api/workouts/${w.id}/restore`);
              isPlan ? loadPlans() : loadHistory();
            });
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

  function renderTagChips(tagsStr) {
    if (!tagsStr) return null;
    const chips = tagsStr
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
    if (!chips.length) return null;
    return el("div", { class: "tags" }, chips.map((t) => el("span", { class: "tag-chip" }, t)));
  }

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
    const tagChips = renderTagChips(e.muscle_tags);
    const metaKids = [
      el("span", { class: "title" }, e.name),
      el(
        "span",
        { class: "sub" },
        `used ${e.use_count}× · last ${e.last_used_at || "never"}`
      ),
    ];
    if (tagChips) metaKids.push(tagChips);
    const meta = el("div", { class: "meta" }, metaKids);
    const actions = el("div", { class: "actions" }, [
      el(
        "button",
        {
          class: "btn icon",
          onclick: async () => {
            const current = e.muscle_tags || "";
            const t = prompt(
              "Muscle tags (comma-separated, e.g. chest,shoulders):",
              current
            );
            if (t === null) return;
            try {
              await api.put(`/api/exercises/${e.id}/tags`, { tags: t });
              loadCatalog();
              toast("Tags updated ✓");
            } catch (err) {
              toast(err.message, "danger");
            }
          },
        },
        "Tags"
      ),
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
            toast("Deleted", "ok", async () => {
              await api.post(`/api/exercises/${e.id}/restore`);
              loadCatalog();
            });
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

  function activeTab() {
    const t = $(".tab.active");
    return t ? t.dataset.tab : null;
  }

  function bindKeyboardShortcuts() {
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      if (e.key === "/") {
        const inp = $("#ex-input");
        if (inp) {
          e.preventDefault();
          switchToTab("today");
          inp.focus();
          inp.select();
        }
        return;
      }

      if (e.key === "Escape") {
        if (document.activeElement) document.activeElement.blur();
        const ul = $("#ex-suggest");
        if (ul) ul.classList.add("hidden");
        return;
      }

      const focused = document.activeElement;
      const tag = focused && focused.tagName;
      if (tag && ["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;

      if (e.key === "t") {
        switchToTab("today");
      } else if (e.key === "n") {
        switchToTab("today");
        if (!state.activeWorkoutId) startWorkout();
      } else if (e.key === "s") {
        if (activeTab() === "today" && state.activeWorkoutId) {
          addSet(true);
        }
      }
    });
  }

  function init() {
    bindTabs();
    bindAutocomplete();
    bindButtons();
    const themeBtn = $("#theme-toggle");
    if (themeBtn) themeBtn.addEventListener("click", toggleTheme);
    initTheme();
    bindKeyboardShortcuts();
    bindWeightAdj();
    bindPlateCalc();
    bindVoiceInput();
    tryResumeActive();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
