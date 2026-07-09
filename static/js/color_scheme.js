// static/js/color-scheme.js
class ColorSchemeManager {
    constructor() {
        this.schemes = {
            'med-blue': {
                name: 'Medical Blue',
                colors: {
                    primary: '#007bff',
                    primaryLight: '#4dabf7',
                    primaryDark: '#0056b3',
                    sidebarBg: 'linear-gradient(180deg, #2c3e50 0%, #1a252f 100%)'
                }
            },
            'med-green': {
                name: 'Medical Green',
                colors: {
                    primary: '#20c997',
                    primaryLight: '#63e6be',
                    primaryDark: '#099268',
                    sidebarBg: 'linear-gradient(180deg, #2d4a3e 0%, #1e3328 100%)'
                }
            },
            // Add other schemes...
        };
        
        this.init();
    }
    
    init() {
        this.loadScheme();
        this.bindEvents();
        this.updateUI();
    }
    
    loadScheme() {
        const saved = localStorage.getItem('colorScheme') || 'med-blue';
        this.setScheme(saved);
    }
    
    setScheme(schemeName) {
        if (!this.schemes[schemeName]) return;
        
        const scheme = this.schemes[schemeName];
        const root = document.documentElement;
        
        // Update CSS variables
        Object.entries(scheme.colors).forEach(([key, value]) => {
            root.style.setProperty(`--${key}`, value);
        });
        
        // Update data attribute
        root.setAttribute('data-color-scheme', schemeName);
        
        // Save to localStorage
        localStorage.setItem('colorScheme', schemeName);
        
        // Update UI
        this.updateUI();
        
        // Dispatch event
        this.dispatchChangeEvent(schemeName);
    }
    
    updateUI() {
        const current = localStorage.getItem('colorScheme') || 'med-blue';
        const schemeName = this.schemes[current]?.name || 'Medical Blue';
        
        // Update badge
        const badge = document.getElementById('currentScheme');
        if (badge) {
            badge.textContent = schemeName;
            badge.className = `badge bg-gradient-primary`;
        }
        
        // Update active option
        document.querySelectorAll('.color-scheme-option').forEach(option => {
            option.classList.remove('active');
            if (option.dataset.scheme === current) {
                option.classList.add('active');
            }
        });
    }
    
    bindEvents() {
        // Color scheme options
        document.querySelectorAll('.color-scheme-option').forEach(option => {
            option.addEventListener('click', (e) => {
                const scheme = e.currentTarget.dataset.scheme;
                this.setScheme(scheme);
            });
        });
        
        // Custom scheme creation
        document.getElementById('createCustomScheme')?.addEventListener('click', () => {
            this.createCustomScheme();
        });
    }
    
    createCustomScheme() {
        // Implementation for custom color scheme creation
        console.log('Custom scheme creation dialog');
    }
    
    dispatchChangeEvent(schemeName) {
        const event = new CustomEvent('colorSchemeChanged', {
            detail: { scheme: schemeName }
        });
        document.dispatchEvent(event);
    }
    
    getCurrentScheme() {
        return localStorage.getItem('colorScheme') || 'med-blue';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.colorSchemeManager = new ColorSchemeManager();
});