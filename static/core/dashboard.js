document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("stock-trend-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const placeholder = document.getElementById("stock-trend-placeholder");

  const primaryColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--color-primary")
    .trim();
  const dangerColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--danger-text")
    .trim() || "#dc2626";

  let chart;

  function renderChart(labels, consumption, wastage) {
    const hasData = consumption.some((v) => v > 0) || wastage.some((v) => v > 0);
    if (!hasData) {
      if (chart) { chart.destroy(); chart = null; }
      canvas.parentElement.classList.add("hidden");
      placeholder.classList.remove("hidden");
      return;
    }
    placeholder.classList.add("hidden");
    canvas.parentElement.classList.remove("hidden");

    const shortLabels = labels.map((l) => {
      const d = new Date(l + "T00:00:00");
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    });

    const dataset = {
      labels: shortLabels,
      datasets: [
        {
          label: "Consumption",
          data: consumption,
          borderColor: primaryColor,
          backgroundColor: primaryColor + "18",
          borderWidth: 2,
          pointRadius: 0,
          pointHitRadius: 8,
          tension: 0.35,
          fill: true,
        },
        {
          label: "Wastage",
          data: wastage,
          borderColor: dangerColor,
          backgroundColor: dangerColor + "18",
          borderWidth: 2,
          pointRadius: 0,
          pointHitRadius: 8,
          tension: 0.35,
          fill: true,
        },
      ],
    };

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(17,24,39,0.9)",
          titleFont: { size: 13 },
          bodyFont: { size: 12 },
          padding: 10,
          cornerRadius: 6,
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { size: 11 },
            color: "#6b7280",
            maxRotation: 45,
            autoSkipPadding: 12,
          },
          border: { display: false },
        },
        y: {
          beginAtZero: true,
          grid: { color: "rgba(0,0,0,0.04)" },
          ticks: {
            font: { size: 11 },
            color: "#6b7280",
            padding: 8,
          },
          border: { display: false },
        },
      },
      layout: { padding: { top: 4, right: 8, bottom: 0, left: 0 } },
    };

    if (!chart) {
      chart = new Chart(ctx, {
        type: "line",
        data: dataset,
        options: chartOptions,
      });
    } else {
      chart.data = dataset;
      chart.options = chartOptions;
      chart.update();
    }
  }

  async function fetchData() {
    const range = document.getElementById("filter-range").value || "30";
    const response = await fetch(`/dashboard-data/?range=${range}`);
    const data = await response.json();
    renderChart(data.labels, data.consumption, data.wastage);
  }

  const rangeInput = document.getElementById("filter-range");
  document.querySelectorAll(".range-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      rangeInput.value = btn.dataset.range;
      document.querySelectorAll(".range-btn").forEach((b) => {
        b.classList.remove("bg-primary", "text-white");
        b.classList.add("bg-surface", "text-bodyText");
        b.removeAttribute("aria-pressed");
      });
      btn.classList.add("bg-primary", "text-white");
      btn.classList.remove("bg-surface", "text-bodyText");
      btn.setAttribute("aria-pressed", "true");
      fetchData();
    });
  });

  renderChart(
    window.initialTrendLabels || [],
    window.initialConsumption || [],
    window.initialWastage || [],
  );
});
