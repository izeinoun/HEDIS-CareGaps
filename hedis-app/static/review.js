// Reviewer: chart with clickable evidence highlights, the AI proposals with
// confirm/modify/reject, the compliance-threshold advisory and compound-exclusion
// tracker, and the measure-level sign-off (with a confidence gate). Every action is
// stamped with the acting user (window.ACTOR) and appended to the audit log server-side.
(function () {
  const findings = JSON.parse(document.getElementById("findings-data").textContent);
  const chartText = JSON.parse(document.getElementById("chart-data").textContent);
  const decisions = findings.decisions || {};
  const elements = findings.elements || [];
  const exclusions = findings.exclusions || [];

  const FINAL_LABELS = {
    gap_closed: "Gap closed", gap_open: "Gap open (care gap remains)",
    exclusion_applied: "Exclusion applied", needs_more_info: "Needs more info",
  };
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const actor = () => window.ACTOR || "u_reviewer";

  // --- 1. Highlighted chart -------------------------------------------------
  const anchors = [];
  elements.forEach((e, i) => { if (e.evidence_anchored && e.char_start != null) anchors.push({ start: e.char_start, end: e.char_end, cls: "el", id: "el-" + i }); });
  exclusions.forEach((x, i) => { if (x.char_start != null) anchors.push({ start: x.char_start, end: x.char_end, cls: "ex", id: "ex-" + i }); });
  anchors.sort((a, b) => a.start - b.start);
  const chartEl = document.getElementById("chart");
  let html = "", cursor = 0;
  for (const a of anchors) {
    if (a.start < cursor) continue;
    html += esc(chartText.slice(cursor, a.start));
    html += `<mark class="${a.cls}" id="hl-${a.id}">` + esc(chartText.slice(a.start, a.end)) + `</mark>`;
    cursor = a.end;
  }
  html += esc(chartText.slice(cursor));
  chartEl.innerHTML = html;
  function flash(id) {
    const mark = document.getElementById("hl-" + id);
    if (!mark) return;
    mark.scrollIntoView({ behavior: "smooth", block: "center" });
    mark.classList.add("flash"); setTimeout(() => mark.classList.remove("flash"), 1400);
  }

  // --- 2. Per-finding decisions --------------------------------------------
  const PASS = window.PASS || "primary";
  async function saveDecision(key, action, finalValue) {
    const res = await fetch(window.DECISION_URL, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, action, final_value: finalValue, actor_id: actor(), pass: PASS }),
    });
    return res.ok;
  }
  function decideControls(key, aiValue, card) {
    const wrap = document.createElement("div"); wrap.className = "decide";
    const prior = decisions[key];
    const modInput = document.createElement("input");
    modInput.placeholder = "corrected value"; modInput.value = (prior && prior.final_value) || "";
    modInput.style.display = "none";
    const note = document.createElement("div"); note.className = "decision-note";
    function reflect(action) {
      wrap.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      const btn = wrap.querySelector(".act-" + action); if (btn) btn.classList.add("active");
      modInput.style.display = action === "modify" ? "" : "none";
      card.classList.remove("decided-confirm", "decided-reject");
      if (action === "confirm") card.classList.add("decided-confirm");
      if (action === "reject") card.classList.add("decided-reject");
    }
    ["confirm", "modify", "reject"].forEach((action) => {
      const b = document.createElement("button"); b.className = "act-" + action;
      b.textContent = action[0].toUpperCase() + action.slice(1);
      b.onclick = async () => {
        const finalValue = action === "confirm" ? aiValue : action === "modify" ? modInput.value : null;
        if (await saveDecision(key, action, finalValue)) {
          decisions[key] = { action, final_value: finalValue };
          reflect(action); note.textContent = "Saved: " + action + (finalValue ? " → " + finalValue : "");
        }
      };
      wrap.appendChild(b);
    });
    wrap.appendChild(modInput);
    card.appendChild(wrap); card.appendChild(note);
    if (prior) { reflect(prior.action); note.textContent = "Recorded: " + prior.action + (prior.final_value ? " → " + prior.final_value : ""); }
  }

  // --- 3. Elements (with compliance advisory) ------------------------------
  const elBox = document.getElementById("elements");
  elements.forEach((e, i) => {
    const key = "el:" + e.element_key;
    const card = document.createElement("div");
    card.className = "finding " + (e.ai_value ? "found" : "not_found");
    const conf = Math.round((e.ai_confidence || 0) * 100);
    const roleBadge = e.evidence_role
      ? `<span class="role-badge">${esc(e.evidence_role.replace(/_/g, " "))}</span>` : "";
    let inner = `<div class="f-head"><span class="f-label">${esc(e.element_label || e.element_key)}${roleBadge}</span>
      <span class="muted small">${esc(e.element_type || "")}${e.unit ? " · " + esc(e.unit) : ""}</span></div>`;
    if (e.ai_value) {
      inner += `<div class="f-value">${esc(e.ai_value)}${e.unit ? " " + esc(e.unit) : ""}${e.required ? '<span class="req">required</span>' : ""}</div>`;
      inner += `<div class="conf"><i style="width:${conf}%"></i></div>`;
    } else {
      inner += `<div class="f-value muted">Not documented${e.required ? '<span class="req">required · gap</span>' : ""}</div>`;
    }
    card.innerHTML = inner;

    // Compliance-threshold advisory (reviewer aid, never a determination)
    const c = e.compliance || {};
    if (e.ai_value && c.checkable) {
      const adv = document.createElement("div");
      adv.className = "advisory " + (c.meets ? "meets" : "nomeet");
      adv.innerHTML = `<b>${c.meets ? "Meets" : "Does not meet"}</b> threshold — ${esc(c.basis)} <span class="muted">· ${esc(c.hint)}</span> <span class="aidnote">reviewer aid, not a determination</span>`;
      card.appendChild(adv);
    } else if (e.ai_value && c.hint) {
      const adv = document.createElement("div"); adv.className = "advisory info";
      adv.innerHTML = `<span class="muted">Hint: ${esc(c.hint)}</span>`;
      card.appendChild(adv);
    }

    if (e.evidence_text) {
      const ev = document.createElement("div");
      ev.className = "evidence" + (e.evidence_anchored ? "" : " unanchored");
      ev.textContent = "“" + e.evidence_text + "”";
      if (e.evidence_anchored) ev.onclick = () => flash("el-" + i);
      card.appendChild(ev);
    }
    const meta = document.createElement("div"); meta.className = "meta";
    meta.innerHTML =
      (e.evidence_anchored ? `<span class="tag">p.${e.page_number ?? "?"}</span>` : `<span class="tag warn">unanchored</span>`) +
      `<span>conf ${conf}%</span>` +
      (e.in_window === false ? `<span class="tag warn">out of window</span>` : "") +
      (e.timing ? `<span>${esc(e.timing)}</span>` : "");
    card.appendChild(meta);
    if (e.ai_value) decideControls(key, e.ai_value, card);
    elBox.appendChild(card);
  });

  // --- 4. Exclusions (with compound tracker) -------------------------------
  const exBox = document.getElementById("exclusions");
  if (!exclusions.length) exBox.innerHTML = '<p class="muted small">No candidate exclusions found in the chart.</p>';
  exclusions.forEach((x, i) => {
    const key = "ex:" + x.rule_key;
    const card = document.createElement("div"); card.className = "finding ex";
    const conf = Math.round((x.ai_confidence || 0) * 100);
    const vsLink = x.value_set_name
      ? `<a href="/vsd?vs=${encodeURIComponent(x.value_set_name)}" target="_blank" title="View codes in the VSD">${esc(x.value_set_name)} ↗</a>`
      : "—";
    card.innerHTML =
      `<div class="f-head"><span class="f-label">${esc(x.rule_label || x.rule_key)}</span>
        <span class="chip scope-${x.scope}">${x.scope}</span></div>
      <div class="small muted">Value set: ${vsLink} · matched “${esc(x.matched_term || "")}”</div>`;

    if (x.compound && Array.isArray(x.components)) {
      const box = document.createElement("div"); box.className = "components";
      box.innerHTML = `<div class="comp-head">Compound — components present / missing:</div>` +
        x.components.map(c => `<span class="comp ${c.present ? "yes" : "no"}">${c.present ? "✓" : "○"} ${esc(c.term)}</span>`).join(" ");
      card.appendChild(box);
    }

    const ev = document.createElement("div"); ev.className = "evidence ex";
    ev.textContent = "…" + (x.evidence_text || "") + "…"; ev.onclick = () => flash("ex-" + i);
    card.appendChild(ev);
    const meta = document.createElement("div"); meta.className = "meta";
    const disp = (x.disposition || "proposed").replace(/_/g, " ");
    meta.innerHTML =
      `<span class="tag">p.${x.page_number ?? "?"}</span>` +
      `<span class="tag ${x.disposition === "proposed" ? "" : "warn"}">${esc(disp)}</span>` +
      `<span>origin: ${esc(x.origin || "measure")}</span>` +
      (x.age_check && x.age_check !== "not_applicable" ? `<span class="tag ${x.age_check === "out_of_band" ? "warn" : ""}">age ${esc(x.age_check.replace(/_/g, " "))}</span>` : "") +
      (x.already_applied ? `<span class="tag">already applied</span>` : "");
    card.appendChild(meta);
    if (x.note) { const n = document.createElement("div"); n.className = "small muted"; n.textContent = x.note; card.appendChild(n); }
    if (!x.already_applied) decideControls(key, x.rule_label || x.rule_key, card);
    exBox.appendChild(card);
  });

  // --- 5. Measure-level sign-off (with confidence gate) --------------------
  const panel = document.getElementById("signoff-panel");
  const mr = findings.measure_result || {};
  const decided = mr.reviewer_decision && mr.reviewer_decision !== "pending";

  function renderSignoff() {
    const options = Object.entries(FINAL_LABELS)
      .map(([v, l]) => `<option value="${v}">${l}</option>`).join("");
    panel.innerHTML = `
      <div class="card signoff ${decided ? "done" : ""}">
        <div class="so-head">
          <div><span class="so-label">Measure result</span>
            <div class="so-status">${esc((mr.proposed_status || "").replace(/_/g, " "))}</div>
            <div class="muted small">${esc(mr.proposed_basis || "")}</div></div>
          <div class="so-state" id="so-state">${decided
            ? `Signed off: <b>${esc(mr.final_status || "")}</b> — ${esc(mr.reviewer_decision)} by ${esc(mr.decided_by || "")}`
            : `<span class="pending">Pending sign-off</span>`}</div>
        </div>
        <div class="so-actions" id="so-actions">
          <button class="btn primary" id="so-accept">Accept result</button>
          <button class="btn" id="so-override">Override…</button>
          <button class="btn" id="so-escalate">Escalate…</button>
          <div class="so-override-box" id="so-obox" style="display:none">
            <select id="so-final">${options}</select>
            <input id="so-note" placeholder="reason (optional)">
            <button class="btn" id="so-save-mod">Save override</button>
            <button class="btn" id="so-save-rej">Reject result</button>
          </div>
        </div>
        <div class="so-msg" id="so-msg"></div>
      </div>`;

    const msg = panel.querySelector("#so-msg");
    async function post(decision) {
      const body = { decision, actor_id: actor(), pass: PASS };
      if (decision !== "accepted") {
        body.final_status = panel.querySelector("#so-final").value;
        body.note = panel.querySelector("#so-note").value;
      }
      const res = await fetch(window.SIGNOFF_URL, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
      const data = await res.json();
      if (res.status === 409 && data.gate === "confidence") {
        msg.className = "so-msg gate";
        msg.innerHTML = `<b>Confidence gate:</b> ${esc(data.message)}<ul>` +
          data.blockers.map(b => `<li>${esc(b.label)} — ${esc(b.why)}</li>`).join("") + `</ul>`;
        return;
      }
      if (data.ok) {
        Object.assign(mr, data.measure_result);
        panel.querySelector("#so-state").innerHTML =
          `Signed off: <b>${esc(mr.final_status)}</b> — ${esc(mr.reviewer_decision)} by ${esc(mr.decided_by || "")}`;
        panel.querySelector(".signoff").classList.add("done");
        panel.querySelector("#so-actions").style.display = "none";
        msg.className = "so-msg ok"; msg.textContent = "Recorded to the audit log.";
      } else {
        msg.className = "so-msg gate"; msg.textContent = data.error || "Could not sign off.";
      }
    }
    panel.querySelector("#so-accept").onclick = () => post("accepted");
    panel.querySelector("#so-override").onclick = () =>
      { const b = panel.querySelector("#so-obox"); b.style.display = b.style.display === "none" ? "flex" : "none"; };
    panel.querySelector("#so-save-mod").onclick = () => post("modified");
    panel.querySelector("#so-save-rej").onclick = () => post("rejected");
    panel.querySelector("#so-escalate").onclick = async () => {
      const reason = prompt("Escalate this measure for review — reason:");
      if (reason === null) return;
      const res = await fetch(window.ESCALATE_URL, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, actor_id: actor(), pass: PASS }),
      });
      const data = await res.json();
      if (data.ok) { msg.className = "so-msg gate"; msg.textContent = "Escalated and logged to the audit trail."; }
    };
  }
  renderSignoff();
})();
