import React, { useState, useEffect } from 'react';
import { 
  Compass, 
  RefreshCw, 
  Search, 
  Filter, 
  ExternalLink, 
  BookmarkPlus, 
  Sparkles, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Coins, 
  Plus, 
  Trash2, 
  ToggleLeft, 
  ToggleRight, 
  Rss, 
  Layers, 
  ShieldCheck, 
  ArrowRight,
  SlidersHorizontal,
  X
} from 'lucide-react';
import { apiFetch } from '../apiClient';
import { useLanguage } from '../context/LanguageContext';

export default function ProjectRadarView({ onSelectAgent, onNavigateTab, onRefreshGlobal }) {
  const { t, language } = useLanguage();
  const [subTab, setSubTab] = useState("opportunities"); // "opportunities" or "feeds"
  const [projects, setProjects] = useState([]);
  const [feeds, setFeeds] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState("");

  // Search & Filters state
  const [keywords, setKeywords] = useState("");
  const [selectedDonor, setSelectedDonor] = useState("all");
  const [selectedAxis, setSelectedAxis] = useState("all");
  const [minScore, setMinScore] = useState(5);

  // New Feed Modal
  const [showAddFeedModal, setShowAddFeedModal] = useState(false);
  const [newFeed, setNewFeed] = useState({
    name: "",
    name_ar: "",
    url: "",
    category: "international",
    focus: ""
  });

  const strategicAxes = language === 'fr' ? [
    "Conservation des écosystèmes forestiers et biodiversité",
    "Écotourisme et développement territorial durable",
    "Renforcement des capacités et autonomisation",
    "Éducation environnementale et écocitoyenneté",
    "Énergies renouvelables et efficacité énergétique",
    "Développement durable et économie circulaire",
    "Gestion et valorisation des ressources en eau",
    "Restauration pastorale et pratiques Agdal",
    "Adaptation aux changements climatiques et SIBE",
    "Autonomisation socio-économique des jeunes et femmes"
  ] : language === 'en' ? [
    "Forest ecosystems conservation and biodiversity monitoring",
    "Eco-tourism and sustainable territorial development",
    "Capacity building and local institutional empowerment",
    "Environmental education and eco-citizenship",
    "Renewable energies and clean technologies",
    "Sustainable development and circular green economy",
    "Surface water quality monitoring and water resources",
    "Rangeland restoration and Agdal pastoral practices",
    "Climate change adaptation and SIBE management",
    "Socio-economic empowerment of rural youth and women"
  ] : [
    "حماية النظم الإيكولوجية الغابوية ورصد التنوع البيولوجي",
    "السياحة الإيكولوجية والبنية التحتية المستدامة",
    "تقوية القدرات والتمكين المؤسساتي والمحلي",
    "التربية البيئية والمواطنة الإيكولوجية وتوعية الناشئة",
    "الطاقات المتجددة والنجاعة الطاقية والتكنولوجيات النظيفة",
    "التنمية المستدامة والاقتصاد الدائري والمقاولات الخضراء",
    "مراقبة جودة المياه السطحية وتثمين الموارد المائية",
    "استعادة المراعي والتدبير الرعوي التقليدي نظام أكدال",
    "التكيف مع التغيرات المناخية وتدبير المواقع ذات الأهمية البيولوجية",
    "التمكين السوسيو-اقتصادي للشباب القروي والنساء"
  ];

  // Initial load
  useEffect(() => {
    fetchFeeds();
    scanForProjects("");
  }, []);

  const fetchFeeds = async () => {
    try {
      const res = await apiFetch('/api/rss/feeds');
      if (res.ok) {
        const data = await res.json();
        setFeeds(data.feeds || []);
      }
    } catch (e) {
      console.error("Error loading feeds:", e);
    }
  };

  const scanForProjects = async (searchKw = keywords, donor = selectedDonor, axis = selectedAxis, score = minScore) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/rss/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords: searchKw,
          donor: donor,
          axis: axis,
          min_score: score,
          force_refresh: true
        })
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Erreur serveur HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.status === 'success') {
        setProjects(data.projects || []);
      } else {
        throw new Error(data.detail || 'Erreur lors du traitement des flux RSS.');
      }
    } catch (err) {
      setError(err.message || t('connError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleImportToPipeline = async (opp) => {
    try {
      const res = await apiFetch('/api/rss/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: opp.title,
          donor: opp.donor,
          link: opp.link,
          amount_mad: opp.ai_analysis?.estimated_budget_mad || 500000,
          currency: opp.ai_analysis?.currency || "MAD",
          deadline: opp.ai_analysis?.deadline || "2026-12-31",
          strategic_axis: opp.ai_analysis?.category,
          summary_ar: opp.ai_analysis?.summary_ar,
          summary_fr: opp.ai_analysis?.summary_fr,
          action_recommendation: opp.ai_analysis?.action_recommendation
        })
      });

      if (res.ok) {
        const titleMsg = opp.title || "";
        const msg = language === 'fr' 
          ? `Opportunité "${titleMsg}" importée avec succès dans le pipeline.` 
          : language === 'en' 
          ? `Opportunity "${titleMsg}" successfully imported to Grants Pipeline.` 
          : `تم استيراد فرصة "${titleMsg}" بنجاح إلى محفظة طلبات التمويل (Grants Pipeline).`;
        setSuccessMsg(msg);
        if (onRefreshGlobal) onRefreshGlobal();
        setTimeout(() => setSuccessMsg(""), 5000);
      }
    } catch (err) {
      setError(t('importError'));
    }
  };

  const handleDraftWithAi = (opp) => {
    if (onSelectAgent) {
      onSelectAgent("agent_grant_writer");
    } else if (onNavigateTab) {
      onNavigateTab("agents");
    }
  };

  const handleToggleFeed = async (feedId) => {
    try {
      const res = await apiFetch(`/api/rss/feeds/${feedId}/toggle`, { method: 'POST' });
      if (res.ok) {
        fetchFeeds();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteFeed = async (feedId) => {
    if (!window.confirm(t('confirmDeleteFeed'))) return;
    try {
      const res = await apiFetch(`/api/rss/feeds/${feedId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchFeeds();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateFeed = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch('/api/rss/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newFeed)
      });
      if (res.ok) {
        setShowAddFeedModal(false);
        setNewFeed({ name: "", name_ar: "", url: "", category: "international", focus: "" });
        fetchFeeds();
        setSuccessMsg(t('addFeedSuccess'));
        setTimeout(() => setSuccessMsg(""), 4000);
      }
    } catch (e) {
      setError(t('addFeedError'));
    }
  };

  const quickThemesPills = language === 'fr' ? [
    "🌲 Conservation des cèdres et biodiversité",
    "🏞️ Écotourisme et circuits de l'Atlas",
    "💧 Ressources en eau et lacs d'Ifrane",
    "🐑 Pastoralisme traditionnel Agdal à Timahdite",
    "☀️ Énergies renouvelables et pompage solaire",
    "🎓 Renforcement des capacités locales",
    "📚 Éducation environnementale et éco-écoles",
    "🌍 Développement durable et économie circulaire"
  ] : language === 'en' ? [
    "🌲 Cedar forest conservation & biodiversity",
    "🏞️ Eco-tourism & Middle Atlas trails",
    "💧 Water resources & natural lakes",
    "🐑 Agdal pastoral management in Timahdite",
    "☀️ Renewable energy & solar pumping",
    "🎓 Capacity building & local empowerment",
    "📚 Environmental education & eco-schools",
    "🌍 Sustainable development & circular economy"
  ] : [
    "🌲 حماية غابات الأرز والتنوع البيولوجي",
    "🏞️ السياحة الإيكولوجية ومسارات الأطلس",
    "💧 الموارد المائية وجودة البحيرات",
    "🐑 التدبير الرعوي أكدال بتمحضيت",
    "☀️ الطاقات المتجددة والضخ الشمسي",
    "🎓 تقوية القدرات والتمكين المحلي",
    "📚 التربية البيئية والمدارس الإيكولوجية",
    "🌍 التنمية المستدامة والاقتصاد الدائري"
  ];

  return (
    <div className="space-y-6">
      
      {/* Top Hero Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-afmi-lightmint text-afmi-forest font-bold">
              <Compass className="w-5 h-5 text-afmi-forest" />
            </span>
            <h2 className="text-xl font-extrabold text-afmi-dark">
              {t('radarTitle')}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t('radarSubtitle')}
          </p>
        </div>

        {/* SubTab Navigation */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-100 p-1 rounded-xl flex items-center">
            <button
              onClick={() => setSubTab("opportunities")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                subTab === "opportunities"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Compass className="w-3.5 h-3.5 text-afmi-gold" />
              <span>{t('tabDetectedOpportunities')} ({projects.length})</span>
            </button>

            <button
              onClick={() => setSubTab("feeds")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                subTab === "feeds"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Rss className="w-3.5 h-3.5 text-amber-600" />
              <span>{t('tabFeedsSources')} ({feeds.length})</span>
            </button>
          </div>

          {subTab === "feeds" && (
            <button
              onClick={() => setShowAddFeedModal(true)}
              className="px-3.5 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t('addNewFeedBtn')}</span>
            </button>
          )}

          <button
            onClick={() => scanForProjects()}
            disabled={isLoading}
            className="px-4 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-afmi-gold ${isLoading ? 'animate-spin' : ''}`} />
            <span>{isLoading ? t('refreshingRadar') : t('refreshRadarBtn')}</span>
          </button>
        </div>
      </div>

      {/* Alerts */}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs font-bold text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* SUBTAB 1: OPPORTUNITIES DETECTED */}
      {subTab === "opportunities" && (
        <div className="space-y-5">
          
          {/* Search & Filter Bar */}
          <div className="afmi-card p-5 space-y-4">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className={`w-4 h-4 text-slate-400 absolute ${language === 'ar' ? 'right-3.5' : 'left-3.5'} top-3.5 pointer-events-none`} />
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && scanForProjects()}
                  placeholder={t('radarKwPlaceholder')}
                  className={`w-full ${language === 'ar' ? 'pr-10 pl-4' : 'pl-10 pr-4'} py-2.5 bg-slate-50 border border-slate-200 focus:border-afmi-forest rounded-xl text-xs font-medium outline-none`}
                />
              </div>

              {/* Donor Filter */}
              <select
                value={selectedDonor}
                onChange={(e) => {
                  setSelectedDonor(e.target.value);
                  scanForProjects(keywords, e.target.value, selectedAxis, minScore);
                }}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none"
              >
                <option value="all">{t('allRssDonors')}</option>
                <option value="GEF">GEF / مرفق البيئة العالمية</option>
                <option value="PNUD">PNUD / برنامج الأمم المتحدة الإنمائي</option>
                <option value="Européenne">Union Européenne / الاتحاد الأوروبي</option>
                <option value="Banque Mondiale">Banque Mondiale / البنك الدولي</option>
                <option value="AFD">AFD / الوكالة الفرنسية للتنمية</option>
                <option value="FAO">FAO / منظمة الفاو</option>
                <option value="IUCN">IUCN / الاتحاد الدولي لصون الطبيعة</option>
                <option value="CEPF">CEPF / شراكة الأنظمة الحرجة</option>
              </select>

              {/* Axis Filter */}
              <select
                value={selectedAxis}
                onChange={(e) => {
                  setSelectedAxis(e.target.value);
                  scanForProjects(keywords, selectedDonor, e.target.value, minScore);
                }}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none max-w-[240px]"
              >
                <option value="all">{t('allStrategicAxes')}</option>
                {strategicAxes.map((ax, i) => (
                  <option key={i} value={ax}>{ax.slice(0, 35)}...</option>
                ))}
              </select>

              {/* Min Score Filter */}
              <select
                value={minScore}
                onChange={(e) => {
                  const val = parseInt(e.target.value, 10);
                  setMinScore(val);
                  scanForProjects(keywords, selectedDonor, selectedAxis, val);
                }}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none"
              >
                <option value="5">{t('scoreAll')}</option>
                <option value="7">{t('scoreStrong')}</option>
                <option value="8">{t('scoreExcellent')}</option>
                <option value="9">{t('scoreExceptional')}</option>
              </select>

              <button
                onClick={() => scanForProjects()}
                disabled={isLoading}
                className="px-5 py-2.5 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-2 shrink-0"
              >
                <Search className="w-3.5 h-3.5 text-afmi-gold" />
                <span>{t('searchAction')}</span>
              </button>
            </div>

            {/* Quick Themes Suggestion Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
              <span className="text-[11px] font-bold text-slate-400">{t('quickThemes')}</span>
              {quickThemesPills.map((pill, pIdx) => (
                <button
                  key={pIdx}
                  onClick={() => {
                    setKeywords(pill);
                    scanForProjects(pill);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-afmi-lightmint hover:text-afmi-forest text-slate-600 text-[11px] font-medium transition-colors"
                >
                  {pill}
                </button>
              ))}
            </div>
          </div>

          {/* Results Grid */}
          {projects.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {projects.map((opp, idx) => {
                const score = opp.ai_analysis?.relevance_score || 8;
                return (
                  <div 
                    key={opp.id || idx}
                    className="afmi-card p-5 border-t-4 border-t-afmi-forest flex flex-col justify-between hover:shadow-md transition-shadow"
                  >
                    <div>
                      {/* Card Top Badges */}
                      <div className="flex items-start justify-between gap-3 mb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-extrabold text-afmi-forest bg-afmi-lightmint px-2.5 py-1 rounded-lg">
                            🏛️ {opp.donor}
                          </span>
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                            {opp.source_type || 'Flux RSS'}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                            score >= 9 ? 'bg-emerald-50 text-emerald-800 border-emerald-300' :
                            score >= 7 ? 'bg-teal-50 text-teal-800 border-teal-200' :
                            'bg-amber-50 text-amber-800 border-amber-200'
                          }`}>
                            {t('relevanceDegree')}: {score}/10
                          </span>
                        </div>
                      </div>

                      {/* Opportunity Title */}
                      <h3 className="font-bold text-sm md:text-base text-slate-800 leading-snug mb-2">
                        {opp.title}
                      </h3>

                      {/* Strategic Axis Badge */}
                      <div className="inline-flex items-center gap-1.5 text-xs text-afmi-forest font-semibold mb-3 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-100">
                        <span>{t('axisLabel')}</span>
                        <span>{opp.ai_analysis?.category || (language === 'fr' ? "Protection environnementale" : language === 'en' ? "Environmental protection" : "حماية البيئة والتنمية المستدامة")}</span>
                      </div>

                      {/* Multilingual Summary */}
                      <div className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100 mb-3 space-y-1.5">
                        <p className="font-medium text-slate-800">
                          {language === 'fr' 
                            ? (opp.ai_analysis?.summary_fr || opp.ai_analysis?.summary_ar) 
                            : language === 'en' 
                            ? (opp.ai_analysis?.summary_en || opp.ai_analysis?.summary_fr || opp.ai_analysis?.summary_ar) 
                            : (opp.ai_analysis?.summary_ar || opp.ai_analysis?.summary_fr)}
                        </p>
                        {opp.ai_analysis?.action_recommendation && (
                          <div className="pt-2 border-t border-slate-200/60 text-afmi-forest font-semibold text-[11px] flex items-start gap-1">
                            <span className="shrink-0">{t('actionTip')}</span>
                            <span>{opp.ai_analysis.action_recommendation}</span>
                          </div>
                        )}
                      </div>

                      {/* Budget & Deadline Metrics */}
                      <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                        <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
                          <span className="text-[10px] text-slate-400 block font-semibold">{t('estimatedBudgetCap')}</span>
                          <span className="font-black text-afmi-forest text-sm font-mono">
                            {opp.ai_analysis?.estimated_budget_mad ? opp.ai_analysis.estimated_budget_mad.toLocaleString() : '500,000'} {opp.ai_analysis?.currency || 'DH'}
                          </span>
                        </div>
                        <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
                          <span className="text-[10px] text-slate-400 block font-semibold">{t('estimatedDeadline')}</span>
                          <span className="font-bold text-slate-700 text-xs flex items-center gap-1 mt-0.5 font-mono">
                            <Clock className="w-3 h-3 text-amber-600" />
                            {opp.ai_analysis?.deadline || '2026-12-31'}
                          </span>
                        </div>
                      </div>

                    </div>

                    {/* Bottom Action Buttons */}
                    <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                      {opp.link && (
                        <a
                          href={opp.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] font-bold text-slate-500 hover:text-afmi-forest flex items-center gap-1"
                        >
                          <span>{t('viewOriginalLink')}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleImportToPipeline(opp)}
                          className="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-afmi-lightmint hover:text-afmi-forest text-slate-700 text-xs font-bold transition-colors flex items-center gap-1"
                          title={t('addToPipeline')}
                        >
                          <BookmarkPlus className="w-3.5 h-3.5" />
                          <span>{t('addToPipeline')}</span>
                        </button>

                        <button
                          onClick={() => handleDraftWithAi(opp)}
                          className="px-3.5 py-1.5 rounded-lg bg-afmi-forest hover:bg-afmi-emerald text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-afmi-gold" />
                          <span>{t('draftProposalAi')}</span>
                        </button>
                      </div>
                    </div>

                  </div>
                );
              })}
            </div>
          ) : (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-3">
              <Compass className="w-12 h-12 text-slate-300 mx-auto" />
              <h3 className="text-base font-bold text-slate-700">{t('emptyRadarTitle')}</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                {t('emptyRadarDesc')}
              </p>
            </div>
          )}

        </div>
      )}

      {/* SUBTAB 2: MONITORED RSS FEEDS MANAGEMENT */}
      {subTab === "feeds" && (
        <div className="space-y-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
            <div>
              <h3 className="font-bold text-slate-800 text-sm">{t('feedsListTitle')}</h3>
              <p className="text-xs text-slate-400">{t('feedsListDesc')}</p>
            </div>
            <button
              onClick={() => setShowAddFeedModal(true)}
              className="px-3.5 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t('addNewFeedBtn')}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {feeds.map((feed) => (
              <div 
                key={feed.id}
                className={`afmi-card p-5 border transition-all ${
                  feed.is_active ? 'border-slate-200' : 'border-slate-200/50 opacity-60 bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <Rss className="w-4 h-4 text-amber-600" />
                    <span className="font-bold text-sm text-slate-800">
                      {language === 'ar' ? (feed.name_ar || feed.name) : (feed.name || feed.name_ar)}
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                    {feed.category}
                  </span>
                </div>

                <div className="text-xs text-slate-500 font-mono break-all mb-3 bg-slate-50 p-2 rounded-lg border border-slate-100">
                  {feed.url}
                </div>

                <p className="text-xs text-slate-600 mb-4 line-clamp-2">
                  {feed.focus}
                </p>

                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <button
                    onClick={() => handleToggleFeed(feed.id)}
                    className="flex items-center gap-1 font-semibold text-slate-600 hover:text-afmi-forest transition-colors"
                  >
                    {feed.is_active ? (
                      <>
                        <ToggleRight className="w-5 h-5 text-emerald-600" />
                        <span className="text-emerald-700 font-bold">{t('feedActive')}</span>
                      </>
                    ) : (
                      <>
                        <ToggleLeft className="w-5 h-5 text-slate-400" />
                        <span>{t('feedInactive')}</span>
                      </>
                    )}
                  </button>

                  <button
                    onClick={() => handleDeleteFeed(feed.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors"
                    title={t('deleteFeed')}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal: Add New RSS Feed */}
      {showAddFeedModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <h3 className="font-bold text-base text-slate-800">{t('modalAddFeedTitle')}</h3>
              <button onClick={() => setShowAddFeedModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateFeed} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('modalFeedName')}</label>
                <input
                  type="text"
                  required
                  value={newFeed.name}
                  onChange={(e) => setNewFeed({ ...newFeed, name: e.target.value })}
                  placeholder="Ex: Fondation Mohammed VI Environnement"
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('modalFeedNameAr')}</label>
                <input
                  type="text"
                  value={newFeed.name_ar}
                  onChange={(e) => setNewFeed({ ...newFeed, name_ar: e.target.value })}
                  placeholder="مثال: مؤسسة محمد السادس لحماية البيئة"
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('modalFeedUrl')}</label>
                <input
                  type="url"
                  required
                  value={newFeed.url}
                  onChange={(e) => setNewFeed({ ...newFeed, url: e.target.value })}
                  placeholder="https://example.org/rss.xml"
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-mono text-left"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('modalFeedCategory')}</label>
                <select
                  value={newFeed.category}
                  onChange={(e) => setNewFeed({ ...newFeed, category: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-semibold"
                >
                  <option value="international">
                    {language === 'fr' ? 'International' : language === 'en' ? 'International' : 'دولي (International)'}
                  </option>
                  <option value="national">
                    {language === 'fr' ? 'National Maroc' : language === 'en' ? 'National Morocco' : 'وطني مغربي (National Maroc)'}
                  </option>
                  <option value="bilateral">
                    {language === 'fr' ? 'Coopération Bilatérale' : language === 'en' ? 'Bilateral Cooperation' : 'ثنائي (Coopération Bilatérale)'}
                  </option>
                  <option value="regional">
                    {language === 'fr' ? 'Régional Fès-Meknès' : language === 'en' ? 'Regional Fez-Meknes' : 'جهوي فاس مكناس (Régional)'}
                  </option>
                </select>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('modalFeedFocus')}</label>
                <input
                  type="text"
                  value={newFeed.focus}
                  onChange={(e) => setNewFeed({ ...newFeed, focus: e.target.value })}
                  placeholder={language === 'fr' ? "Ex: Projets société civile, forêts et eau..." : language === 'en' ? "Ex: Civil society grants, forest and water..." : "مثال: منح المجتمع المدني، حماية الغابات والمياه..."}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddFeedModal(false)}
                  className="px-4 py-2 rounded-lg text-slate-600 font-bold hover:bg-slate-100"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-afmi-forest text-white font-bold hover:bg-afmi-emerald shadow-sm"
                >
                  {t('addFeedAction')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
