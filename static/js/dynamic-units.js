/**
 * Dynamic unit selection functionality
 * Updates purchase units based on selected base unit
 */

function updatePurchaseUnits(baseUnit) {
    console.log('updatePurchaseUnits called with:', baseUnit);
    
    const purchaseUnitSelect = document.querySelector('select[data-field="purchase_unit"]');
    console.log('Purchase unit select found:', purchaseUnitSelect);
    
    if (!purchaseUnitSelect) {
        console.error('Purchase unit select not found');
        return;
    }
    
    // Clear current options
    purchaseUnitSelect.innerHTML = '<option value="">Loading...</option>';
    
    // If no base unit selected, show all purchase units
    const url = `/items/purchase-units/?base_unit=${encodeURIComponent(baseUnit || '')}`;
    console.log('Fetching from URL:', url);
    
    fetch(url)
        .then(response => {
            console.log('Response status:', response.status);
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            // Clear and populate options
            purchaseUnitSelect.innerHTML = '<option value="">Select Purchase Unit</option>';
            
            data.purchase_units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit[0];
                option.textContent = unit[1];
                purchaseUnitSelect.appendChild(option);
            });
            console.log('Options updated successfully');
        })
        .catch(error => {
            console.error('Error loading purchase units:', error);
            purchaseUnitSelect.innerHTML = '<option value="">Error loading units</option>';
        });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, setting up dynamic units');
    
    const baseUnitSelect = document.querySelector('select[data-field="base_unit"]');
    console.log('Base unit select found:', baseUnitSelect);
    
    if (baseUnitSelect) {
        console.log('Setting up change handler');
        // Set up change handler
        baseUnitSelect.addEventListener('change', function() {
            console.log('Base unit changed to:', this.value);
            updatePurchaseUnits(this.value);
        });
        
        // Load initial purchase units if base unit is already selected
        if (baseUnitSelect.value) {
            console.log('Initial base unit value:', baseUnitSelect.value);
            updatePurchaseUnits(baseUnitSelect.value);
        }
    } else {
        console.error('Base unit select not found!');
    }
});
