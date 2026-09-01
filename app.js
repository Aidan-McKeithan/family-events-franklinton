const ORIGIN = { lat: 36.101, lon: -78.458 };
const { dateKey, addDateKeyDays, weekendKeys, ageMatch, distanceMiles, parseSaved, validDateRange, applyQuickDate } = LittleDayOutLogic;
let state = { date: "today", startDate: "", endDate: "", age: 2.5, anyAge: false, includeUnknownAge: true, distance: 20, anyDistance: false, cost: "all", setting: "all", registration: "all", includeUnknownFacts: false, category: "all", savedOnly: false };
let events = [];
let saved = parseSaved(localStorage.getItem("little-day-out-saved"));
let controlsBound = false;

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const addDays = (date, days) => new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + days, 12));
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]);
const safeUrl = (value) => {
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : "#";
  } catch { return "#"; }
};

function ageMatches(event) {
  return ageMatch(event, state.anyAge ? null : state.age);
}

function dateMatches(event) {
  const key = dateKey(new Date(event.start));
  if (state.startDate || state.endDate) return (!state.startDate || key >= state.startDate) && (!state.endDate || key <= state.endDate);
  const today = new Date();
  const todayKey = dateKey(today);
  if (state.date === "today") return key === todayKey;
  if (state.date === "tomorrow") return key === addDateKeyDays(todayKey, 1);
  if (state.date === "weekend") return weekendKeys(today).includes(key);
  return key >= todayKey && key <= addDateKeyDays(todayKey, 30);
}

function factMatches(value, selected) {
  if (selected === "all") return true;
  return value === selected || (state.includeUnknownFacts && value === "unknown");
}

function filteredEvents() {
  return events.filter((event) => {
    event.distanceMiles = distanceMiles(ORIGIN, { lat: event.latitude, lon: event.longitude });
    return event.status !== "cancelled" && dateMatches(event) && (state.anyDistance || event.distanceMiles <= state.distance) &&
      factMatches(event.costStatus, state.cost) && factMatches(event.setting, state.setting) && factMatches(event.registrationRequired, state.registration) &&
      (state.category === "all" || event.category === state.category) &&
      (!state.savedOnly || saved.has(event.id));
  }).sort((a, b) => new Date(a.start) - new Date(b.start));
}

function formatAge(event) {
  if (event.ageMin == null && event.ageMax == null) return "Age unknown";
  if (event.ageMin == null) return `Up to age ${event.ageMax}`;
  if (event.ageMax == null) return `Age ${event.ageMin}+`;
  return `Ages ${event.ageMin}–${event.ageMax}`;
}

function card(event) {
  const date = new Date(event.start);
  const day = new Intl.DateTimeFormat("en-US", { day: "numeric", timeZone: "America/New_York" }).format(date);
  const month = new Intl.DateTimeFormat("en-US", { month: "short", timeZone: "America/New_York" }).format(date);
  const time = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }).format(date);
  const cost = event.costStatus === "free" ? "Free" : event.costStatus === "paid" ? event.costLabel || "Paid" : "Cost unknown";
  const registration = event.registrationRequired === "true" ? "Registration required" : event.registrationRequired === "false" ? "No registration" : "Registration unknown";
  const distanceLabel = `${event.coordinatePrecision === "venue" ? "" : "about "}${event.distanceMiles.toFixed(event.coordinatePrecision === "venue" ? 1 : 0)} mi`;
  const safeId = encodeURIComponent(event.id);
  return `<article class="event-card" data-category="${escapeHtml(event.category)}">
    <div class="card-top"><div class="date-tile"><strong>${day}</strong><span>${month}</span></div>
      <button class="save-card ${saved.has(event.id) ? "saved" : ""}" data-save="${safeId}" type="button" aria-label="${saved.has(event.id) ? "Remove from" : "Save to"} saved events" aria-pressed="${saved.has(event.id)}">${saved.has(event.id) ? "♥" : "♡"}</button></div>
    <div class="card-body"><span class="card-kicker">${escapeHtml(event.sourceName)}</span><h3>${escapeHtml(event.title)}</h3>
      <div class="details"><p>◷ ${time}${event.end ? ` – ${new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "America/New_York" }).format(new Date(event.end))}` : ""}</p>
      <p>⌖ ${escapeHtml(event.venue)}, ${escapeHtml(event.town)} · ${escapeHtml(distanceLabel)}</p></div>
      <div class="badges"><span class="badge ${event.costStatus === "free" ? "free" : ""}">${escapeHtml(cost)}</span><span class="badge">${escapeHtml(event.audienceLabel || formatAge(event))}</span><span class="badge">${escapeHtml(event.setting === "unknown" ? "Setting unknown" : event.setting)}</span><span class="badge">${escapeHtml(registration)}</span>${event.status === "postponed" ? '<span class="badge">Postponed</span>' : ""}</div>
      ${event.accessibility ? `<p class="card-note">Accessibility: ${escapeHtml(event.accessibility)}</p>` : ""}
      <small>Checked ${escapeHtml(new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(event.lastChecked)))}</small>
      ${event.registrationUrl ? `<a class="source-link" href="${escapeHtml(safeUrl(event.registrationUrl))}" target="_blank" rel="noopener noreferrer"><span>Registration</span><span aria-hidden="true">↗</span></a>` : ""}
      <a class="source-link" href="${escapeHtml(safeUrl(event.sourceUrl))}" target="_blank" rel="noopener noreferrer"><span>Check official details</span><span aria-hidden="true">↗</span></a>
      ${(event.additionalSources || []).map((source) => `<a class="source-link" href="${escapeHtml(safeUrl(source.sourceUrl))}" target="_blank" rel="noopener noreferrer"><span>Also listed by ${escapeHtml(source.sourceName)}</span><span aria-hidden="true">↗</span></a>`).join("")}
    </div></article>`;
}

function render() {
  const filtered = filteredEvents();
  const matches = filtered.filter((event) => ageMatches(event) === "match");
  const unknown = state.includeUnknownAge ? filtered.filter((event) => ageMatches(event) === "unknown") : [];
  $("#eventGrid").innerHTML = matches.map(card).join("");
  $("#unknownEventGrid").innerHTML = unknown.map(card).join("");
  $("#emptyState").hidden = matches.length > 0;
  $("#unknownAgeSection").hidden = unknown.length === 0;
  $("#resultSummary").textContent = `${matches.length} definite ${matches.length === 1 ? "match" : "matches"}${unknown.length ? ` · ${unknown.length} to verify` : ""}`;
  $("#savedCount").textContent = saved.size;
  $("#savedButton").setAttribute("aria-pressed", String(state.savedOnly));
  bindSaveButtons();
}

function bindSaveButtons() {
  $$('[data-save]').forEach((button) => button.addEventListener("click", () => {
    const id = decodeURIComponent(button.dataset.save);
    saved.has(id) ? saved.delete(id) : saved.add(id);
    localStorage.setItem("little-day-out-saved", JSON.stringify([...saved]));
    render();
  }));
}

function selectButton(group, button) {
  group.forEach((item) => item.classList.toggle("active", item === button));
  group.forEach((item) => item.setAttribute("aria-pressed", String(item === button)));
}

function setDateLabels() {
  const format = (date) => new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" }).format(date);
  const today = new Date();
  $("#todayLabel").textContent = format(today);
  $("#tomorrowLabel").textContent = format(addDays(today, 1));
  const [saturdayKey, sundayKey] = weekendKeys(today);
  $("#weekendLabel").textContent = `${format(new Date(`${saturdayKey}T12:00:00`))}–${format(new Date(`${sundayKey}T12:00:00`))}`;
}

function bindControls() {
  const dateButtons = $$('[data-date]');
  const chooseQuickDate = (date, button) => { state = applyQuickDate(state, date); $("#startDate").value = $("#endDate").value = ""; $("#customDateError").textContent = ""; selectButton(dateButtons, button); render(); };
  dateButtons.forEach((button) => button.addEventListener("click", () => chooseQuickDate(button.dataset.date, button)));
  const categoryButtons = $$('[data-category]');
  categoryButtons.forEach((button) => button.addEventListener("click", () => { state.category = button.dataset.category; selectButton(categoryButtons, button); render(); }));
  $("#ageRange").addEventListener("input", (event) => { state.age = Number(event.target.value); $("#ageOutput").textContent = state.age === 2.5 ? "2½ years" : `${state.age} ${state.age === 1 ? "year" : "years"}`; render(); });
  $("#anyAge").addEventListener("change", (event) => { state.anyAge = event.target.checked; $("#ageRange").disabled = state.anyAge; render(); });
  $("#includeUnknownAge").addEventListener("change", (event) => { state.includeUnknownAge = event.target.checked; render(); });
  $("#distanceRange").addEventListener("input", (event) => { state.distance = Number(event.target.value); $("#distanceOutput").textContent = `${state.distance} miles`; render(); });
  $("#anyDistance").addEventListener("change", (event) => { state.anyDistance = event.target.checked; $("#distanceRange").disabled = state.anyDistance; render(); });
  $("#costFilter").addEventListener("change", (event) => { state.cost = event.target.value; render(); });
  $("#settingFilter").addEventListener("change", (event) => { state.setting = event.target.value; render(); });
  $("#registrationFilter").addEventListener("change", (event) => { state.registration = event.target.value; render(); });
  $("#includeUnknownFacts").addEventListener("change", (event) => { state.includeUnknownFacts = event.target.checked; render(); });
  ["startDate", "endDate"].forEach((id) => $("#" + id).addEventListener("change", () => {
    state.startDate = $("#startDate").value; state.endDate = $("#endDate").value;
    const invalid = !validDateRange(state.startDate, state.endDate);
    $("#customDateError").textContent = invalid ? "The start date must be before the end date." : "";
    selectButton(dateButtons, null);
    if (!invalid) render();
  }));
  $("#clearDates").addEventListener("click", () => { state.startDate = state.endDate = ""; $("#startDate").value = $("#endDate").value = ""; $("#customDateError").textContent = ""; selectButton(dateButtons, dateButtons.find((button) => button.dataset.date === state.date)); render(); });
  $("#savedButton").addEventListener("click", () => { state.savedOnly = !state.savedOnly; render(); });
  $("#showUpcoming").addEventListener("click", () => chooseQuickDate("all", dateButtons.find((b) => b.dataset.date === "all")));
  $("#resetFilters").addEventListener("click", () => { window.location.reload(); });
  $("#retryLoad").addEventListener("click", init);
}

function validDataset(data) {
  return data && Array.isArray(data.events) && data.events.every((event) => typeof event.id === "string" && typeof event.title === "string" && Number.isFinite(event.latitude) && Number.isFinite(event.longitude) && typeof event.sourceUrl === "string");
}

async function init() {
  setDateLabels();
  if (!controlsBound) { bindControls(); controlsBound = true; }
  try {
    const apiBase = typeof window.EVENTS_API_BASE === "string" ? window.EVENTS_API_BASE.replace(/\/$/, "") : "";
    let response = apiBase ? await fetch(`${apiBase}/api/events`, { cache: "no-store" }) : null;
    let usingFallback = false;
    if (!response || !response.ok) {
      usingFallback = true;
      response = await fetch("public/data/events.json", { cache: "no-store" });
    }
    if (!response.ok) throw new Error("Could not load events");
    const data = await response.json();
    if (!validDataset(data)) throw new Error("Invalid event data");
    events = data.events;
    $("#errorState").hidden = true;
    $("#freshness").textContent = `${usingFallback ? "Using saved catalog · " : "Updated "}${new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(data.generatedAt))}`;
    const failures = Array.isArray(data.sourceFailures) ? data.sourceFailures : [];
    const sources = Array.isArray(data.sources) ? data.sources : [];
    $("#sourceFreshness").innerHTML = sources.map((source) => `<span>${escapeHtml(source.sourceName)}: ${escapeHtml(source.status)}${source.lastSuccessfulRefresh ? ` · ${escapeHtml(new Intl.DateTimeFormat("en-US", { dateStyle: "medium" }).format(new Date(source.lastSuccessfulRefresh)))}` : " · never refreshed"}</span>`).join("");
    $("#sourceWarning").hidden = failures.length === 0;
    $("#sourceWarning").textContent = failures.length ? `Some calendars could not refresh and may be stale: ${failures.map((failure) => failure.sourceName).join(", ")}.` : "";
    render();
  } catch (error) {
    $("#resultSummary").textContent = "Events are temporarily unavailable";
    $("#emptyState").hidden = true;
    $("#errorState").hidden = false;
  }
}

init();
