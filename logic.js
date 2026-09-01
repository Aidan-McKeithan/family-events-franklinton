(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.LittleDayOutLogic = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const EASTERN = "America/New_York";
  const dateKey = (date) => {
    const parts = new Intl.DateTimeFormat("en-US", { timeZone: EASTERN, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}`;
  };
  const addDateKeyDays = (key, days) => {
    const [year, month, day] = key.split("-").map(Number);
    const date = new Date(Date.UTC(year, month - 1, day + days, 12));
    return date.toISOString().slice(0, 10);
  };
  const weekday = (date) => Number(new Intl.DateTimeFormat("en-US", { timeZone: EASTERN, weekday: "short" }).formatToParts(date).find((part) => part.type === "weekday") ? ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(new Intl.DateTimeFormat("en-US", { timeZone: EASTERN, weekday: "short" }).format(date)) : 0);
  const weekendKeys = (now) => {
    const today = dateKey(now);
    const day = weekday(now);
    if (day === 0) return [addDateKeyDays(today, -1), today];
    const saturday = addDateKeyDays(today, 6 - day);
    return [saturday, addDateKeyDays(saturday, 1)];
  };
  const ageMatch = (event, age) => {
    if (age == null) return "match";
    if (event.ageMin == null && event.ageMax == null) {
      if (event.audienceGroup === "early-childhood") return age <= 5 ? "match" : "no";
      if (event.audienceGroup === "school-age") return age >= 5 ? "match" : "no";
      if (event.audienceGroup === "teen") return age >= 13 ? "match" : "no";
      return "unknown";
    }
    return age >= (event.ageMin ?? -Infinity) && age <= (event.ageMax ?? Infinity) ? "match" : "no";
  };
  const distanceMiles = (a, b) => {
    const rad = (n) => n * Math.PI / 180;
    const dLat = rad(b.lat - a.lat), dLon = rad(b.lon - a.lon);
    const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
    return 3958.8 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  };
  const parseSaved = (raw) => {
    try { const value = JSON.parse(raw || "[]"); return new Set(Array.isArray(value) ? value.filter((item) => typeof item === "string") : []); }
    catch { return new Set(); }
  };
  const validDateRange = (start, end) => !start || !end || start <= end;
  const applyQuickDate = (state, date) => ({ ...state, date, startDate: "", endDate: "" });
  return { dateKey, addDateKeyDays, weekendKeys, ageMatch, distanceMiles, parseSaved, validDateRange, applyQuickDate };
});
