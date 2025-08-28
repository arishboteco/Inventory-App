/**
 * Smart Item Management - Enhanced navigation and workflow
 */

class SmartItemManager {
    constructor() {
        this.initializeQuickActions();
        this.initializeSmartNavigation();
        this.initializeDropdowns();
    }

    initializeQuickActions() {
        // Handle quick action clicks
        document.addEventListener('click', (e) => {
            const action = e.target.dataset.action;
            if (action) {
                e.preventDefault();
                this.handleQuickAction(action, e.target);
            }
        });
    }

    handleQuickAction(action, element) {
        const itemId = element.dataset.itemId;
        const itemName = element.dataset.itemName;

        switch (action) {
            case 'export':
                this.exportItemData(itemId);
                break;
            case 'qr-code':
                this.generateQRCode(itemName, itemId);
                break;
        }
    }

    async exportItemData(itemId) {
        try {
            const response = await fetch(`/items/${itemId}/export/`);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `item_${itemId}_data.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            window.notifications.showToast('Item data exported successfully!', 'success');
        } catch (error) {
            console.error('Export failed:', error);
            window.notifications.showToast('Export failed. Please try again.', 'error');
        }
    }

    generateQRCode(itemName, itemId) {
        const qrData = `${window.location.origin}/items/${itemId}/`;
        const qrContainer = document.createElement('div');
        qrContainer.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        qrContainer.innerHTML = `
            <div class="bg-white p-6 rounded-lg max-w-sm w-full mx-4">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">QR Code for ${itemName}</h3>
                    <button class="text-gray-500 hover:text-gray-700" onclick="this.closest('.fixed').remove()">✕</button>
                </div>
                <div id="qr-code-canvas" class="flex justify-center mb-4"></div>
                <p class="text-sm text-gray-600 text-center">Scan to view item details</p>
                <div class="mt-4 flex space-x-2">
                    <button onclick="this.closest('.fixed').remove()" class="flex-1 btn-secondary">Close</button>
                    <button onclick="window.print()" class="flex-1 btn-primary">Print</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(qrContainer);
        
        // Generate QR code (you would need to include a QR code library)
        const canvas = document.getElementById('qr-code-canvas');
        canvas.innerHTML = `<div class="w-32 h-32 bg-gray-200 flex items-center justify-center">QR Code<br>for Item ${itemId}</div>`;
        
        window.notifications.showToast('QR Code generated!', 'success');
    }

    initializeSmartNavigation() {
        // Smart back navigation
        const backButtons = document.querySelectorAll('[href*="items"]');
        backButtons.forEach(button => {
            if (button.textContent.includes('Back')) {
                button.addEventListener('click', (e) => {
                    // Preserve filters if coming from list
                    const referrer = document.referrer;
                    if (referrer && referrer.includes('/items/')) {
                        e.preventDefault();
                        window.history.back();
                    }
                });
            }
        });

        // Smart form submissions
        const forms = document.querySelectorAll('form[hx-post]');
        forms.forEach(form => {
            form.addEventListener('htmx:afterRequest', (e) => {
                if (e.detail.successful) {
                    window.notifications.showToast('Action completed successfully!', 'success');
                    
                    // Smart redirect logic
                    if (e.detail.xhr.responseURL) {
                        const url = new URL(e.detail.xhr.responseURL);
                        if (url.pathname.includes('/items/')) {
                            setTimeout(() => {
                                window.location.href = '/items/';
                            }, 1000);
                        }
                    }
                }
            });
        });
    }

    initializeDropdowns() {
        document.addEventListener('click', (e) => {
            const toggle = e.target.closest('.dropdown-toggle');
            if (toggle) {
                e.preventDefault();
                const dropdownId = toggle.dataset.dropdown;
                const dropdown = document.getElementById(dropdownId);
                
                // Close other dropdowns
                document.querySelectorAll('.dropdown-menu:not(.hidden)').forEach(menu => {
                    if (menu.id !== dropdownId) {
                        menu.classList.add('hidden');
                    }
                });
                
                // Toggle current dropdown
                dropdown.classList.toggle('hidden');
            } else {
                // Close dropdowns when clicking outside
                if (!e.target.closest('.dropdown')) {
                    document.querySelectorAll('.dropdown-menu').forEach(menu => {
                        menu.classList.add('hidden');
                    });
                }
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new SmartItemManager();
});

// Global functions for backward compatibility
window.exportItemData = function(itemId) {
    const manager = new SmartItemManager();
    manager.exportItemData(itemId);
};

window.generateQRCode = function(itemName, itemId) {
    const manager = new SmartItemManager();
    manager.generateQRCode(itemName, itemId);
};
