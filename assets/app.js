const STORE_KEY = "ai-map-progress-v2";
const completed = new Set(JSON.parse(localStorage.getItem(STORE_KEY) || "[]"));
const page = document.body.dataset.page;
let curriculum;

const $ = (selector, scope = document) => scope.querySelector(selector);
const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
const params = new URLSearchParams(location.search);

async function load() {
  const response = await fetch("curriculum/concepts.json");
  if (!response.ok) throw new Error(`Curriculum request failed: ${response.status}`);
  curriculum = await response.json();
  setupMobileNav();
  if (page === "home") renderHome();
  if (page === "roadmap") renderRoadmapPage();
  if (page === "concept") renderConceptPage();
  if (page === "lesson") renderLessonPage();
  if (page === "lab") renderLabPage();
}

function setupMobileNav() {
  const trigger = $("#menu-button");
  if (!trigger) return;
  trigger.addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    trigger.setAttribute("aria-expanded", String(open));
  });
}

function concept(id) { return curriculum.concepts.find((item) => item.id === id); }
function track(id) { return curriculum.tracks.find((item) => item.id === id); }
function trackConcepts(id) { return curriculum.concepts.filter((item) => item.track === id).sort((a, b) => a.order - b.order); }
function nextConcept(item) { return trackConcepts(item.track).find((candidate) => candidate.order > item.order); }
function conceptRefs(item) {
  const ids = [...track(item.track).refs, ...(item.refs || [])];
  return [...new Set(ids)].map((id) => curriculum.references[id]).filter(Boolean);
}
function donePercent() { return Math.round((completed.size / curriculum.concepts.length) * 100); }
function saveProgress() { localStorage.setItem(STORE_KEY, JSON.stringify([...completed])); }
function toggleDone(id) { completed.has(id) ? completed.delete(id) : completed.add(id); saveProgress(); }
function isUnlocked(item) { return item.prerequisites.every((id) => completed.has(id)); }
function queryLink(path, id) { return `${path}?id=${encodeURIComponent(id)}`; }

function exerciseProfile(item) {
  const verb = item.exercise.split(" ")[0].toLowerCase().replace(/[^a-z-]/g, "");
  const inspectVerbs = new Set(["audit", "benchmark", "classify", "compare", "evaluate", "measure", "review", "run", "visualize"]);
  const modifyVerbs = new Set(["add", "configure", "reduce", "rewrite", "secure"]);
  const mode = inspectVerbs.has(verb) ? "inspect" : modifyVerbs.has(verb) ? "modify" : "build";
  const filenames = {
    safety: "security-review.md", evals: "evaluation.yaml", dataops: "pipeline.py",
    applied: "experiment.py", ml: "experiment.py", multimodal: "media-evaluation.json",
    agents: "agent-harness.py", rag: "retrieval-harness.py", context: "context-contract.md",
    models: "model-harness.py", production: "production-plan.yaml", foundations: "implementation.py",
  };
  const filename = filenames[item.track] || "artifact.md";
  const checks = [
    `Produces: ${item.exercise.replace(/\.$/, "")}`,
    ...item.outcomes.map((value) => `Evidence shows: ${value}`),
    "Records inputs, versions, and provenance",
    "Includes one failure case and one trade-off",
  ];
  let starter;
  if (filename.endsWith(".md")) {
    starter = `# ${item.title}\n\n## Goal\n${item.exercise}\n\n## Inputs and versions\n- TODO\n\n## Evidence\n- ${item.outcomes.join("\n- ")}\n\n## Failure case\nTODO\n\n## Trade-off\nTODO`;
  } else if (filename.endsWith(".yaml")) {
    starter = `task: ${item.id}\nobjective: ${JSON.stringify(item.exercise)}\ninputs: []\nversions: {}\nchecks:\n${item.outcomes.map((value) => `  - ${JSON.stringify(value)}`).join("\n")}\nfailure_case: TODO\ntrade_off: TODO`;
  } else if (filename.endsWith(".json")) {
    starter = JSON.stringify({task:item.id, objective:item.exercise, inputs:[], versions:{}, evidence:item.outcomes, failure_case:"TODO", trade_off:"TODO"}, null, 2);
  } else {
    starter = `"""Hands-on exercise: ${item.title}."""\n\nTASK = ${JSON.stringify(item.exercise)}\nOUTCOMES = ${JSON.stringify(item.outcomes, null, 4)}\n\ndef build_artifact(fixtures, policy):\n    """TODO: implement, measure, and preserve provenance."""\n    raise NotImplementedError\n\ndef verify(artifact):\n    assert artifact.get("provenance")\n    assert artifact.get("failure_case")\n    return True\n`;
  }
  return {mode, label: mode.toUpperCase(), filename, checks, starter};
}

function renderHome() {
  const totalMinutes = curriculum.concepts.reduce((sum, item) => sum + item.minutes, 0);
  $("#concept-count").textContent = curriculum.concepts.length;
  $("#track-count").textContent = curriculum.tracks.length;
  $("#hour-count").textContent = `${Math.round(totalMinutes / 60)}h`;
  $("#review-date").textContent = curriculum.reviewedAt;
  $("#track-preview").innerHTML = curriculum.tracks.map((item, index) => `
    <a class="preview-row" href="roadmap.html?track=${item.id}">
      <span class="preview-index">${String(index + 1).padStart(2, "0")}</span>
      <span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.phase)}</small></span>
      <span class="preview-count">${trackConcepts(item.id).length} topics →</span>
    </a>`).join("");
}

function renderRoadmapPage() {
  const state = { track: params.get("track") || "all", query: "", selected: params.get("id") || "model-apis", hideDone: false };
  if (!curriculum.tracks.some((item) => item.id === state.track)) state.track = "all";
  const graph = $("#dependency-graph");
  const filterBox = $("#track-filters");
  filterBox.innerHTML = [{id:"all", title:"All tracks"}, ...curriculum.tracks].map((item) =>
    `<button class="chip" data-track="${item.id}" aria-pressed="${state.track === item.id}">${escapeHtml(item.title)}</button>`).join("");

  function filtered() {
    const needle = state.query.toLowerCase().trim();
    return curriculum.concepts.filter((item) =>
      (state.track === "all" || item.track === state.track) &&
      (!state.hideDone || !completed.has(item.id)) &&
      (!needle || [item.title, item.summary, ...item.outcomes, track(item.track).title].join(" ").toLowerCase().includes(needle)));
  }

  function draw(focusTarget) {
    $$("[data-track]", filterBox).forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.track === state.track)));
    const visible = filtered();
    state.selected = visible.find((item) => item.id === state.selected)?.id || visible[0]?.id || null;
    const visibleTracks = curriculum.tracks.filter((item) => visible.some((entry) => entry.track === item.id));
    $("#roadmap-grid").innerHTML = visibleTracks.length ? visibleTracks.map((lane, laneIndex) => `
      <section class="lane" style="--track:${lane.color}">
        <header><span>${String(laneIndex + 1).padStart(2,"0")} · ${escapeHtml(lane.phase)}</span><h2>${escapeHtml(lane.title)}</h2></header>
        ${visible.filter((item) => item.track === lane.id).map((item) => `
          <button class="topic-card ${completed.has(item.id) ? "is-done" : ""} ${!isUnlocked(item) ? "is-locked" : ""} ${state.selected === item.id ? "is-selected" : ""}" data-topic="${item.id}" aria-pressed="${state.selected === item.id}">
            <span class="topic-status">${completed.has(item.id) ? "✓ complete" : isUnlocked(item) ? item.level : "prerequisite open"}</span>
            <b>${escapeHtml(item.title)}</b><small>${item.minutes} min</small>
          </button>`).join("")}
      </section>`).join("") : `<div class="empty">No topics match this view.</div>`;
    renderInspector(state.selected);
    renderDependencies();
    $("#roadmap-status").textContent = `${visible.length} topics shown.${state.selected ? ` Selected: ${concept(state.selected).title}.` : " No topics match. Clear filters to continue."}`;
    $("#map-progress").textContent = `${completed.size}/${curriculum.concepts.length}`;
    $("#progress-fill").style.width = `${donePercent()}%`;
    if (focusTarget) {
      const target = $(focusTarget) || $("[data-topic].is-selected") || $("#search");
      target.focus({preventScroll:true});
      target.scrollIntoView({block:"nearest", inline:"nearest", behavior:"instant"});
    }
  }

  function renderDependencies() {
    const item = concept(state.selected);
    if (!item) { graph.innerHTML = ""; return; }
    const groups = [item.prerequisites.map(concept), [item], curriculum.concepts.filter((entry) => entry.prerequisites.includes(item.id))];
    const labels = ["Prerequisites", "Selected topic", "Next topics"];
    graph.innerHTML = `<svg class="dependency-edges" aria-hidden="true" focusable="false"><defs><marker id="dependency-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs><g></g></svg>` + groups.map((items, index) => `
      <section class="dependency-column" aria-label="${labels[index]}"><h3>${labels[index]}</h3>${items.length ? items.map((entry) => `<button class="dependency-node ${index === 1 ? "is-current" : ""}" data-dependency="${entry.id}" data-column="${index}" tabindex="${index === 1 ? 0 : -1}" aria-label="${escapeHtml(`${entry.title}. ${index === 0 ? `Prerequisite of ${item.title}` : index === 2 ? `Requires ${item.title}` : "Selected topic"}${completed.has(entry.id) ? ". Complete" : ""}`)}"><span>${escapeHtml(entry.title)}</span><small>${escapeHtml(track(entry.track).title)}${completed.has(entry.id) ? " · Complete" : ""}</small></button>`).join("") : `<p>${index === 0 ? "No prerequisites. Start here." : "No dependent topics yet."}</p>`}</section>`).join("");
    drawEdges();
  }

  function drawEdges() {
    const selected = $('[data-column="1"]', graph);
    if (!selected) return;
    const bounds = graph.getBoundingClientRect();
    const svg = $("svg", graph);
    svg.setAttribute("viewBox", `0 0 ${bounds.width} ${bounds.height}`);
    const point = (node, end) => {
      const rect = node.getBoundingClientRect();
      return {x:(end ? rect.right : rect.left) - bounds.left, y:rect.top + rect.height / 2 - bounds.top};
    };
    $("g", svg).innerHTML = $$('[data-dependency]:not([data-column="1"])', graph).map((node) => {
      const incoming = node.dataset.column === "0";
      const from = point(incoming ? node : selected, true);
      const to = point(incoming ? selected : node, false);
      const mid = (from.x + to.x) / 2;
      return `<path d="M ${from.x} ${from.y} C ${mid} ${from.y}, ${mid} ${to.y}, ${to.x} ${to.y}" marker-end="url(#dependency-arrow)"/>`;
    }).join("");
  }

  new ResizeObserver(drawEdges).observe(graph);
  graph.addEventListener("focusin", (event) => {
    if (!event.target.matches("[data-dependency]")) return;
    $$("[data-dependency]", graph).forEach((node) => { node.tabIndex = node === event.target ? 0 : -1; });
  });
  graph.addEventListener("keydown", (event) => {
    const node = event.target.closest("[data-dependency]");
    if (!node || event.altKey || event.ctrlKey || event.metaKey) return;
    const nodes = $$("[data-dependency]", graph);
    const column = nodes.filter((entry) => entry.dataset.column === node.dataset.column);
    let target;
    if (event.key === "Home") target = nodes[0];
    else if (event.key === "End") target = nodes.at(-1);
    else if (event.key === "ArrowUp") target = column[Math.max(0, column.indexOf(node) - 1)];
    else if (event.key === "ArrowDown") target = column[Math.min(column.length - 1, column.indexOf(node) + 1)];
    else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      const next = Number(node.dataset.column) + (event.key === "ArrowLeft" ? -1 : 1);
      const candidates = nodes.filter((entry) => Number(entry.dataset.column) === next);
      target = candidates[Math.min(column.indexOf(node), candidates.length - 1)] || node;
    } else return;
    event.preventDefault();
    target.focus({preventScroll:true});
    target.scrollIntoView({block:"nearest", inline:"nearest", behavior:"instant"});
  });
  graph.addEventListener("click", (event) => {
    const node = event.target.closest("[data-dependency]");
    if (!node) return;
    const hidden = !filtered().some((item) => item.id === node.dataset.dependency);
    if (hidden) {
      state.track = "all"; state.query = ""; state.hideDone = false;
      $("#search").value = ""; $("#hide-complete").checked = false;
    }
    state.selected = node.dataset.dependency;
    draw('[data-column="1"]');
    if (hidden) $("#roadmap-status").textContent += " Filters cleared to show the related topic.";
  });

  function renderInspector(id) {
    const item = concept(id);
    if (!item) { $("#concept-inspector").innerHTML = '<p>No topic selected.</p>'; return; }
    const prereqs = item.prerequisites.map(concept).filter(Boolean);
    $("#concept-inspector").innerHTML = `
      <div class="inspector-top"><span class="overline">${escapeHtml(track(item.track).title)}</span><span>${item.minutes} min</span></div>
      <h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p>
      <h3>Learning outcomes</h3><ul class="check-list">${item.outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join("")}</ul>
      <h3>Prerequisites</h3><div class="mini-links">${prereqs.length ? prereqs.map((entry) => `<a href="${queryLink("concept.html",entry.id)}">${escapeHtml(entry.title)}</a>`).join("") : "<span>Start here</span>"}</div>
      <div class="inspector-actions"><a class="button primary" href="${queryLink("concept.html",item.id)}">Open concept</a><button class="button ghost" id="toggle-complete">${completed.has(item.id) ? "Mark incomplete" : "Mark complete"}</button></div>
      <p class="reviewed">Technical review · ${curriculum.reviewedAt}</p>`;
    $("#toggle-complete").addEventListener("click", () => { toggleDone(item.id); draw("#toggle-complete"); });
  }

  filterBox.addEventListener("click", (event) => { const button = event.target.closest("[data-track]"); if (button) { state.track = button.dataset.track; draw(); } });
  $("#search").addEventListener("input", (event) => { state.query = event.target.value; draw(); });
  $("#hide-complete").addEventListener("change", (event) => { state.hideDone = event.target.checked; draw(); });
  $("#roadmap-grid").addEventListener("click", (event) => { const card = event.target.closest("[data-topic]"); if (card) { state.selected = card.dataset.topic; draw("[data-topic].is-selected"); } });
  draw();
}

function renderConceptPage() {
  const item = concept(params.get("id")) || concept("embeddings");
  const lane = track(item.track);
  const items = trackConcepts(item.track);
  const next = nextConcept(item);
  document.title = `${item.title} · AI Engineer Map`;
  $("#concept-track-nav").innerHTML = curriculum.tracks.map((entry) => `<a class="${entry.id === item.track ? "active" : ""}" href="roadmap.html?track=${entry.id}"><i style="--dot:${entry.color}"></i>${escapeHtml(entry.title)}</a>`).join("");
  $("#concept-content").innerHTML = `
    <div class="concept-breadcrumb"><a href="roadmap.html?track=${item.track}">${escapeHtml(lane.title)}</a><span>Concept ${item.order} of ${items.length}</span></div>
    <p class="overline">${escapeHtml(lane.phase)} · ${item.level}</p><h1>${escapeHtml(item.title)}</h1><p class="lede">${escapeHtml(item.summary)}</p>
    <div class="mechanism-visual" style="--track:${lane.color}"><span>INPUT</span><i></i><strong>${escapeHtml(item.title)}</strong><i></i><span>EVIDENCE</span></div>
    <section><h2>What you will learn</h2><div class="outcome-grid">${item.outcomes.map((value, index) => `<article><span>0${index + 1}</span><p>${escapeHtml(value)}</p></article>`).join("")}</div></section>
    <section><h2>Proof of understanding</h2><div class="exercise-callout"><span>${exerciseProfile(item).label}</span><p>${escapeHtml(item.exercise)}</p><a href="${queryLink("lab.html",item.id)}">Open guided lab →</a></div></section>
    <section><h2>Primary references</h2><ul class="reference-list">${conceptRefs(item).map((ref) => `<li><a href="${ref.url}" target="_blank" rel="noreferrer">${escapeHtml(ref.title)} ↗</a></li>`).join("")}</ul></section>`;
  $("#concept-rail").innerHTML = `
    <span class="overline">Track progress</span><strong>${items.filter((entry) => completed.has(entry.id)).length} / ${items.length}</strong><div class="progress"><i style="width:${items.filter((entry) => completed.has(entry.id)).length / items.length * 100}%"></i></div>
    <h3>Prerequisites</h3>${item.prerequisites.length ? item.prerequisites.map((id) => `<a class="rail-link" href="${queryLink("concept.html",id)}">${escapeHtml(concept(id).title)} <span>→</span></a>`).join("") : `<p class="muted">No prerequisites.</p>`}
    <h3>Continue</h3>${next ? `<a class="rail-link" href="${queryLink("concept.html",next.id)}">${escapeHtml(next.title)} <span>→</span></a>` : `<a class="rail-link" href="roadmap.html">Review the full map <span>→</span></a>`}
    <a class="button primary wide" href="${queryLink("lesson.html",item.id)}">Start lesson</a><button class="button ghost wide" id="concept-complete">${completed.has(item.id) ? "Completed ✓" : "Mark complete"}</button>
    <p class="reviewed">Reviewed ${curriculum.reviewedAt}</p>`;
  $("#concept-complete").addEventListener("click", () => { toggleDone(item.id); renderConceptPage(); });
}

function renderLessonPage() {
  const item = concept(params.get("id")) || concept("embeddings");
  const lane = track(item.track);
  const refs = conceptRefs(item);
  const next = nextConcept(item);
  document.title = `${item.title} lesson · AI Engineer Map`;
  $("#lesson-track-list").innerHTML = trackConcepts(item.track).map((entry) => `<a class="${entry.id === item.id ? "active" : ""}" href="${queryLink("lesson.html",entry.id)}"><span>${String(entry.order).padStart(2,"0")}</span>${escapeHtml(entry.title)}${completed.has(entry.id) ? " ✓" : ""}</a>`).join("");
  const mechanism = `${item.title} is best understood as an engineering boundary: inputs are transformed under explicit constraints, useful evidence is preserved, and failure remains observable. The durable skill is not memorizing one framework—it is knowing what the component guarantees, what it cannot guarantee, and how to measure it.`;
  $("#lesson-article").innerHTML = `
    <p class="overline">${escapeHtml(lane.title)} · ${item.minutes} minutes</p><h1>${escapeHtml(item.title)}</h1><p class="lede">${escapeHtml(item.summary)}</p>
    <div class="lesson-meta"><span>${item.level}</span><span>Reviewed ${curriculum.reviewedAt}</span><span>${refs.length} primary sources</span></div>
    <section id="mental-model"><h2>1. Mental model</h2><p>${escapeHtml(mechanism)}</p><blockquote>Production rule: make the contract explicit, retain provenance, and test the failure path before optimizing the happy path.</blockquote></section>
    <section id="mechanism"><h2>2. Mechanism</h2><p>Start with a small deterministic baseline. Record the input, configuration, intermediate state, output, latency, and cost. Replace one piece at a time and compare against a representative evaluation set.</p><pre><code>result = component.run(input, policy=versioned_policy)
assert result.provenance
assert result.status in {"ok", "insufficient_evidence", "blocked"}
trace.record(result.metrics)</code></pre></section>
    <section id="production"><h2>3. Production pattern</h2><div class="production-grid"><article><b>Contract</b><p>Version inputs, outputs, policy, and artifacts.</p></article><article><b>Evidence</b><p>Capture traces and task-specific quality measures.</p></article><article><b>Control</b><p>Bound cost, latency, data access, and external effects.</p></article></div></section>
    <section id="failures"><h2>4. Failure modes</h2><ul><li>Testing only examples that shaped the implementation.</li><li>Hiding partial failure behind retries or fluent model output.</li><li>Coupling product behavior to one provider-specific payload.</li><li>Logging sensitive inputs without an explicit data policy.</li></ul></section>
    <section id="exercise"><h2>5. Guided exercise</h2><div class="exercise-callout"><span>${exerciseProfile(item).label}</span><p>${escapeHtml(item.exercise)}</p><a href="${queryLink("lab.html",item.id)}">Open lab workspace →</a></div></section>
    <section id="check"><h2>6. Knowledge check</h2><details><summary>What evidence would prove this component works?</summary><p>A representative dataset, a task-specific metric or deterministic assertion, traceable inputs and versions, and a documented failure case.</p></details><details><summary>What belongs outside the model?</summary><p>Authorization, secrets, irreversible effects, schema validation, budgets, and other deterministic policy enforcement.</p></details></section>
    <section id="references"><h2>7. Primary references</h2><ul class="reference-list">${refs.map((ref) => `<li><a href="${ref.url}" target="_blank" rel="noreferrer">${escapeHtml(ref.title)} ↗</a></li>`).join("")}</ul></section>
    ${next ? `<a class="next-lesson" href="${queryLink("lesson.html",next.id)}"><span>Next concept</span><b>${escapeHtml(next.title)} →</b></a>` : ""}`;
  $("#lesson-toc").innerHTML = ["mental-model","mechanism","production","failures","exercise","check","references"].map((id, index) => `<a href="#${id}">0${index + 1} ${id.replace("-", " ")}</a>`).join("") + `<button class="button primary wide" id="lesson-complete">${completed.has(item.id) ? "Completed ✓" : "Complete lesson"}</button>`;
  $("#lesson-complete").addEventListener("click", () => { toggleDone(item.id); renderLessonPage(); });
}

// Display argv as a POSIX command without interpreting curriculum strings as shell code.
function shellCommand(argv) {
  return argv.map((part) => /^[a-zA-Z0-9_@%+=:,./-]+$/.test(part) ? part : `'${part.replace(/'/g, `'"'"'`)}'`).join(" ");
}

async function renderLabExecution(item) {
  const panel = $("#lab-execution");
  const restoreFocus = panel.contains(document.activeElement);
  panel.setAttribute("aria-busy", "true");
  try {
    const response = await fetch("curriculum/hoe.json");
    if (!response.ok) throw new Error("Execution catalog unavailable");
    const catalog = await response.json();
    const profileId = catalog.topics?.[item.id];
    const execution = catalog.profiles?.[profileId];
    const strings = (value) => Array.isArray(value) && value.every((entry) => typeof entry === "string");
    const command = (value) => value === null || (strings(value) && value.length > 0 && value.every((part) => part.length > 0));
    if (catalog.schemaVersion !== 1 || !execution ||
        !["guided", "automated", "setup-ready"].includes(execution.status) ||
        !["browser", "local", "byo-api", "gpu"].includes(execution.mode) ||
        !["requirements", "artifacts", "cleanup"].every((key) => strings(execution[key])) ||
        !["setup", "run", "verify"].every((key) => command(execution[key])) ||
        !Number.isInteger(execution.estimatedMinutes) || execution.estimatedMinutes <= 0 ||
        typeof execution.estimatedCost !== "string" || !execution.estimatedCost ||
        (execution.status === "automated" && (!execution.run || !execution.verify || execution.mode !== "local"))) {
      throw new Error("Execution contract unavailable");
    }
    const explanations = {
      guided: "Guided exercise. Complete the artifact and collect evidence manually; no automated runner is declared.",
      automated: "Automated commands are available for your terminal. Your environment and results have not been checked by this page.",
      "setup-ready": "Setup instructions are available. The topic experiment is not automated; environment checks do not prove the learning outcomes.",
    };
    const list = (items, empty) => items.length ? `<ul>${items.map((text) => `<li>${escapeHtml(text)}</li>`).join("")}</ul>` : `<p>${empty}</p>`;
    const renderCommand = (title, argv, empty) => `<div class="execution-command"><h3>${title}</h3>${argv ? `<pre><code>${escapeHtml(shellCommand(argv))}</code></pre>` : `<p>${empty}</p>`}</div>`;
    const external = ["byo-api", "gpu"].includes(execution.mode);
    const prereqs = item.prerequisites.map(concept);
    panel.innerHTML = `
      <header><div><p class="overline">Execution guide</p><h2>${escapeHtml(item.title)}</h2></div><span class="execution-badge" data-execution-status="${execution.status}">${escapeHtml(execution.status)}</span></header>
      <p>${explanations[execution.status]}</p>
      <a class="execution-jump" href="#code-editor">Go to artifact editor ↓</a>
      <dl class="execution-meta"><div><dt>Mode</dt><dd>${escapeHtml(execution.mode)}</dd></div><div><dt>Estimated time</dt><dd>${execution.estimatedMinutes} minutes</dd></div><div><dt>Estimated cost</dt><dd>${escapeHtml(execution.estimatedCost)}</dd></div><div><dt>Provider / GPU</dt><dd>${escapeHtml(execution.provider || "none")} / ${escapeHtml(execution.gpuBackend || "none")}</dd></div></dl>
      <div class="execution-columns"><section><h3>Prerequisite concepts</h3>${prereqs.length ? `<ul>${prereqs.map((entry) => `<li><a href="${queryLink("concept.html", entry.id)}">${escapeHtml(entry.title)}</a></li>`).join("")}</ul>` : "<p>No prerequisite concepts.</p>"}<h3>Environment requirements</h3>${list(execution.requirements, "No additional requirements listed.")}</section>
      <section><h3>Expected artifacts</h3>${list(execution.artifacts, "Record evidence for the learning outcomes.")}<h3>Cleanup</h3>${list(execution.cleanup, "No cleanup steps declared for this profile.")}</section></div>
      ${external ? `<div class="execution-notice"><h3>Before using paid services</h3><p>Set a spend limit and keep credentials in your local environment or ignored .env file. Never paste secrets into this page. Review the cleanup steps before starting.</p>${execution.mode === "gpu" ? "<p>Choose an available GPU, region, and workload in your terminal before provisioning. Run the environment check on your GPU host; paused instances can retain billable storage.</p>" : ""}<p>The HOE CLI requires <code>--allow-billable</code> for API/GPU run or verify commands. This acknowledgement does not provision resources.</p><a href="docs/BYO_LLM_AND_GPU.md">Read API and GPU setup guidance →</a></div>` : ""}
      <p class="execution-location">Commands below are POSIX terminal instructions from the repository root${execution.mode === "gpu" ? " (verification runs on the GPU host)" : ""}. This page does not execute them.</p>
      <div class="execution-commands">${renderCommand("Setup / readiness check", execution.setup, "No setup command declared; check the requirements above.")}${renderCommand("Run exercise", execution.run, execution.status === "guided" ? "Use the artifact editor below and complete the exercise manually." : "No topic run command declared. Follow the setup guidance and perform the topic experiment manually.")}${renderCommand(execution.status === "setup-ready" ? "Environment verification only" : "Verify results", execution.verify, "No automated verification declared. Review real evidence against every learning outcome.")}</div>
      <p class="execution-source">Profile: ${escapeHtml(profileId)} · <a href="curriculum/hoe.json">Execution catalog</a> · Inspect locally: <code>${escapeHtml(shellCommand(["./run.sh", "hoe", "inspect", item.id]))}</code></p>`;
  } catch {
    panel.innerHTML = `<h2>Execution instructions unavailable</h2><p role="status">The catalog could not be loaded or this topic has an invalid profile. Readiness is unknown. You can still draft your artifact below.</p><button class="button ghost" id="retry-execution">Retry loading instructions</button>`;
    $("#retry-execution").addEventListener("click", () => renderLabExecution(item));
  } finally {
    panel.setAttribute("aria-busy", "false");
    if (restoreFocus) { panel.tabIndex = -1; panel.focus({preventScroll:true}); }
  }
}

function renderLabPage() {
  const item = concept(params.get("id")) || concept("vector-indexes");
  const profile = exerciseProfile(item);
  document.title = `${item.title} lab · AI Engineer Map`;
  $("#lab-title").textContent = item.title;
  $("#editor-filename").textContent = profile.filename;
  renderLabExecution(item);
  $("#lab-task").innerHTML = `<span class="overline">${profile.label} exercise</span><h1>${escapeHtml(item.exercise)}</h1><p>Every topic uses the same evidence contract, adapted to its artifact: complete the work, satisfy both learning outcomes, preserve provenance, and document a failure and trade-off.</p><ol><li>Read the objective and acceptance checks.</li><li>Complete the topic-specific starter artifact.</li><li>Validate each item with observable evidence.</li><li>Record a failure mode and production trade-off.</li></ol>`;
  $("#code-editor").value = profile.starter;
  $("#test-list").innerHTML = profile.checks.map((test) => `<li><i></i>${escapeHtml(test)}</li>`).join("");
  $("#run-tests").addEventListener("click", () => {
    $("#terminal").textContent = `Manual review checklist for ${profile.filename}\n\n${profile.checks.map((check) => `□ ${check}`).join("\n")}\n\nNo code was executed or verified. Save your artifact and attach real output, measurements, or screenshots. Record completion in the roadmap after verifying your evidence.`;
  });
}

load().catch((error) => {
  console.error(error);
  const main = $("main") || document.body;
  main.innerHTML = `<div class="fatal"><h1>Curriculum unavailable</h1><p>Serve the repository through a local HTTP server, then reload.</p></div>`;
});
