(() => {
  "use strict";
  const form = document.getElementById("invite-form");
  const err = document.getElementById("invite-error");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    err.hidden = true;
    const code = document.getElementById("invite-code").value;
    const res = await fetch("/v1/preview/unlock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) {
      const json = await res.json().catch(() => ({}));
      err.textContent = json?.error?.message || "That invite code is not valid.";
      err.hidden = false;
      return;
    }
    location.reload();
  });
})();
