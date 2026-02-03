/**
 * UPDATE #91: Multi-Language Support (i18n)
 * Internationalization framework
 */

type Language = 'en' | 'es' | 'fr' | 'de' | 'pt' | 'ja' | 'zh';

interface Translation {
    [key: string]: string | Translation;
}

interface Translations {
    [lang: string]: Translation;
}

class I18nManager {
    private currentLanguage: Language = 'en';
    private translations: Translations = {};
    private fallbackLanguage: Language = 'en';

    /**
     * Load translations
     */
    loadTranslations(lang: Language, translations: Translation): void {
        this.translations[lang] = translations;
    }

    /**
     * Set current language
     */
    setLanguage(lang: Language): void {
        this.currentLanguage = lang;
        if (typeof document !== 'undefined') {
            document.documentElement.lang = lang;
        }
    }

    /**
     * Get current language
     */
    getLanguage(): Language {
        return this.currentLanguage;
    }

    /**
     * Translate a key
     */
    t(key: string, params?: Record<string, string>): string {
        const keys = key.split('.');
        let translation: any = this.translations[this.currentLanguage];

        // Navigate through nested keys
        for (const k of keys) {
            if (translation && typeof translation === 'object') {
                translation = translation[k];
            } else {
                break;
            }
        }

        // Fallback to English if not found
        if (!translation || typeof translation !== 'string') {
            translation = this.getFallback(key);
        }

        // Replace parameters
        if (params && typeof translation === 'string') {
            Object.entries(params).forEach(([param, value]) => {
                translation = translation.replace(`{{${param}}}`, value);
            });
        }

        return typeof translation === 'string' ? translation : key;
    }

    private getFallback(key: string): string {
        const keys = key.split('.');
        let translation: any = this.translations[this.fallbackLanguage];

        for (const k of keys) {
            if (translation && typeof translation === 'object') {
                translation = translation[k];
            } else {
                break;
            }
        }

        return typeof translation === 'string' ? translation : key;
    }
}

export const i18n = new I18nManager();

// Load English translations
i18n.loadTranslations('en', {
    common: {
        search: 'Search',
        filter: 'Filter',
        sort: 'Sort',
        loading: 'Loading...',
        error: 'Error',
        save: 'Save',
        cancel: 'Cancel',
        delete: 'Delete',
        edit: 'Edit'
    },
    movies: {
        title: 'Movies',
        watchTrailer: 'Watch Trailer',
        addToQueue: 'Add to Queue',
        rating: 'Rating',
        releaseYear: 'Release Year',
        genre: 'Genre'
    },
    user: {
        profile: 'Profile',
        settings: 'Settings',
        logout: 'Logout',
        login: 'Login',
        register: 'Register'
    }
});

// Load Spanish translations
i18n.loadTranslations('es', {
    common: {
        search: 'Buscar',
        filter: 'Filtrar',
        sort: 'Ordenar',
        loading: 'Cargando...',
        error: 'Error',
        save: 'Guardar',
        cancel: 'Cancelar',
        delete: 'Eliminar',
        edit: 'Editar'
    },
    movies: {
        title: 'Películas',
        watchTrailer: 'Ver Tráiler',
        addToQueue: 'Añadir a la Cola',
        rating: 'Calificación',
        releaseYear: 'Año de Estreno',
        genre: 'Género'
    },
    user: {
        profile: 'Perfil',
        settings: 'Configuración',
        logout: 'Cerrar Sesión',
        login: 'Iniciar Sesión',
        register: 'Registrarse'
    }
});

/**
 * React hook for translations
 */
import { useState, useCallback } from 'react';

export function useTranslation() {
    const [language, setLanguage] = useState(i18n.getLanguage());

    const changeLanguage = useCallback((lang: Language) => {
        i18n.setLanguage(lang);
        setLanguage(lang);
    }, []);

    const t = useCallback((key: string, params?: Record<string, string>) => {
        return i18n.t(key, params);
    }, [language]);

    return { t, language, changeLanguage };
}
