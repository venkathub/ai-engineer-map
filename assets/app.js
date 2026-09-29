const state = {
  concepts: [],
  tracks: [],
  activeTrack: "all",
  search: "",
  hideComplete: false,
  selectedId: null,
  completed: new Set(JSON.parse(localStorage.getItem("ai-map-progress") || "[]")),
};

const elements = {
  grid: document.querySelector("#roadmap-grid"),
  panel: document.querySelector("#concept-panel"),
  filters: document.querySelector("#track-filters"),
  search: document.querySelector("#search"),
  hideComplete: document.querySelector("#hide-complete"),
};

async function loadCurriculum() {
  try {
    const response = await fetch("curriculum/concepts.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    state.concepts = data.concepts;
    state.tracks = data.tracks;
    renderStats();
    renderFilters();
    renderRoadmap();
  } catch (error) {
    elements.grid.innerHTML = `<div class="empty-state">Could not load the curriculum. Run this site through a local HTTP server.</div>`;
    console.error(error);
  }
}

function renderStats() {
  document.querySelector("#concept-count").textContent = state.concepts.length;
  document.querySelector("#published-count").textContent = state.concepts.filter((item) => item.status === "published").length;
  document.querySelector("#minute-count").textContent = state.concepts.reduce((sum, item) => sum + item.minutes, 0);
}

function renderFilters() {
  const filters = [{ id: "all", title: "All" }, ...state.tracks];
  elements.filters.innerHTML = filters.map((track) => `
    <button class="filter-button" data-track="${track.id}" aria-pressed="${track.id === state.activeTrack}">
      ${track.title}
    </button>`).join("");
}

function filteredConcepts() {
  const query = state.search.trim().toLowerCase();
  return state.concepts.filter((concept) => {
    const trackMatches = state.activeTrack === "all" || concept.track === state.activeTrack;
    const completionMatches = !state.hideComplete || !state.completed.has(concept.id);
    const haystack = [concept.title, concept.summary, concept.track, ...concept.outcomes].join(" ").toLowerCase();
    return trackMatches && completionMatches && (!query || haystack.includes(query));
  });
}

function renderRoadmap() {
  const concepts = filteredConcepts();
  if (!concepts.length) {
    elements.grid.innerHTML = `<div class="empty-state">No concepts match this view.</div>`;
    return;
  }

  const visibleTracks = state.tracks.filter((track) => concepts.some((concept) => concept.track === track.id));
  elements.grid.innerHTML = visibleTracks.map((track, trackIndex) => {
    const cards = concepts
      .filter((concept) => concept.track === track.id)
      .sort((a, b) => a.order - b.order)
      .map(renderCard)
      .join("");
    return `<section class="track-column" aria-labelledby="track-${track.id}">
      <div class="track-header">
        <span class="track-number">${String(trackIndex + 1).padStart(2, "0")} · ${track.phase}</span>
        <h3 id="track-${track.id}">${track.title}</h3>
      </div>
      ${cards}
    </section>`;
  }).join("");
}

function renderCard(concept) {
  const complete = state.completed.has(concept.id);
  const prerequisitesDone = concept.prerequisites.every((id) => state.completed.has(id));
  const dimmed = concept.prerequisites.length && !prerequisitesDone && !complete;
  return `<button class="concept-card ${complete ? "complete" : ""} ${dimmed ? "dimmed" : ""} ${state.selectedId === concept.id ? "selected" : ""}"
      data-concept="${concept.id}" aria-label="Open ${concept.title}">
    <div class="concept-meta"><span><i class="status-dot ${concept.status}"></i> ${concept.status}</span><span>${concept.level}</span></div>
    <h4>${concept.title}</h4>
    <p>${concept.summary}</p>
    <div class="concept-footer">
      <span>${concept.minutes} min</span>
      <span class="complete-button" data-complete="${concept.id}">${complete ? "Completed ✓" : "Mark complete"}</span>
    </div>
  </button>`;
}

function showConcept(id) {
  const concept = state.concepts.find((item) => item.id === id);
  if (!concept) return;
  state.selectedId = id;
  const names = Object.fromEntries(state.concepts.map((item) => [item.id, item.title]));
  elements.panel.innerHTML = `
    <p class="panel-kicker">${trackTitle(concept.track)}</p>
    <h3>${concept.title}</h3>
    <div class="panel-meta"><span>${concept.level}</span><span>${concept.minutes} minutes</span><span>${concept.status}</span></div>
    <p>${concept.summary}</p>
    <div class="panel-section"><h4>You will be able to</h4><ul>${concept.outcomes.map((item) => `<li>${item}</li>`).join("")}</ul></div>
    <div class="panel-section"><h4>Prerequisites</h4><ul>${concept.prerequisites.length ? concept.prerequisites.map((item) => `<li>${names[item]}</li>`).join("") : "<li>None</li>"}</ul></div>
    <div class="panel-section"><h4>Next concepts</h4><ul>${concept.next.length ? concept.next.map((item) => `<li>${names[item]}</li>`).join("") : "<li>Complete the track project</li>"}</ul></div>
    <div class="panel-links">
      ${concept.lesson ? `<a class="panel-link" href="${concept.lesson}">Open lesson</a>` : ""}
      ${concept.exercise ? `<a class="panel-link secondary" href="${concept.exercise}">Open exercise</a>` : ""}
    </div>`;
  renderRoadmap();
}

function trackTitle(id) {
  return state.tracks.find((track) => track.id === id)?.title || id;
}

function toggleComplete(id) {
  if (state.completed.has(id)) state.completed.delete(id);
  else state.completed.add(id);
  localStorage.setItem("ai-map-progress", JSON.stringify([...state.completed]));
  renderRoadmap();
}

elements.filters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-track]");
  if (!button) return;
  state.activeTrack = button.dataset.track;
  renderFilters();
  renderRoadmap();
});

elements.search.addEventListener("input", (event) => {
  state.search = event.target.value;
  renderRoadmap();
});

elements.hideComplete.addEventListener("change", (event) => {
  state.hideComplete = event.target.checked;
  renderRoadmap();
});

elements.grid.addEventListener("click", (event) => {
  const completion = event.target.closest("[data-complete]");
  if (completion) {
    event.stopPropagation();
    toggleComplete(completion.dataset.complete);
    return;
  }
  const card = event.target.closest("[data-concept]");
  if (card) showConcept(card.dataset.concept);
});

loadCurriculum();
