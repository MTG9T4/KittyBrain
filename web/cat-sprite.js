/* KITTYBRAIN hero cartoon cat — interactivity for the inline SVG sprite.
 *
 * The sprite itself is hand-coded SVG in index.html: an illustrative
 * cartoon mascot (full sitting cat), not a scientific reconstruction and
 * not final branding. This module wires the reactions: every click/tap (or
 * Enter/Space) plays one of eight short sprite animations picked at random
 * — blink, ear twitch, happy bounce, wink, tail swish, purr shake, plus two
 * body-level ones (paw wave, loaf squash) — each 300–600ms from CSS
 * keyframes. Rapid taps are queued (capped, serialized) so animations
 * never overlap or stack-break.
 *
 * With prefers-reduced-motion, the global CSS already disables all
 * animation, so taps produce only a single subtle blink driven directly by
 * JS (inline lid styles snap them shut for 140ms, no motion). Engine
 * activity feeds a faint amber glow behind the eyes and a soft halo —
 * decoration only.
 */
(function () {
  "use strict";

  var ANIMATIONS = [
    { name: "blink", ms: 320 },
    { name: "ear-twitch", ms: 400 },
    { name: "bounce", ms: 480 },
    { name: "wink", ms: 460 },
    { name: "tail-swish", ms: 560 },
    { name: "purr", ms: 520 },
    { name: "paw-wave", ms: 480 },
    { name: "loaf-squash", ms: 540 },
  ];
  var REDUCED_MS = 140; // reduced-motion blink: lids shut this long, no motion
  var QUEUE_CAP = 3; // unbounded queues stack; cap and drop extras
  var GLOW_BASE = 0.06;
  var GLOW_RANGE = 0.30; // halo opacity across the activity range
  var EYE_GLOW_BASE = 0.18;
  var EYE_GLOW_RANGE = 0.55; // eye glow across the activity range

  var sprite = {
    root: null,
    lidL: null,
    lidR: null,
    halo: null,
    eyeGlow: null,
    reducedMotion: false,
    random: Math.random,
    activity: 0.12, // matches the engine's idle glow floor
    playing: null,
    timer: 0,
    queue: [],
    counts: {},
  };

  function pick() {
    if (sprite.reducedMotion) return ANIMATIONS[0]; // blink only
    var n = ANIMATIONS.length;
    var i = Math.floor(sprite.random() * n);
    if (i >= n) i = n - 1; // a random() of exactly 1 must stay in range
    return ANIMATIONS[i];
  }

  function play(anim) {
    sprite.playing = anim.name;
    if (sprite.reducedMotion) {
      // The stylesheet hides the lid circles (scaleY(0)); the inline style
      // overrides that, so this blink is actually visible — group-level
      // transforms don't touch the circles' own transform.
      if (sprite.lidL) sprite.lidL.style.transform = "scaleY(1)";
      if (sprite.lidR) sprite.lidR.style.transform = "scaleY(1)";
      sprite.timer = setTimeout(finish, REDUCED_MS);
    } else {
      sprite.root.classList.add("playing-" + anim.name);
      sprite.timer = setTimeout(finish, anim.ms);
    }
  }

  function finish() {
    sprite.timer = 0;
    if (sprite.playing) {
      if (sprite.reducedMotion) {
        if (sprite.lidL) sprite.lidL.style.transform = "";
        if (sprite.lidR) sprite.lidR.style.transform = "";
      } else {
        sprite.root.classList.remove("playing-" + sprite.playing);
      }
      sprite.playing = null;
    }
    if (sprite.queue.length) play(sprite.queue.shift());
  }

  function applyGlow() {
    var a = sprite.activity;
    var set = function (el, v) { if (el) el.setAttribute("opacity", v.toFixed(3)); };
    set(sprite.halo, GLOW_BASE + GLOW_RANGE * a);
    set(sprite.eyeGlow, EYE_GLOW_BASE + EYE_GLOW_RANGE * a);
  }

  window.CatSprite = {
    ANIMATIONS: ANIMATIONS.map(function (a) { return a.name; }),
    QUEUE_CAP: QUEUE_CAP,
    init: function (rootId, opts) {
      opts = opts || {};
      if (sprite.timer) { clearTimeout(sprite.timer); sprite.timer = 0; }
      if (sprite.root && sprite.playing && !sprite.reducedMotion) {
        sprite.root.classList.remove("playing-" + sprite.playing);
      }
      sprite.root = document.getElementById(rootId);
      if (!sprite.root) return false;
      sprite.lidL = document.getElementById("cat-lid-l");
      sprite.lidR = document.getElementById("cat-lid-r");
      sprite.halo = document.getElementById("cat-halo");
      sprite.eyeGlow = document.getElementById("cat-eyeglow");
      sprite.reducedMotion = !!opts.reducedMotion;
      sprite.random = (typeof opts.random === "function") ? opts.random : Math.random;
      sprite.playing = null;
      sprite.queue = [];
      sprite.counts = {};
      applyGlow();
      sprite.root.addEventListener("click", window.CatSprite.pet);
      sprite.root.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " " || ev.key === "Spacebar") {
          if (ev.preventDefault) ev.preventDefault();
          window.CatSprite.pet();
        }
      });
      return true;
    },
    pet: function () {
      if (!sprite.root) return false;
      var anim = pick();
      sprite.counts[anim.name] = (sprite.counts[anim.name] || 0) + 1;
      if (sprite.playing) {
        if (sprite.queue.length < QUEUE_CAP) sprite.queue.push(anim);
        return true; // queued (or dropped at cap) — never overlaps
      }
      play(anim);
      return true;
    },
    setActivity: function (x) {
      if (typeof x !== "number" || !isFinite(x)) return;
      sprite.activity = x < 0 ? 0 : (x > 1 ? 1 : x);
      applyGlow();
    },
    getState: function () {
      var counts = {};
      for (var k in sprite.counts) counts[k] = sprite.counts[k];
      return {
        playing: sprite.playing,
        queued: sprite.queue.map(function (a) { return a.name; }),
        reducedMotion: sprite.reducedMotion,
        activity: sprite.activity,
        counts: counts,
      };
    },
  };
})();
