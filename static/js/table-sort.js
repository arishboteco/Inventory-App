// Initialize sortable tables using List.js
window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("table[data-sortable]").forEach((table) => {
    const container = table.parentElement; // div wrapping table
    const headers = table.querySelectorAll("thead th");
    const valueNames = [];
    headers.forEach((th, index) => {
      const key = `col${index}`;
      valueNames.push(key);
      const text = th.textContent.trim();
      th.innerHTML = `<button class="sort flex items-center" data-sort="${key}">${text}<span class="ml-1">⇅</span></button>`;
    });
    table.querySelectorAll("tbody tr").forEach((tr) => {
      tr.querySelectorAll("td").forEach((td, index) => {
        td.classList.add(`col${index}`);
      });
    });
    new List(container, { valueNames });
  });
});
