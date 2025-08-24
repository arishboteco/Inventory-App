document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  const collapsedClasses = ["-translate-x-full", "md:-translate-x-full"];

  function setCollapsed(state) {
    collapsedClasses.forEach(cls =>
      sidebar.classList[state ? "add" : "remove"](cls)
    );
    localStorage.setItem("sidebar-collapsed", state.toString());
  }

  if (sidebar) {
    const stored = localStorage.getItem("sidebar-collapsed");
    const startCollapsed =
      stored === null ? window.innerWidth < 768 : stored === "true";
    setCollapsed(startCollapsed);
  }

  if (toggle && sidebar) {
    toggle.addEventListener("click", function () {
      const isCollapsed = sidebar.classList.contains("-translate-x-full");
      setCollapsed(!isCollapsed);
    });
  }
});
