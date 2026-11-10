import React from 'react';
import { 
  LayoutDashboard, 
  Bot, 
  FileScan, 
  Briefcase, 
  Sliders, 
  Building2, 
  Trees, 
  Compass,
  Workflow,
  Landmark,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

export default function Sidebar({ activeTab, setActiveTab }) {
  const { language, t, isRtl } = useLanguage();

  const menuItems = [
    {
      id: 'dashboard',
      label_ar: 'لوحة القيادة التفاعلية',
      label_fr: 'Tableau de Bord',
      label_en: 'Interactive Dashboard',
      icon: LayoutDashboard,
      badge: t('badgeStats')
    },
    {
      id: 'agents',
      label_ar: 'مساحات الوكلاء الأذكياء',
      label_fr: 'Agents IA Spécialisés',
      label_en: 'Specialized AI Agents',
      icon: Bot,
      badge: t('badgeAgents')
    },
    {
      id: 'workflows',
      label_ar: 'سلاسل الوكلاء المترابطة',
      label_fr: "Chaînes d'Agents",
      label_en: 'Agent Chains',
      icon: Workflow,
      badge: t('badgeWorkflows')
    },
    {
      id: 'ocr',
      label_ar: 'مختبر التدقيق و OCR المالي',
      label_fr: 'Laboratoire OCR & Finance',
      label_en: 'OCR & Financial Audit',
      icon: FileScan,
      badge: t('badgeOcr')
    },
    {
      id: 'payroll',
      label_ar: 'الأجور والتصريحات الضريبية',
      label_fr: 'Paie & Déclarations',
      label_en: 'Payroll & Tax Filings',
      icon: Landmark,
      badge: t('badgePayroll')
    },
    {
      id: 'grants',
      label_ar: 'المنح والمشاريع التنموية',
      label_fr: 'Subventions & Projets',
      label_en: 'Grants & Projects',
      icon: Briefcase,
      badge: t('badgeGrants')
    },
    {
      id: 'radar',
      label_ar: 'رادار خلاصات RSS',
      label_fr: 'Radar Projets (RSS)',
      label_en: 'Project Radar (RSS)',
      icon: Compass,
      badge: t('badgeRadar')
    },
    {
      id: 'studio',
      label_ar: 'استوديو الوكلاء والإضافات',
      label_fr: 'Studio & Plugins',
      label_en: 'Studio & Plugins',
      icon: Sliders,
      badge: t('badgeStudio')
    },
    {
      id: 'memory',
      label_ar: 'الذاكرة المؤسساتية والإعدادات',
      label_fr: 'Mémoire & Paramètres',
      label_en: 'Institutional Memory',
      icon: Building2,
      badge: t('badgeMemory')
    }
  ];

  return (
    <aside className={`w-64 bg-white ${isRtl ? 'border-l' : 'border-r'} border-slate-200/80 flex flex-col justify-between shrink-0 h-[calc(100vh-4rem)] sticky top-16 shadow-sm`}>
      
      {/* Navigation Links */}
      <div className="p-4 space-y-1.5 overflow-y-auto">
        <div className={`px-3 py-2 text-[11px] font-bold text-slate-400 uppercase tracking-wider ${isRtl ? 'text-right' : 'text-left'}`}>
          {t('modulesSection')}
        </div>

        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          let primaryLabel = item.label_ar;
          let secondaryLabel = item.label_fr;
          if (language === 'fr') {
            primaryLabel = item.label_fr;
            secondaryLabel = item.label_ar;
          } else if (language === 'en') {
            primaryLabel = item.label_en;
            secondaryLabel = item.label_fr;
          }

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-sm font-semibold transition-all duration-200 group ${
                isActive
                  ? 'bg-afmi-forest text-white shadow-md shadow-afmi-forest/20'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-afmi-forest'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-5 h-5 transition-transform duration-200 ${
                  isActive ? 'text-afmi-gold' : 'text-slate-400 group-hover:text-afmi-forest'
                }`} />
                <div className={isRtl ? 'text-right' : 'text-left'}>
                  <span className="block leading-tight font-bold">{primaryLabel}</span>
                  <span className={`text-[10px] block font-normal leading-tight mt-0.5 ${
                    isActive ? 'text-emerald-200' : 'text-slate-400'
                  }`}>
                    {secondaryLabel}
                  </span>
                </div>
              </div>

              {item.badge && (
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  isActive
                    ? 'bg-white/20 text-white'
                    : 'bg-slate-100 text-slate-500 group-hover:bg-afmi-lightmint group-hover:text-afmi-forest'
                }`}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Territorial & Legal Badge */}
      <div className="p-4 m-3 rounded-xl bg-slate-50 border border-slate-200/80 text-xs">
        <div className="flex items-center gap-2 text-afmi-forest font-bold mb-1">
          <Trees className="w-4 h-4 text-emerald-600" />
          <span>{t('footerRegion')}</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          {t('footerCopyright')}<br />
          ICE: <span className="font-mono text-slate-700 font-semibold">001894235000088</span>
        </p>
      </div>

    </aside>
  );
}
