document.addEventListener('DOMContentLoaded', function () {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const collapsedClass = '-translate-x-full';

  if (sidebar && localStorage.getItem('sidebar-collapsed') === 'true') {
    sidebar.classList.add(collapsedClass);
  }

  if (toggle && sidebar) {
    toggle.addEventListener('click', function () {
      sidebar.classList.toggle(collapsedClass);
      const isCollapsed = sidebar.classList.contains(collapsedClass);
      localStorage.setItem('sidebar-collapsed', isCollapsed);
    });
  }
});
