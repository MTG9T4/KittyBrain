/* KITTYBRAIN dashboard logic (vanilla JS). Polls the local API and renders
 * radar, decision panel, and the session-only execution trace. */
(function () {
  "use strict";

  var POLL_MS = 3000;

  function $(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    return n;
  }

  function fetchJson(path, done) {
    fetch(path, { cache: "no-store" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (obj) { done(null, obj); })
      .catch(function (err) { done(err, null); });
  }

  function fmtPrice(v) {
    if (v === null || v === undefined) return null;
    if (v >= 1000) return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
    if (v >= 1) return v.toFixed(4);
    return v.toPrecision(4);
  }

  function nodataCell(reason) {
    var td = el("td", "num nodata", "NO DATA");
    if (reason) td.title = reason;
    return td;
  }

  /* --- radar ---------------------------------------------------------- */
  function renderRadar(rows) {
    var body = $("radar-body");
    body.textContent = "";
    if (!rows || !rows.length) {
      var tr = document.createElement("tr");
      var td = el("td", "nodata", "NO DATA — no market tracked");
      td.colSpan = 6;
      tr.appendChild(td);
      body.appendChild(tr);
      return;
    }
    rows.forEach(function (m) {
      var tr = document.createElement("tr");
      var label = el("td", null);
      label.appendChild(el("div", null, m.label || "?"));
      var pool = el("div", "mono fine", m.pool || "");
      pool.title = m.pool || "";
      label.appendChild(pool);
      tr.appendChild(label);
      var price = fmtPrice(m.price);
      tr.appendChild(price === null ? nodataCell("no observation yet")
        : el("td", "num", price));
      ["change_1h_pct", "volume_24h_usd", "liquidity_usd"].forEach(function (key) {
        var v = m[key];
        tr.appendChild(v === null || v === undefined
          ? nodataCell(m.unavailable_reason || "not reported")
          : el("td", "num", String(v)));
      });
      var sig = el("td", null);
      sig.appendChild(el("span", "signal " + (m.signal || "waiting"),
        (m.signal || "waiting").toUpperCase()));
      tr.appendChild(sig);
      body.appendChild(tr);
    });
  }

  /* --- decision panel --------------------------------------------------- */
  function renderDecision(status, latest) {
    var state = $("decision-state");
    var kv = $("decision-kv");
    kv.textContent = "";
    function row(k, v) {
      kv.appendChild(el("dt", null, k));
      kv.appendChild(el("dd", null, v));
    }
    if (status && status.live_blocker) {
      state.textContent = "NO DATA";
      state.className = "decision-state nodata";
      row("Reason", status.live_blocker);
      row("Orders", "none — no wallet connected");
      return;
    }
    if (status && status.last_error && !latest) {
      state.textContent = "NO DATA";
      state.className = "decision-state nodata";
      row("Last error", status.last_error);
      row("Orders", "none — no wallet connected");
      return;
    }
    var warm = status ? status.warmup : null;
    if (!latest) {
      state.textContent = "Waiting…";
      state.className = "decision-state waiting";
      if (warm) row("Warmup", warm.sample_count + " / " + warm.needed + " samples");
      row("Orders", "none — no wallet connected");
      return;
    }
    state.textContent = (latest.signal || "?").toUpperCase();
    state.className = "decision-state signal " + (latest.signal || "neutral");
    row("Price", fmtPrice(latest.price));
    if (latest.ma_fast !== undefined) {
      row("MA5 / MA20", fmtPrice(latest.ma_fast) + " / " + fmtPrice(latest.ma_slow));
      row("Spread", (latest.spread * 100).toFixed(3) + " %");
      row("Activity", latest.activity.toFixed(2));
      row("Samples", String(latest.sample_count));
    }
    if (status && status.last_error) row("Last error", status.last_error);
  }

  /* --- trace ------------------------------------------------------------ */
  function renderTrace(events) {
    var list = $("trace-list");
    list.textContent = "";
    if (!events || !events.length) {
      var li = document.createElement("li");
      li.appendChild(el("span", "nodata", "No session events yet."));
      list.appendChild(li);
      return;
    }
    events.slice().reverse().forEach(function (ev) {
      var li = document.createElement("li");
      var time = document.createElement("time");
      var d = new Date(ev.ts * 1000);
      time.textContent = d.toLocaleTimeString("en-GB", { hour12: false });
      time.title = d.toISOString();
      li.appendChild(time);
      li.appendChild(el("span", "stage " + ev.stage, String(ev.stage).toUpperCase()));
      li.appendChild(el("span", "kind", ev.kind || ""));
      li.appendChild(el("span", null, ev.message || ""));
      list.appendChild(li);
    });
  }

  /* --- mode banner -------------------------------------------------------- */
  function renderMode(env) {
    var badge = $("mode-badge");
    var banner = $("mode-banner");
    var mode = env.mode || "?";
    var live = mode === "live";
    badge.textContent = live ? "LIVE · DEX" : "SHOWCASE · SYNTHETIC";
    badge.className = "badge " + (live ? "live" : "showcase");
    document.title = live ? "KITTYBRAIN — observation terminal (live)"
      : "KITTYBRAIN — observation terminal (local showcase)";
    banner.textContent = env.illustrative
      ? "Illustrative showcase: synthetic demo data. Observations are not financial advice."
      : "Live observations of public market data. Not financial advice.";
  }

  function renderOffline() {
    var badge = $("mode-badge");
    badge.textContent = "OFFLINE";
    badge.className = "badge";
    $("mode-banner").textContent = "Local server unreachable — showing last received data.";
  }

  /* --- poll loop ---------------------------------------------------------- */
  function refresh() {
    fetchJson("/api/status", function (err, env) {
      if (err || !env || !env.data) { renderOffline(); return; }
      renderMode(env);
      var status = env.data;
      fetchJson("/api/latest", function (err2, env2) {
        var latest = (!err2 && env2 && env2.data) ? env2.data.latest : null;
        renderDecision(status, latest);
        if (latest && window.CatCloud) {
          var act = latest.activity;
          window.CatCloud.setActivity(act);
          if (window.CatSprite) window.CatSprite.setActivity(act);
          // Meaning hint: the scalar is 0–1 with a 0.12 idle-glow floor;
          // bands are honest labels for that scale, nothing more.
          var band = act < 0.25 ? "resting glow" : (act < 0.55 ? "stirring" : "bright");
          $("activity-readout").textContent =
            "activity " + act.toFixed(2) + " / 1.00 — " + band;
        }
      });
    });
    fetchJson("/api/radar", function (err, env) {
      if (!err && env && env.data) renderRadar(env.data.markets);
    });
    fetchJson("/api/events?limit=20", function (err, env) {
      if (!err && env && env.data) renderTrace(env.data.events);
    });
  }

  /* --- boot --------------------------------------------------------------- */
  function boot() {
    var reduceMotion = window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var paused = !!reduceMotion;
    if (window.CatCloud) {
      if (paused) window.CatCloud.setPaused(true);
      window.CatCloud.init("catchart", { reducedMotion: reduceMotion });
    }
    if (window.CatSprite) {
      window.CatSprite.init("cat-sprite", { reducedMotion: reduceMotion });
    }
    if (window.CatMoods) {
      window.CatMoods.init({ reducedMotion: reduceMotion });
    }
    var toggle = $("motion-toggle");
    function paintToggle() {
      toggle.textContent = paused ? "Resume motion" : "Pause motion";
    }
    paintToggle();
    toggle.addEventListener("click", function () {
      paused = window.CatCloud ? window.CatCloud.setPaused(!paused) : !paused;
      paintToggle();
    });
    refresh();
    window.setInterval(refresh, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
