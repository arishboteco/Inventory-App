/**
 * Recipe Items Table - Interactive formset management
 * Simplified from components to direct item selection
 */
(function() {
  'use strict';
  
  console.log('🔥 Loading recipe-components.js 🔥');
  
  // Immediate test - add this to see if the script loads at all
  window.DEBUG_RECIPE_JS_LOADED = true;
  
  // Enhanced debugging info at the top level
  console.log('🔍 Recipe Components Debug Info:', {
    location: window.location.href,
    readyState: document.readyState,
    allTables: document.querySelectorAll('table').length,
    allButtons: document.querySelectorAll('button').length,
    itemsTable: !!document.getElementById('items-table'),
    addButton: !!document.getElementById('add-row'),
    initPredictiveDropdowns: typeof window.initPredictiveDropdowns,
    predictiveDropdownsAvailable: !!window.initPredictiveDropdowns
  });
  
  function initRecipeComponentsTable(root, tableId) {
    console.log('🚀 === INITIALIZING RECIPE COMPONENTS TABLE === 🚀');
    console.log('Root element:', root);
    console.log('Table ID:', tableId);
    
    root = root || document;
    tableId = tableId || 'items-table';
    
    // No global/window flags; guard per-table only
    
    // Find the table - scope to root to avoid collisions with background pages
    var table = (root && root.querySelector) ? root.querySelector('#' + tableId) : null;
    if (!table) {
      console.log('⚠️ Table not found in root, trying document...');
      table = document.querySelector('#' + tableId);
    }
    if (!table) {
      console.log('⚠️ Table not found with querySelector, searching all tables...');
      var tables = document.querySelectorAll('table');
      console.log('Found tables:', Array.from(tables).map(t => ({ id: t.id, classes: t.className })));
      
      // Look for table with recipe-related content
      for (var i = 0; i < tables.length; i++) {
        var t = tables[i];
        if (t.querySelector('tbody') && (t.id === tableId || t.id.includes('table') || t.querySelector('[id*="item"]'))) {
          console.log('✅ Using table as fallback:', t.id || 'no-id');
          table = t;
          break;
        }
      }
    }
    
    if (!table) {
      console.error('❌ No items table found yet. This means the table HTML has not loaded.');
      console.log('Available elements:', {
        allTables: document.querySelectorAll('table').length,
        allDivs: document.querySelectorAll('div[id*="item"]').length,
        formElements: document.querySelectorAll('input[name*="item"]').length
      });
      return;
    }
    
    console.log('✅ Found table:', table.id);
    // If table is already fully initialized, bail out
    if (table.dataset.recipeInitialized === '1') {
      console.log('⚠️ Table already marked initialized via dataset, skipping');
      return;
    }
    
    var tbody = table.querySelector('tbody');
    if (!tbody) {
      console.error('❌ Table has no tbody');
      return;
    }
    
    // Find form management elements
  var totalForms = (root && root.querySelector) ? root.querySelector('#id_items-TOTAL_FORMS') : null;
  var emptyRow = (root && root.querySelector) ? root.querySelector('#items-empty-row') : null;
    
    console.log('Form elements:', {
      totalForms: !!totalForms,
      emptyRow: !!emptyRow,
      totalFormsValue: totalForms ? totalForms.value : 'N/A'
    });
    
    if (!totalForms || !emptyRow) {
      console.error('❌ Missing form management elements. Available elements:');
      console.log('- All form inputs:', document.querySelectorAll('input[id*="TOTAL_FORMS"]'));
      console.log('- All hidden rows:', document.querySelectorAll('tr.hidden'));
      return;
    }
    
    // Bind existing rows
    var existingRows = tbody.querySelectorAll('tr.form-row:not(.hidden)');
    console.log('Found existing rows:', existingRows.length);
    
    // Initialize predictive dropdowns for existing rows
    if (window.initPredictiveDropdowns && existingRows.length > 0) {
      console.log('🔍 Initializing predictive dropdowns for existing rows...');
      existingRows.forEach(function(row) {
        window.initPredictiveDropdowns(row);
      });
    }
    
    existingRows.forEach(function(row) {
      bindRowEvents(row);
      try { bootstrapExistingRow(row); } catch (err) { console.warn('bootstrapExistingRow failed', err); }
    });
    try { debugFormsetState(table, 'after-init-existing-binds'); } catch(e) {}
    
    // Find and setup add button
    var addBtn = (root && root.querySelector) ? root.querySelector('#add-row') : null;
    if (!addBtn) {
      console.log('⚠️ Add button not found in scoped root, trying document...');
      addBtn = document.querySelector('#add-row');
    }
    if (!addBtn) {
      console.log('⏳ Add button not yet in DOM; attaching observer to wait...');
      if (!table._addBtnObserverAttached) {
        table._addBtnObserverAttached = true;
        var observer = new MutationObserver(function() {
          var btnCandidate = (root && root.querySelector) ? root.querySelector('#add-row') : document.querySelector('#add-row');
          if (btnCandidate) {
            observer.disconnect();
            table._addBtnObserverAttached = false;
            // Bind and finish init now that the button exists
            setupAddButton(btnCandidate);
            finalizeInit();
          }
        });
        observer.observe(root || document, { childList: true, subtree: true });
      }
    }
    function setupAddButton(btn) {
      console.log('✅ Setting up Add Item button');
      if (btn.dataset.recipeHandlerAttached) {
        console.log('⚠️ Add button already has recipe handler attached, skipping...');
        return;
      }
      var newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
      btn = newBtn;
      btn.dataset.recipeHandlerAttached = 'true';
      btn.title = 'Add a recipe item';
      btn.onclick = function(e) {
        e.preventDefault();
        // Prevent any other handlers on this button from acting on this event
        if (typeof e.stopImmediatePropagation === 'function') {
          e.stopImmediatePropagation();
        } else {
          e.stopPropagation();
        }
        // Event-level guard: only handle the first listener for this click
        if (btn._lastRecipeClickStamp === e.timeStamp) {
          console.log('🛑 Duplicate add-row handler suppressed for this click');
          return;
        }
        btn._lastRecipeClickStamp = e.timeStamp;
        console.log('🔥 === ADD ITEM CLICKED === 🔥');
        try {
          addNewRow(table, tbody, totalForms, emptyRow);
        } catch (error) {
          console.error('❌ Error adding row:', error);
        }
      };
      console.log('✅ Add button setup complete');
    }

    function finalizeInit() {
      table.dataset.recipeInitialized = '1';
      console.log('✅ Recipe components table initialized for', tableId);
      try { debugFormsetState(table, 'finalize-init'); } catch(e) {}

      // Attach submit guard: require at least one positive quantity
      try {
        var formEl = (root && root.querySelector) ? root.querySelector('form[data-modal-form]') : document.querySelector('form[data-modal-form]');
        if (formEl && !formEl.dataset.recipeSubmitGuardAttached) {
          formEl.dataset.recipeSubmitGuardAttached = '1';
          formEl.addEventListener('submit', function(e) {
            var rows = table.querySelectorAll('tr.form-row:not(.hidden)');
            var hasPositive = false;
            var firstQtyToFocus = null;
            var rowsSummary = [];
            rows.forEach(function(r){
              var itemSel = r.querySelector('select[id$="-item"]');
              var qtyInp = r.querySelector('input[id$="-quantity"]');
              var qty = qtyInp ? parseFloat(qtyInp.value || '0') : 0;
              if (itemSel && itemSel.value && qty > 0) hasPositive = true;
              if (!firstQtyToFocus && itemSel && itemSel.value && qtyInp && (!qty || qty <= 0)) firstQtyToFocus = qtyInp;
              rowsSummary.push({
                rowIndex: r.getAttribute('data-form-index'),
                item: itemSel ? itemSel.value : '',
                quantity: qtyInp ? qtyInp.value : '',
                quantityNum: qty,
                delete: (r.querySelector('input[id$="-DELETE"]')||{}).checked || false
              });
            });
            try { console.group('🧾 Submit Check: Recipe Items'); } catch(_) {}
            try {
              var rootScope = table.closest('.drawer-panel') || table.closest('[data-modal-root]') || document;
              var tf = rootScope.querySelector('#id_items-TOTAL_FORMS');
              var inf = rootScope.querySelector('#id_items-INITIAL_FORMS');
              console.log('Mgmt counts → TOTAL_FORMS:', tf?tf.value:'n/a', 'INITIAL_FORMS:', inf?inf.value:'n/a');
              console.table(rowsSummary);
              debugFormsetState(table, 'before-submit');
            } catch(_) {}
            try { console.groupEnd(); } catch(_) {}
            if (!hasPositive) {
              e.preventDefault();
              if (firstQtyToFocus) firstQtyToFocus.focus();
              console.warn('🛑 Prevented submit: need at least one positive quantity');
            }
          });
        }
      } catch (err) {
        console.warn('Submit guard attach failed:', err);
      }
    }

    if (addBtn) {
      setupAddButton(addBtn);
      finalizeInit();
    }

    // If inside a modal/drawer, reset init on close so re-open re-initializes
    var modalRoot = table.closest('[data-modal-root], .drawer-panel');
    if (modalRoot) {
      var resetInit = function() {
        // Also clear handler flag to allow rebind on next open
        var btn = modalRoot.querySelector('#add-row');
        if (btn) delete btn.dataset.recipeHandlerAttached;
        if (table) delete table.dataset.recipeInitialized;
        console.log('♻️ Recipe components init reset for', tableId);
      };
      // Common close triggers
      modalRoot.addEventListener('modal:close', resetInit, { once: true });
      var closeBtn = modalRoot.querySelector('[data-modal-close]');
      if (closeBtn) closeBtn.addEventListener('click', resetInit, { once: true });
    }
  }
  
  function addNewRow(table, tbody, totalForms, emptyRow) {
    console.log('🔧 Adding new row...');
    // Prevent concurrent adds creating duplicate indices
    if (totalForms.dataset.addLock === '1') {
      console.warn('🛑 Add row currently locked; skipping duplicate call');
      return;
    }
    totalForms.dataset.addLock = '1';

    var index = parseInt(totalForms.value, 10) || 0;
    console.log('Current form count:', index);
    // Increment immediately to reserve index even if another call slips in
    totalForms.value = index + 1;

    // Clone the empty row
    var newRow = emptyRow.cloneNode(true);
    try {
      newRow.dataset.category = (newRow.dataset.category || '').trim();
      newRow.dataset.subcategory = (newRow.dataset.subcategory || '').trim();
      newRow.dataset.itemName = (newRow.dataset.itemName || '').trim();
    } catch (err) {
      console.warn('Dataset init failed for new row:', err);
    }

    // Replace the prefix in all form elements
    var inputs = newRow.querySelectorAll('input, select, textarea');
    inputs.forEach(function(input) {
      if (input.name) {
        input.name = input.name.replace('__prefix__', index);
      }
      if (input.id) {
        input.id = input.id.replace('__prefix__', index);
      }
      
      // Clear values for new row (except hidden fields)
      if (input.type !== 'hidden') {
        if (input.tagName === 'SELECT') {
          input.selectedIndex = 0; // Reset to first option (usually empty)
          // Ensure the select has the predictive class
          if (input.id && input.id.endsWith('-item')) {
            if (!input.classList.contains('predictive')) {
              input.classList.add('predictive');
              console.log('🔧 Added predictive class to:', input.id);
            }
          }
        } else {
          input.value = '';
        }
      }
    });
    
    // Replace prefix in labels
    var labels = newRow.querySelectorAll('label');
    labels.forEach(function(label) {
      if (label.htmlFor) {
        label.htmlFor = label.htmlFor.replace('__prefix__', index);
      }
    });
    
    // Clear the ID, stamp index, and make visible
    newRow.id = '';
    try { newRow.setAttribute('data-form-index', String(index)); } catch (e) {}
    newRow.classList.remove('hidden');
    tbody.appendChild(newRow);

    console.log('🔧 Initializing new row...');
    
    // Use setTimeout to ensure DOM is updated before initializing dropdowns
    setTimeout(function() {
      console.log('🔧 Starting dropdown initialization for new row...');
      
      // Find the item select in the new row
      var itemSelect = newRow.querySelector('select[id$="-item"]');
      if (itemSelect) {
        console.log('🔍 Found item select:', itemSelect.id);
        
        // Ensure it has the predictive class and proper setup
        if (!itemSelect.classList.contains('predictive')) {
          itemSelect.classList.add('predictive');
          console.log('✅ Added predictive class');
        }
        // Dedupe any stray predictive inputs with the same id (defensive)
        var textId = itemSelect.id + '_text';
        var textInputs = document.querySelectorAll('#' + CSS.escape(textId));
        if (textInputs.length > 1) {
          console.warn('⚠️ Duplicate predictive inputs found, removing extras for', textId);
          textInputs.forEach(function(inp, idx) { if (idx > 0) inp.remove(); });
        }

        console.log('🔍 Item select state before initialization:', {
          id: itemSelect.id,
          hasPredictiveClass: itemSelect.classList.contains('predictive'),
          isUpgraded: itemSelect.dataset.predictiveUpgraded,
          optionsCount: itemSelect.options.length
        });
      }
      
      // Check if initPredictiveDropdowns is available
      console.log('🔍 initPredictiveDropdowns available:', typeof window.initPredictiveDropdowns);
      
      // Initialize predictive dropdowns for the new row
      if (window.initPredictiveDropdowns) {
        // Only initialize if not already upgraded
        var shouldInit = true;
        if (itemSelect) {
          if (itemSelect.dataset.predictiveUpgraded === '1' || document.getElementById(itemSelect.id + '_text')) {
            shouldInit = false;
          }
        }
        if (shouldInit) {
          console.log('🔍 Calling initPredictiveDropdowns for new row...');
          try {
            window.initPredictiveDropdowns(newRow);
            console.log('✅ initPredictiveDropdowns called successfully for new row');
          } catch (error) {
            console.error('❌ Error calling initPredictiveDropdowns:', error);
          }
        } else {
          console.log('ℹ️ Predictive already initialized for this select; skipping re-init');
        }
      } else {
        console.warn('⚠️ initPredictiveDropdowns not available');
      }
      
      // Bind events for the new row
      setTimeout(function() {
        bindRowEvents(newRow);
        // Run a dedupe pass across the table to ensure no duplicate _text inputs exist
        try { dedupePredictiveInputs(table); } catch (e) { console.warn('Dedupe failed:', e); }
        if (window.updateRecipeCosts) {
          window.updateRecipeCosts();
        }
      }, 200);
    }, 10);

    // Release lock in next tick to allow another add
    setTimeout(function(){ delete totalForms.dataset.addLock; }, 0);
    console.log('✅ Row added and scheduled for initialization! New count:', totalForms.value);
  }

  // Remove duplicate predictive text inputs for a given table
  function dedupePredictiveInputs(table) {
    var selects = table.querySelectorAll('select[id$="-item"]');
    selects.forEach(function(sel) {
      var textId = sel.id + '_text';
      var texts = table.querySelectorAll('#' + CSS.escape(textId));
      if (texts.length > 1) {
        // Keep the first visible one, remove the rest
        texts.forEach(function(inp, idx) { if (idx > 0) inp.remove(); });
        console.log('🧹 Removed duplicate predictive inputs for', textId);
      }
    });
  }

  // Collect and print current formset state for debugging
  function debugFormsetState(table, label) {
    try {
      var root = table.closest('.drawer-panel') || table.closest('[data-modal-root]') || document;
      var totalForms = root.querySelector('#id_items-TOTAL_FORMS');
      var initialForms = root.querySelector('#id_items-INITIAL_FORMS');
      var rows = Array.from(table.querySelectorAll('tr.form-row:not(.hidden)'));
      var dump = rows.map(function(r){
        var item = r.querySelector('select[id$="-item"]');
        var qty = r.querySelector('input[id$="-quantity"]');
        var unit = r.querySelector('input[id$="-unit"]');
        var unitDisplay = r.querySelector('input[id$="-unit_display"]');
        var del = r.querySelector('input[id$="-DELETE"]');
        return {
          rowIndex: r.getAttribute('data-form-index'),
          itemId: item ? item.value : '',
          itemText: (item && document.getElementById(item.id + '_text')) ? document.getElementById(item.id + '_text').value : '',
          quantity: qty ? qty.value : '',
          unit: unit ? unit.value : '',
          unitDisplay: unitDisplay ? unitDisplay.value : '',
          markedDelete: del ? (del.checked || del.value === 'on' || del.value === '1') : false
        };
      });
      console.group('🧭 Recipe Formset Debug [' + (label||'') + ']');
      console.log('TOTAL_FORMS:', totalForms ? totalForms.value : 'n/a', 'INITIAL_FORMS:', initialForms ? initialForms.value : 'n/a');
      console.table(dump);
      console.groupEnd();
    } catch (e) {
      console.warn('debugFormsetState error:', e);
    }
  }
  
  function bindRowEvents(row) {
    console.log('🔗 Binding events for row:', row);
    
    // Find item selector - look for select with pattern ending in "-item"
    var itemSelect = row.querySelector('select[id$="-item"]');
    if (itemSelect) {
      console.log('✅ Binding change event to item selector:', itemSelect.id);
      
      // Bind to the original select element
      itemSelect.addEventListener('change', function() {
        var val = itemSelect.value;
        console.log('🔄 Item changed to:', val);
        
        if (!val) {
          handleItemChange(itemSelect, null);
          return;
        }
        
        handleItemChange(itemSelect, val);
      });
      
      // Also bind to the predictive dropdown text input if it exists
      var predictiveTextInput = row.querySelector('input[id$="-item_text"]');
      if (predictiveTextInput) {
        console.log('✅ Also binding to predictive text input:', predictiveTextInput.id);
        predictiveTextInput.addEventListener('input', function() {
          // The predictive dropdown should update the original select, which will trigger our change event
          console.log('🔄 Predictive input changed:', predictiveTextInput.value);
        });
      }
      
      // Use a more aggressive approach to detect predictive dropdown creation
      var checkForPredictiveInput = function() {
        var textInput = row.querySelector('input[id$="-item_text"]');
        if (textInput && !textInput._eventsBound) {
          console.log('🔍 Predictive text input detected, binding events');
          textInput._eventsBound = true;
          textInput.addEventListener('input', function() {
            console.log('🔄 Predictive input changed:', textInput.value);
          });
        } else if (!textInput) {
          // Keep checking for a bit
          setTimeout(checkForPredictiveInput, 100);
        }
      };
      
      // Start checking immediately and after a short delay
      setTimeout(checkForPredictiveInput, 10);
      setTimeout(checkForPredictiveInput, 100);
      setTimeout(checkForPredictiveInput, 500);
      
    } else {
      console.error('❌ Item select not found in row');
    }
    
    // Bind quantity input change to debug values
    var qtyInput = row.querySelector('input[id$="-quantity"]');
    if (qtyInput) {
      ['input','change','blur'].forEach(function(ev){
        qtyInput.addEventListener(ev, function(){
          console.log('🧮 Quantity', ev, '→', qtyInput.value, 'for', qtyInput.id);
          var itemSel = row.querySelector('select[id$="-item"]');
          if (itemSel) {
            try { updateRowCost(itemSel, null); } catch(_) {}
          }
        });
      });
    }

    // Also bind to remove button
    var removeBtn = row.querySelector('.remove-row');
    if (removeBtn) {
      removeBtn.addEventListener('click', function(e) {
        e.preventDefault();
        console.log('🗑️ Remove button clicked');
        row.remove();
        if (window.updateRecipeCosts) {
          window.updateRecipeCosts();
        }
        // Note: In a real formset, you'd need to handle the DELETE field properly
      });
    }
  }

  function bootstrapExistingRow(row) {
    if (!row || row.dataset.recipeBootstrapped === '1') {
      return;
    }
    var itemSelect = row.querySelector('select[id$="-item"]');
    if (!itemSelect || !itemSelect.value) {
      return;
    }
    row.dataset.recipeBootstrapped = '1';

    if (!row.dataset.costPerBaseUnit) {
      var attrCost = row.getAttribute('data-cost-per-base-unit');
      if (attrCost) {
        row.dataset.costPerBaseUnit = attrCost;
      }
    }

    if (row.dataset.recipeMetaReady === '1' || row.dataset.costPerBaseUnit) {
      try { updateRowCost(itemSelect, null); } catch (_) {}
      return;
    }

    if (itemSelect.dataset.recipeFetching === '1') {
      return;
    }

    handleItemChange(itemSelect, itemSelect.value, { bootstrap: true });
  }

  function handleItemChange(itemSelect, val, options) {
    options = options || {};
    console.log('🔄 Handling item change for:', itemSelect.id, 'value:', val);

    // Find unit fields for this row - the formset uses patterns like id_items-0-item, id_items-0-unit, etc.
    var baseId = itemSelect.id.replace('-item', '');
    var unitHidden = document.getElementById(baseId + '-unit');
    var unitDisplay = document.getElementById(baseId + '-unit_display');
    
    console.log('Unit fields lookup:', {
      baseId: baseId,
      searching_for_hidden: baseId + '-unit',
      searching_for_display: baseId + '-unit_display',
      hidden_found: !!unitHidden,
      display_found: !!unitDisplay,
      hiddenId: unitHidden ? unitHidden.id : 'not found',
      displayId: unitDisplay ? unitDisplay.id : 'not found'
    });
    
    // Debug: List all input fields in the row to see what's actually available
    var row = itemSelect.closest('tr');
    if (row) {
      var allInputs = row.querySelectorAll('input, select');
      console.log('All inputs in row:', Array.from(allInputs).map(function(inp) {
        return { id: inp.id, name: inp.name, type: inp.type };
      }));
    }

    if (options.bootstrap && row && row.dataset.recipeMetaReady === '1') {
      try { updateRowCost(itemSelect, null); } catch (_) {}
      if (window.updateRecipeCosts) {
        window.updateRecipeCosts();
      }
      return;
    }

    // If no item selected, clear unit fields
    if (!val) {
      if (unitHidden) {
        unitHidden.value = '';
        console.log('✅ Cleared unit hidden field');
      }
      if (unitDisplay) {
        unitDisplay.value = '';
        console.log('✅ Cleared unit display field');
      }
      if (row) {
        row.dataset.category = '';
        row.dataset.subcategory = '';
        row.dataset.itemName = '';
        delete row.dataset.costPerBaseUnit;
        delete row.dataset.recipeMetaReady;
      }
      updateRowCost(itemSelect, null);
      if (window.updateRecipeCosts) {
        window.updateRecipeCosts();
      }
      return;
    }

    if (itemSelect.dataset.recipeFetching === '1') {
      console.log('⏳ Skipping duplicate fetch for', itemSelect.id);
      return;
    }

    // Fetch item metadata using the item's primary key
    console.log('🌐 Fetching item meta for ID:', val);
    itemSelect.dataset.recipeFetching = '1';
    fetch('/items/meta/' + val + '/')
      .then(function(r) {
        console.log('📡 Item meta fetch status:', r.status);
        if (!r.ok) {
          throw new Error('Failed to fetch item meta: ' + r.status);
        }
        return r.json(); 
      })
      .then(function(data) {
        console.log('📦 Item data received:', data);
        if (data && data.ok) {
          // Update unit fields to BASE unit for recipes
          if (unitHidden) {
            unitHidden.value = data.base_unit || '';
            console.log('✅ Set unit hidden (BASE) to:', data.base_unit);
          }
          if (unitDisplay) {
            unitDisplay.value = data.base_unit || '';
            console.log('✅ Set unit display (BASE) to:', data.base_unit);
          }
          // Cache cost per base unit on the row for quick recompute
          try {
            if (row) {
              row.dataset.costPerBaseUnit = String(data.cost_per_base_unit || 0);
              row.dataset.category = (data.category || '').trim();
              row.dataset.subcategory = (data.subcategory || '').trim();
              row.dataset.itemName = (data.name || '').trim();
              row.dataset.recipeMetaReady = '1';
            }
          } catch (_) {}

          // Update cost
          updateRowCost(itemSelect, data);
          if (window.updateRecipeCosts) {
            window.updateRecipeCosts();
          }
          try { var table = itemSelect.closest('table'); if (table) debugFormsetState(table, 'after-item-change'); } catch(e) {}
        } else {
          console.error('❌ Invalid item data received:', data);
        }
      })
      .catch(function(err) {
        console.error('❌ Failed to fetch item meta:', err);
      })
      .finally(function() {
        delete itemSelect.dataset.recipeFetching;
      });
  }
  
  function updateRowCost(itemSelect, itemData) {
    console.log('💰 Updating row cost...');

    // Prefer cost per base unit from API; fall back to last_price/conversion
    var costPerBase = null;
    if (itemData) {
      if (typeof itemData.cost_per_base_unit !== 'undefined') {
        costPerBase = parseFloat(itemData.cost_per_base_unit);
      }
      if (!costPerBase || isNaN(costPerBase)) {
        var conv = parseFloat(itemData.conversion_factor || '0');
        var lastP = parseFloat(itemData.last_purchase_price || '0');
        costPerBase = conv ? (lastP / conv) : null;
      }
    } else {
      var rowCached = itemSelect.closest('tr');
      if (rowCached && rowCached.dataset.costPerBaseUnit) {
        costPerBase = parseFloat(rowCached.dataset.costPerBaseUnit);
      }
    }
    if (costPerBase === null || typeof costPerBase === 'undefined' || isNaN(costPerBase)) {
      costPerBase = 0;
    }

    // Find the cost display element for this row
    var row = itemSelect.closest('tr');
    var costElement = row ? row.querySelector('[data-line-cost]') : null;

    if (costElement) {
      // Get quantity to calculate line cost - use the same base ID pattern
      var baseId = itemSelect.id.replace('-item', '');
      var quantityInput = document.getElementById(baseId + '-quantity');
      var quantity = quantityInput ? parseFloat(quantityInput.value) || 0 : 0;

      var lineCost = quantity * costPerBase;

      costElement.textContent = lineCost.toFixed(2);
      console.log('✅ Updated line cost to:', lineCost.toFixed(2));

      // Trigger recipe cost recalculation if available
      if (window.updateRecipeCosts) {
        setTimeout(window.updateRecipeCosts, 100);
      }
    }
  }

  function slugifyCategoryLabel(label) {
    return String(label || 'uncategorized')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'uncategorized';
  }

  function parseLineCost(el) {
    if (!el) {
      return 0;
    }
    var text = String(el.textContent || '').replace(/[^0-9.-]/g, '');
    var value = parseFloat(text);
    return Number.isFinite(value) ? value : 0;
  }

  function clampMarginValue(raw) {
    if (!Number.isFinite(raw)) {
      return 0;
    }
    if (raw < 0) {
      return 0;
    }
    if (raw > 95) {
      return 95;
    }
    return raw;
  }

  window.updateRecipeCosts = function(root) {
    try {
      var scope = root || document;
      var table = scope.querySelector('#items-table');
      if (!table) {
        return;
      }
      var tbody = table.querySelector('tbody');
      if (!tbody) {
        return;
      }

      var activeElement = document.activeElement;
      var shouldRestoreFocus = Boolean(activeElement && table.contains(activeElement));
      var selectionStart = null;
      var selectionEnd = null;
      var selectionDirection = null;
      var hasSelection = false;
      if (shouldRestoreFocus) {
        try {
          var start = activeElement.selectionStart;
          var end = activeElement.selectionEnd;
          if (typeof start === 'number' && typeof end === 'number') {
            selectionStart = start;
            selectionEnd = end;
            selectionDirection = activeElement.selectionDirection || null;
            hasSelection = true;
          }
        } catch (_) {
          selectionStart = null;
          selectionEnd = null;
          selectionDirection = null;
        }
      }

      var hiddenTemplate = table.querySelector('#items-empty-row');
      if (hiddenTemplate && hiddenTemplate.parentNode === tbody) {
        tbody.removeChild(hiddenTemplate);
      }

      Array.from(tbody.querySelectorAll('tr[data-category-heading]')).forEach(function(row) {
        row.remove();
      });

      var visibleRows = Array.from(tbody.querySelectorAll('tr.form-row'));
      var groups = [];
      var groupMap = Object.create(null);
      var totalCost = 0;

      visibleRows.forEach(function(row, index) {
        if (row.classList.contains('hidden')) {
          return;
        }
        var deleteField = row.querySelector('input[id$="-DELETE"]');
        if (deleteField && deleteField.checked) {
          return;
        }

        var category = (row.dataset.category || '').trim();
        if (!category) {
          category = 'Uncategorized';
        }
        var key = category.toLowerCase() || 'uncategorized';
        var group = groupMap[key];
        if (!group) {
          group = { key: key, label: category, rows: [], total: 0 };
          groupMap[key] = group;
          groups.push(group);
        }

        var lineCost = parseLineCost(row.querySelector('[data-line-cost]'));
        totalCost += lineCost;
        group.total += lineCost;
        group.rows.push({ row: row, index: index });
      });

      groups.sort(function(a, b) {
        if (a.label === b.label) {
          return 0;
        }
        if (a.label === 'Uncategorized') {
          return 1;
        }
        if (b.label === 'Uncategorized') {
          return -1;
        }
        return a.label.localeCompare(b.label);
      });

      var fragment = document.createDocumentFragment();
      groups.forEach(function(group, idx) {
        var headingId = 'recipe-category-' + slugifyCategoryLabel(group.label) + '-' + idx;
        var headingRow = document.createElement('tr');
        headingRow.setAttribute('data-category-heading', '1');
        headingRow.setAttribute('data-category-key', group.key);
        headingRow.setAttribute('role', 'row');
        var headingCell = document.createElement('th');
        headingCell.setAttribute('scope', 'colgroup');
        headingCell.setAttribute('colspan', '6');
        headingCell.id = headingId;
        headingCell.className = 'px-4 py-2 text-xs font-semibold uppercase tracking-wide text-gray-600 bg-surfaceSubtle';
        headingCell.textContent = group.label;
        headingRow.appendChild(headingCell);
        fragment.appendChild(headingRow);
        group.headingId = headingId;
        group.rows.forEach(function(entry) {
          entry.row.setAttribute('aria-labelledby', headingId);
          fragment.appendChild(entry.row);
        });
      });

      if (fragment.childNodes.length) {
        tbody.appendChild(fragment);
      }

      if (hiddenTemplate) {
        tbody.appendChild(hiddenTemplate);
      }

      var costContainer = scope.querySelector('#cost-by-category');
      if (costContainer) {
        while (costContainer.firstChild) {
          costContainer.removeChild(costContainer.firstChild);
        }
        if (!groups.length) {
          var emptyMessage = document.createElement('p');
          emptyMessage.className = 'text-sm text-gray-500';
          emptyMessage.textContent = 'Add items to see category totals.';
          costContainer.appendChild(emptyMessage);
        } else {
          groups.forEach(function(group) {
            var item = document.createElement('div');
            item.className = 'flex items-center justify-between gap-2';
            item.setAttribute('role', 'group');
            if (group.headingId) {
              item.setAttribute('aria-labelledby', group.headingId);
            }
            var label = document.createElement('span');
            label.className = 'text-gray-600';
            label.textContent = group.label;
            var value = document.createElement('span');
            value.className = 'font-medium text-bodyText';
            value.textContent = group.total.toFixed(2);
            item.appendChild(label);
            item.appendChild(value);
            costContainer.appendChild(item);
          });
        }
      }

      var totalCostEl = scope.querySelector('#recipe-total-cost');
      if (totalCostEl) {
        totalCostEl.textContent = totalCost.toFixed(2);
      }

      var marginInput = scope.querySelector('#recipe-margin');
      if (marginInput && !marginInput.dataset.recipeMarginBound) {
        var marginHandler = function() {
          window.updateRecipeCosts(scope);
        };
        marginInput.addEventListener('input', marginHandler);
        marginInput.addEventListener('change', marginHandler);
        marginInput.dataset.recipeMarginBound = '1';
      }

      var suggestedEl = scope.querySelector('#recipe-suggested-price');
      var marginValue = marginInput ? parseFloat(marginInput.value || '0') : 0;
      var clampedMargin = clampMarginValue(marginValue);
      if (marginInput && marginValue !== clampedMargin) {
        marginInput.value = clampedMargin;
      }
      var marginDecimal = clampedMargin / 100;
      var suggested = totalCost;
      if (marginDecimal > 0 && marginDecimal < 0.999) {
        suggested = totalCost / (1 - marginDecimal);
      }
      if (suggestedEl) {
        suggestedEl.textContent = Number.isFinite(suggested)
          ? suggested.toFixed(2)
          : totalCost.toFixed(2);
      }

      if (shouldRestoreFocus && activeElement) {
        var isConnected = typeof activeElement.isConnected === 'boolean'
          ? activeElement.isConnected
          : document.contains(activeElement);
        if (isConnected) {
          if (document.activeElement !== activeElement) {
            try { activeElement.focus({ preventScroll: true }); } catch (_) {}
          }
          if (hasSelection && typeof activeElement.setSelectionRange === 'function') {
            try {
              if (selectionDirection) {
                activeElement.setSelectionRange(selectionStart, selectionEnd, selectionDirection);
              } else {
                activeElement.setSelectionRange(selectionStart, selectionEnd);
              }
            } catch (_) {}
          }
        }
      }

      table.dataset.recipeGroupingApplied = groups.length ? '1' : '0';
    } catch (err) {
      console.error('updateRecipeCosts failed:', err);
    }
  };
  
  // Expose globally with the correct name for modal.js
  window.initRecipeComponentsTable = initRecipeComponentsTable;
  window.initRecipeItemsTable = initRecipeComponentsTable; // Keep backward compatibility
  
  // Add a simple debug function
  window.testRecipeJS = function() {
    console.log('🧪 Testing recipe JS...');
    console.log('- Add button exists:', !!document.getElementById('add-row'));
    console.log('- Table exists:', !!document.getElementById('items-table'));
    console.log('- TOTAL_FORMS exists:', !!document.getElementById('id_items-TOTAL_FORMS'));
    console.log('- Empty row exists:', !!document.getElementById('items-empty-row'));
    
    var addBtn = document.getElementById('add-row');
    if (addBtn) {
      addBtn.style.backgroundColor = 'lime';
      addBtn.style.color = 'black';
      addBtn.title = 'FOUND BY TEST';
      console.log('✅ Add button found and highlighted!');
      
      // Try to manually add a click listener
      addBtn.onclick = function() {
        alert('Manual click handler works!');
        console.log('🎯 Manual click triggered!');
      };
      console.log('🔗 Manual click handler attached');
    } else {
      console.log('❌ Add button not found!');
    }
    
    // Run dropdown debug
    window.debugRecipeDropdowns();
  };
  
  // Add a function to debug dropdown state
  window.debugRecipeDropdowns = function() {
    console.log('🔍 === DROPDOWN DEBUG === 🔍');
    var allSelects = document.querySelectorAll('select[id*="item"]');
    console.log('Total item selects found:', allSelects.length);
    
    allSelects.forEach(function(select, idx) {
      var hasPredictiveClass = select.classList.contains('predictive');
      var hasTextInput = !!document.getElementById(select.id + '_text');
      var isUpgraded = select.dataset.predictiveUpgraded === '1';
      
      console.log(`Select ${idx + 1}:`, {
        id: select.id,
        hasPredictiveClass: hasPredictiveClass,
        hasTextInput: hasTextInput,
        isUpgraded: isUpgraded,
        visible: !select.style.display || select.style.display !== 'none'
      });
    });
    
    var allTextInputs = document.querySelectorAll('input[id*="item_text"]');
    console.log('Predictive text inputs found:', allTextInputs.length);
    
    allTextInputs.forEach(function(input, idx) {
      console.log(`Text input ${idx + 1}:`, {
        id: input.id,
        visible: input.offsetParent !== null
      });
    });
  };

  // Add a function to manually trigger adding a row
  window.manualAddRow = function() {
    console.log('🔧 Manual add row triggered...');
    var table = document.querySelector('#items-table');
    var root = table ? (table.closest('.drawer-panel') || table.closest('[data-modal-root]') || document) : document;
    var totalForms = root.querySelector('#id_items-TOTAL_FORMS');
    var emptyRow = root.querySelector('#items-empty-row');
    
    if (!totalForms || !emptyRow || !table) {
      console.error('Missing required elements:', {
        totalForms: !!totalForms,
        emptyRow: !!emptyRow,
        table: !!table
      });
      return;
    }
    
    var tbody = table.querySelector('tbody');
    addNewRow(table, tbody, totalForms, emptyRow);
  };
  
  // No global auto-init; templates call init with a proper root.
  console.log('� recipe-components.js loaded (manual init only)');
})();