// PWA Installation and Management
class PWAManager {
    constructor() {
        this.deferredPrompt = null;
        this.isInstalled = false;
        this.init();
    }

    init() {
        // Register service worker
        this.registerServiceWorker();
        
        // Setup install prompt
        this.setupInstallPrompt();
        
        // Check if already installed
        this.checkInstallStatus();
        
        // Setup notification permission
        this.setupNotifications();
    }

    async registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('Service Worker registered successfully:', registration);
                
                // Update on refresh
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            // Show update available message
                            this.showUpdateAvailable();
                        }
                    });
                });
            } catch (error) {
                console.error('Service Worker registration failed:', error);
            }
        }
    }

    setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallButton();
        });

        window.addEventListener('appinstalled', () => {
            this.isInstalled = true;
            this.hideInstallButton();
            this.showInstalledMessage();
        });
    }

    checkInstallStatus() {
        // Check if running as PWA
        if (window.matchMedia('(display-mode: standalone)').matches || 
            window.navigator.standalone === true) {
            this.isInstalled = true;
            this.hideInstallButton();
        }
    }

    async installApp() {
        if (!this.deferredPrompt) return;

        this.deferredPrompt.prompt();
        const { outcome } = await this.deferredPrompt.userChoice;
        
        if (outcome === 'accepted') {
            console.log('User accepted the install prompt');
        } else {
            console.log('User dismissed the install prompt');
        }
        
        this.deferredPrompt = null;
    }

    showInstallButton() {
        let installButton = document.getElementById('pwa-install-btn');
        if (!installButton) {
            installButton = document.createElement('button');
            installButton.id = 'pwa-install-btn';
            installButton.className = 'btn btn-primary btn-sm position-fixed';
            installButton.style.cssText = 'bottom: 20px; right: 20px; z-index: 1051; border-radius: 25px;';
            installButton.innerHTML = '<i class="fas fa-download me-2"></i>Instalar App';
            installButton.onclick = () => this.installApp();
            document.body.appendChild(installButton);
        }
        installButton.style.display = 'block';
    }

    hideInstallButton() {
        const installButton = document.getElementById('pwa-install-btn');
        if (installButton) {
            installButton.style.display = 'none';
        }
    }

    showInstalledMessage() {
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed';
        toast.style.cssText = 'bottom: 20px; right: 20px; z-index: 1052;';
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas fa-check-circle text-success me-2"></i>
                <strong class="me-auto">Aplicativo Instalado</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                Sistema de Vouchers foi instalado com sucesso!
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 5000);
    }

    showUpdateAvailable() {
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed';
        toast.style.cssText = 'bottom: 20px; right: 20px; z-index: 1052;';
        toast.innerHTML = `
            <div class="toast-header">
                <i class="fas fa-sync-alt text-info me-2"></i>
                <strong class="me-auto">Atualização Disponível</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                Uma nova versão está disponível. Recarregue a página para atualizar.
                <div class="mt-2">
                    <button class="btn btn-sm btn-primary" onclick="window.location.reload()">
                        Atualizar Agora
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { autohide: false });
        bsToast.show();
    }

    async setupNotifications() {
        if ('Notification' in window) {
            const permission = await Notification.requestPermission();
            if (permission === 'granted') {
                console.log('Notification permission granted');
            }
        }
    }

    // Utility method to send notifications
    sendNotification(title, options = {}) {
        if ('serviceWorker' in navigator && 'Notification' in window) {
            if (Notification.permission === 'granted') {
                navigator.serviceWorker.ready.then(function(registration) {
                    registration.showNotification(title, {
                        icon: '/static/icons/icon-192x192.png',
                        badge: '/static/icons/icon-72x72.png',
                        ...options
                    });
                });
            }
        }
    }
}

// Initialize PWA when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.pwaManager = new PWAManager();
});

// Offline detection
window.addEventListener('online', function() {
    console.log('Back online');
    document.body.classList.remove('offline');
});

window.addEventListener('offline', function() {
    console.log('Gone offline');
    document.body.classList.add('offline');
});