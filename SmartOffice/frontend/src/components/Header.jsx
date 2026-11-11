import React, { useEffect, useState } from 'react';
import { apiFetch } from '../apiClient';
import { ShieldCheck, Cpu, Database, RefreshCw, Sparkles, Building, ExternalLink, Globe } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Header({ activeTab, onRefresh, llmConfig, totalBudget, totalBalance }) {
  const { language, setLanguage, t, isRtl } = useLanguage();
  // Identité, version et chiffres de la base unique ; l'état de l'IA reflète le mode hors ligne réel.
  const [info, setInfo] = useState(null);
  useEffect(() => { apiFetch('/api/settings/header').then((r) => (r.ok ? r.json() : null)).then(setInfo).catch(() => {}); }, [activeTab]);
  const mad = (cents) => (cents / 100).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  const engineLabel = info?.offline !== false ? 'IA locale (hors ligne)'
    : (llmConfig?.current_provider === 'ollama' ? t('engineOllama') : t('engineGemini'));

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
                  {info ? `v${info.version}` : t('appVersion')}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium line-clamp-1">
                {info?.association || t('orgSubtitle')}
              </p>
              {info?.demo && <span className="text-[10px] font-bold text-amber-700">DÉMONSTRATION — données fictives</span>}
            </div>
          </div>

          {/* Quick Metrics, Language Selector & Engine Status */}
          <div className="flex items-center gap-3 sm:gap-4">
            
            {/* Chiffres de la base unique (masqués si elle est indisponible : jamais de valeur par défaut fictive) */}
            {info?.treasury_mad != null && (
              <div className="hidden lg:flex items-center gap-3 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 text-xs">
                <div className="text-start">
                  <span className="text-[10px] text-slate-400 block font-semibold">Budgets (MAD)</span>
                  <span className="text-xs font-bold text-afmi-forest">{mad(info.budget_mad)}</span>
                </div>
                <div className="h-6 w-px bg-slate-200"></div>
                <div className="text-start">
                  <span className="text-[10px] text-slate-400 block font-semibold">Trésorerie (MAD)</span>
                  <span className={`text-xs font-bold ${info.treasury_mad < 0 ? 'text-red-600' : 'text-emerald-600'}`}>{mad(info.treasury_mad)}</span>
                </div>
              </div>
            )}

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
            <div title="Réglage : Paramètres › Intelligence artificielle" className={`hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border ${info?.offline !== false ? 'bg-slate-50 text-slate-700 border-slate-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200/70'}`}>
              <div className={`w-2 h-2 rounded-full ${info?.offline !== false ? 'bg-slate-400' : 'bg-emerald-500 animate-pulse'}`}></div>
              <div className="flex items-center gap-1">
                <Cpu className="w-3.5 h-3.5 text-emerald-600" />
                <span className="font-semibold">
                  {engineLabel}
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
