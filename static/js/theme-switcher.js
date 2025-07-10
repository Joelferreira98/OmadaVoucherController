// Theme Switcher Functionality
class ThemeSwitcher {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }

    init() {
        // Apply saved theme
        this.applyTheme(this.currentTheme);
        
        // Create theme toggle button if it doesn't exist
        this.createToggleButton();
        
        // Listen for system theme changes
        this.listenForSystemThemeChanges();
    }

    createToggleButton() {
        // Check if toggle already exists
        if (document.querySelector('.theme-toggle')) return;
        
        const toggleButton = document.createElement('div');
        toggleButton.className = 'theme-toggle';
        toggleButton.innerHTML = '<i class="fas fa-moon"></i>';
        toggleButton.setAttribute('title', 'Alternar tema');
        toggleButton.addEventListener('click', () => this.toggleTheme());
        
        // Add to body
        document.body.appendChild(toggleButton);
        
        // Update icon based on current theme
        this.updateToggleIcon();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.currentTheme = theme;
        localStorage.setItem('theme', theme);
        this.updateToggleIcon();
    }

    toggleTheme() {
        const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        
        // Add smooth transition effect
        document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
        
        // Update charts if available
        if (typeof updateChartsTheme === 'function') {
            updateChartsTheme();
        }
    }

    updateToggleIcon() {
        const toggleButton = document.querySelector('.theme-toggle i');
        if (toggleButton) {
            if (this.currentTheme === 'light') {
                toggleButton.className = 'fas fa-moon';
                toggleButton.parentElement.setAttribute('title', 'Modo escuro');
            } else {
                toggleButton.className = 'fas fa-sun';
                toggleButton.parentElement.setAttribute('title', 'Modo claro');
            }
        }
    }

    listenForSystemThemeChanges() {
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', (e) => {
                // Only auto-switch if user hasn't manually set a preference
                if (!localStorage.getItem('theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    // Get current theme
    getTheme() {
        return this.currentTheme;
    }

    // Force set theme (useful for admin preferences)
    setTheme(theme) {
        if (['light', 'dark'].includes(theme)) {
            this.applyTheme(theme);
        }
    }
}

// Initialize theme switcher when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.themeSwitcher = new ThemeSwitcher();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSwitcher;
}