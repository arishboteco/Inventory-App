document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("stock-trend-chart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const placeholder = document.getElementById("stock-trend-placeholder");
  const primaryColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--color-primary")
    .trim();
  let chart;

  function renderChart(labels, values, metric) {
    if (!values.length) {
      if (chart) {
        chart.destroy();
        chart = null;
      }
      placeholder.classList.remove("hidden");
      return;
    }

    placeholder.classList.add("hidden");
    const dataset = {
      labels,
      datasets: [
        {
          label: metric,
          data: values,
          borderColor: primaryColor,
          fill: false,
          tension: 0.1,
        },
      ],
    };

    if (!chart) {
      chart = new Chart(ctx, {
        type: "line",
        data: dataset,
        options: { responsive: true, maintainAspectRatio: false },
      });
    } else {
      chart.data = dataset;
      chart.update();
    }
  }

  async function fetchData() {
    const form = document.getElementById("dashboard-filters");
    const params = new URLSearchParams(new FormData(form));
    const response = await fetch(`/dashboard-data/?${params.toString()}`);
    const data = await response.json();
    const metric =
      params.get("metric") === "value" ? "Stock Value" : "Stock Quantity";
    renderChart(data.labels, data.values, metric);
  }

  // Auto-fetch on any select change
  document.querySelectorAll("#dashboard-filters select").forEach((sel) => {
    sel.addEventListener("change", fetchData);
  });

  // Range pill buttons
  const rangeInput = document.getElementById("range-value");
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
    window.initialTrendValues || [],
    "Stock Quantity",
  );
});
