document.addEventListener("DOMContentLoaded", () => {
  const ctx = document.getElementById("stock-trend-chart").getContext("2d");
  const placeholder = document.getElementById("stock-trend-placeholder");
  const primaryColor = getComputedStyle(document.documentElement)
    .getPropertyValue("--color-primary")
    .trim();
  let chart;

  async function fetchData() {
    const form = document.getElementById("dashboard-filters");
    const params = new URLSearchParams(new FormData(form));
    const response = await fetch(`/dashboard/data/?${params.toString()}`);
    const data = await response.json();

    if (!data.values.length) {
      if (chart) {
        chart.destroy();
        chart = null;
      }
      placeholder.classList.remove("hidden");
      return;
    }

    placeholder.classList.add("hidden");
    const metric =
      params.get("metric") === "value" ? "Stock Value" : "Stock Quantity";
    const dataset = {
      labels: data.labels,
      datasets: [
        {
          label: metric,
          data: data.values,
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
        options: {
          responsive: true,
          maintainAspectRatio: false,
        },
      });
    } else {
      chart.data = dataset;
      chart.update();
    }
  }

  document.getElementById("apply-filters").addEventListener("click", fetchData);
  fetchData();
});
