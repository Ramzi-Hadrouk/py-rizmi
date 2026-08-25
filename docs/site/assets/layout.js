/* py-Rizmi docs chrome: sidebar, topbar (back/home/theme), active nav.
   Pages contain <div id="site-chrome"></div> and <div class="shell">…  */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    /* All pages are flat in one directory — RELATIVE paths work on
       file://, localhost, and GitHub Pages (/py-rizmi/) alike. */
    var current = location.pathname.split("/").pop() || "index.html";

    /* ── sidebar ─────────────────────────────────────────── */
    var groups = [
      ["Getting started", [
        ["Overview", "index.html"],
        ["Quick start", "quickstart.html"],
      ]],
      ["Reference", [
        ["CLI reference", "cli.html"],
        ["Integration guide", "integration.html"],
      ]],
      ["Operations", [
        ["Packaging", "packaging.html"],
        ["Troubleshooting", "troubleshooting.html"],
      ]],
      ["Project", [
        ["Vision & roadmap", "vision.html"],
      ]],
    ];

    var sidebarHTML =
      '<a class="brand" href="index.html">' +
      '<img src="assets/logo.png" alt="py-Rizmi logo">' +
      '<span class="name">py-<span>Rizmi</span></span></a>';

    groups.forEach(function (g) {
      sidebarHTML += '<div class="nav-group"><h4>' + g[0] + "</h4>";
      g[1].forEach(function (link) {
        var cls = link[1] === current ? " active" : "";
        sidebarHTML += '<a class="' + cls.trim() + '" href="' + link[1] + '">' + link[0] + "</a>";
      });
      sidebarHTML += "</div>";
    });

    sidebarHTML +=
      '<div class="sidebar-foot">py-Rizmi Licensing · MIT<br>' +
      'created &amp; maintained by <b>Ramzi Hadrouk</b><br>' +
      '<a href="https://github.com/Ramzi-Hadrouk/py-rizmi">GitHub repository</a></div>';

    /* ── mount ───────────────────────────────────────────── */
    var aside = document.querySelector(".sidebar");
    if (aside) aside.innerHTML = sidebarHTML;

    var topbar = document.querySelector(".topbar");
    if (topbar) {
      topbar.innerHTML =
        '<button class="hamburger" id="nav-toggle" aria-label="Menu">&#9776;</button>' +
        '<a class="tb" href="#" id="back-btn">&larr; Back</a>' +
        '<a class="tb" href="index.html">Home</a>' +
        '<span class="spacer"></span>' +
        '<button class="tb" id="theme-toggle" aria-label="Toggle theme">' +
        '<span class="sun">&#9728;&#65039;</span><span class="moon">&#127769;</span>' +
        "<span>&nbsp;Theme</span></button>";
    }

    /* ── behaviour ───────────────────────────────────────── */
    var back = document.getElementById("back-btn");
    if (back) {
      back.addEventListener("click", function (e) {
        e.preventDefault();
        if (history.length > 1) history.back();
        else location.href = "index.html";
      });
    }

    var burger = document.getElementById("nav-toggle");
    if (burger) {
      burger.addEventListener("click", function () {
        document.body.classList.toggle("nav-open");
      });
      document.querySelectorAll(".nav-group a").forEach(function (a) {
        a.addEventListener("click", function () {
          document.body.classList.remove("nav-open");
        });
      });
      /* backdrop: click anywhere outside the drawer to close it */
      var scrim = document.createElement("div");
      scrim.className = "scrim";
      scrim.addEventListener("click", function () {
        document.body.classList.remove("nav-open");
      });
      document.body.appendChild(scrim);
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") document.body.classList.remove("nav-open");
      });
    }

    var toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", function () {
        var root = document.documentElement;
        var dark = root.getAttribute("data-theme") === "dark";
        var next = dark ? "light" : "dark";
        if (next === "dark") root.setAttribute("data-theme", "dark");
        else root.removeAttribute("data-theme");
        try { localStorage.setItem("rz-theme", next); } catch (e) {}
      });
    }

    /* keep theme consistent if the user toggles in another tab */
    window.addEventListener("storage", function (e) {
      if (e.key !== "rz-theme") return;
      var root = document.documentElement;
      if (e.newValue === "dark") root.setAttribute("data-theme", "dark");
      else root.removeAttribute("data-theme");
    });
  });
})();
