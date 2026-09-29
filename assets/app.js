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

  function draw() {
    $$("[data-track]", filterBox).forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.track === state.track)));
    const visible = filtered();
    const visibleTracks = curriculum.tracks.filter((item) => visible.some((entry) => entry.track === item.id));
    $("#roadmap-grid").innerHTML = visibleTracks.length ? visibleTracks.map((lane, laneIndex) => `
      <section class="lane" style="--track:${lane.color}">
        <header><span>${String(laneIndex + 1).padStart(2,"0")} · ${escapeHtml(lane.phase)}</span><h2>${escapeHtml(lane.title)}</h2></header>
        ${visible.filter((item) => item.track === lane.id).map((item) => `
          <button class="topic-card ${completed.has(item.id) ? "is-done" : ""} ${!isUnlocked(item) ? "is-locked" : ""} ${state.selected === item.id ? "is-selected" : ""}" data-topic="${item.id}">
            <span class="topic-status">${completed.has(item.id) ? "✓ complete" : isUnlocked(item) ? item.level : "prerequisite open"}</span>
            <b>${escapeHtml(item.title)}</b><small>${item.minutes} min</small>
          </button>`).join("")}
      </section>`).join("") : `<div class="empty">No topics match this view.</div>`;
    renderInspector(state.selected);
    $("#map-progress").textContent = `${completed.size}/${curriculum.concepts.length}`;
    $("#progress-fill").style.width = `${donePercent()}%`;
  }

  function renderInspector(id) {
    const matches = filtered();
    const item = matches.find((entry) => entry.id === id) || matches[0] || concept(id);
    if (!item) return;
    state.selected = item.id;
    const prereqs = item.prerequisites.map(concept).filter(Boolean);
    $("#concept-inspector").innerHTML = `
      <div class="inspector-top"><span class="overline">${escapeHtml(track(item.track).title)}</span><span>${item.minutes} min</span></div>
      <h2>${escapeHtml(item.title)}</h2><p>${escapeHtml(item.summary)}</p>
      <h3>Learning outcomes</h3><ul class="check-list">${item.outcomes.map((outcome) => `<li>${escapeHtml(outcome)}</li>`).join("")}</ul>
      <h3>Prerequisites</h3><div class="mini-links">${prereqs.length ? prereqs.map((entry) => `<a href="${queryLink("concept.html",entry.id)}">${escapeHtml(entry.title)}</a>`).join("") : "<span>Start here</span>"}</div>
      <div class="inspector-actions"><a class="button primary" href="${queryLink("concept.html",item.id)}">Open concept</a><button class="button ghost" id="toggle-complete">${completed.has(item.id) ? "Mark incomplete" : "Mark complete"}</button></div>
      <p class="reviewed">Technical review · ${curriculum.reviewedAt}</p>`;
    $("#toggle-complete").addEventListener("click", () => { toggleDone(item.id); draw(); });
  }

  filterBox.addEventListener("click", (event) => { const button = event.target.closest("[data-track]"); if (button) { state.track = button.dataset.track; draw(); } });
  $("#search").addEventListener("input", (event) => { state.query = event.target.value; draw(); });
  $("#hide-complete").addEventListener("change", (event) => { state.hideDone = event.target.checked; draw(); });
  $("#roadmap-grid").addEventListener("click", (event) => { const card = event.target.closest("[data-topic]"); if (card) { state.selected = card.dataset.topic; draw(); } });
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

function renderLabPage() {
  const item = concept(params.get("id")) || concept("vector-indexes");
  const profile = exerciseProfile(item);
  document.title = `${item.title} lab · AI Engineer Map`;
  $("#lab-title").textContent = item.title;
  $("#editor-filename").textContent = profile.filename;
  $("#run-tests").textContent = profile.mode === "build" ? "Run checks ↗" : "Validate artifact ↗";
  $("#lab-task").innerHTML = `<span class="overline">${profile.label} exercise</span><h1>${escapeHtml(item.exercise)}</h1><p>Every topic uses the same evidence contract, adapted to its artifact: complete the work, satisfy both learning outcomes, preserve provenance, and document a failure and trade-off.</p><ol><li>Read the objective and acceptance checks.</li><li>Complete the topic-specific starter artifact.</li><li>Validate each item with observable evidence.</li><li>Record a failure mode and production trade-off.</li></ol>`;
  $("#code-editor").value = profile.starter;
  $("#test-list").innerHTML = profile.checks.map((test) => `<li><i></i>${escapeHtml(test)}</li>`).join("");
  $("#run-tests").addEventListener("click", () => {
    const button = $("#run-tests"); button.disabled = true; button.textContent = "Validating…";
    $("#terminal").textContent = `$ validate ${profile.filename}\n\nCollecting ${profile.checks.length} acceptance checks for ${item.id}…`;
    setTimeout(() => {
      $$("#test-list li").forEach((row, index) => setTimeout(() => row.classList.add("pass"), index * 100));
      $("#terminal").textContent = `$ validate ${profile.filename}\n${".".repeat(profile.checks.length)}\n----------------------------------------------------------------------\n${profile.checks.length} acceptance checks recorded\n\nREADY FOR REVIEW\n\nAttach real output, measurements, or screenshots before claiming completion.`;
      button.disabled = false; button.textContent = profile.mode === "build" ? "Run checks ↗" : "Validate artifact ↗";
      completed.add(item.id); saveProgress();
    }, 500);
  });
}

load().catch((error) => {
  console.error(error);
  const main = $("main") || document.body;
  main.innerHTML = `<div class="fatal"><h1>Curriculum unavailable</h1><p>Serve the repository through a local HTTP server, then reload.</p></div>`;
});
