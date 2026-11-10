import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations } from '../i18n';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [language, setLanguageState] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('afmi_lang');
      if (saved && ['ar', 'fr', 'en'].includes(saved)) {
        return saved;
      }
    }
    return 'ar';
  });

  const dir = language === 'ar' ? 'rtl' : 'ltr';
  const isRtl = dir === 'rtl';

  const setLanguage = (newLang) => {
    if (['ar', 'fr', 'en'].includes(newLang)) {
      setLanguageState(newLang);
      if (typeof window !== 'undefined') {
        localStorage.setItem('afmi_lang', newLang);
      }
    }
  };

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = language;
      document.documentElement.dir = dir;
    }
  }, [language, dir]);

  const t = (key, fallback = "") => {
    const langDict = translations[language];
    if (langDict && langDict[key] !== undefined) {
      return langDict[key];
    }
    // Fallback order: French -> Arabic -> English -> fallback param
    return translations.fr[key] || translations.ar[key] || translations.en[key] || fallback || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, dir, isRtl, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
