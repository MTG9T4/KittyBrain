/* KITTYBRAIN volumetric activity graph (vanilla JS, no dependencies).
 *
 * Illustrative procedural geometry only: ~2200 seeded nodes in 7 gaussian
 * clusters fill an ellipsoid cranium volume, joined by precomputed
 * nearest-neighbor links. Motion, brightness, and the firing subset scale
 * with engine activity, which never drops below the 0.12 idle glow, so the
 * field stays visibly alive. This is NOT brain data, NOT a brain model, and
 * NOT a neural net — a deterministic drawing seeded for repeatability.
 * The viewport is orbitable: drag to rotate, scroll/pinch to zoom (clamped),
 * double-click to reset. A gentle idle drift runs until the first
 * interaction, and stays off while motion is paused or reduced-motion is
 * preferred.
 */
(function () {
  "use strict";

  var DEFAULT_YAW = 0;
  var DEFAULT_PITCH = 0;
  var DEFAULT_ZOOM = 1;
  var ZOOM_MIN = 0.5;
  var ZOOM_MAX = 2.5;
  var PITCH_MAX = 1.2; // ~69 degrees; keeps the volume readable
  var DRAG_RAD_PER_PX = 0.008;
  var DRIFT_RAD_PER_SEC = 0.06; // slow idle yaw, stops on first interaction
  var PERSP = 0.9; // perspective strength for depth cueing
  var SEED = 20260918;
  var LINK_RADIUS = 0.14; // max link length in layout units
  var LINK_K = 2; // nearest neighbors linked per node
  var EDGE_CAP = 5000; // hard ceiling on precomputed links
  var FIRING_FLOOR = 0.03; // fraction of nodes drawn bright at zero activity
  var FIRING_MAX = 0.35; // fraction drawn bright at full activity
  var EDGE_ALPHA_MAX = 0.2; // ruling #12: links stay faint, capped at 0.2
  var CANVAS_FILL = 0.74; // cloud spans ~99% of canvas height at zoom 1,
                          // without clipping the ear tips
  // Mood circuits — illustrative fiction, never a neuroscience claim: the
  // Fear/Hunt moods each highlight a seeded ~15% subset of nodes as a
  // glowing "active circuit" (bright core + soft halo). Fear glows red,
  // Hunt glows blue; Normal keeps the regular palette. The subsets come
  // from one salted seeded shuffle, so they are stable across frames and
  // re-inits, disjoint from each other, and contain no Math.random
  // anywhere.
  var MOODS = ["normal", "fear", "hunt"];
  var CIRCUIT_FRACTION = 0.15; // of all nodes, per mood
  var CIRCUIT_SALT = 0xc11c17; // keeps circuit subsets independent of layout
  // Per-mood glow: bright core + soft halo of the same hue, readable on
  // near-black. Fear stays the original red; Hunt is bright blue.
  var CIRCUIT_COLORS = {
    fear: { core: [255, 78, 66], halo: [255, 82, 70] },
    hunt: { core: [89, 167, 255], halo: [96, 172, 255] },
  };
  // Halo layers, outer to inner: [radius × node size, alpha].
  var CIRCUIT_HALO_LAYERS = [[2.8, 0.05], [1.9, 0.10], [1.25, 0.17]];
  // Ellipsoid cranium radii (x, y, z) about CRANIUM_C. Depth is real: rz is
  // the same order as rx/ry, so orbiting reveals a volume, not a card.
  var CRANIUM_R = [0.60, 0.52, 0.48];
  var CRANIUM_C = [0, -0.02, 0];
  // Muted lab palette on near-black: 3 region hues + one firing bright.
  var REGION_COLORS = [
    [110, 158, 160], // 0 cranium teal-slate
    [226, 216, 196], // 1 ear bone
    [133, 172, 110], // 2 lobe sage
  ];
  var FIRING_COLOR = [255, 246, 228]; // bright warm white, distinct prefix
  var EDGE_COLOR = [110, 158, 160];
  var BG_COLOR = "#0d0f0e";

  function mulberry32(seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function clamp(v, lo, hi) {
    return v < lo ? lo : (v > hi ? hi : v);
  }

  // Deterministic per-node, per-tick hash in [0, 1). No Math.random anywhere
  // in the draw path: the same (index, tick) always fires the same way.
  function fireHash(index, tick) {
    var h = (Math.imul(index + 1, 2654435761) ^ Math.imul(tick + 1, 40503)) >>> 0;
    h = (h ^ (h >>> 15)) >>> 0;
    h = Math.imul(h, 2246822519) >>> 0;
    h = (h ^ (h >>> 13)) >>> 0;
    return h / 4294967296;
  }

  // 7 seeded gaussian clusters, 2200 nodes total:
  // 4 cranium quadrants filling the ellipsoid, 1 midline lobe, 2 ear cones.
  // Counts and spreads are fixed so getStats().nodes is stable.
  var CLUSTERS = [
    { n: 420, c: [-0.22, 0.12, 0.10], s: [0.30, 0.26, 0.45], g: 0, cone: null },
    { n: 420, c: [0.22, 0.12, 0.10], s: [0.30, 0.26, 0.45], g: 0, cone: null },
    { n: 420, c: [-0.22, -0.18, -0.08], s: [0.32, 0.28, 0.48], g: 0, cone: null },
    { n: 420, c: [0.22, -0.18, -0.08], s: [0.32, 0.28, 0.48], g: 0, cone: null },
    { n: 200, c: [0, -0.02, 0.05], s: [0.14, 0.34, 0.40], g: 2, cone: null },
    // Ear bases sit inside the cranium shell (y 0.34 < surface ~0.35 at
    // x ±0.42) so the ears read attached to the head at rest view.
    { n: 160, c: [-0.42, 0.34, 0], s: null, g: 1, cone: { h: 0.46, r: 0.17 } },
    { n: 160, c: [0.42, 0.34, 0], s: null, g: 1, cone: { h: 0.46, r: 0.17 } },
  ];

  function buildNodes(rand) {
    var pts = [];
    function gauss() {
      return (rand() + rand() + rand() - 1.5) / 1.5; // ~N(0, ~0.33), in [-1, 1]
    }
    function pushClamped(x, y, z, group) {
      // Cranium clusters stay inside the ellipsoid: project strays onto it.
      var dx = (x - CRANIUM_C[0]) / CRANIUM_R[0];
      var dy = (y - CRANIUM_C[1]) / CRANIUM_R[1];
      var dz = (z - CRANIUM_C[2]) / CRANIUM_R[2];
      var r2 = dx * dx + dy * dy + dz * dz;
      if (r2 > 1) {
        var k = 0.97 / Math.sqrt(r2);
        x = CRANIUM_C[0] + (x - CRANIUM_C[0]) * k;
        y = CRANIUM_C[1] + (y - CRANIUM_C[1]) * k;
        z = CRANIUM_C[2] + (z - CRANIUM_C[2]) * k;
      }
      pts.push({ x: x, y: y, z: z, g: group, p: rand() * Math.PI * 2, s: 0.6 + rand() * 0.8 });
    }
    function pushRaw(x, y, z, group) {
      pts.push({ x: x, y: y, z: z, g: group, p: rand() * Math.PI * 2, s: 0.6 + rand() * 0.8 });
    }
    for (var c = 0; c < CLUSTERS.length; c++) {
      var cl = CLUSTERS[c];
      for (var i = 0; i < cl.n; i++) {
        if (cl.cone) {
          // Ear cone: stacked discs shrinking toward the apex, full z-depth.
          var t = rand();
          var rr = (1 - t) * cl.cone.r * Math.sqrt(rand());
          var aa = rand() * Math.PI * 2;
          pushRaw(cl.c[0] + Math.cos(aa) * rr, cl.c[1] + t * cl.cone.h,
            cl.c[2] + Math.sin(aa) * rr * 0.9, cl.g);
        } else {
          pushClamped(cl.c[0] + gauss() * cl.s[0], cl.c[1] + gauss() * cl.s[1],
            cl.c[2] + gauss() * cl.s[2], cl.g);
        }
      }
    }
    return pts;
  }

  // Link each node to its LINK_K nearest neighbors within LINK_RADIUS.
  // Precomputed once per init from the seeded layout, so the link set is
  // deterministic; deduped and capped at EDGE_CAP. Returns a flat [a0,b0,..]
  // index array plus the z-spread and a layout hash for testability.
  function buildLinks(points) {
    var n = points.length;
    var r2max = LINK_RADIUS * LINK_RADIUS;
    var links = [];
    var seen = {};
    var count = 0;
    var zMin = Infinity, zMax = -Infinity;
    var hash = 0;
    var i, j;
    for (i = 0; i < n; i++) {
      var z = points[i].z;
      if (z < zMin) zMin = z;
      if (z > zMax) zMax = z;
      hash = (Math.imul(hash, 31) + Math.round(points[i].x * 4096)) | 0;
      hash = (Math.imul(hash, 31) + Math.round(points[i].y * 4096)) | 0;
      hash = (Math.imul(hash, 31) + Math.round(points[i].z * 4096)) | 0;
    }
    for (i = 0; i < n && count < EDGE_CAP; i++) {
      var b1 = -1, b2 = -1, d1 = r2max, d2 = r2max;
      var pi = points[i];
      for (j = 0; j < n; j++) {
        if (j === i) continue;
        var dx = pi.x - points[j].x;
        var dy = pi.y - points[j].y;
        var dz = pi.z - points[j].z;
        var dist2 = dx * dx + dy * dy + dz * dz;
        if (dist2 < d1 && dist2 <= r2max) {
          d2 = d1; b2 = b1; d1 = dist2; b1 = j;
        } else if (dist2 < d2 && dist2 <= r2max) {
          d2 = dist2; b2 = j;
        }
      }
      var cands = b2 >= 0 ? [b1, b2] : (b1 >= 0 ? [b1] : []);
      for (var k = 0; k < cands.length && count < EDGE_CAP; k++) {
        var a = i < cands[k] ? i : cands[k];
        var b = i < cands[k] ? cands[k] : i;
        var key = a * n + b;
        if (!seen[key]) {
          seen[key] = 1;
          links.push(a, b);
          count++;
        }
      }
    }
    return { links: links, count: count, zMin: zMin, zMax: zMax, hash: (hash >>> 0).toString(16) };
  }

  var cloud = {
    points: [],
    links: [],
    linkCount: 0,
    zMin: 0,
    zMax: 0,
    layoutHash: "",
    firing: 0, // bright nodes drawn on the last frame (for getStats)
    tick: 0, // frames drawn since init; seeds the firing subset
    mood: "normal", // mood circuit selection; "normal" | "fear" | "hunt"
    circuitIndex: { fear: [], hunt: [] }, // node indices per mood
    circuitFlag: { fear: null, hunt: null }, // Uint8Array lookups per mood
    circuitDrawn: 0, // circuit nodes drawn on the last frame (for getStats)
    activity: 0.12,
    paused: false,
    reducedMotion: false,
    canvas: null,
    ctx: null,
    wired: false,
    raf: 0,
    t0: 0,
    lastT: 0,
    yaw: DEFAULT_YAW,
    pitch: DEFAULT_PITCH,
    zoom: DEFAULT_ZOOM,
    interacted: false, // set on first drag/wheel/pinch; kills the idle drift
  };

  // One seeded shuffle of all node indices drives both mood circuits:
  // fear takes the first ~15%, hunt the next ~15% — disjoint by
  // construction, stable across frames and inits, and driven by the same
  // mulberry32 seed mechanism as the layout (different salt).
  function buildCircuits(n) {
    var size = Math.round(n * CIRCUIT_FRACTION);
    var rand = mulberry32(SEED ^ CIRCUIT_SALT);
    var order = new Array(n);
    var i, j, tmp;
    for (i = 0; i < n; i++) order[i] = i;
    for (i = n - 1; i > 0; i--) {
      j = Math.floor(rand() * (i + 1));
      tmp = order[i]; order[i] = order[j]; order[j] = tmp;
    }
    var fear = order.slice(0, size);
    var hunt = order.slice(size, size * 2);
    var fearFlag = new Uint8Array(n);
    var huntFlag = new Uint8Array(n);
    for (i = 0; i < size; i++) {
      fearFlag[fear[i]] = 1;
      huntFlag[hunt[i]] = 1;
    }
    cloud.circuitIndex = { fear: fear, hunt: hunt };
    cloud.circuitFlag = { fear: fearFlag, hunt: huntFlag };
  }

  function rebuildLayout() {
    var rand = mulberry32(SEED);
    cloud.points = buildNodes(rand);
    var built = buildLinks(cloud.points);
    cloud.links = built.links;
    cloud.linkCount = built.count;
    cloud.zMin = built.zMin;
    cloud.zMax = built.zMax;
    cloud.layoutHash = built.hash;
    buildCircuits(cloud.points.length);
    cloud.tick = 0;
    cloud.firing = 0;
    cloud.circuitDrawn = 0;
  }

  function markInteracted() {
    cloud.interacted = true;
  }

  function setZoom(z) {
    cloud.zoom = clamp(z, ZOOM_MIN, ZOOM_MAX);
    return cloud.zoom;
  }

  function resetView() {
    cloud.yaw = DEFAULT_YAW;
    cloud.pitch = DEFAULT_PITCH;
    cloud.zoom = DEFAULT_ZOOM;
  }

  function resize() {
    if (!cloud.canvas) return;
    var dpr = window.devicePixelRatio || 1;
    var w = cloud.canvas.clientWidth, h = cloud.canvas.clientHeight;
    cloud.canvas.width = Math.max(1, Math.round(w * dpr));
    cloud.canvas.height = Math.max(1, Math.round(h * dpr));
  }

  // Rotate (x, y, z): yaw about Y, then pitch about X. Perspective divide
  // gives nearer points a larger screen offset for a true orbit feel.
  function project(p, cosY, sinY, cosP, sinP, out) {
    var x1 = p.x * cosY + p.z * sinY;
    var z1 = -p.x * sinY + p.z * cosY;
    var y2 = p.y * cosP - z1 * sinP;
    var z2 = p.y * sinP + z1 * cosP;
    var s = 1 / (1 + z2 * PERSP);
    out.x = x1 * s;
    out.y = y2 * s;
    out.s = s;
    return out;
  }

  function draw(now) {
    var ctx = cloud.ctx;
    if (!ctx) return;
    var W = cloud.canvas.width, H = cloud.canvas.height;
    var t = (now - cloud.t0) / 1000;
    var act = Math.max(0, Math.min(1, cloud.activity));
    var cx = W / 2, cy = H / 2;
    var scale = Math.min(W, H) * CANVAS_FILL * cloud.zoom;
    var wobble = 0.004 + act * 0.030;
    var breathe = 1 + Math.sin(t * 1.4) * (0.004 + act * 0.020);
    var frac = FIRING_FLOOR + (FIRING_MAX - FIRING_FLOOR) * act;
    var tick = cloud.tick;

    ctx.fillStyle = BG_COLOR;
    ctx.fillRect(0, 0, W, H);

    var cosY = Math.cos(cloud.yaw), sinY = Math.sin(cloud.yaw);
    var cosP = Math.cos(cloud.pitch), sinP = Math.sin(cloud.pitch);
    var dpr = window.devicePixelRatio || 1;
    var size = Math.max(2.0, 2.6 * dpr);
    var n = cloud.points.length;
    var sx = new Array(n), sy = new Array(n), ss = new Array(n), sd = new Array(n);
    var pr = { x: 0, y: 0, s: 1 };
    var i, p;
    for (i = 0; i < n; i++) {
      p = cloud.points[i];
      project(p, cosY, sinY, cosP, sinP, pr);
      var sway = Math.sin(t * (0.8 + act * 2.2) * p.s + p.p) * wobble;
      var lift = Math.cos(t * (0.6 + act * 1.8) * p.s + p.p * 1.7) * wobble;
      var cs = Math.cos(sway * 3), sn = Math.sin(sway * 3);
      sx[i] = cx + (pr.x * cs - pr.y * sn) * scale * breathe;
      sy[i] = cy + (pr.x * sn + pr.y * cs) * scale * breathe + lift * scale;
      ss[i] = pr.s;
      sd[i] = clamp((pr.s - 0.7) / 0.9, 0, 1); // 0 far … 1 near
    }

    // Links first, faint, in 3 depth buckets so one stroke covers each.
    var buckets = [[], [], []];
    var links = cloud.links;
    for (i = 0; i < links.length; i += 2) {
      var sAvg = (ss[links[i]] + ss[links[i + 1]]) / 2;
      var bucket = sAvg < 0.95 ? 0 : (sAvg < 1.05 ? 1 : 2);
      buckets[bucket].push(links[i], links[i + 1]);
    }
    var edgeAlphas = [0.08, 0.135, EDGE_ALPHA_MAX];
    for (var b = 0; b < 3; b++) {
      var bl = buckets[b];
      if (!bl.length) continue;
      ctx.beginPath();
      for (var e = 0; e < bl.length; e += 2) {
        ctx.moveTo(sx[bl[e]], sy[bl[e]]);
        ctx.lineTo(sx[bl[e + 1]], sy[bl[e + 1]]);
      }
      ctx.strokeStyle = "rgba(" + EDGE_COLOR[0] + "," + EDGE_COLOR[1] + "," +
        EDGE_COLOR[2] + "," + edgeAlphas[b] + ")";
      ctx.stroke();
    }

    // Mood circuit: soft halo layered behind the circuit nodes (three
    // alpha circles per node) so the subset glows on the near-black field
    // instead of reading as flat dots. Red for Fear, blue for Hunt.
    var moodFlag = cloud.mood === "fear" ? cloud.circuitFlag.fear
      : (cloud.mood === "hunt" ? cloud.circuitFlag.hunt : null);
    var glow = CIRCUIT_COLORS[cloud.mood] || null;
    if (moodFlag && glow) {
      for (var L = 0; L < CIRCUIT_HALO_LAYERS.length; L++) {
        var haloMult = CIRCUIT_HALO_LAYERS[L][0];
        var haloAlpha = CIRCUIT_HALO_LAYERS[L][1];
        ctx.fillStyle = "rgba(" + glow.halo[0] + "," + glow.halo[1] +
          "," + glow.halo[2] + "," + haloAlpha + ")";
        ctx.beginPath();
        for (i = 0; i < n; i++) {
          if (!moodFlag[i]) continue;
          var hr = Math.max(1, size * (0.7 + 0.8 * sd[i])) * haloMult;
          ctx.moveTo(sx[i] + hr, sy[i]); // separate each circle's subpath
          ctx.arc(sx[i], sy[i], hr, 0, Math.PI * 2);
        }
        ctx.fill();
      }
    }

    var firing = 0;
    var circuitDrawn = 0;
    for (i = 0; i < n; i++) {
      p = cloud.points[i];
      var depth = sd[i];
      var bright = fireHash(i, tick) < frac;
      var ps = size * (0.7 + 0.8 * depth);
      if (moodFlag && moodFlag[i]) {
        // Circuit core: bright mood-color, slightly larger; membership
        // overrides the normal/firing color while the mood is active.
        circuitDrawn++;
        var ca = 0.78 + 0.22 * depth;
        ctx.fillStyle = "rgba(" + glow.core[0] + "," + glow.core[1] +
          "," + glow.core[2] + "," + ca.toFixed(3) + ")";
        var off = ps * 0.125;
        ctx.fillRect(sx[i] - off, sy[i] - off, Math.max(1, ps * 1.25), Math.max(1, ps * 1.25));
        continue;
      }
      var alpha, col;
      if (bright) {
        firing++;
        col = FIRING_COLOR;
        alpha = 0.85 + 0.15 * depth;
      } else {
        col = REGION_COLORS[p.g];
        alpha = 0.38 + 0.50 * depth + act * 0.25 * (0.5 + 0.5 * Math.sin(p.p * 3 + t));
        if (alpha > 1) alpha = 1;
      }
      ctx.fillStyle = "rgba(" + col[0] + "," + col[1] + "," + col[2] + "," + alpha.toFixed(3) + ")";
      ctx.fillRect(sx[i], sy[i], Math.max(1, ps), Math.max(1, ps));
    }
    cloud.firing = firing;
    cloud.circuitDrawn = circuitDrawn;
    cloud.tick = tick + 1;
  }

  function frame(now) {
    if (cloud.lastT && !cloud.interacted && !cloud.paused && !cloud.reducedMotion) {
      cloud.yaw += DRIFT_RAD_PER_SEC * (now - cloud.lastT) / 1000;
    }
    cloud.lastT = now;
    draw(now);
    if (!cloud.paused) cloud.raf = window.requestAnimationFrame(frame);
  }

  function wireInteractions() {
    var canvas = cloud.canvas;
    if (cloud.wired) return;
    cloud.wired = true;
    canvas.style.touchAction = "none";
    var pointers = {}; // pointerId -> {x, y}
    var pinchD0 = 0;
    var pinchZ0 = DEFAULT_ZOOM;

    function pointerIds() {
      return Object.keys(pointers);
    }

    function pinchDistance() {
      var ids = pointerIds();
      if (ids.length < 2) return 0;
      var a = pointers[ids[0]], b = pointers[ids[1]];
      var dx = a.x - b.x, dy = a.y - b.y;
      return Math.sqrt(dx * dx + dy * dy);
    }

    function forgetPointer(ev) {
      delete pointers[ev.pointerId];
      if (pointerIds().length < 2) pinchD0 = 0;
    }

    canvas.addEventListener("pointerdown", function (ev) {
      markInteracted();
      pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if (pointerIds().length === 2) {
        pinchD0 = pinchDistance();
        pinchZ0 = cloud.zoom;
      }
      try {
        if (canvas.setPointerCapture) canvas.setPointerCapture(ev.pointerId);
      } catch (err) { /* headless stubs may not implement capture */ }
    });

    canvas.addEventListener("pointermove", function (ev) {
      var prev = pointers[ev.pointerId];
      if (!prev) return;
      if (pointerIds().length >= 2) {
        pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
        var d = pinchDistance();
        if (pinchD0 > 0 && d > 0) setZoom(pinchZ0 * d / pinchD0);
        return;
      }
      var dx = ev.clientX - prev.x, dy = ev.clientY - prev.y;
      pointers[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      cloud.yaw += dx * DRAG_RAD_PER_PX;
      cloud.pitch = clamp(cloud.pitch + dy * DRAG_RAD_PER_PX, -PITCH_MAX, PITCH_MAX);
    });

    canvas.addEventListener("pointerup", forgetPointer);
    canvas.addEventListener("pointercancel", forgetPointer);

    canvas.addEventListener("wheel", function (ev) {
      if (ev.preventDefault) ev.preventDefault();
      markInteracted();
      setZoom(cloud.zoom * Math.pow(1.0015, -(ev.deltaY || 0)));
    }, { passive: false });

    canvas.addEventListener("dblclick", function () {
      resetView();
    });
  }

  window.CatCloud = {
    init: function (canvasId, opts) {
      cloud.canvas = document.getElementById(canvasId);
      if (!cloud.canvas) return false;
      cloud.ctx = cloud.canvas.getContext("2d");
      if (!cloud.ctx) return false;
      cloud.reducedMotion = !!(opts && opts.reducedMotion);
      rebuildLayout();
      resize();
      window.addEventListener("resize", resize);
      wireInteractions();
      cloud.t0 = window.performance ? window.performance.now() : Date.now();
      cloud.lastT = 0;
      var now = window.performance ? window.performance.now() : Date.now();
      draw(now);
      if (!cloud.paused) cloud.raf = window.requestAnimationFrame(frame);
      return true;
    },
    setActivity: function (x) {
      if (typeof x === "number" && isFinite(x)) cloud.activity = x;
    },
    setPaused: function (paused) {
      paused = !!paused;
      if (paused === cloud.paused) return cloud.paused;
      cloud.paused = paused;
      cloud.lastT = 0; // avoid a drift jump across the pause gap
      if (!paused) {
        cloud.raf = window.requestAnimationFrame(frame);
      } else if (cloud.raf) {
        window.cancelAnimationFrame(cloud.raf);
        cloud.raf = 0;
      }
      return cloud.paused;
    },
    isPaused: function () { return cloud.paused; },
    resetView: function () { resetView(); },
    getCamera: function () {
      return { yaw: cloud.yaw, pitch: cloud.pitch, zoom: cloud.zoom };
    },
    // Mood circuits: exactly one of normal/fear/hunt. Unknown names are
    // ignored. Every accepted switch redraws immediately so paused and
    // reduced-motion users still see the change.
    setMood: function (m) {
      if (MOODS.indexOf(m) === -1) return cloud.mood;
      if (m === cloud.mood) return cloud.mood;
      cloud.mood = m;
      var now = window.performance ? window.performance.now() : Date.now();
      draw(now);
      return cloud.mood;
    },
    getMood: function () { return cloud.mood; },
    getCircuit: function (m) {
      if (m !== "fear" && m !== "hunt") return [];
      return cloud.circuitIndex[m].slice();
    },
    getStats: function () {
      return {
        nodes: cloud.points.length,
        edges: cloud.linkCount,
        firing: cloud.firing,
        tick: cloud.tick,
        zSpread: cloud.zMax - cloud.zMin,
        layoutHash: cloud.layoutHash,
        mood: cloud.mood,
        circuit: cloud.circuitDrawn,
        circuitSize: cloud.circuitIndex.fear.length,
      };
    },
  };
})();
