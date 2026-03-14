// Language Manager
class LanguageManager {
    constructor() {
        this.supportedLanguages = ['it', 'en', 'fr', 'es', 'de'];
        this.defaultLanguage = 'it';
        this.currentLanguage = this.getCurrentLanguage();
        this.translations = {};
        this.init();
    }

    init() {
        // Load translations for current language and initialize
        this.loadTranslations(this.currentLanguage);
        this.setupLanguageSwitcher();
    }

    getCurrentLanguage() {
        // Check localStorage first
        const saved = localStorage.getItem('preferredLanguage');
        if (saved && this.supportedLanguages.includes(saved)) {
            return saved;
        }

        // Check browser language if no saved preference
        const browserLang = this.getBrowserLanguage();
        if (this.supportedLanguages.includes(browserLang)) {
            localStorage.setItem('preferredLanguage', browserLang);
            return browserLang;
        }

        // Default to Italian
        localStorage.setItem('preferredLanguage', this.defaultLanguage);
        return this.defaultLanguage;
    }

    getBrowserLanguage() {
        const lang = navigator.language || navigator.userLanguage;
        const langCode = lang.split('-')[0].toLowerCase();
        return langCode;
    }

    loadTranslations(language) {
        return fetch(`data/${language}.json`)
            .then(response => response.json())
            .then(data => {
                this.translations = data;
                this.currentLanguage = language;
                localStorage.setItem('preferredLanguage', language);
                this.applyTranslations();
                // Trigger custom event for other scripts
                document.dispatchEvent(new CustomEvent('languageChanged', { detail: language }));
            })
            .catch(err => console.error('Error loading translations:', err));
    }

    applyTranslations() {
        // Update all elements with data-i18n attribute
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (this.translations[key]) {
                const text = this.translations[key];

                // Check if it's HTML content (contains HTML tags)
                if (text.includes('<')) {
                    element.innerHTML = text;
                } else {
                    element.textContent = text;
                }
            }
        });

        // Update document lang attribute
        document.documentElement.lang = this.currentLanguage;
        document.documentElement.setAttribute('data-language', this.currentLanguage);

        // Update page title
        document.title = 'Terra Mia Como';
    }

    translate(key) {
        return this.translations[key] || key;
    }

    setLanguage(language) {
        if (this.supportedLanguages.includes(language)) {
            return this.loadTranslations(language);
        }
        return Promise.reject('Invalid language');
    }

    setupLanguageSwitcher() {
        const switcher = document.getElementById('lang-switcher');
        if (!switcher) return;

        // Set current language button as active
        this.updateLanguageSwitcherUI();

        // Add click handlers to language buttons
        document.querySelectorAll('[data-lang]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const lang = btn.getAttribute('data-lang');
                this.setLanguage(lang).then(() => {
                    this.updateLanguageSwitcherUI();
                    // Close dropdown on mobile
                    const dropdown = document.getElementById('lang-dropdown');
                    if (dropdown) {
                        dropdown.classList.remove('active');
                    }
                });
            });
        });
    }

    updateLanguageSwitcherUI() {
        document.querySelectorAll('[data-lang]').forEach(btn => {
            if (btn.getAttribute('data-lang') === this.currentLanguage) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }
}

// Global language manager instance
let languageManager;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        languageManager = new LanguageManager();
    });
} else {
    languageManager = new LanguageManager();
}
