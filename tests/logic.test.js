const test = require("node:test");
const assert = require("node:assert/strict");
const { ageMatch, dateKey, addDateKeyDays, weekendKeys, distanceMiles, parseSaved, validDateRange, applyQuickDate } = require("../logic.js");

test("age matching uses inclusive and open bounds", () => {
  assert.equal(ageMatch({ ageMin: 0, ageMax: 2.5 }, 2.5), "match");
  assert.equal(ageMatch({ ageMin: null, ageMax: 5 }, 2.5), "match");
  assert.equal(ageMatch({ ageMin: 3, ageMax: null }, 2.5), "no");
  assert.equal(ageMatch({ ageMin: null, ageMax: null }, 2.5), "unknown");
});
test("Sunday belongs to the current weekend", () => {
  const sunday = new Date("2026-09-06T16:00:00Z");
  assert.deepEqual(weekendKeys(sunday), ["2026-09-05", "2026-09-06"]);
});

test("calendar arithmetic crosses DST by date, not elapsed hours", () => {
  assert.equal(addDateKeyDays("2026-10-31", 2), "2026-11-02");
  assert.equal(dateKey(new Date("2026-11-01T04:30:00Z")), "2026-11-01");
});

test("distance calculation has stable boundaries", () => {
  const miles = distanceMiles({ lat: 36.101, lon: -78.458 }, { lat: 36.0243, lon: -78.4744 });
  assert.ok(miles > 5 && miles < 7);
});

test("corrupt saved data safely becomes empty", () => {
  assert.equal(parseSaved("not-json").size, 0);
  assert.equal(parseSaved('{"bad":true}').size, 0);
  assert.deepEqual([...parseSaved('["a", 2]')], ["a"]);
});

test("custom date ranges reject reversed boundaries", () => {
  assert.equal(validDateRange("2026-09-01", "2026-09-30"), true);
  assert.equal(validDateRange("2026-09-30", "2026-09-01"), false);
  assert.equal(validDateRange("", "2026-09-01"), true);
});

test("quick date selection clears a custom range", () => {
  const next = applyQuickDate({ date: "today", startDate: "2026-09-10", endDate: "2026-09-12", age: 2.5 }, "weekend");
  assert.equal(next.date, "weekend");
  assert.equal(next.startDate, "");
  assert.equal(next.endDate, "");
  assert.equal(next.age, 2.5);
});
