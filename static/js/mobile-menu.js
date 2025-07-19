// Mobile Menu Management
class MobileMenu {
    constructor() {
        this.sidebar = document.getElementById('sidebar');
        this.overlay = document.getElementById('mobileSidebarOverlay');
        this.toggle = document.getElementById('mobileMenuToggle');
        this.isOpen = false;
        
        this.init();
    }
    
    init() {
        if (!this.toggle || !this.sidebar || !this.overlay) return;
        
        // Toggle menu on button click
        this.toggle.addEventListener('click', () => {
            this.toggleMenu();
        });
        
        // Close menu on overlay click
        this.overlay.addEventListener('click', () => {
            this.closeMenu();
        });
        
        // Close menu on navigation link click (mobile)
        const navLinks = this.sidebar.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    this.closeMenu();
                }
            });
        });
        
        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                this.closeMenu();
            }
        });
        
        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.closeMenu();
            }
        });
        
        // Prevent body scroll when menu is open
        this.preventBodyScroll();
    }
    
    toggleMenu() {
        if (this.isOpen) {
            this.closeMenu();
        } else {
            this.openMenu();
        }
    }
    
    openMenu() {
        this.sidebar.classList.add('show');
        this.overlay.classList.add('show');
        this.toggle.innerHTML = '<i class="fas fa-times"></i>';
        this.isOpen = true;
        
        // Prevent body scroll
        document.body.style.overflow = 'hidden';
        
        // Focus management for accessibility
        this.sidebar.setAttribute('aria-hidden', 'false');
        this.sidebar.focus();
    }
    
    closeMenu() {
        this.sidebar.classList.remove('show');
        this.overlay.classList.remove('show');
        this.toggle.innerHTML = '<i class="fas fa-bars"></i>';
        this.isOpen = false;
        
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Focus management for accessibility
        this.sidebar.setAttribute('aria-hidden', 'true');
        this.toggle.focus();
    }
    
    preventBodyScroll() {
        // Prevent scroll when touching the sidebar
        this.sidebar.addEventListener('touchmove', (e) => {
            e.stopPropagation();
        });
        
        // Prevent background scroll on iOS
        this.overlay.addEventListener('touchmove', (e) => {
            e.preventDefault();
        });
    }
}

// Initialize mobile menu when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.mobileMenu = new MobileMenu();
});

// Handle orientation change
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        if (window.mobileMenu && window.innerWidth > 768) {
            window.mobileMenu.closeMenu();
        }
    }, 100);
});