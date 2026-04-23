// ── Theme ──────────────────────────────────────────────────
let darkMode = true;

function applyTheme(dark) {
  darkMode = dark;
  const root = document.getElementById("html-root");
  const btn = document.getElementById("theme-btn");
  root.setAttribute("data-theme", dark ? "dark" : "light");
  btn.textContent = dark ? "🌙" : "☀️";

  if (window._chart) {
    const gColor = dark ? "rgba(255,255,255,0.05)" : "rgba(37,99,235,0.06)";
    const tColor = dark ? "#6b7280" : "#94a3b8";
    window._chart.options.scales.y.grid.color = gColor;
    window._chart.options.scales.x.grid.color = gColor;
    window._chart.options.scales.y.ticks.color = tColor;
    window._chart.options.scales.x.ticks.color = tColor;
    window._chart.data.datasets[0].borderColor = dark ? "#D4AF37" : "#3b82f6";
    window._chart.data.datasets[0].backgroundColor = dark
      ? "rgba(212,175,55,0.07)"
      : "rgba(59,130,246,0.07)";
    window._chart.update("none");
  }
  localStorage.setItem("ls_dark", dark ? "1" : "0");
}

function toggleTheme() {
  applyTheme(!darkMode);
}

// ── Chart ─────────────────────────────────────────────────
function initChart() {
  const ctx = document.getElementById("crowd-chart").getContext("2d");
  window._chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "People Inside",
          data: [],
          borderColor: "#D4AF37",
          backgroundColor: "rgba(212,175,55,0.07)",
          fill: true,
          tension: 0.45,
          borderWidth: 2,
          pointRadius: 0,
          pointHoverRadius: 4,
          pointHoverBackgroundColor: "#D4AF37",
        },
      ],
    },
    options: {
      responsive: true,
      animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1e1e1e",
          titleColor: "#D4AF37",
          bodyColor: "#f0f0f0",
          borderColor: "rgba(212,175,55,0.3)",
          borderWidth: 1,
          padding: 10,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          min: 0,
          grid: { color: "rgba(255,255,255,0.05)", drawBorder: false },
          ticks: {
            color: "#6b7280",
            font: { family: "DM Mono", size: 11 },
            maxTicksLimit: 6,
          },
        },
        x: {
          grid: { color: "rgba(255,255,255,0.03)", drawBorder: false },
          ticks: {
            color: "#6b7280",
            font: { family: "DM Mono", size: 11 },
            maxTicksLimit: 20,
            maxRotation: 0,
          },
        },
      },
    },
  });
}

// ── Color mapping ──────────────────────────────────────────
const COLOR_MAP = {
  green: "var(--state-green)",
  yellow: "var(--state-yellow)",
  red: "var(--state-red)",
};
function stateColor(level_color) {
  return COLOR_MAP[level_color] || "var(--state-green)";
}

// ── Previous count for animation ──────────────────────────
let prevCount = null;

// ── Update dashboard ───────────────────────────────────────
function updateDashboard() {
  fetch("/data")
    .then((r) => r.json())
    .then((d) => {
      const col = stateColor(d.level_color);
      const maxCap = d.max_cap || 50;
      const occ = Math.min((d.current / maxCap) * 100, 100).toFixed(1);

      // Big number (animate on change)
      const countEl = document.getElementById("current-count");
      if (prevCount !== d.current) {
        countEl.classList.remove("big-num-animate");
        void countEl.offsetWidth;
        countEl.classList.add("big-num-animate");
        prevCount = d.current;
      }
      countEl.textContent = d.current;
      countEl.style.color = col;
      document.getElementById("ghost-count").textContent = d.current;

      // Progress bar
      document.getElementById("prog-bar").style.width = occ + "%";
      document.getElementById("prog-bar").style.background = col;
      document.getElementById("occ-pct").textContent = occ + "% capacity";
      document.getElementById("max-cap-label").textContent = "Max: " + maxCap;

      // Status card
      const sc = document.getElementById("status-card");
      const level = document.getElementById("crowd-level");
      level.textContent = d.crowd_level;
      level.style.color = col;
      sc.style.borderLeftColor = col;

      document.getElementById("suggestion").textContent = d.suggestion;

      // Wait time
      const wt = d.wait_time || 0;
      document.getElementById("wait-time").textContent =
        wt > 0 ? wt + " min" : "< 1 min";
      document.getElementById("wait-method").textContent =
        d.exit_rate && d.exit_rate > 0
          ? "based on service rate"
          : "occupancy estimate";

      // Stat cards
      document.getElementById("total-entry").textContent = d.entry;
      document.getElementById("total-exit").textContent = d.exit;
      document.getElementById("predicted").textContent =
        d.predicted_15 >= 0 ? d.predicted_15 : "–";
      document.getElementById("rush-time").textContent = d.rush_time || "–";

      // Rate chips
      document.getElementById("entry-rate").textContent = (
        d.entry_rate || 0
      ).toFixed(1);
      document.getElementById("exit-rate").textContent = (
        d.exit_rate || 0
      ).toFixed(1);
      document.getElementById("net-rate").textContent = (
        d.net_rate || 0
      ).toFixed(1);

      // Prediction text – richer now
      const pred = d.predicted_15 >= 0 ? d.predicted_15 : "?";
      const net = d.net_rate || 0;
      const trend =
        net > 0.5
          ? "📈 Crowd is growing."
          : net < -0.5
            ? "📉 Crowd is shrinking."
            : "➡ Crowd is stable.";
      const rushLine =
        d.rush_time && d.rush_time !== "--:--"
          ? `Rush expected around ${d.rush_time}.`
          : "No significant rush predicted in the near term.";
      document.getElementById("prediction-text").textContent =
        `${trend} Expected occupancy in ~15 min: ${pred} people (net flow: ${(net >= 0 ? "+" : "") + net}/min). ${rushLine}`;

      // Best window
      document.getElementById("best-window").textContent = d.best_window;

      // Footer
      document.getElementById("last-action").textContent = d.action;
      document.getElementById("last-ts").textContent = d.timestamp;
    })
    .catch(() => {});

  // Graph update
  fetch("/history")
    .then((r) => r.json())
    .then((h) => {
      const c = window._chart;
      if (!c) return;

      document.getElementById("history-count").textContent = h.length;

      if (h.length === 0) return; // keep existing graph

      // Show up to last 60 data points for a longer x-axis view
      const slice = h.slice(-60);
      c.data.labels = slice.map((x) => x.time);
      c.data.datasets[0].data = slice.map((x) => x.current);

      const maxCap = parseInt(
        (document.getElementById("max-cap-label").textContent.match(/\d+/) || [
          "50",
        ])[0],
      );
      const dataMax = Math.max(...c.data.datasets[0].data, 1);
      c.options.scales.y.max = Math.ceil(
        Math.max(dataMax * 1.2, maxCap * 1.1, 10),
      );
      c.update("none");
    })
    .catch(() => {});
}

// ── Boot ───────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const saved = localStorage.getItem("ls_dark");
  applyTheme(saved === null ? true : saved === "1");

  initChart();
  updateDashboard();
  setInterval(updateDashboard, 1000);
});
