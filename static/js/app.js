/* ============================================================
   app.js — small progressive-enhancement helpers.
   The heavy interactivity (live availability check, drawer loading)
   is done with HTMX attributes in the templates; this file only
   handles the drawer close behaviour and auto-dismissing messages.
   ============================================================ */
(function () {
  "use strict";

  // Close the room drawer when the backdrop or a [data-close] element is clicked.
  document.addEventListener("click", function (e) {
    if (e.target.matches(".drawer-backdrop, [data-close]")) {
      const drawer = document.getElementById("room-drawer");
      if (drawer) drawer.innerHTML = "";
    }
  });

  // Close the drawer on Escape.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      const drawer = document.getElementById("room-drawer");
      if (drawer) drawer.innerHTML = "";
    }
  });

  // Auto-dismiss flash messages after 5 seconds.
  window.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".messages li").forEach(function (el) {
      setTimeout(function () {
        el.style.transition = "opacity .4s";
        el.style.opacity = "0";
        setTimeout(function () { el.remove(); }, 400);
      }, 5000);
    });
  });
})();
