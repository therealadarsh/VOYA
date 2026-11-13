/* VOYA web app: plain JS, no build step. Every amount shown is labeled "est." unless it is money already spent. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (v, d = 0) => "$" + Number(v || 0).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  const money2 = (v) => money(v, Number(v) % 1 ? 2 : 0);
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* private mode */ } },
  };
  const state = { meta: null, planId: store.get("voya.plan"), version: 1, data: null, token: store.get("voya.token"), kids: [], interests: new Set(), dInterests: new Set() };

  async function api(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (state.token) headers["X-VOYA-Token"] = state.token;
    const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(json?.error?.message || (Array.isArray(json?.detail) ? json.detail.map((d) => d.msg).join("; ") : "Something went wrong."));
      err.code = json?.error?.code; err.status = res.status; throw err;
    }
    return json;
  }
  function toast(msg, action) {
    const t = $("#toast");
    t.innerHTML = `<span>${esc(msg)}</span>` + (action ? `<button type="button">${esc(action.label)}</button>` : "");
    t.hidden = false;
    if (action) $("button", t).onclick = () => { t.hidden = true; action.fn(); };
    clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), action ? 6000 : 3000);
  }
  function tab(name) {
    $$(".tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
    $$(".tab").forEach((s) => (s.hidden = s.id !== "tab-" + name));
    if (name === "trip") renderTrip();
    window.scrollTo(0, 0);
  }
  function seg(el, onChange) {
    $$("button", el).forEach((b) => (b.onclick = () => { $$("button", el).forEach((x) => x.setAttribute("aria-pressed", String(x === b))); onChange && onChange(b.dataset.v); }));
  }
  const segVal = (el) => $('button[aria-pressed="true"]', el)?.dataset.v || null;
  function chips(el, items, set) {
    el.innerHTML = items.map((i) => `<button type="button" class="chip" data-v="${esc(i)}" aria-pressed="${set.has(i)}">${esc(i[0].toUpperCase() + i.slice(1))}</button>`).join("");
    $$(".chip", el).forEach((c) => (c.onclick = () => { set.has(c.dataset.v) ? set.delete(c.dataset.v) : set.add(c.dataset.v); c.setAttribute("aria-pressed", String(set.has(c.dataset.v))); }));
  }
  function nextSaturday() { const d = new Date(); d.setDate(d.getDate() + ((6 - d.getDay() + 7) % 7 || 7)); return d.toISOString().slice(0, 10); }

  function rangeBar(low, point, high, budget, dashed) {
    const max = Math.max(Number(high), Number(budget || 0)) * 1.08 || 1;
    const pct = (v) => Math.min(100, (Number(v) / max) * 100).toFixed(2);
    return `<div class="range${dashed ? " dashed" : ""}" role="img" aria-label="Likely between ${money(low)} and ${money(high)}${budget ? `, budget ${money(budget)}` : ""}">
      <div class="span" style="left:${pct(low)}%;width:${Math.max(1, pct(high) - pct(low))}%"></div>
      <div class="pt" style="left:calc(${pct(point)}% - 2px)"></div>
      ${budget ? `<div class="cap" style="left:${pct(budget)}%" title="Budget"></div>` : ""}</div>`;
  }

  // ---------------------------------------------------------------- setup
  async function init() {
    state.meta = await api("GET", "/v1/meta");
    $("#demo-banner").hidden = !state.meta.demo_data;
    if ($("#preview-badge")) $("#preview-badge").hidden = !state.meta.preview;
    const opts = (kind) => state.meta.destinations.filter((d) => d.kind === kind).map((d) => `<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("");
    $("#f-dest").innerHTML = `<optgroup label="Cities">${opts("city")}</optgroup><optgroup label="National parks">${opts("park")}</optgroup>`;
    const cities = state.meta.destinations.filter((d) => d.kind === "city").map((d) => `<option value="${esc(d.id)}">${esc(d.name)}</option>`).join("");
    $("#f-from").insertAdjacentHTML("beforeend", cities);
    $("#d-from").insertAdjacentHTML("beforeend", cities);
    chips($("#interests"), state.meta.interests, state.interests);
    chips($("#d-interests"), state.meta.interests, state.dInterests);
    $("#f-date").value = $("#d-date").value = nextSaturday();
    seg($("#pace")); seg($("#firmness"), () => $(".firm").classList.remove("needs")); seg($("#d-firmness"));
    $("#f-budget").oninput = () => { const v = $("#f-budget").value; $("#firm-q").textContent = v ? `Is ${money(v)} a hard limit, or is there a little wiggle room?` : "Is this budget a hard limit, or is there a little wiggle room?"; };
    $("#f-days").oninput = () => ($("#lodging-box").hidden = Number($("#f-days").value) < 2);
    $("#f-lodging-booked").onchange = (e) => ($("#lodging-amt-wrap").hidden = !e.target.checked);
    $("#add-kid").onclick = () => { if (state.kids.length < 11) { state.kids.push($("#kid-band").value); renderKids(); } };
    $$(".tabs button").forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
    $$("[data-goto]").forEach((a) => (a.onclick = (e) => { e.preventDefault(); tab(a.dataset.goto); }));
    $("#plan-form").onsubmit = submitPlan;
    $("#disc-form").onsubmit = submitDiscover;
    $("#sheet-close").onclick = () => ($("#sheet").hidden = true);
    $("#signin-close").onclick = () => ($("#signin").hidden = true);
    $("#helper-form").onsubmit = (e) => { e.preventDefault(); ask($("#helper-msg").value); };
    $("#signin-form").onsubmit = signIn;
    $("#feedback-open").onclick = () => { $("#fb-sent").hidden = true; $("#fb-error").hidden = true; $("#feedback").hidden = false; $("#fb-message").focus(); };
    $("#feedback-close").onclick = () => ($("#feedback").hidden = true);
    $("#feedback-form").onsubmit = sendFeedback;
    const quick = ["It's raining, what now?", "Make it $20 cheaper", "Swap a stop for something outdoorsy", "Find something I'd like", "Why is dinner so expensive?"];
    $("#helper-chips").innerHTML = quick.map((q) => `<button type="button" class="chip">${esc(q)}</button>`).join("");
    $$("#helper-chips .chip").forEach((c) => (c.onclick = () => { $("#helper-msg").value = c.textContent; if (/rain/i.test(c.textContent)) $("#helper-rain").checked = true; ask(c.textContent); }));
    if (state.token) {
      try {
        const m = await api("GET", "/v1/me/memory");
        const get = (k) => m.remembered.find((p) => p.key === k)?.value;
        if (get("interests")) { get("interests").split(",").filter(Boolean).forEach((i) => state.interests.add(i)); chips($("#interests"), state.meta.interests, state.interests); }
        if (get("pace")) $$("#pace button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === get("pace"))));
        if (get("firmness")) $$("#firmness button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === get("firmness"))));
      } catch { /* signed out or no memory yet */ }
    }
    if (state.planId) { try { await loadPlan(); } catch { state.planId = null; store.set("voya.plan", null); } }
  }
  function renderKids() {
    $("#kids-list").innerHTML = state.kids.map((k, i) => `<button type="button" class="chip" aria-pressed="true" data-i="${i}" aria-label="Remove kid age ${esc(k)}">Age ${esc(k)} ✕</button>`).join("");
    $$("#kids-list .chip").forEach((c) => (c.onclick = () => { state.kids.splice(Number(c.dataset.i), 1); renderKids(); }));
  }

  // ----------------------------------------------------------------- plan
  function planRequest() {
    const firm = segVal($("#firmness"));
    if (!firm) { $(".firm").classList.add("needs"); throw new Error("Tell us if the budget is a hard limit or has some wiggle room."); }
    const req = {
      destination: $("#f-dest").value, start_date: $("#f-date").value, days: Number($("#f-days").value),
      budget: $("#f-budget").value, firmness: firm, pace: segVal($("#pace")) || "balanced",
      party: { adults: Number($("#f-adults").value), children: state.kids }, interests: [...state.interests],
      getting_there: { from_id: $("#f-from").value || null, mode: $("#f-mode").value, include_in_total: $("#f-gt-include").checked },
    };
    if (req.days > 1 && $("#f-lodging-booked").checked) req.lodging = { status: "booked", amount: $("#f-lodging-amt").value || "0" };
    const at = $("#f-anchor-title").value.trim();
    if (at && $("#f-anchor-start").value) req.anchor = { title: at, start: $("#f-anchor-start").value, duration_min: Math.round(Number($("#f-anchor-hours").value || 2) * 60), cost: $("#f-anchor-cost").value || "0" };
    return req;
  }
  async function submitPlan(e) {
    e.preventDefault();
    const err = $("#plan-error"); err.hidden = true;
    let req; try { req = planRequest(); } catch (x) { err.textContent = x.message; err.hidden = false; return; }
    $("#plan-btn").disabled = true; $("#plan-btn").textContent = "Planning…";
    try { show(await api("POST", "/v1/plans", req)); }
    catch (x) { err.textContent = x.message; err.hidden = false; }
    finally { $("#plan-btn").disabled = false; $("#plan-btn").textContent = "Plan my trip"; }
  }
  async function loadPlan() { show(await api("GET", `/v1/plans/${state.planId}`), true); }
  function show(res, quiet) {
    state.planId = res.plan_id; state.version = res.version; state.data = res; store.set("voya.plan", res.plan_id);
    $("#plan-form").hidden = true; $("#plan-view").hidden = false;
    renderPlan();
    if (!quiet) window.scrollTo(0, 0);
  }

  function renderPlan() {
    const { plan, saved, request } = state.data;
    const h = plan.headline;
    const firmText = h.firmness === "hard" ? "hard limit" : "some wiggle room";
    const fitLine = plan.status === "ready"
      ? (h.firmness === "hard" ? "Fits even if prices come in high." : `Fits in about ${Math.round(h.p_under_budget_est * 10)} of 10 price scenarios.`)
      : "";
    const gt = plan.getting_there_optional;
    let html = `<div class="card headline">
      <div class="sub">${esc(plan.destination.name)} · ${request.days} day${request.days > 1 ? "s" : ""} · ${request.party.adults + request.party.children.length} ${request.party.adults + request.party.children.length > 1 ? "people" : "person"}</div>
      <div><span class="big">est. ${money(h.point)}</span> <span class="sub">of ${money(h.budget)} · ${firmText}</span></div>
      ${rangeBar(h.low, h.point, h.high, h.budget)}
      <div class="legend"><span>likely ${money(h.low)}–${money(h.high)}</span><span>budget ${money(h.budget)}</span></div>
      ${plan.status === "ready" ? `<div class="keep">You could keep about ${money(h.you_could_keep)}</div><p class="hint">${fitLine}</p>` : ""}
      <div class="stat-row"><span>Hidden costs <b>${money(h.hidden_costs)}</b> (tax, tips, transit, extras)</span><span><b>${Math.round(h.data_backed_share * 100)}%</b> from real price data</span></div>
    </div>`;
    if (plan.status !== "ready") {
      const why = h.firmness === "hard" ? "to fit even if prices run high" : "to fit in 9 of 10 price scenarios";
      html += `<div class="card warn-card"><h2>About ${money(plan.gap)} more needed ${why}</h2>
        <p>This is the cheapest plan we could make. Free ideas: ${plan.free_alternatives.map(esc).join(", ") || "parks and walks"}.</p>
        <p class="hint">Try ${h.firmness === "hard" ? '"Some wiggle room", ' : ""}fewer days, booked lodging, or a bigger budget.</p></div>`;
    }
    if (gt && gt.available) {
      html += `<div class="card"><div class="row" style="align-items:center"><div><b>${esc(gt.label)}</b><div class="hint">${esc(gt.mode)} · about ${Math.round((gt.minutes_one_way || 0) / 60 * 10) / 10} h each way</div></div>
        <label class="check" style="flex:0 0 auto"><input type="checkbox" id="gt-toggle" ${gt.included ? "checked" : ""}> Include</label></div></div>`;
    }
    if (plan.worth_it.length || plan.status === "ready") {
      html += `<div class="card"><h2>Worth it?</h2><p class="hint">Upgrades that still fit your budget. Your call.</p><div class="upgrades">` +
        plan.worth_it.map((u) => `<div class="up"><div class="grow"><b>${esc(u.title)}</b> <span class="muted">instead of ${esc(u.replaces)}</span><div class="hint">${esc(u.why)}</div></div>
          <div><div class="delta">+${money2(u.delta)}</div><button class="small go" data-up="${esc(u.upgrade_id)}">Add</button></div></div>`).join("") +
        `</div><button class="ghost" style="margin-top:10px;width:100%" id="find-like">Find something I'd like</button></div>`;
    }
    for (const d of plan.days) {
      html += `<div class="card day"><h3><span>${new Date(d.date + "T12:00:00").toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}</span><span>est. ${money(d.day_total)}</span></h3>`;
      for (const it of d.items) {
        const c = it.cost;
        const guess = c && c.source === "type_guess";
        const kids = (it.children || []).map((k) => `${esc(k.label)} ${money2(k.amount)}`).join(" · ");
        html += `<div class="item"><div class="t">${esc(it.time)}</div><div><b>${esc(it.title)}</b> ${it.hidden_gem ? '<span class="pill gem">hidden gem</span>' : ""} ${it.kind === "anchor" ? '<span class="pill">your plan</span>' : ""}</div>
          <div class="amt">${c ? (Number(it.item_total) === 0 ? "Free" : "est. " + money2(it.item_total)) : ""}</div>
          ${c && Number(c.high) > 0 && c.low !== c.high ? `<div class="mini">${rangeBar(c.low, c.amount, c.high, null, guess)}</div>` : ""}
          <div class="why">${esc(it.why)}${guess ? " · price is a guess" : ""}</div>${kids ? `<div class="kids">incl. ${kids}</div>` : ""}</div>`;
      }
      if (d.transit.length) html += `<p class="hint">Transit: ${d.transit.map((t) => `est. ${money2(t.amount)}`).join(" + ")}</p>`;
      html += `</div>`;
    }
    html += `<div class="card lines"><h3>Trip costs</h3>` + plan.trip_lines.filter((l) => l.category !== "extras").map((l) => `<div><span>${esc(l.label)}</span><span>${l.is_estimate ? "est. " : ""}${money2(l.amount)}${l.line_id === "gifts" ? ` <button class="small" id="edit-gifts">Edit</button>` : ""}</span></div>`).join("") +
      `<div><span>Water, snacks, lockers</span><span>est. ${money2(plan.trip_lines.filter((l) => l.category === "extras").reduce((a, l) => a + Number(l.amount), 0))}</span></div>` +
      `<div><span>Tip on sit-down meals</span><span>${esc(request.tip_pct)}% <button class="small" id="edit-tip">Edit</button></span></div></div>`;
    if (plan.notes?.length) html += `<p class="hint">${plan.notes.map(esc).join(" ")}</p>`;
    html += `<div class="actions"><button class="ghost" id="new-plan">New plan</button><button class="ghost" id="undo">Undo</button>
      <button class="ghost" id="ask">Ask VOYA</button><button class="primary" style="margin:0" id="save">${saved ? "Saved ✓ · Track spend" : "Save trip"}</button></div>`;
    $("#plan-view").innerHTML = html;

    $$("[data-up]").forEach((b) => (b.onclick = async () => { try { show(await api("POST", `/v1/plans/${state.planId}/upgrades/${encodeURIComponent(b.dataset.up)}`), true); toast("Upgrade added", { label: "Undo", fn: undo }); } catch (x) { toast(x.message); } }));
    $("#find-like") && ($("#find-like").onclick = () => { openHelper(); $("#helper-msg").value = "Find something I'd like"; ask("Find something I'd like"); });
    $("#gt-toggle") && ($("#gt-toggle").onchange = (e) => edit({ include_getting_there: e.target.checked }));
    $("#edit-gifts") && ($("#edit-gifts").onclick = () => { const v = prompt("Gifts & souvenirs allowance (USD)", plan.trip_lines.find((l) => l.line_id === "gifts")?.amount || "0"); if (v !== null && v !== "" && !isNaN(v)) edit({ gifts_amount: v }); });
    $("#edit-tip").onclick = () => { const v = prompt("Tip % on sit-down meals", request.tip_pct); if (v !== null && v !== "" && !isNaN(v)) edit({ tip_pct: v }); };
    $("#new-plan").onclick = () => { $("#plan-form").hidden = false; $("#plan-view").hidden = true; window.scrollTo(0, 0); };
    $("#undo").onclick = undo;
    $("#ask").onclick = openHelper;
    $("#save").onclick = () => (saved ? tab("trip") : save());
  }
  async function edit(body) { try { show(await api("POST", `/v1/plans/${state.planId}/edit`, body), true); } catch (x) { toast(x.message); } }
  async function undo() { try { show(await api("POST", `/v1/plans/${state.planId}/undo`), true); toast("Undone"); } catch (x) { toast(x.message); } }

  // ------------------------------------------------------------- accounts
  async function save() {
    if (!state.token) { $("#signin").hidden = false; return; }
    try { show(await api("POST", `/v1/plans/${state.planId}/save`), true); toast("Trip saved. You can track spending now."); }
    catch (x) { if (x.status === 401) { state.token = null; store.set("voya.token", null); $("#signin").hidden = false; } else toast(x.message); }
  }
  async function sendFeedback(e) {
    e.preventDefault();
    const err = $("#fb-error"); err.hidden = true;
    try {
      await api("POST", "/v1/feedback", { message: $("#fb-message").value, contact: $("#fb-contact").value || null });
      $("#fb-sent").hidden = false;
      $("#fb-message").value = "";
    } catch (x) { err.textContent = x.message; err.hidden = false; }
  }
  async function signIn(e) {
    e.preventDefault();
    const err = $("#si-error"); err.hidden = true;
    try {
      const r = await api("POST", "/v1/auth/start", { email: $("#si-email").value, is_adult: $("#si-adult").checked });
      if (r.status === "email_sent") { $("#si-sent").hidden = false; return; }
      state.token = r.token; store.set("voya.token", r.token); $("#signin").hidden = true; await save();
    } catch (x) { err.textContent = x.message; err.hidden = false; }
  }

  // --------------------------------------------------------------- helper
  function openHelper() {
    const days = state.data?.request.days || 1;
    $("#helper-day").innerHTML = Array.from({ length: days }, (_, i) => `<option value="${i}">Day ${i + 1}</option>`).join("");
    const n = new Date(); $("#helper-time").value = `${String(n.getHours()).padStart(2, "0")}:${String(n.getMinutes()).padStart(2, "0")}`;
    $("#helper-out").innerHTML = ""; $("#sheet").hidden = false; $("#helper-msg").focus();
  }
  async function ask(message) {
    if (!message.trim()) return;
    const out = $("#helper-out"); out.innerHTML = `<p class="hint">Thinking…</p>`;
    try {
      const r = await api("POST", `/v1/plans/${state.planId}/helper`, { message, local_time: $("#helper-time").value || null, day: Number($("#helper-day").value || 0), raining: $("#helper-rain").checked });
      let html = `<p>${esc(r.message)}</p>`;
      html += r.options.map((o) => `<div class="opt"><div class="row"><div><b>${esc(o.title)}</b><div class="hint">${esc(o.why || "")}${o.walk_min != null ? ` · ${o.walk_min} min walk` : ""}${o.est_cost ? ` · est. ${money2(o.est_cost)}` : ""}</div>
        <div class="hint">New total est. ${money2(o.new_total)}</div></div>
        <div style="flex:0 0 auto"><button class="small ${o.raises_total ? "" : "go"}" data-prop="${esc(o.proposal_id)}" data-token="${esc(o.token)}" data-raise="${o.raises_total}">${o.raises_total ? `Add (+${money2(o.delta)})` : Number(o.delta) < 0 ? `Apply (−${money2(Math.abs(o.delta))})` : "Apply"}</button></div></div></div>`).join("");
      if (r.info?.free_option) html += `<div class="opt"><b>${esc(r.info.free_option.title)}</b><div class="hint">${esc(r.info.free_option.why)}</div></div>`;
      if (r.info?.explain) html += `<table class="ex">${r.info.explain.lines.map((l) => `<tr><td>${esc(l.label)}</td><td>est. ${money2(l.amount)}</td><td>${money2(l.low)}–${money2(l.high)}</td><td>${esc(l.source.replace("_", " "))} · ${Math.round(l.confidence * 100)}% sure</td></tr>`).join("")}</table>`;
      html += `<p class="hint">${r.used_model ? "AI-assisted" : "Built-in helper"} · ${esc(r.stop_reason)} · every option re-checked against your budget</p>`;
      out.innerHTML = html;
      $$("[data-prop]", out).forEach((b) => (b.onclick = async () => {
        try {
          show(await api("POST", `/v1/plans/${state.planId}/proposals/${b.dataset.prop}/apply`, { token: b.dataset.token }), true);
          $("#sheet").hidden = true; toast("Plan updated", { label: "Undo", fn: undo });
        } catch (x) { toast(x.message); }
      }));
    } catch (x) { out.innerHTML = `<p class="error">${esc(x.message)}</p>`; }
  }

  // ------------------------------------------------------------- discover
  async function submitDiscover(e) {
    e.preventDefault();
    const out = $("#disc-results"); out.innerHTML = `<p class="hint">Looking…</p>`;
    try {
      const r = await api("POST", "/v1/discover", { from_id: $("#d-from").value || null, start_date: $("#d-date").value, days: Number($("#d-days").value), budget: $("#d-budget").value, firmness: segVal($("#d-firmness")) || "wiggle", party: { adults: Number($("#d-adults").value) }, interests: [...state.dInterests] });
      out.innerHTML = (r.empty_note ? `<p class="hint">${esc(r.empty_note)}</p>` : "") + r.options.map((o, i) => `<div class="card">
        <div class="row"><div><h2>${esc(o.name)}</h2><div class="hint">${esc(o.kind)}${o.minutes_one_way ? ` · ${Math.round(o.minutes_one_way / 6) / 10} h away` : ""}</div></div>
        <div style="text-align:right;flex:0 0 auto"><div><b>est. ${money(o.est_total)}</b></div>${o.fits ? `<span class="pill good">fits · keep ~${money(o.you_could_keep)}</span>` : `<span class="pill warn">${money(o.gap)} over</span>`}</div></div>
        ${rangeBar(o.range[0], o.est_total, o.range[1], $("#d-budget").value)}
        <p class="hint">${o.highlights.map(esc).join(" · ")}${o.getting_there_optional?.available ? ` · + ${esc(o.getting_there_optional.label)}` : ""}</p>
        <button class="ghost" data-i="${i}" style="width:100%">Plan this</button></div>`).join("");
      $$("[data-i]", out).forEach((b) => (b.onclick = async () => {
        const preq = r.options[Number(b.dataset.i)].plan_request;
        try { show(await api("POST", "/v1/plans", preq)); tab("plan"); } catch (x) { toast(x.message); }
      }));
    } catch (x) { out.innerHTML = `<p class="error">${esc(x.message)}</p>`; }
  }

  // ----------------------------------------------------------------- trip
  async function renderTrip() {
    const v = $("#trip-view");
    if (!state.planId || !state.data) { v.innerHTML = `<div class="card"><h2>No trip yet</h2><p>Plan a trip, then save it to track what you spend.</p></div>`; return; }
    if (!state.token || !state.data.saved) { v.innerHTML = `<div class="card"><h2>Save your trip first</h2><p>Sign in to keep this trip and track spending.</p><button class="primary" id="t-save">Sign in & save</button></div>`; $("#t-save").onclick = save; return; }
    v.innerHTML = `<p class="hint">Loading…</p>`;
    try {
      const r = await api("GET", `/v1/plans/${state.planId}/budget`);
      const b = r.budget;
      const stops = state.data.plan.days.flatMap((d) => d.items.filter((i) => i.cost).map((i) => ({ id: i.line_id, label: `Day ${d.day + 1} · ${i.time} ${i.title}` })));
      v.innerHTML = `<div class="card headline"><div class="sub">${esc(state.data.plan.destination.name)}</div>
        <div><span class="big">${money2(b.spent)}</span> <span class="sub">spent of ${money(b.budget)}</span></div>
        ${rangeBar(b.spent, b.projected_total_est, b.projected_fit_value, b.budget)}
        <div class="stat-row"><span>Projected <b>est. ${money(b.projected_total_est)}</b></span><span>${b.status === "on_track" ? `<span class="pill good">on track ✓</span>` : `<span class="pill warn">at risk</span>`}</span><span>Could keep <b>~${money(b.you_could_keep)}</b></span></div></div>
        ${b.recovery_note ? `<div class="card warn-card"><h2>Heads up</h2><p>${esc(b.recovery_note)}</p></div>` : ""}
        ${b.recovery.length ? `<div class="card warn-card"><h2>Ways to get back under</h2>${b.recovery.map((o, i) => `<div class="opt"><div class="row"><div><b>${esc(o.summary)}</b><div class="hint">saves about ${money2(o.saving_est)}</div></div><button class="small go" style="flex:0 0 auto" data-rec="${i}">Apply</button></div></div>`).join("")}</div>` : ""}
        <form class="card form" id="spend-form"><h2>Log spend</h2>
          <div class="row"><label>Amount (USD) <input type="number" id="s-amt" min="0.01" step="0.01" required></label>
          <label>Category <select id="s-cat">${state.meta.spend_categories.map((c) => `<option>${esc(c)}</option>`).join("")}</select></label></div>
          <label>For which stop? <select id="s-line"><option value="">— not in the plan —</option>${stops.map((s) => `<option value="${esc(s.id)}">${esc(s.label)}</option>`).join("")}</select></label>
          <label>Note <input id="s-note" maxlength="120" placeholder="optional"></label>
          <button class="primary" type="submit">Log it</button></form>
        <div class="card lines"><h3>Logged</h3>${r.spends.length ? r.spends.map((s) => `<div><span>${esc(s.category)}${s.note ? " · " + esc(s.note) : ""}</span><span>${money2(s.amount)} ✓ <button class="small" data-del="${esc(s.id)}" aria-label="Delete entry">✕</button></span></div>`).join("") : `<p class="hint">Nothing yet.</p>`}</div>
        <div class="card"><h3>What VOYA remembers</h3><div id="mem-list" class="lines"></div>
          <button class="ghost" id="remember" style="width:100%;margin-top:8px">Remember my interests, pace and tip from this trip</button></div>
        <div class="card"><h3>Your data</h3><div class="row"><button class="ghost" id="export">Export</button><button class="ghost" id="delete-me">Delete my data</button></div></div>`;
      $("#spend-form").onsubmit = async (e) => {
        e.preventDefault();
        try {
          await api("POST", `/v1/plans/${state.planId}/spend`, { amount: $("#s-amt").value, category: $("#s-cat").value, line_id: $("#s-line").value || null, note: $("#s-note").value || null, idempotency_key: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random() });
          toast("Logged"); renderTrip();
        } catch (x) { toast(x.message); }
      };
      $$("[data-del]", v).forEach((btn) => (btn.onclick = async () => { await api("DELETE", `/v1/plans/${state.planId}/spend/${btn.dataset.del}`); renderTrip(); }));
      $$("[data-rec]", v).forEach((btn) => (btn.onclick = async () => {
        const o = b.recovery[Number(btn.dataset.rec)];
        try { show(await api("POST", `/v1/plans/${state.planId}/recovery`, { slot_id: o.slot_id, action: o.action, to_place_id: o.to_place_id }), true); toast("Plan updated", { label: "Undo", fn: undo }); renderTrip(); } catch (x) { toast(x.message); }
      }));
      const showMem = (m) => {
        $("#mem-list").innerHTML = m.remembered.length
          ? m.remembered.map((p) => `<div><span>${esc(p.key)}: <b>${esc(p.value)}</b> <span class="hint">(${esc(p.source)})</span></span><button class="small" data-forget="${esc(p.key)}">Forget</button></div>`).join("")
          : `<p class="hint">Nothing yet. VOYA only remembers what you ask it to.</p>`;
        $$("[data-forget]", v).forEach((f) => (f.onclick = async () => showMem(await api("DELETE", `/v1/me/memory/${f.dataset.forget}`))));
      };
      showMem(await api("GET", "/v1/me/memory"));
      $("#remember").onclick = async () => {
        const q = state.data.request;
        showMem(await api("POST", "/v1/me/memory", { values: { interests: q.interests.join(","), pace: q.pace, tip_pct: String(q.tip_pct), firmness: q.firmness } }));
        toast("Remembered. Forget anytime.");
      };
      $("#export").onclick = async () => { const data = await api("GET", "/v1/me/export"); const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })); a.download = "voya-export.json"; a.click(); };
      $("#delete-me").onclick = async () => { if (!confirm("Delete your trips, spending and preferences? This can't be undone.")) return; await api("DELETE", "/v1/me"); state.token = null; store.set("voya.token", null); toast("Your data was deleted."); renderTrip(); };
    } catch (x) { v.innerHTML = `<div class="card"><p class="error">${esc(x.message)}</p></div>`; }
  }

  init().catch((x) => { document.querySelector("main").insertAdjacentHTML("afterbegin", `<p class="error">${esc(x.message)}</p>`); });
})();
