(function () {
  document.addEventListener("DOMContentLoaded", function () {
    var mount = document.getElementById("site-header");
    if (!mount) return;
    var parts = location.pathname.split("/").filter(Boolean);
    // GitHub Pages serves the site at /py-rizmi/<page>.html
    var base = "/";
    if (parts.length > 0 && parts[0] !== "") {
      base = "/" + parts[0] + "/";
    }
    var links = [
      ["Features", "#features"],
      ["Quick Start", "quickstart.html"],
      ["CLI", "cli.html"],
      ["Integration", "integration.html"],
      ["Packaging", "packaging.html"],
      ["Troubleshooting", "troubleshooting.html"],
      ["Vision", "vision.html"],
    ];
    var html =
      '<header class="site"><div class="container">' +
      '<a class="logo" href="' + base + '">py-<span>Rizmi</span></a>' +
      '<nav class="main">' +
      links.map(function (l) {
        return '<a href="' + base + l[1] + '">' + l[0] + "</a>";
      }).join("") +
      '</nav><a class="gh-btn" href="https://github.com/Ramzi-Hadrouk/py-rizmi">GitHub &#9733;</a>' +
      "</div></header>";
    mount.outerHTML = html;
  });
})();
