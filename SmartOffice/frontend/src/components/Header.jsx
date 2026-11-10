import React from 'react';
import { ShieldCheck, Cpu, Database, RefreshCw, Sparkles, Building, ExternalLink, Globe } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Header({ activeTab, onRefresh, llmConfig, totalBudget, totalBalance }) {
  const { language, setLanguage, t, isRtl } = useLanguage();

  return (
    <header className="bg-white border-b border-slate-200/80 sticky top-0 z-30 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-afmi-gradient flex items-center justify-center text-white shadow-md shadow-afmi-forest/20 shrink-0">
              <span className="text-xl font-bold">🌲</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-afmi-dark tracking-tight">
                  {t('appTitle')}
                </h1>
                <span className="text-xs bg-afmi-lightmint text-afmi-forest font-semibold px-2 py-0.5 rounded-full border border-afmi-mint/30">
                  {t('appVersion')}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium line-clamp-1">
                {t('orgSubtitle')}
              </p>
            </div>
          </div>

          {/* Quick Metrics, Language Selector & Engine Status */}
          <div className="flex items-center gap-3 sm:gap-4">
            
            {/* Quick Metrics */}
            <div className="hidden lg:flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
              <div className={isRtl ? "text-right" : "text-left"}>
                <span className="text-[10px] text-slate-400 block font-semibold">{t('projectsPortfolio')}</span>
                <span className="text-xs font-bold text-afmi-forest">
                  {totalBudget ? totalBudget.toLocaleString() : '1,050,000'} {t('currencyMAD')}
                </span>
              </div>
              <div className="h-6 w-px bg-slate-200"></div>
              <div className={isRtl ? "text-right" : "text-left"}>
                <span className="text-[10px] text-slate-400 block font-semibold">{t('availableBalance')}</span>
                <span className="text-xs font-bold text-emerald-600">
                  {totalBalance ? totalBalance.toLocaleString() : '264,000'} {t('currencyMAD')}
                </span>
              </div>
            </div>

            {/* Trilingual Language Switcher */}
            <div className="flex items-center bg-slate-100 p-0.5 rounded-xl border border-slate-200 text-xs font-bold">
              <button
                type="button"
                onClick={() => setLanguage('ar')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  language === 'ar'
                    ? 'bg-afmi-forest text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="العربية (RTL)"
              >
                عربية
              </button>
              <button
                type="button"
                onClick={() => setLanguage('fr')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  language === 'fr'
                    ? 'bg-afmi-forest text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="Français (LTR)"
              >
                FR
              </button>
              <button
                type="button"
                onClick={() => setLanguage('en')}
                className={`px-2.5 py-1 rounded-lg transition-all ${
                  language === 'en'
                    ? 'bg-afmi-forest text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
                title="English (LTR)"
              >
                EN
              </button>
            </div>

            {/* AI Engine Status Badge */}
            <div className="hidden sm:flex items-center gap-2 bg-emerald-50 text-emerald-800 border border-emerald-200/70 px-3 py-1.5 rounded-lg text-xs font-medium">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
              <div className="flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                <span className="font-semibold">
                  {llmConfig?.current_provider === 'ollama' ? t('engineOllama') : t('engineGemini')}
                </span>
              </div>
            </div>

            {/* Refresh Button */}
            <button 
              onClick={onRefresh}
              title={t('refreshData')}
              className="p-2 text-slate-400 hover:text-afmi-forest hover:bg-slate-100 rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
            </button>

          </div>
        </div>
      </div>
    </header>
  );
}
