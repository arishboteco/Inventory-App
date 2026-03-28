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
      placeholder.classList.remove("hidden");
      return;
    }
    placeholder.classList.add("hidden");

    const dataset = {
      labels,
      datasets: [
        {
          label: "Consumption",
          data: consumption,
          borderColor: primaryColor,
          backgroundColor: primaryColor + "18",
          pointRadius: 0,
          tension: 0.35,
          fill: true,
        },
        {
          label: "Wastage",
          data: wastage,
          borderColor: dangerColor,
          backgroundColor: dangerColor + "18",
          pointRadius: 0,
          tension: 0.35,
          fill: true,
        },
      ],
    };

    if (!chart) {
      chart = new Chart(ctx, {
        type: "line",
        data: dataset,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
        },
      });
    } else {
      chart.data = dataset;
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
