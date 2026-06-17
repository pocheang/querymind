import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import zh from './locales/zh.json';

const savedLanguage = localStorage.getItem('language') || 'en';

function applyLanguageAttributes(language: string) {
  const normalized = language.startsWith('zh') ? 'zh' : 'en';
  document.documentElement.lang = normalized === 'zh' ? 'zh-CN' : 'en';
  document.documentElement.dataset.language = normalized;
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      zh: { translation: zh },
    },
    lng: savedLanguage,
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

applyLanguageAttributes(i18n.language);
i18n.on('languageChanged', applyLanguageAttributes);

export default i18n;
