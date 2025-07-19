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
            // Sync sites first
            await this.syncSites(false);
            
            // Then sync vouchers for current site
            await this.syncVouchers(false);
            
            this.syncErrors = 0;
            this.lastSyncTime = Date.now();
            
            if (manual) {
                this.showNotification('Sincronização concluída com sucesso', 'success');
            }
            
        } catch (error) {
            console.error('Erro na sincronização:', error);
            this.syncErrors++;
            
            if (manual || this.syncErrors >= this.maxErrors) {
                this.showNotification('Erro na sincronização com Omada Controller', 'danger');
            }
            
            // Disable auto-sync after too many errors
            if (this.syncErrors >= this.maxErrors) {
                this.isEnabled = false;
                localStorage.setItem('autoSync', 'false');
                this.stopAutoSync();
            }
        } finally {
            this.isSyncing = false;
            this.updateSyncStatus();
        }
    }
    
    async syncSites(showNotification = true) {
        try {
            const response = await fetch('/api/sync-sites', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
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
            if (!currentSite) return;
            
            const response = await fetch(`/api/sync-vouchers/${currentSite}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
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
    
    getCurrentSiteId() {
        // Try to get site ID from page data or URL
        const siteSelect = document.getElementById('site_id');
        if (siteSelect) {
            return siteSelect.value;
        }
        
        // Try to get from URL path
        const pathMatch = window.location.pathname.match(/\/site\/(\d+)/);
        if (pathMatch) {
            return pathMatch[1];
        }
        
        // Try to get from session storage
        return sessionStorage.getItem('currentSiteId');
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
        window.autoSyncManager = new AutoSyncManager();
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