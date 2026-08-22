(() => {
  "use strict";

  const STORAGE_KEY = "liftlog:v1";
  const DATA_URL = "workout.json";

  const header = document.getElementById("header-title");
  const backBtn = document.getElementById("back-btn");
  const main = document.getElementById("app-main");
  const cycleSelect = document.getElementById("cycle-select");
  const exportBtn = document.getElementById("export-btn");

  const tplWeekItem = document.getElementById("tpl-week-list-item");
  const tplDayCard = document.getElementById("tpl-day-card");
  const tplExercise = document.getElementById("tpl-exercise");
  const tplSetRow = document.getElementById("tpl-set-row");

  /** @type {{title: string, weeks: Array}} */
  let workoutData = null;

  /** view = "weeks" | "days" | "exercises" */
  const nav = { view: "weeks", weekIdx: 0, dayIdx: 0 };

  let store = loadStore();

  function loadStore() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) return JSON.parse(raw);
    } catch (err) {
      console.warn("Failed to read saved logs, starting fresh.", err);
    }
    return { currentCycle: 1, logs: {} };
  }

  function saveStore() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }

  function getSetLog(cycle, weekIdx, dayIdx, exIdx, setIdx) {
    return store.logs?.[cycle]?.[weekIdx]?.[dayIdx]?.[exIdx]?.[setIdx] || null;
  }

  function setSetLog(cycle, weekIdx, dayIdx, exIdx, setIdx, partial) {
    store.logs[cycle] ??= {};
    store.logs[cycle][weekIdx] ??= {};
    store.logs[cycle][weekIdx][dayIdx] ??= {};
    store.logs[cycle][weekIdx][dayIdx][exIdx] ??= {};
    const existing = store.logs[cycle][weekIdx][dayIdx][exIdx][setIdx] || {};
    store.logs[cycle][weekIdx][dayIdx][exIdx][setIdx] = { ...existing, ...partial };
    saveStore();
  }

  function findPreviousWeight(weekIdx, dayIdx, exIdx, setIdx) {
    for (let c = store.currentCycle - 1; c >= 1; c--) {
      const log = getSetLog(c, weekIdx, dayIdx, exIdx, setIdx);
      if (log && log.weight) return log.weight;
    }
    return null;
  }

  function dayStats(cycle, weekIdx, dayIdx, day) {
    let total = 0;
    let done = 0;
    day.exercises.forEach((ex, exIdx) => {
      for (let s = 0; s < ex.sets; s++) {
        total++;
        if (getSetLog(cycle, weekIdx, dayIdx, exIdx, s)?.done) done++;
      }
    });
    return { total, done };
  }

  function weekStats(cycle, weekIdx, week) {
    let total = 0;
    let done = 0;
    week.days.forEach((day, dayIdx) => {
      const s = dayStats(cycle, weekIdx, dayIdx, day);
      total += s.total;
      done += s.done;
    });
    return { total, done };
  }

  function populateCycleSelect() {
    const maxKnown = Object.keys(store.logs)
      .map(Number)
      .reduce((m, c) => Math.max(m, c), 1);
    const optionCount = Math.max(store.currentCycle, maxKnown) + 1;
    cycleSelect.innerHTML = "";
    for (let c = 1; c <= optionCount; c++) {
      const opt = document.createElement("option");
      opt.value = String(c);
      opt.textContent = `#${c}`;
      cycleSelect.appendChild(opt);
    }
    cycleSelect.value = String(store.currentCycle);
  }

  cycleSelect.addEventListener("change", () => {
    store.currentCycle = Number(cycleSelect.value);
    saveStore();
    render();
  });

  async function exportLogs() {
    const payload = JSON.stringify(store, null, 2);
    const filename = `liftlog-export-${new Date().toISOString().slice(0, 10)}.json`;
    const file = new File([payload], filename, { type: "application/json" });

    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      try {
        await navigator.share({ files: [file], title: filename });
        return;
      } catch (err) {
        if (err && err.name === "AbortError") return;
        console.warn("Share failed, falling back to download.", err);
      }
    }

    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  exportBtn.addEventListener("click", exportLogs);

  backBtn.addEventListener("click", () => {
    if (nav.view === "exercises") {
      nav.view = "days";
    } else if (nav.view === "days") {
      nav.view = "weeks";
    }
    render();
  });

  function render() {
    populateCycleSelect();
    if (nav.view === "weeks") renderWeeks();
    else if (nav.view === "days") renderDays();
    else renderExercises();
  }

  function renderWeeks() {
    backBtn.hidden = true;
    header.textContent = workoutData.title;
    main.innerHTML = "";
    const list = document.createElement("ul");
    workoutData.weeks.forEach((week, weekIdx) => {
      const node = tplWeekItem.content.cloneNode(true);
      const btn = node.querySelector(".week-btn");
      node.querySelector(".week-name").textContent = `Week ${week.number}`;
      const stats = weekStats(store.currentCycle, weekIdx, week);
      node.querySelector(".week-progress").textContent = `${stats.done}/${stats.total}`;
      btn.addEventListener("click", () => {
        nav.view = "days";
        nav.weekIdx = weekIdx;
        render();
      });
      list.appendChild(node);
    });
    main.appendChild(list);
  }

  function renderDays() {
    backBtn.hidden = false;
    const week = workoutData.weeks[nav.weekIdx];
    header.textContent = `Week ${week.number}`;
    main.innerHTML = "";
    const list = document.createElement("ul");
    week.days.forEach((day, dayIdx) => {
      const node = tplDayCard.content.cloneNode(true);
      const btn = node.querySelector(".day-btn");
      node.querySelector(".day-name").textContent = day.name;
      const stats = dayStats(store.currentCycle, nav.weekIdx, dayIdx, day);
      node.querySelector(".day-progress").textContent = `${stats.done}/${stats.total}`;
      btn.addEventListener("click", () => {
        nav.view = "exercises";
        nav.dayIdx = dayIdx;
        render();
      });
      list.appendChild(node);
    });
    main.appendChild(list);
  }

  function renderExercises() {
    backBtn.hidden = false;
    const week = workoutData.weeks[nav.weekIdx];
    const day = week.days[nav.dayIdx];
    header.textContent = day.name;
    main.innerHTML = "";
    const list = document.createElement("ul");

    day.exercises.forEach((ex, exIdx) => {
      const node = tplExercise.content.cloneNode(true);
      node.querySelector(".exercise-name").textContent = ex.name;
      node.querySelector(".exercise-target").textContent = ex.target;
      const rowsContainer = node.querySelector(".set-rows");

      for (let setIdx = 0; setIdx < ex.sets; setIdx++) {
        const rowNode = tplSetRow.content.cloneNode(true);
        const row = rowNode.querySelector(".set-row");
        rowNode.querySelector(".set-index").textContent = String(setIdx + 1);
        const weightInput = rowNode.querySelector(".set-weight");
        const repsInput = rowNode.querySelector(".set-reps");
        const doneBtn = rowNode.querySelector(".set-done");

        const log = getSetLog(store.currentCycle, nav.weekIdx, nav.dayIdx, exIdx, setIdx);
        if (log?.weight != null) weightInput.value = log.weight;
        if (log?.reps != null) repsInput.value = log.reps;
        if (log?.done) row.classList.add("is-done");

        const prevWeight = findPreviousWeight(nav.weekIdx, nav.dayIdx, exIdx, setIdx);
        if (prevWeight != null) weightInput.placeholder = `last ${prevWeight}`;

        weightInput.addEventListener("input", () => {
          setSetLog(store.currentCycle, nav.weekIdx, nav.dayIdx, exIdx, setIdx, {
            weight: weightInput.value === "" ? null : Number(weightInput.value),
          });
        });
        repsInput.addEventListener("input", () => {
          setSetLog(store.currentCycle, nav.weekIdx, nav.dayIdx, exIdx, setIdx, {
            reps: repsInput.value === "" ? null : Number(repsInput.value),
          });
        });
        doneBtn.addEventListener("click", () => {
          const nowDone = !row.classList.contains("is-done");
          row.classList.toggle("is-done", nowDone);
          setSetLog(store.currentCycle, nav.weekIdx, nav.dayIdx, exIdx, setIdx, { done: nowDone });
        });

        rowsContainer.appendChild(rowNode);
      }

      list.appendChild(node);
    });

    main.appendChild(list);
  }

  async function boot() {
    try {
      const res = await fetch(DATA_URL, { cache: "no-cache" });
      workoutData = await res.json();
      localStorage.setItem("liftlog:data-cache", JSON.stringify(workoutData));
    } catch (err) {
      const cached = localStorage.getItem("liftlog:data-cache");
      if (cached) {
        workoutData = JSON.parse(cached);
      } else {
        main.innerHTML = '<p class="empty-state">Could not load workout data. Connect once to download it, then it works offline.</p>';
        return;
      }
    }
    render();
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("sw.js").catch((err) => {
        console.warn("Service worker registration failed:", err);
      });
    });
  }

  boot();
})();
