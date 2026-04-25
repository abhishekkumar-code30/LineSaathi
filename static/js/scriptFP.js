let darkMode = true;
function applyTheme(dark) {
  darkMode = dark;
  const html = document.getElementById("html-root");
  const btn = document.getElementById("theme-btn");
  if (dark) {
    html.classList.remove("light-mode");
    btn.textContent = "🌙 Dark";
  } else {
    html.classList.add("light-mode");
    btn.textContent = "☀️ Light";
  }
  localStorage.setItem("ls_dark", dark ? "1" : "0");
  if (window._crowdChart) window._crowdChart.update("none");
}

function toggleTheme() {
  applyTheme(!darkMode);
}

function initChart() {
  const ctx = document.getElementById("crowd-chart").getContext("2d");
  window._crowdChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "People Inside",
          data: [],
          borderColor: "#d4af77",
          backgroundColor: "rgba(212,175,119,0.1)",
          fill: true,
          tension: 0.4,
          borderWidth: 3,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 300 },
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "rgba(212,175,119,0.1)" },
          ticks: { color: "#a8a8a8" },
        },
        x: {
          grid: { color: "rgba(212,175,119,0.1)" },
          ticks: { color: "#a8a8a8", maxTicksLimit: 24 },
        },
      },
    },
  });
}

function setColor(level_color) {
  const map = {
    silver: "var(--status-low)",
    medium: "var(--status-medium)",
    high: "var(--status-high)",
  };
  return map[level_color] || "var(--status-low)";
}

function updateDashboard() {
  fetch("/data")
    .then((r) => r.json())
    .then((d) => {
      const col = setColor(d.level_color);
      const maxCap = d.max_cap || 50;
      const occ = Math.min((d.current / maxCap) * 100, 100).toFixed(1);

      document.getElementById("current-count").textContent = d.current;
      document.getElementById("current-count").style.color = col;
      document.getElementById("ghost-count").textContent = d.current;

      document.getElementById("prog-bar").style.width = occ + "%";
      document.getElementById("prog-bar").style.background = col;
      document.getElementById("occ-pct").textContent = occ + "% used";
      document.getElementById("max-cap-label").textContent =
        "Capacity: " + maxCap;

      const card = document.getElementById("status-card");
      const levelEl = document.getElementById("crowd-level");
      levelEl.textContent = d.crowd_level;
      levelEl.style.color = col;
      card.style.borderLeftColor = col;

      document.getElementById("suggestion").textContent = d.suggestion;
      document.getElementById("wait-time").textContent = d.wait_time + " min";

      document.getElementById("total-entry").textContent = d.entry;
      document.getElementById("total-exit").textContent = d.exit;
      document.getElementById("predicted").textContent =
        d.predicted_15 >= 0 ? d.predicted_15 : "–";
      document.getElementById("rush-time").textContent = d.rush_time || "–";

      // Prediction text (fixed grammar + dynamic)
      const peopleWord = d.predicted_15 === 1 ? "person" : "people";
      document.getElementById("prediction-text").innerHTML =
        `Expected <strong>${d.predicted_15}</strong> ${peopleWord} in ~15 minutes.<br>Rush expected around <strong>${d.rush_time}</strong>.`;

      document.getElementById("best-window").textContent = d.best_window;

      document.getElementById("last-action").textContent = d.action;
      document.getElementById("last-ts").textContent = d.timestamp;
    })
    .catch(() => {});

  // Graph
  fetch("/history")
    .then((r) => r.json())
    .then((h) => {
      const c = window._crowdChart;
      if (!c || h.length === 0) return;
      c.data.labels = h.map((x) => x.time);
      c.data.datasets[0].data = h.map((x) => x.current);
      c.options.scales.y.max = Math.max(
        30,
        Math.ceil(
          (document
            .getElementById("max-cap-label")
            .textContent.match(/\d+/)?.[0] || 50) * 1.2,
        ),
      );
      c.update("none");
    })
    .catch(() => {});
}

window.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("ls_dark");
  applyTheme(saved === null ? true : saved === "1");
  initChart();
  updateDashboard();
  setInterval(updateDashboard, 1000);
});
