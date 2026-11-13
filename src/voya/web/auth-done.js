(() => {
  "use strict";
  const token = document.querySelector('meta[name="voya-token"]')?.content || "";
  if (token) {
    try { localStorage.setItem("voya.token", token); } catch { /* private mode */ }
  }
  location.replace("/");
})();
