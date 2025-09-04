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

  document.getElementById("apply-filters").addEventListener("click", fetchData);
  renderChart(
    window.initialTrendLabels || [],
    window.initialTrendValues || [],
    "Stock Quantity"
  );
});
