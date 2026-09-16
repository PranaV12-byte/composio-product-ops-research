const labels = {
  ready_now: "Ready now",
  buildable_with_caveat: "Buildable with caveat",
  product_ops_required: "Product Ops required",
  unknown: "Unknown",
  self_serve_free: "Self-serve free",
  self_serve_trial: "Self-serve trial",
  paid_plan: "Paid plan",
  admin_approval: "Admin approval",
  partner_gated: "Partner gated",
  official: "Official MCP",
  third_party: "Third-party MCP",
};

const pillClass = {
  ready_now: "pill-ready",
  buildable_with_caveat: "pill-caveat",
  product_ops_required: "pill-ops",
  unknown: "pill-unknown",
};

const state = { apps: [] };
const search = document.querySelector("#search");
const categoryFilter = document.querySelector("#category-filter");
const buildabilityFilter = document.querySelector("#buildability-filter");
const accessFilter = document.querySelector("#access-filter");

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function display(value) {
  return labels[value] || String(value || "Unknown").replaceAll("_", " ");
}

function renderMatrix(apps) {
  const categories = [...new Set(apps.map((app) => app.category))].sort();
  document.querySelector("#category-matrix").innerHTML = categories.map((category) => {
    const rows = apps.filter((app) => app.category === category);
    const count = (status) => rows.filter((app) => app.buildability === status).length;
    const ready = count("ready_now");
    const caveat = count("buildable_with_caveat");
    const ops = count("product_ops_required");
    const unknown = count("unknown");
    return `<div class="matrix-row">
      <span class="matrix-label">${escapeHtml(category)}</span>
      <div class="matrix-bar" aria-label="${ready} ready, ${caveat} caveat, ${ops} Product Ops, ${unknown} unknown">
        <span class="ready" style="width:${ready * 10}%" title="${ready} ready now"></span>
        <span class="caveat" style="width:${caveat * 10}%" title="${caveat} with caveat"></span>
        <span class="ops" style="width:${ops * 10}%" title="${ops} Product Ops required"></span>
        <span class="unknown" style="width:${unknown * 10}%" title="${unknown} unknown"></span>
      </div>
      <span class="matrix-total">${ready} ready</span>
    </div>`;
  }).join("");
}

function renderTable() {
  const query = search.value.trim().toLowerCase();
  const filtered = state.apps.filter((app) => {
    const searchable = `${app.app} ${app.category} ${app.primary_blocker} ${app.description}`.toLowerCase();
    return (!query || searchable.includes(query))
      && (!categoryFilter.value || app.category === categoryFilter.value)
      && (!buildabilityFilter.value || app.buildability === buildabilityFilter.value)
      && (!accessFilter.value || app.access_status === accessFilter.value);
  });

  document.querySelector("#result-count").textContent = `Showing ${filtered.length} of ${state.apps.length} apps`;
  document.querySelector("#app-table").innerHTML = filtered.map((app) => {
    const evidence = app.evidence || [];
    const evidenceLinks = evidence.map((item, index) =>
      `<a href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${index + 1}. ${escapeHtml(item.title || "Official source")}</a>`
    ).join("");
    const mcp = app.mcp_status === "official" || app.mcp_status === "third_party"
      ? display(app.mcp_status)
      : "MCP unconfirmed";
    return `<tr>
      <td>${escapeHtml(app.app)}<span class="subtext">${escapeHtml(app.description)}</span></td>
      <td>${escapeHtml(app.category)}</td>
      <td>${escapeHtml(display(app.access_status))}<span class="subtext">${escapeHtml(app.auth_methods.join(", "))}</span></td>
      <td>${escapeHtml(app.api_types.join(", "))}<span class="subtext">${escapeHtml(mcp)}</span></td>
      <td><span class="pill ${pillClass[app.buildability] || "pill-unknown"}">${escapeHtml(display(app.buildability))}</span><span class="subtext">${escapeHtml(app.primary_blocker)}</span></td>
      <td>${evidence.length ? `<details class="evidence-list"><summary>${evidence.length} sources</summary><div>${evidenceLinks}</div></details><span class="subtext">${escapeHtml(app.confidence)} confidence</span>` : "Unknown"}</td>
    </tr>`;
  }).join("");
}

async function init() {
  try {
    const response = await fetch("data/apps.json");
    if (!response.ok) throw new Error("Dataset could not be loaded.");
    state.apps = await response.json();
    const categories = [...new Set(state.apps.map((app) => app.category))].sort();
    categoryFilter.insertAdjacentHTML("beforeend", categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join(""));
    renderMatrix(state.apps);
    renderTable();
    const requestedSection = new URLSearchParams(window.location.search).get("section");
    if (requestedSection === "explorer") document.body.classList.add("capture-explorer");
    const target = requestedSection
      ? document.querySelector(`#${CSS.escape(requestedSection)}`)
      : document.querySelector(window.location.hash);
    if (target) window.setTimeout(() => target.scrollIntoView(), 50);
  } catch (error) {
    document.querySelector("#result-count").textContent = "The dataset could not be loaded. Please open this page through a local server or the deployed site.";
  }
}

[search, categoryFilter, buildabilityFilter, accessFilter].forEach((control) => control.addEventListener("input", renderTable));
init();
