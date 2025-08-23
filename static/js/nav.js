document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('nav-toggle').addEventListener('click', function () {
    document.getElementById('nav-menu').classList.toggle('max-sm:hidden');
  });
  document.querySelectorAll('.nav-group').forEach(function (group) {
    const btn = group.querySelector('[data-dropdown]');
    const menu = document.getElementById(btn.dataset.dropdown);
    let hideTimer;

    group.addEventListener('mouseenter', function () {
      clearTimeout(hideTimer);
      if (window.matchMedia('(min-width: 641px)').matches) {
        menu.classList.remove('hidden');
      }
    });

    group.addEventListener('mouseleave', function () {
      if (window.matchMedia('(min-width: 641px)').matches) {
        hideTimer = setTimeout(function () {
          menu.classList.add('hidden');
        }, 200);
      }
    });

    group.addEventListener('focusin', function () {
      clearTimeout(hideTimer);
      if (window.matchMedia('(min-width: 641px)').matches) {
        menu.classList.remove('hidden');
      }
    });

    group.addEventListener('focusout', function (e) {
      if (window.matchMedia('(min-width: 641px)').matches && !group.contains(e.relatedTarget)) {
        hideTimer = setTimeout(function () {
          menu.classList.add('hidden');
        }, 200);
      }
    });

    btn.addEventListener('click', function (e) {
      if (window.matchMedia('(max-width: 640px)').matches) {
        e.preventDefault();
        menu.classList.toggle('hidden');
      }
    });
  });
});
