// PWA functionality
class PWAManager {
  constructor() {
    this.deferredPrompt = null;
    this.isInstalled = false;
    this.isOnline = navigator.onLine;
    
    this.init();
  }

  async init() {
    // Register service worker
    await this.registerServiceWorker();
    
    // Setup install prompt
    this.setupInstallPrompt();
    
    // Setup online/offline detection
    this.setupNetworkDetection();
    
    // Setup notifications
    this.setupNotifications();
    
    // Check if already installed
    this.checkInstallStatus();
    
    // Setup update detection
    this.setupUpdateDetection();
  }

  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/static/sw.js');
        console.log('Service Worker registered successfully:', registration);
        
        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.showUpdateNotification();
            }
          });
        });
        
        return registration;
      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  setupInstallPrompt() {
    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallButton();
    });

    // Listen for app installed event
    window.addEventListener('appinstalled', () => {
      console.log('PWA was installed');
      this.isInstalled = true;
      this.hideInstallButton();
      this.showInstalledNotification();
    });
  }

  setupNetworkDetection() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.hideOfflineIndicator();
      this.showOnlineNotification();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.showOfflineIndicator();
      this.showOfflineNotification();
    });

    // Initial state
    if (!this.isOnline) {
      this.showOfflineIndicator();
    }
  }

  async setupNotifications() {
    if ('Notification' in window) {
      if (Notification.permission === 'default') {
        const permission = await Notification.requestPermission();
        console.log('Notification permission:', permission);
      }
    }
  }

  checkInstallStatus() {
    // Check if running in standalone mode
    if (window.matchMedia('(display-mode: standalone)').matches) {
      this.isInstalled = true;
      console.log('Running as installed PWA');
    }
  }

  setupUpdateDetection() {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.location.reload();
      });
    }
  }

  // UI Methods
  showInstallButton() {
    let installBtn = document.getElementById('pwa-install-btn');
    if (!installBtn) {
      installBtn = document.createElement('button');
      installBtn.id = 'pwa-install-btn';
      installBtn.className = 'btn btn-primary btn-sm position-fixed';
      installBtn.style.cssText = `
        bottom: 20px;
        right: 20px;
        z-index: 1050;
        border-radius: 50px;
        padding: 12px 20px;
        font-size: 14px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0,123,255,0.3);
        border: none;
        background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
        transition: all 0.3s ease;
      `;
      installBtn.innerHTML = '<i class="fas fa-download me-2"></i>Instalar App';
      
      installBtn.addEventListener('click', () => this.promptInstall());
      installBtn.addEventListener('mouseenter', () => {
        installBtn.style.transform = 'translateY(-2px)';
        installBtn.style.boxShadow = '0 6px 16px rgba(0,123,255,0.4)';
      });
      installBtn.addEventListener('mouseleave', () => {
        installBtn.style.transform = 'translateY(0)';
        installBtn.style.boxShadow = '0 4px 12px rgba(0,123,255,0.3)';
      });
      
      document.body.appendChild(installBtn);
    }
    installBtn.style.display = 'block';
  }

  hideInstallButton() {
    const installBtn = document.getElementById('pwa-install-btn');
    if (installBtn) {
      installBtn.style.display = 'none';
    }
  }

  async promptInstall() {
    if (this.deferredPrompt) {
      this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;
      console.log('Install prompt outcome:', outcome);
      this.deferredPrompt = null;
      this.hideInstallButton();
    }
  }

  showOfflineIndicator() {
    let indicator = document.getElementById('offline-indicator');
    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'offline-indicator';
      indicator.className = 'alert alert-warning position-fixed';
      indicator.style.cssText = `
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 1060;
        margin: 0;
        padding: 8px 16px;
        font-size: 14px;
        border-radius: 25px;
        border: none;
        background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
        color: #000;
        box-shadow: 0 2px 8px rgba(255,193,7,0.3);
      `;
      indicator.innerHTML = '<i class="fas fa-wifi-slash me-2"></i>Modo Offline';
      document.body.appendChild(indicator);
    }
    indicator.style.display = 'block';
  }

  hideOfflineIndicator() {
    const indicator = document.getElementById('offline-indicator');
    if (indicator) {
      indicator.style.display = 'none';
    }
  }

  showUpdateNotification() {
    this.showNotification('Atualização Disponível', {
      body: 'Uma nova versão do aplicativo está disponível. Recarregue a página para atualizar.',
      icon: '/static/icons/icon-192x192.png',
      actions: [
        { action: 'update', title: 'Atualizar' },
        { action: 'later', title: 'Mais Tarde' }
      ]
    });
  }

  showInstalledNotification() {
    this.showNotification('App Instalado', {
      body: 'O Sistema de Vouchers foi instalado com sucesso!',
      icon: '/static/icons/icon-192x192.png'
    });
  }

  showOnlineNotification() {
    this.showNotification('Conectado', {
      body: 'Conexão com a internet restaurada.',
      icon: '/static/icons/icon-192x192.png'
    });
  }

  showOfflineNotification() {
    this.showNotification('Offline', {
      body: 'Você está offline. Algumas funcionalidades podem estar limitadas.',
      icon: '/static/icons/icon-192x192.png'
    });
  }

  showNotification(title, options = {}) {
    if ('Notification' in window && Notification.permission === 'granted') {
      const notification = new Notification(title, {
        badge: '/static/icons/badge-72x72.png',
        vibrate: [100, 50, 100],
        ...options
      });

      notification.addEventListener('click', () => {
        window.focus();
        notification.close();
      });

      // Auto close after 5 seconds
      setTimeout(() => notification.close(), 5000);
    }
  }

  // Utility methods
  isOnlineStatus() {
    return this.isOnline;
  }

  isInstalledStatus() {
    return this.isInstalled;
  }

  // Background sync for offline voucher creation
  async addToSync(data) {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        // Store data in IndexedDB for background sync
        await this.storeForSync(data);
        
        // Register background sync
        const registration = await navigator.serviceWorker.ready;
        await registration.sync.register('background-sync-vouchers');
        
        console.log('Background sync registered');
      } catch (error) {
        console.error('Background sync registration failed:', error);
      }
    }
  }

  async storeForSync(data) {
    // Implementation for storing data in IndexedDB
    console.log('Storing data for background sync:', data);
  }
}

// Initialize PWA when page loads
document.addEventListener('DOMContentLoaded', () => {
  window.pwaManager = new PWAManager();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
  module.exports = PWAManager;
}