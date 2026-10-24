(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var token = sessionStorage.getItem("cl_token") || localStorage.getItem("cl_token") || "";
  var sharedFolder = false;
  var mode = "workspace";       // "library" = My files mode: the server finds the files by itself
  var canOpen = false;          // true only when this page runs on the same computer as the server
  var pollTimer = null;

  // ---------- small helpers ----------
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ } }
  function load(key, fallback) {
    try { var v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
  }
  function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }
  function typingNow() {
    var t = document.activeElement && document.activeElement.tagName;
    return t === "INPUT" || t === "TEXTAREA";
  }

  // ---------- talking to the server ----------
  function api(path, options) {
    options = options || {};
    var headers = { "Content-Type": "application/json" };
    if (token) { headers.Authorization = "Bearer " + token; }
    return fetch(path, { method: options.method || "GET", headers: headers,
                         body: options.body ? JSON.stringify(options.body) : undefined })
      .then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          if (res.status === 401 && token && path !== "/api/login") { logout(); }
          if (!res.ok) {
            var text = typeof data.detail === "string" ? data.detail : "Something went wrong (" + res.status + ").";
            if (res.status === 429) { text += " Wait " + (res.headers.get("Retry-After") || "a few") + " seconds."; }
            var error = new Error(text); error.status = res.status; throw error;
          }
          return data;
        });
      });
  }

  // ---------- login ----------
  function authMessage(text, good) { var m = $("auth-msg"); m.textContent = text; m.className = good ? "msg ok" : "msg"; }
  function credentials() { return { username: $("user").value, password: $("pass").value }; }

  function storeToken(t) {
    var keep = $("remember").checked;
    (keep ? localStorage : sessionStorage).setItem("cl_token", t);
    (keep ? sessionStorage : localStorage).removeItem("cl_token");
  }
  function showApp() {
    $("auth").hidden = true; $("app").hidden = false;
    api("/api/me").then(function (me) {
      sharedFolder = !!me.shared_folder; mode = me.mode || "workspace"; canOpen = !!me.can_open;
      applyMode();
      if (mode === "library") { pollLibrary(); } else { refreshFiles(); }
    }).catch(function () {});
    restoreBar();
  }
  function logout() {
    token = ""; sessionStorage.removeItem("cl_token"); localStorage.removeItem("cl_token");
    clearTimeout(pollTimer);
    $("app").hidden = true; $("auth").hidden = false; $("pass").value = "";
  }
  function applyMode() {
    var library = mode === "library";
    $("toggle-files").hidden = library; $("files").hidden = true; $("refresh").hidden = !library;
    $("q").placeholder = library ? "Type a word or phrase you remember...   ( / to focus )"
                                 : "Search your files...   ( / to focus )";
    setStatus(library ? "Type a word or phrase from the file you are looking for." : "Add some files, then search.");
  }
  // My files mode: show what the server is doing in the background
  function pollLibrary() {
    api("/api/library").then(function (s) {
      var box = $("library"); box.textContent = "";
      var where = s.roots.map(function (r) { return r.split(/[\\/]/).filter(Boolean).pop(); }).join(", ");
      if (s.state === "ready") {
        box.textContent = "Searching " + s.files + " files in " + where + ".";
      } else if (s.state === "error") {
        box.textContent = "Problem while reading files: " + s.error;
      } else {
        box.textContent = (s.state === "indexing" ? "Reading your files: " + s.files + " ready, " + s.pending + " to go. You can already search."
                                                    : "Looking for files in " + where + "...");
        var bar = document.createElement("div"); bar.className = "progress"; bar.appendChild(document.createElement("div"));
        box.appendChild(bar);
      }
      pollTimer = setTimeout(pollLibrary, s.state === "ready" ? 20000 : 2000);
    }).catch(function () { pollTimer = setTimeout(pollLibrary, 5000); });
  }
  $("refresh").addEventListener("click", function () {
    api("/api/index", { method: "POST" }).then(function () { clearTimeout(pollTimer); pollLibrary(); }).catch(function (e) { setStatus(e.message); });
  });
  $("login").addEventListener("click", function () {
    api("/api/login", { method: "POST", body: credentials() }).then(function (d) {
      token = d.token; storeToken(token); authMessage(""); showApp();
    }).catch(function (e) { authMessage(e.message); });
  });
  $("signup").addEventListener("click", function () {
    api("/api/register", { method: "POST", body: credentials() }).then(function () {
      authMessage("Account created. Now log in.", true);
    }).catch(function (e) { authMessage(e.message); });
  });
  $("pass").addEventListener("keydown", function (e) { if (e.key === "Enter") { $("login").click(); } });
  $("logout").addEventListener("click", logout);

  // ---------- the flexible search bar ----------
  var bar = $("bar");
  var state = load("cl_bar", { mode: "wide", left: null, top: null, width: null });

  function applyBar() {
    bar.setAttribute("data-mode", state.mode);
    if (state.left !== null && state.top !== null) {
      bar.style.transform = "none";
      bar.style.left = clamp(state.left, 0, window.innerWidth - 56) + "px";
      bar.style.top = clamp(state.top, 0, window.innerHeight - 56) + "px";
    }
    if (state.mode === "wide" && state.width) { bar.style.width = clamp(state.width, 280, window.innerWidth - 16) + "px"; }
    else { bar.style.width = ""; }
  }
  function restoreBar() { applyBar(); }
  function setMode(mode) {
    state.mode = mode; applyBar(); save("cl_bar", state);
    if (mode !== "min") { $("q").focus(); }
  }
  $("min").addEventListener("click", function () { setMode("min"); });
  $("orb").addEventListener("click", function () { setMode("wide"); });
  $("size").addEventListener("click", function () { setMode(state.mode === "wide" ? "compact" : "wide"); });

  // dragging with the grip (mouse, finger or pen)
  $("grip").addEventListener("pointerdown", function (e) {
    var box = bar.getBoundingClientRect(), dx = e.clientX - box.left, dy = e.clientY - box.top;
    function move(ev) {
      state.left = ev.clientX - dx; state.top = ev.clientY - dy; applyBar();
    }
    function up() { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); save("cl_bar", state); }
    document.addEventListener("pointermove", move); document.addEventListener("pointerup", up);
    e.preventDefault();
  });
  // resizing with the pink handle
  $("resize").addEventListener("pointerdown", function (e) {
    var left = bar.getBoundingClientRect().left;
    state.mode = "wide";
    function move(ev) {
      state.width = clamp(ev.clientX - left + 6, 280, window.innerWidth - 16);
      state.left = left; state.top = bar.getBoundingClientRect().top; applyBar();
    }
    function up() { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); save("cl_bar", state); }
    document.addEventListener("pointermove", move); document.addEventListener("pointerup", up);
    e.preventDefault(); e.stopPropagation();
  });
  window.addEventListener("resize", applyBar);

  // ---------- search ----------
  var timer = null, shown = [];
  function setStatus(text) { $("status").textContent = text; }

  function highlight(parent, text, words) {
    var safe = words.filter(Boolean).map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
    if (!safe.length) { parent.appendChild(document.createTextNode(text)); return; }
    var re = new RegExp("(" + safe.join("|") + ")", "ig"), last = 0, m;
    while ((m = re.exec(text)) !== null) {
      if (m.index > last) { parent.appendChild(document.createTextNode(text.slice(last, m.index))); }
      var mark = document.createElement("mark"); mark.textContent = m[0]; parent.appendChild(mark);
      last = m.index + m[0].length;
      if (m[0].length === 0) { re.lastIndex++; }
    }
    if (last < text.length) { parent.appendChild(document.createTextNode(text.slice(last))); }
  }
  function renderResults(data) {
    var list = $("results"); list.textContent = "";
    data.results.forEach(function (r) {
      var li = document.createElement("li");
      var score = document.createElement("span"); score.className = "score"; score.textContent = "score " + r.score;
      var parts = r.path.split("/"), fileName = parts.pop(), folderName = parts.join("/");
      var path = document.createElement("div"); path.className = "name"; path.textContent = fileName;
      li.appendChild(score); li.appendChild(path);
      if (folderName) { var folder = document.createElement("div"); folder.className = "folder"; folder.textContent = folderName; li.appendChild(folder); }
      if (r.snippet) {
        var snip = document.createElement("div"); snip.className = "snip";
        snip.appendChild(document.createTextNode("line " + r.line + ": "));
        highlight(snip, r.snippet, data.words);       // text nodes only: no HTML from the server is ever trusted
        li.appendChild(snip);
      }
      if (mode === "library") {
        var actions = document.createElement("div"); actions.className = "actions";
        if (canOpen) { actions.appendChild(actionButton("Open", function () { openFile(r.path, fileName); })); }
        actions.appendChild(actionButton("Download", function () { downloadFile(r.path, fileName); }));
        li.appendChild(actions);
      }
      list.appendChild(li);
    });
    var note = data.corrections.map(function (c) { return "No match for '" + c.typed + "', showing results for '" + c.used + "'. "; }).join("");
    setStatus(note + data.total + " file(s) in " + data.ms + " ms" + (data.total > data.results.length ? ", showing the best " + data.results.length : ""));
  }
  function actionButton(label, onClick) {
    var b = document.createElement("button"); b.type = "button"; b.textContent = label; b.addEventListener("click", onClick); return b;
  }
  function openFile(path, name) {
    api("/api/open", { method: "POST", body: { path: path } }).then(function () { setStatus("Opened " + name + "."); })
      .catch(function (e) { setStatus(e.message); });
  }
  function downloadFile(path, name) {
    fetch("/api/download?path=" + encodeURIComponent(path), { headers: { Authorization: "Bearer " + token } })
      .then(function (res) { if (!res.ok) { throw new Error("Download failed (" + res.status + ")."); } return res.blob(); })
      .then(function (blob) {
        var url = URL.createObjectURL(blob), a = document.createElement("a");
        a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
      }).catch(function (e) { setStatus(e.message); });
  }
  function runSearch() {
    var q = $("q").value.trim(); hideSuggest();
    if (!q) { return; }
    api("/api/search?q=" + encodeURIComponent(q) + "&phrase=" + ($("phrase").checked ? "true" : "false"))
      .then(renderResults).catch(function (e) { setStatus(e.message); });
  }
  function hideSuggest() { $("suggest").hidden = true; shown = []; }
  function showSuggest(items, prefix) {
    var box = $("suggest"); box.textContent = ""; shown = items;
    if (!items.length) { box.hidden = true; return; }
    items.forEach(function (it) {
      var b = document.createElement("button"); b.type = "button";
      var a = document.createElement("span"); a.textContent = it.word;
      var n = document.createElement("span"); n.className = "muted"; n.textContent = it.files + " file(s)";
      b.appendChild(a); b.appendChild(n);
      b.addEventListener("click", function () {
        var parts = $("q").value.split(/\s+/); parts[parts.length - 1] = it.word;
        $("q").value = parts.join(" ") + " "; hideSuggest(); $("q").focus();
      });
      box.appendChild(b);
    });
    box.hidden = false;
  }
  $("q").addEventListener("input", function () {
    clearTimeout(timer);
    var last = ($("q").value.split(/\s+/).pop() || "").replace(/[^A-Za-z0-9]/g, "");
    if (last.length < 2) { hideSuggest(); return; }
    timer = setTimeout(function () {
      api("/api/suggest?prefix=" + encodeURIComponent(last)).then(function (d) { showSuggest(d.suggestions, last); }).catch(hideSuggest);
    }, 200);
  });
  $("q").addEventListener("keydown", function (e) { if (e.key === "Enter") { runSearch(); } });
  $("phrase").addEventListener("change", runSearch);

  // ---------- files (only used when the server is NOT in My files mode) ----------
  function readBase64(file) {
    return new Promise(function (resolve, reject) {
      var reader = new FileReader();
      reader.onload = function () { resolve(String(reader.result).split(",")[1] || ""); };
      reader.onerror = reject; reader.readAsDataURL(file);
    });
  }
  function refreshFiles() {
    api("/api/files").then(function (d) {
      var ul = $("filelist"); ul.textContent = "";
      d.files.forEach(function (name) {
        var li = document.createElement("li"); var s = document.createElement("span"); s.textContent = name; li.appendChild(s);
        if (!sharedFolder) {
          var del = document.createElement("button"); del.className = "tiny"; del.textContent = "Delete";
          del.addEventListener("click", function () {
            api("/api/files/" + encodeURIComponent(name), { method: "DELETE" }).then(refreshFiles).catch(function (e) { setStatus(e.message); });
          });
          li.appendChild(del);
        }
        ul.appendChild(li);
      });
      $("files-note").textContent = sharedFolder ? "This server searches a shared folder. Uploads are off." : d.files.length + " file(s). Text and code files only.";
      $("pick").hidden = sharedFolder;
    }).catch(function () {});
  }
  $("toggle-files").addEventListener("click", function () { $("files").hidden = !$("files").hidden; });
  $("pick").addEventListener("change", function () {
    var files = Array.prototype.slice.call($("pick").files), chain = Promise.resolve();
    files.forEach(function (file) {
      chain = chain.then(function () {
        return readBase64(file).then(function (data) {
          return api("/api/files", { method: "POST", body: { name: file.name, content_base64: data } });
        }).catch(function (e) { setStatus(file.name + ": " + e.message); });
      });
    });
    chain.then(function () { $("pick").value = ""; return api("/api/index", { method: "POST" }); })
         .then(function (r) { if (r) { setStatus("Index ready: " + r.files + " files, " + r.words + " words."); } refreshFiles(); })
         .catch(function () {});
  });

  // ---------- keyboard ----------
  document.addEventListener("keydown", function (e) {
    if ($("app").hidden) { return; }
    if (e.key === "/" && !typingNow()) { e.preventDefault(); if (state.mode === "min") { setMode("wide"); } else { $("q").focus(); } }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setMode(state.mode === "min" ? "wide" : "min"); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "m") { e.preventDefault(); setMode(state.mode === "wide" ? "compact" : "wide"); }
    else if (e.key === "Escape") { if (!$("suggest").hidden) { hideSuggest(); } else { setMode("min"); } }
    else if (/^[1-6]$/.test(e.key) && !typingNow()) { setAnimation(parseInt(e.key, 10) - 1); }
  });

  // ---------- six animated backgrounds ----------
  var canvas = $("bg"), ctx = canvas.getContext("2d"), W = 0, H = 0;
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var mouse = { x: 0.5, y: 0.5 };
  function fit() {
    var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    W = canvas.width = Math.floor(window.innerWidth * dpr); H = canvas.height = Math.floor(window.innerHeight * dpr);
    if (current && current.init) { current.init(); }
  }
  window.addEventListener("resize", fit);
  window.addEventListener("pointermove", function (e) { mouse.x = e.clientX / window.innerWidth; mouse.y = e.clientY / window.innerHeight; });
  function clear(alpha) { ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(11,15,26," + alpha + ")"; ctx.fillRect(0, 0, W, H); }
  var TAU = Math.PI * 2;

  var animations = [
    { name: "Aurora", blobs: [], init: function () {
        this.blobs = [["0,229,255", 0.0], ["255,61,154", 1.7], ["120,80,255", 3.1], ["70,229,138", 4.4]].map(function (c, i) { return { rgb: c[0], phase: c[1], r: 0.35 + i * 0.04 }; });
      },
      draw: function (t) {
        clear(0.25); ctx.globalCompositeOperation = "lighter";
        this.blobs.forEach(function (b) {
          var x = W * (0.5 + 0.38 * Math.sin(t * 0.00035 + b.phase)), y = H * (0.5 + 0.3 * Math.cos(t * 0.0003 + b.phase * 1.3)), r = Math.max(W, H) * b.r;
          var g = ctx.createRadialGradient(x, y, 0, x, y, r); g.addColorStop(0, "rgba(" + b.rgb + ",0.42)"); g.addColorStop(1, "rgba(" + b.rgb + ",0)");
          ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
        });
      } },
    { name: "Network", dots: [], init: function () {
        var n = Math.round(clamp(W * H / 14000, 40, 130)); this.dots = [];
        for (var i = 0; i < n; i++) { this.dots.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - 0.5) * 0.7, vy: (Math.random() - 0.5) * 0.7 }); }
      },
      draw: function () {
        clear(0.35); var d = this.dots, link = Math.min(W, H) * 0.16, mx = mouse.x * W, my = mouse.y * H;
        for (var i = 0; i < d.length; i++) {
          var p = d[i]; p.x += p.vx; p.y += p.vy; if (p.x < 0 || p.x > W) { p.vx *= -1; } if (p.y < 0 || p.y > H) { p.vy *= -1; }
          ctx.fillStyle = "#00e5ff"; ctx.fillRect(p.x - 1.5, p.y - 1.5, 3, 3);
          for (var j = i + 1; j < d.length; j++) {
            var q = d[j], dist = Math.hypot(p.x - q.x, p.y - q.y);
            if (dist < link) { ctx.strokeStyle = "rgba(0,229,255," + (1 - dist / link) * 0.55 + ")"; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke(); }
          }
          var dm = Math.hypot(p.x - mx, p.y - my);
          if (dm < link * 1.5) { ctx.strokeStyle = "rgba(255,61,154," + (1 - dm / (link * 1.5)) * 0.7 + ")"; ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(mx, my); ctx.stroke(); }
        }
      } },
    { name: "Code rain", cols: [], size: 16, init: function () {
        this.size = Math.round(clamp(W / 70, 12, 20)); var n = Math.ceil(W / this.size); this.cols = [];
        for (var i = 0; i < n; i++) { this.cols.push(Math.random() * -50); }
      },
      draw: function () {
        clear(0.12); ctx.font = this.size + "px monospace"; var chars = "{}[]()<>=+-*/;:#&|01defretclasswhileimport", s = this.size;
        for (var i = 0; i < this.cols.length; i++) {
          var y = this.cols[i] * s; ctx.fillStyle = (i % 7 === 0) ? "#ff3d9a" : "#46e58a";
          ctx.fillText(chars.charAt(Math.floor(Math.random() * chars.length)), i * s, y);
          this.cols[i] = (y > H && Math.random() > 0.975) ? 0 : this.cols[i] + 1;
        }
      } },
    { name: "Waves", init: function () {},
      draw: function (t) {
        clear(0.22); var layers = 5;
        for (var k = 0; k < layers; k++) {
          ctx.beginPath(); ctx.lineWidth = 2.5; ctx.strokeStyle = "hsla(" + (180 + k * 38) + ",100%,60%,0.75)";
          for (var x = 0; x <= W; x += 8) {
            var y = H * (0.5 + 0.12 * (k - 2)) + Math.sin(x * 0.006 + t * 0.0012 * (1 + k * 0.2) + k) * H * 0.07 + Math.sin(x * 0.013 - t * 0.0009 + k * 2) * H * 0.025;
            if (x === 0) { ctx.moveTo(x, y); } else { ctx.lineTo(x, y); }
          }
          ctx.stroke();
        }
      } },
    { name: "Warp", stars: [], init: function () {
        this.stars = []; for (var i = 0; i < 220; i++) { this.stars.push({ a: Math.random() * TAU, d: Math.random(), s: 0.002 + Math.random() * 0.012 }); }
      },
      draw: function () {
        clear(0.28); var cx = W * (0.35 + mouse.x * 0.3), cy = H * (0.35 + mouse.y * 0.3), reach = Math.max(W, H);
        for (var i = 0; i < this.stars.length; i++) {
          var s = this.stars[i], before = s.d; s.d += s.s * (1 + s.d * 3); if (s.d > 1) { s.d = 0.01; s.a = Math.random() * TAU; before = s.d; }
          ctx.strokeStyle = s.d > 0.6 ? "#ff3d9a" : "#00e5ff"; ctx.lineWidth = 1 + s.d * 2;
          ctx.beginPath(); ctx.moveTo(cx + Math.cos(s.a) * before * reach * 0.9, cy + Math.sin(s.a) * before * reach * 0.9);
          ctx.lineTo(cx + Math.cos(s.a) * s.d * reach * 0.9, cy + Math.sin(s.a) * s.d * reach * 0.9); ctx.stroke();
        }
      } },
    { name: "Ripples", rings: [], last: 0, init: function () { this.rings = []; this.last = 0; },
      draw: function (t) {
        clear(0.2); if (t - this.last > 650) { this.last = t; this.rings.push({ born: t, x: W * (0.2 + Math.random() * 0.6), y: H * (0.2 + Math.random() * 0.6) }); }
        this.rings = this.rings.filter(function (r) { return t - r.born < 4200; });
        this.rings.forEach(function (r) {
          var age = (t - r.born) / 4200; ctx.strokeStyle = "hsla(" + (age * 300 + 170) + ",100%,60%," + (1 - age) * 0.8 + ")"; ctx.lineWidth = 2;
          ctx.beginPath(); ctx.arc(r.x, r.y, age * Math.max(W, H) * 0.45, 0, TAU); ctx.stroke();
        });
      } }
  ];
  var current = null, frame = 0;
  function setAnimation(i) {
    i = ((i % animations.length) + animations.length) % animations.length;
    current = animations[i]; save("cl_anim", i); $("anim-name").textContent = current.name;
    ctx.fillStyle = "#0b0f1a"; ctx.fillRect(0, 0, W, H);
    if (current.init) { current.init(); }
    if (reduce) { for (var k = 0; k < 40; k++) { current.draw(k * 80); } }     // one still picture, no motion
  }
  function loop(t) {
    if (!reduce && !document.hidden && current) { current.draw(t); }
    frame = requestAnimationFrame(loop);
  }
  $("anim").addEventListener("click", function () { setAnimation(load("cl_anim", 0) + 1); });

  // ---------- install as an app (phones, tablets, laptops) ----------
  var installEvent = null;
  window.addEventListener("beforeinstallprompt", function (e) { e.preventDefault(); installEvent = e; $("install").hidden = false; });
  $("install").addEventListener("click", function () {
    if (!installEvent) { return; }
    installEvent.prompt(); installEvent = null; $("install").hidden = true;
  });
  if ("serviceWorker" in navigator) { navigator.serviceWorker.register("/sw.js").catch(function () { /* not available: fine */ }); }

  fit();
  setAnimation(load("cl_anim", 0));
  frame = requestAnimationFrame(loop);
  if (token) { showApp(); }
})();
