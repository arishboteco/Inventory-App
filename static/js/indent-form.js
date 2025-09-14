(function(){
  function resolveItemIdFromInput(inp){
    const listId = inp.getAttribute('list');
    const list = listId ? document.getElementById(listId) : null;
    const typed = (inp.value || '').trim();
    let id = '';
    if (list){
      const opts = Array.from(list.querySelectorAll('option'));
      const match = opts.find(o => ((o.value||'').trim().toLowerCase()===typed.toLowerCase()) || ((o.textContent||'').trim().toLowerCase()===typed.toLowerCase()));
      if (match) id = match.dataset.id || match.getAttribute('data-id') || '';
    }
    if (!id){
      const m = typed.match(/^(\d+)\s*-|\(\s*id\s*[:#-]?\s*(\d+)\s*\)$/i);
      if (m) id = m[1] || m[2] || '';
    }
    return id;
  }

  function bindItemInputs(root){
    const scope = root || document;
    scope.querySelectorAll("input[name^='items-'][name$='-item']").forEach((itemInput)=>{
      if (itemInput._indentBound) return; itemInput._indentBound = true;
      const wrapper = itemInput.closest('div') || itemInput.parentElement;
      let info = null, err = null;
      if (wrapper){
        info = document.createElement('div'); info.className='mt-1 text-xs text-gray-500'; info.setAttribute('data-item-meta',''); wrapper.appendChild(info);
        err = document.createElement('div'); err.className='mt-1 text-xs text-red-600 hidden'; err.setAttribute('data-item-error',''); wrapper.appendChild(err);
      }
      function setInvalid(msg){ if (!err) return; if (msg){ err.textContent = msg; err.classList.remove('hidden'); } else { err.textContent=''; err.classList.add('hidden'); } }
      function refresh(){
        const id = resolveItemIdFromInput(itemInput);
        const typed = (itemInput.value||'').trim();
        if (info) info.textContent='';
        if (!typed){ setInvalid(''); return; }
        if (!id){ setInvalid('Choose a valid item from the list.'); return; }
        fetch(`/items/meta/${id}/`).then(r=>r.ok?r.json():null).then(data=>{
          if (!data || !data.ok){ setInvalid('Selected item not found.'); return; }
          const parts=[]; if (data.unit) parts.push(data.unit); if (data.category) parts.push(data.category); if (data.subcategory) parts.push(data.subcategory);
          if (info) info.textContent = parts.filter(Boolean).join(' • ');
          setInvalid('');
          // When a valid item is confirmed, re-run auto-add check so the next row appears promptly
          try {
            const table = itemInput.closest('#items-table');
            if (table && typeof table._maybeAdd === 'function') {
              table._maybeAdd();
            }
          } catch(_) {}
        }).catch(()=>{});
      }
      let t=null; const deb=()=>{ clearTimeout(t); t=setTimeout(refresh,250); };
      itemInput.addEventListener('input', deb);
      itemInput.addEventListener('change', refresh);
      itemInput.addEventListener('blur', refresh);
    });
  }

  function checkDuplicates(root){
    const scope = root || document;
    const form = (scope && scope.querySelector) ? scope.querySelector('#indent-form') : document.getElementById('indent-form');
    const submitBtn = form ? form.querySelector('button[type="submit"]') : null;
    const inputs = form ? Array.from(form.querySelectorAll("input[name^='items-'][name$='-item']")) : [];
    const ids = inputs.map(inp => resolveItemIdFromInput(inp)).filter(Boolean);
    const counts = ids.reduce((a,id)=>{ a[id]=(a[id]||0)+1; return a; },{});
    let hasDup = false;
    inputs.forEach(inp=>{
      const id = resolveItemIdFromInput(inp);
      let warn = inp.closest('div')?.querySelector('[data-dup-warning]');
      if (!warn){ warn=document.createElement('div'); warn.className='mt-1 text-xs text-orange-600 hidden'; warn.setAttribute('data-dup-warning',''); const wrap=inp.closest('div')||inp.parentElement; if (wrap) wrap.appendChild(warn); }
      if (id && counts[id]>1){ hasDup = true; warn.textContent='Duplicate item selected'; warn.classList.remove('hidden'); } else { warn.textContent=''; warn.classList.add('hidden'); }
    });
    if (submitBtn) submitBtn.disabled = !!hasDup;
  }

  function ensureHiddenIdsOnSubmit(root){
    const scope = root || document;
    const form = (scope && scope.querySelector) ? scope.querySelector('#indent-form') : document.getElementById('indent-form');
    if (!form || form._boundHidden) return; form._boundHidden=true;
    form.addEventListener('submit', function(ev){
      const inputs = form.querySelectorAll("input[name^='items-'][name$='-item']");
      let invalid=false;
      inputs.forEach((itemInput)=>{
        const id = resolveItemIdFromInput(itemInput);
        const err = itemInput.closest('div')?.querySelector('[data-item-error]');
        const typed = (itemInput.value||'').trim();
        if (!typed){ if (err) err.classList.add('hidden'); return; }
        if (!id){ invalid=true; if (err){ err.textContent='Choose a valid item from the list.'; err.classList.remove('hidden'); } return; }
        let hidden = form.querySelector(`input[type="hidden"][data-item-hidden-for='${itemInput.name}']`);
        if (!hidden){ hidden=document.createElement('input'); hidden.type='hidden'; hidden.setAttribute('data-item-hidden-for', itemInput.name); form.appendChild(hidden); }
        hidden.name = itemInput.name; hidden.value = id;
        if (!itemInput.dataset.originalName) itemInput.dataset.originalName = itemInput.name;
        itemInput.name = itemInput.dataset.originalName + '_display';
        setTimeout(()=>{ itemInput.name = itemInput.dataset.originalName; }, 0);
      });
      if (invalid) ev.preventDefault();
    });
  }

  function setupAutoAdd(root){
    const scope = root || document;
    const table = (scope && scope.querySelector) ? scope.querySelector('#items-table') : document.getElementById('items-table');
    const addBtn = (scope && scope.querySelector) ? scope.querySelector('#add-row') : document.getElementById('add-row');
    if (!table || !addBtn) return;
    // Prevent duplicate bindings if initIndentForm runs multiple times
    if (table._autoAddBound) return; table._autoAddBound = true;
    function maybeAdd(){
      const rows = table.querySelectorAll('tr.form-row');
      if (!rows.length) return;
      const last = rows[rows.length-1];
      if (last.dataset.autoExtended === '1') return;
      const itemInput = last.querySelector("input[name$='-item']");
      const qtyInput = last.querySelector("input[name$='-requested_qty']");
      const hasItem = itemInput && resolveItemIdFromInput(itemInput);
      const hasQty = qtyInput && parseFloat(qtyInput.value) > 0;
      if (hasItem && hasQty){
        addBtn.click();
        last.dataset.autoExtended = '1';
        setTimeout(()=>{
          bindItemInputs(table);
          if (window.initPredictiveDatalistOverlay) window.initPredictiveDatalistOverlay(table);
          checkDuplicates(scope);
          // Focus next row's item field for faster entry
          const rows2 = table.querySelectorAll('tr.form-row');
          const newLast = rows2[rows2.length-1];
          const nextItem = newLast && newLast.querySelector("input[name$='-item']");
          if (nextItem) nextItem.focus();
        }, 0);
      }
    }
    // Expose a scoped trigger for other scripts (e.g., after async item meta fetch)
    table._maybeAdd = maybeAdd;
  function handler(){ maybeAdd(); checkDuplicates(scope); }
    table.addEventListener('input', function(e){
      if (e.target && (e.target.matches("input[name$='-item']") || e.target.matches("input[name$='-requested_qty']"))) {
        handler();
      }
    });
    table.addEventListener('change', function(e){
      if (e.target && (e.target.matches("input[name$='-item']") || e.target.matches("input[name$='-requested_qty']"))) {
        handler();
      }
    });
    // Re-check after formset script adds a row
    document.addEventListener('click', function(e){
      if (e.target && e.target.id === 'add-row') {
        setTimeout(maybeAdd, 0);
      }
    });
    setTimeout(maybeAdd, 0);
  }

  function setupDepartmentSync(root){
    const scope = root || document;
    const ui = (scope && scope.querySelector) ? scope.querySelector('#department-ui') : document.getElementById('department-ui');
    const hidden = (scope && scope.querySelector) ? scope.querySelector('#id_department') : document.getElementById('id_department');
    if (hidden && ui){
      // Initialize hidden from UI if hidden is empty but UI already has a value
      if (hidden.value) {
        ui.value = hidden.value;
      } else if (ui.value) {
        hidden.value = ui.value;
      }
      ui.addEventListener('change', ()=> { hidden.value = ui.value; });
      ui.addEventListener('input', ()=> { hidden.value = ui.value; });

      // Ensure sync just before submit in case no change/input fired after opening modal
      const form = (scope && scope.querySelector) ? scope.querySelector('#indent-form') : document.getElementById('indent-form');
      if (form && !form._syncDeptOnSubmit){
        form._syncDeptOnSubmit = true;
        form.addEventListener('submit', function(){ hidden.value = ui.value; });
      }
    }
  }

  window.initIndentForm = function(root){
    const scope = root || document;
    bindItemInputs(scope);
    ensureHiddenIdsOnSubmit(scope);
    setupAutoAdd(scope);
    setupDepartmentSync(scope);
    checkDuplicates(scope);
  };
})();
