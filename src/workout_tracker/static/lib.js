/* Pure logic shared between the browser UI and Node-based tests.
 * No DOM, no fetch, no timers. Exports both as `window.WorkoutLib`
 * (browser) and CommonJS `module.exports` (node / tests).
 *
 * Keep this file framework-free and side-effect-free.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.WorkoutLib = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Standard plates commonly available in commercial gyms.
  const DEFAULT_PLATES_LBS = [45, 35, 25, 10, 5, 2.5];
  const DEFAULT_PLATES_KG = [25, 20, 15, 10, 5, 2.5, 1.25];

  /**
   * Compute which plates to load PER SIDE to reach `target` total weight,
   * given a bar of `barWeight` and an available plate list (descending).
   *
   * Returns { perSide: [{plate, count}], leftover, achievable }.
   *  - leftover: residual weight (per side × 2) that couldn't be matched.
   *  - achievable: target - leftover (actual total weight loaded).
   *
   * Target below bar weight returns empty plates and leftover = 0 (just the bar).
   */
  function platesFor(target, barWeight, plates) {
    const tgt = Number(target);
    const bar = Number(barWeight);
    if (!isFinite(tgt) || !isFinite(bar) || tgt < 0 || bar < 0) {
      return { perSide: [], leftover: 0, achievable: 0, error: "invalid" };
    }
    if (tgt < bar) {
      return { perSide: [], leftover: 0, achievable: bar, warning: "below_bar" };
    }
    const perSideTarget = (tgt - bar) / 2;
    const list = (plates && plates.length ? plates : DEFAULT_PLATES_LBS)
      .slice()
      .sort((a, b) => b - a);
    const perSide = [];
    let remaining = perSideTarget;
    // Floating-point tolerance for 2.5lb increments.
    const EPS = 1e-6;
    for (const p of list) {
      if (p <= 0) continue;
      const count = Math.floor((remaining + EPS) / p);
      if (count > 0) {
        perSide.push({ plate: p, count });
        remaining -= count * p;
      }
    }
    // Round leftover to 2 decimals to avoid 2.22e-16 noise.
    const leftoverPerSide = Math.round(remaining * 100) / 100;
    return {
      perSide,
      leftover: leftoverPerSide * 2,
      achievable: tgt - leftoverPerSide * 2,
    };
  }

  /** Human-readable plate summary: "2×45, 1×10 per side" */
  function formatPlates(result) {
    if (!result || !result.perSide || !result.perSide.length) return "Just the bar";
    return (
      result.perSide.map((p) => `${p.count}×${p.plate}`).join(", ") + " per side"
    );
  }

  /**
   * Adjust a weight by a step, clamping to >= 0 and snapping to a clean
   * multiple of the step's magnitude (avoids 42.49999 noise).
   */
  function stepWeight(current, delta) {
    const c = Number(current) || 0;
    const d = Number(delta) || 0;
    const next = Math.max(0, c + d);
    // Snap to 0.25 lb resolution — good enough for 2.5 / 5 / 10 increments.
    return Math.round(next * 4) / 4;
  }

  /**
   * Parse voice / text input like:
   *   "bench 5 by 135"
   *   "squat five reps at 225"
   *   "deadlift 3x405"
   *   "overhead press 8 reps 95 pounds"
   * Returns { exercise, reps, weight, unit } with fields null if absent.
   * Returns null if nothing intelligible is found.
   */
  function parseVoiceCommand(text) {
    if (!text || typeof text !== "string") return null;
    const original = text.trim();
    if (!original) return null;
    const normalized = wordsToDigits(original.toLowerCase());

    // Pattern: "<exercise> <reps> (x|by|×|reps?) <weight> [unit]"
    //   or "<exercise> <reps> reps (at|@) <weight> [unit]"
    //   or "<exercise> <reps>x<weight>"
    const RE = new RegExp(
      String.raw`^(?<ex>.+?)\s+` +
        String.raw`(?<reps>\d+(?:\.\d+)?)` +
        String.raw`\s*(?:x|by|×|\*|reps?\s*(?:at|@)?)\s*` +
        String.raw`(?<weight>\d+(?:\.\d+)?)` +
        String.raw`\s*(?<unit>lbs?|pounds?|kg|kilos?|kilograms?)?\s*$`,
      "i",
    );
    const m = normalized.match(RE);
    if (!m || !m.groups) return null;
    const ex = m.groups.ex.trim();
    if (!ex) return null;
    const unit = normalizeUnit(m.groups.unit);
    return {
      exercise: titleCase(ex),
      reps: Number(m.groups.reps),
      weight: Number(m.groups.weight),
      unit,
    };
  }

  function normalizeUnit(raw) {
    if (!raw) return null;
    const s = raw.toLowerCase();
    if (s.startsWith("k")) return "kg";
    return "lbs";
  }

  const NUMBER_WORDS = {
    zero: "0", one: "1", two: "2", three: "3", four: "4",
    five: "5", six: "6", seven: "7", eight: "8", nine: "9",
    ten: "10", eleven: "11", twelve: "12", fifteen: "15", twenty: "20",
  };
  function wordsToDigits(s) {
    return s.replace(/\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)\b/g,
      (w) => NUMBER_WORDS[w]);
  }

  function titleCase(s) {
    return s
      .split(/\s+/)
      .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
      .join(" ");
  }

  /**
   * Format a list of sets as a compact recall string:
   *   [{reps:5,weight:135},{reps:5,weight:145}]  → "5×135, 5×145"
   * Omits unit; caller can append if desired.
   */
  /** Format a seconds count as MM:SS (negative/NaN → "00:00"). */
  function fmtMMSS(totalSeconds) {
    const s = Math.max(0, Math.floor(Number(totalSeconds) || 0));
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
  }

  function formatRecall(sets) {
    if (!sets || !sets.length) return "";
    return sets
      .map((s) => {
        const r = s.reps != null ? s.reps : s.actual_reps;
        const w = s.weight != null ? s.weight : (s.actual_weight != null ? s.actual_weight : s.planned_weight);
        if (r == null && w == null) return null;
        if (w == null) return `${r}`;
        if (r == null) return `×${w}`;
        return `${r}×${w}`;
      })
      .filter(Boolean)
      .join(", ");
  }

  return {
    DEFAULT_PLATES_LBS,
    DEFAULT_PLATES_KG,
    platesFor,
    formatPlates,
    stepWeight,
    parseVoiceCommand,
    formatRecall,
    fmtMMSS,
  };
});
