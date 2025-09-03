// Initialize sortable tables using List.js
window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("table[data-sortable]").forEach((table) => {
    const container = table.parentElement; // div wrapping table
    const headers = table.querySelectorAll("thead th");
    const valueNames = [];
    headers.forEach((th, index) => {
      const btn = th.querySelector("[data-sort]");
      if (btn) {
        valueNames.push(btn.getAttribute("data-sort"));
      }
    });
    table.querySelectorAll("tbody tr").forEach((tr) => {
      tr.querySelectorAll("td").forEach((td, index) => {
        td.classList.add(`col${index}`);
      });
    });
    new List(container, { valueNames });
  });
});
