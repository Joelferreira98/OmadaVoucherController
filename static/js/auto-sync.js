// Auto-sync system for Omada Controller integration
class AutoSyncManager {
    constructor() {
        this.syncInterval = 60000; // 1 minute
        this.syncIntervalId = null;
        this.isEnabled = true;
        this.isSyncing = false;
        this.lastSyncTime = null;
        this.syncErrors = 0;
        this.maxErrors = 5;
        
        this.init();
    }
    
    init() {
        // Load sync preference from localStorage
        this.isEnabled = localStorage.getItem('autoSync') !== 'false';
        
        // Create sync status indicator
        this.createSyncIndicator();
        
        // Start auto-sync if enabled
        if (this.isEnabled) {
            this.startAutoSync();
        }
        
        // Update indicator
        this.updateSyncStatus();
    }
    
    createSyncIndicator() {
        // Create sync status container
        const syncContainer = document.createElement('div');
        syncContainer.id = 'sync-status-container';
        syncContainer.className = 'position-fixed';
        syncContainer.style.cssText = 'top: 10px; right: 80px; z-index: 1040;';
        
        syncContainer.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" id="syncDropdown" data-bs-toggle="dropdown">
                        <i class="fas fa-sync-alt" id="syncIcon"></i>
                        <span id="syncText">Sync</span>
                    </button>
                    <ul class="dropdown-menu" aria-labelledby="syncDropdown">
                        <li>
                            <h6 class="dropdown-header">Sincronização Automática</h6>
                        </li>
                        <li>
                            <a class="dropdown-item" href="#" onclick="autoSyncManager.toggleAutoSync()">
                                <i class="fas fa-power-off me-2"></i>
                                <span id="autoSyncToggleText">Desativar</span>
                            </a>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <a class="dropdown-item" href="#" onclick="autoSyncManager.syncNow()">
                                <i class="fas fa-sync me-2"></i>Sincronizar Agora
                            </a>
                        </li>
                        <li>
                            <a class="dropdown-item" href="#" onclick="autoSyncManager.syncSites()">
                                <i class="fas fa-building me-2"></i>Sincronizar Sites
                            </a>
                        </li>
                        <li>
                            <a class="dropdown-item" href="#" onclick="autoSyncManager.syncVouchers()">
                                <i class="fas fa-ticket-alt me-2"></i>Sincronizar Vouchers
                            </a>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        <li>
                            <span class="dropdown-item-text">
                                <small class="text-muted">
                                    Última sync: <span id="lastSyncDisplay">Nunca</span>
                                </small>
                            </span>
                        </li>
                    </ul>
                </div>
            </div>
        `;
        
        document.body.appendChild(syncContainer);
    }
    
    updateSyncStatus() {
        const syncIcon = document.getElementById('syncIcon');
        const syncText = document.getElementById('syncText');
        const autoSyncToggleText = document.getElementById('autoSyncToggleText');
        const lastSyncDisplay = document.getElementById('lastSyncDisplay');
        
        if (!syncIcon) return;
        
        // Update auto-sync toggle text
        if (autoSyncToggleText) {
            autoSyncToggleText.textContent = this.isEnabled ? 'Desativar' : 'Ativar';
        }
        
        // Update last sync time
        if (lastSyncDisplay && this.lastSyncTime) {
            const timeDiff = Date.now() - this.lastSyncTime;
            const minutes = Math.floor(timeDiff / 60000);
            if (minutes < 1) {
                lastSyncDisplay.textContent = 'Agora mesmo';
            } else if (minutes === 1) {
                lastSyncDisplay.textContent = '1 minuto atrás';
            } else {
                lastSyncDisplay.textContent = `${minutes} minutos atrás`;
            }
        }
        
        // Update status based on current state
        if (this.isSyncing) {
            syncIcon.className = 'fas fa-sync-alt fa-spin';
            syncText.textContent = 'Sincronizando...';
            syncIcon.parentElement.classList.add('text-primary');
        } else if (this.isEnabled) {
            syncIcon.className = 'fas fa-sync-alt';
            syncText.textContent = 'Sync Ativo';
            syncIcon.parentElement.classList.remove('text-primary', 'text-danger');
            syncIcon.parentElement.classList.add('text-success');
        } else {
            syncIcon.className = 'fas fa-sync-alt';
            syncText.textContent = 'Sync Pausado';
            syncIcon.parentElement.classList.remove('text-primary', 'text-success');
            syncIcon.parentElement.classList.add('text-muted');
        }
        
        // Show error state if too many errors
        if (this.syncErrors >= this.maxErrors) {
            syncIcon.parentElement.classList.remove('text-success', 'text-primary');
            syncIcon.parentElement.classList.add('text-danger');
            syncText.textContent = 'Erro de Sync';
        }
    }
    
    startAutoSync() {
        if (this.syncIntervalId) {
            clearInterval(this.syncIntervalId);
        }
        
        this.syncIntervalId = setInterval(() => {
            this.performSync();
        }, this.syncInterval);
        
        console.log('Auto-sync iniciado (1 minuto)');
    }
    
    stopAutoSync() {
        if (this.syncIntervalId) {
            clearInterval(this.syncIntervalId);
            this.syncIntervalId = null;
        }
        
        console.log('Auto-sync parado');
    }
    
    toggleAutoSync() {
        this.isEnabled = !this.isEnabled;
        localStorage.setItem('autoSync', this.isEnabled.toString());
        
        if (this.isEnabled) {
            this.startAutoSync();
            this.showNotification('Sincronização automática ativada', 'success');
        } else {
            this.stopAutoSync();
            this.showNotification('Sincronização automática desativada', 'warning');
        }
        
        this.updateSyncStatus();
    }
    
    async syncNow() {
        await this.performSync(true);
    }
    
    async performSync(manual = false) {
        if (this.isSyncing) return;
        
        this.isSyncing = true;
        this.updateSyncStatus();
        
        try {
            let syncCount = 0;
            
            // Only sync sites if user is master
            if (this.getUserType() === 'master') {
                try {
                    const sitesResult = await this.syncSites(false);
                    syncCount += sitesResult.count || 0;
                } catch (error) {
                    console.log('Sites sync skipped or failed:', error.message);
                }
            }
            
            // Try to sync vouchers for current site (only if we have a site)
            const currentSite = this.getCurrentSiteId();
            if (currentSite) {
                try {
                    const vouchersResult = await this.syncVouchers(false);
                    syncCount += vouchersResult.count || 0;
                } catch (error) {
                    console.log('Vouchers sync skipped or failed:', error.message);
                }
            } else {
                console.log('No site selected, skipping voucher sync');
            }
            
            this.syncErrors = 0;
            this.lastSyncTime = Date.now();
            
            if (manual) {
                if (syncCount > 0) {
                    this.showNotification(`Sincronização concluída: ${syncCount} itens`, 'success');
                } else {
                    this.showNotification('Sincronização concluída: Nenhum item para sincronizar', 'info');
                }
            }
            
        } catch (error) {
            console.error('Erro na sincronização:', error);
            this.syncErrors++;
            
            if (manual) {
                this.showNotification('Erro na sincronização com Omada Controller', 'danger');
            }
            
            // Only show notification after several consecutive errors
            if (this.syncErrors >= 3 && manual) {
                this.showNotification('Múltiplos erros na sincronização', 'warning');
            }
            
            // Disable auto-sync after too many errors
            if (this.syncErrors >= this.maxErrors) {
                this.isEnabled = false;
                localStorage.setItem('autoSync', 'false');
                this.stopAutoSync();
                this.showNotification('Auto-sync desativado devido a muitos erros', 'warning');
            }
        } finally {
            this.isSyncing = false;
            this.updateSyncStatus();
        }
    }
    
    getUserType() {
        // Try to get user type from page data
        const userTypeElement = document.querySelector('[data-user-type]');
        if (userTypeElement) {
            return userTypeElement.getAttribute('data-user-type');
        }
        
        // Try to get from sidebar class or other indicators
        if (document.querySelector('.sidebar [href*="master"]')) {
            return 'master';
        } else if (document.querySelector('.sidebar [href*="admin"]')) {
            return 'admin';
        } else if (document.querySelector('.sidebar [href*="vendor"]')) {
            return 'vendor';
        }
        
        return 'unknown';
    }
    
    async syncSites(showNotification = true) {
        try {
            const csrfToken = this.getCSRFToken();
            const response = await fetch('/api/sync-sites', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                credentials: 'same-origin',
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            
            if (showNotification) {
                this.showNotification(`Sites sincronizados: ${result.count || 0}`, 'success');
            }
            
            return result;
        } catch (error) {
            console.error('Erro ao sincronizar sites:', error);
            if (showNotification) {
                this.showNotification('Erro ao sincronizar sites', 'danger');
            }
            throw error;
        }
    }
    
    async syncVouchers(showNotification = true) {
        try {
            // Get current site ID from page or session
            const currentSite = this.getCurrentSiteId();
            if (!currentSite) {
                console.log('No site ID found, skipping voucher sync');
                return { count: 0 };
            }
            
            const csrfToken = this.getCSRFToken();
            const response = await fetch(`/api/sync-vouchers/${currentSite}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                credentials: 'same-origin',
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            
            const result = await response.json();
            
            if (showNotification) {
                this.showNotification(`Vouchers sincronizados: ${result.count || 0}`, 'success');
            }
            
            // Refresh current page if showing vouchers
            if (window.location.pathname.includes('voucher')) {
                this.refreshVoucherData();
            }
            
            return result;
        } catch (error) {
            console.error('Erro ao sincronizar vouchers:', error);
            if (showNotification) {
                this.showNotification('Erro ao sincronizar vouchers', 'danger');
            }
            throw error;
        }
    }
    
    getCSRFToken() {
        // Try to get CSRF token from meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            return csrfMeta.getAttribute('content');
        }
        
        // Try to get from form hidden input
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        
        // Try to get from cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrf_token') {
                return value;
            }
        }
        
        return '';
    }
    
    getCurrentSiteId() {
        // Try to get site ID from page data or URL
        const siteSelect = document.getElementById('site_id');
        if (siteSelect && siteSelect.value && siteSelect.value !== '') {
            return siteSelect.value;
        }
        
        // Try to get from URL path
        const pathMatch = window.location.pathname.match(/\/site\/(\d+)/);
        if (pathMatch) {
            return pathMatch[1];
        }
        
        // Try to get from admin/vendor dashboard path patterns
        const adminMatch = window.location.pathname.match(/\/admin(?:\/(\d+))?/);
        if (adminMatch && adminMatch[1]) {
            return adminMatch[1];
        }
        
        const vendorMatch = window.location.pathname.match(/\/vendor(?:\/(\d+))?/);
        if (vendorMatch && vendorMatch[1]) {
            return vendorMatch[1];
        }
        
        // Try to get from session storage (check if available)
        if (typeof sessionStorage !== 'undefined') {
            const sessionSite = sessionStorage.getItem('currentSiteId');
            if (sessionSite && sessionSite !== 'null') {
                return sessionSite;
            }
        }
        
        // Try to get from data attributes
        const siteData = document.querySelector('[data-site-id]');
        if (siteData) {
            return siteData.getAttribute('data-site-id');
        }
        
        // Try to get from current page context
        const pageContext = document.querySelector('.current-site-id');
        if (pageContext) {
            return pageContext.textContent || pageContext.value;
        }
        
        return null;
    }
    
    refreshVoucherData() {
        // Refresh voucher tables and charts if present
        const voucherTable = document.querySelector('.table');
        if (voucherTable) {
            // Add subtle loading indication
            voucherTable.style.opacity = '0.7';
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }
    
    showNotification(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast position-fixed`;
        toast.style.cssText = 'bottom: 20px; right: 20px; z-index: 1060;';
        
        const iconMap = {
            'success': 'fa-check-circle text-success',
            'danger': 'fa-exclamation-circle text-danger',
            'warning': 'fa-exclamation-triangle text-warning',
            'info': 'fa-info-circle text-info'
        };
        
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas ${iconMap[type] || iconMap.info} me-2"></i>
                <strong class="me-auto">Sincronização</strong>
                <small class="text-muted">agora</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        // Remove toast after showing
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }
}

// Initialize auto-sync when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if user is authenticated
    if (document.body.querySelector('.sidebar')) {
        // Small delay to ensure page is fully loaded
        setTimeout(() => {
            window.autoSyncManager = new AutoSyncManager();
        }, 1000);
    }
});

// Handle visibility change to pause/resume sync
document.addEventListener('visibilitychange', function() {
    if (window.autoSyncManager) {
        if (document.hidden) {
            // Pause sync when tab is hidden
            window.autoSyncManager.stopAutoSync();
        } else {
            // Resume sync when tab is visible
            if (window.autoSyncManager.isEnabled) {
                window.autoSyncManager.startAutoSync();
            }
        }
    }
});