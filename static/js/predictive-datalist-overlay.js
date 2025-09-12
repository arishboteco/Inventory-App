(function(){
  function buildOverlay(input){
    const listId = input.getAttribute('list');
    const datalist = listId && document.getElementById(listId);
    if (!datalist) return null;

    if (input._overlay) return input._overlay;

  const overlay = document.createElement('div');
  overlay.className = 'predictive-overlay absolute left-0 right-0 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto hidden z-[60]';
    overlay.setAttribute('role', 'listbox');

    function position(){
      const rect = input.getBoundingClientRect();
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
      overlay.style.position = 'absolute';
      overlay.style.minWidth = rect.width + 'px';
      overlay.style.width = rect.width + 'px';
      overlay.style.top = rect.bottom + scrollTop + 'px';
      overlay.style.left = rect.left + scrollLeft + 'px';
    }

    let activeIndex = -1;
    function render(filter){
      const q = (filter || '').toLowerCase();
      const options = Array.from(datalist.querySelectorAll('option'));
      const items = options.filter(o => !q || (o.value || o.textContent || '').toLowerCase().includes(q));
      overlay.innerHTML = '';
      activeIndex = -1;
      items.forEach((o, idx) => {
        const row = document.createElement('div');
        row.className = 'px-3 py-2 cursor-pointer hover:bg-blue-50';
        row.textContent = o.textContent || o.value || '';
        row.setAttribute('role', 'option');
        row.addEventListener('mousedown', (e)=>{
          e.preventDefault();
          input.value = o.value || o.textContent || '';
          input.dispatchEvent(new Event('input', {bubbles:true}));
          input.dispatchEvent(new Event('change', {bubbles:true}));
          hide();
        });
        overlay.appendChild(row);
      });
      if (items.length === 0){
        const msg = document.createElement('div');
        msg.className = 'px-3 py-2 text-gray-500';
        msg.textContent = q ? 'No matches' : 'Type to search...';
        overlay.appendChild(msg);
      }
    }

    function show(){
      position();
      render(input.value);
      overlay.classList.remove('hidden');
      document.body.appendChild(overlay);
      window.addEventListener('scroll', position, true);
      window.addEventListener('resize', position);
      document.addEventListener('mousedown', onDocDown);
    }
    function hide(){
      overlay.classList.add('hidden');
      if (overlay.parentNode === document.body) document.body.removeChild(overlay);
      window.removeEventListener('scroll', position, true);
      window.removeEventListener('resize', position);
      document.removeEventListener('mousedown', onDocDown);
    }
    function onDocDown(e){
      if (e.target === input || overlay.contains(e.target)) return;
      hide();
    }

    input.addEventListener('focus', show);
    input.addEventListener('input', ()=>render(input.value));
    input.addEventListener('keydown', (e)=>{
      const rows = overlay.querySelectorAll('[role="option"]');
      if (e.key === 'Escape') { hide(); return; }
      if (!rows.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = Math.min(activeIndex + 1, rows.length - 1);
        rows.forEach(r=>r.classList.remove('bg-blue-50'));
        rows[activeIndex].classList.add('bg-blue-50');
        rows[activeIndex].scrollIntoView({block:'nearest'});
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = Math.max(activeIndex - 1, 0);
        rows.forEach(r=>r.classList.remove('bg-blue-50'));
        rows[activeIndex].classList.add('bg-blue-50');
        rows[activeIndex].scrollIntoView({block:'nearest'});
      } else if (e.key === 'Enter' && activeIndex >= 0) {
        e.preventDefault();
        rows[activeIndex].dispatchEvent(new Event('mousedown', {bubbles:true}));
      }
    });

    input._overlay = {show, hide, element: overlay};
    return input._overlay;
  }

  function init(root){
    const scope = root || document;
    scope.querySelectorAll('input[list]').forEach(buildOverlay);
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    init();
  });
  document.body.addEventListener('htmx:afterSwap', (e)=>{
    init(e.target);
    // If a datalist was updated, refresh any open overlay using it
    const target = e.target;
    if (target && target.tagName === 'DATALIST' && target.id) {
      document.querySelectorAll(`input[list='${target.id}']`).forEach(inp=>{
        if (inp._overlay) {
          // Rebuild or re-render content to match new options
          const val = inp.value;
          inp._overlay.hide();
          const ol = buildOverlay(inp);
          if (document.activeElement === inp) {
            ol.show();
          }
        }
      });
    }
  });

  // Allow overlays to re-render on demand
  document.addEventListener('force-render', function(e){ /* noop root handler */ });
})();
