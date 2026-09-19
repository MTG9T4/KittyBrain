/* KITTYBRAIN mood circuits — button row + hero scene swap (vanilla JS, no
 * deps). Exactly one of Normal / Fear / Hunt is active at a time; Normal is
 * the default on load. Fear and Hunt hide the tappable mascot and show a
 * hand-coded inline-SVG cartoon chase loop (dog chases cat / cat chases
 * mouse, no asset files), which runs until another mood is picked; under
 * prefers-reduced-motion the loops are frozen by the global stylesheet and
 * a static-frame note is shown. The same switch asks CatCloud to light a
 * seeded "circuit" subset in the activity graph (red glow for Fear, blue
 * for Hunt).
 *
 * Honesty: these circuits are illustrative fiction for play. No real fear
 * or hunt neurons are modeled and no neuroscience claim is made — that
 * label lives on the page next to the buttons and in each hero caption.
 */
(function () {
  "use strict";

  var MOODS = ["normal", "fear", "hunt"];
  // DOM ids: button and the visual element shown per mood.
  var BUTTONS = { normal: "mood-normal", fear: "mood-fear", hunt: "mood-hunt" };
  var VIEWS = { normal: "cat-sprite", fear: "mood-fear-scene", hunt: "mood-hunt-scene" };
  var CAPTIONS = {
    normal: "Cartoon mascot, hand-coded inline SVG (no asset files). " +
      "Illustrative only — not a scientific reconstruction, not final " +
      "branding. Tap or press it — it reacts.",
    fear: "Cartoon dog-chases-cat loop, hand-coded inline SVG (no asset " +
      "files). Illustrative fiction — no real fear or hunt neurons are " +
      "modeled, and no neuroscience claim. Loops until another mood is picked.",
    hunt: "Cartoon cat-chases-mouse loop, hand-coded inline SVG (no asset " +
      "files). Illustrative fiction — no real fear or hunt neurons are " +
      "modeled, and no neuroscience claim. Loops until another mood is picked."
  };

  var state = {
    mood: "normal",
    reducedMotion: false,
    wired: false,
  };

  function $(id) { return document.getElementById(id); }

  function setShown(el, show) {
    if (!el) return;
    if (show) el.removeAttribute("hidden");
    else el.setAttribute("hidden", "");
  }

  function apply(mood) {
    state.mood = mood;
    for (var k = 0; k < MOODS.length; k++) {
      var m = MOODS[k];
      var btn = $(BUTTONS[m]);
      if (btn) btn.setAttribute("aria-pressed", m === mood ? "true" : "false");
      setShown($(VIEWS[m]), m === mood);
    }
    setShown($("tap-hint"), mood === "normal");
    var cap = $("mascot-caption");
    if (cap) cap.textContent = CAPTIONS[mood];
    // Reduced motion: loops are frozen by the stylesheet; show the note so
    // the still frame is understood, not mistaken for a broken loop.
    setShown($("motion-note"), state.reducedMotion && mood !== "normal");
    if (window.CatCloud && typeof window.CatCloud.setMood === "function") {
      window.CatCloud.setMood(mood);
    }
  }

  window.CatMoods = {
    MOODS: MOODS.slice(),
    init: function (opts) {
      opts = opts || {};
      state.reducedMotion = !!opts.reducedMotion;
      for (var k = 0; k < MOODS.length; k++) {
        if (!$(BUTTONS[MOODS[k]]) || !$(VIEWS[MOODS[k]])) return false;
      }
      if (!state.wired) {
        state.wired = true;
        MOODS.forEach(function (m) {
          $(BUTTONS[m]).addEventListener("click", function () {
            window.CatMoods.setMood(m);
          });
        });
      }
      apply("normal"); // Normal is active on load
      return true;
    },
    setMood: function (m) {
      if (MOODS.indexOf(m) === -1) return state.mood; // unknown: ignore
      apply(m);
      return state.mood;
    },
    getMood: function () { return state.mood; },
    getState: function () {
      return { mood: state.mood, reducedMotion: state.reducedMotion };
    },
  };
})();
