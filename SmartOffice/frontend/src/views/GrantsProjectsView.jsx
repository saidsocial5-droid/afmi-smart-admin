import React, { useState, useEffect } from 'react';
import { 
  Briefcase, 
  FileCheck, 
  Plus, 
  Calendar, 
  User, 
  DollarSign, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  X, 
  Target, 
  Trees, 
  Globe, 
  Search, 
  ExternalLink, 
  Sparkles, 
  Download, 
  Bot, 
  Filter, 
  ShieldCheck, 
  ArrowRight,
  RefreshCw,
  BookmarkPlus,
  Rss,
  Compass
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, getApiBaseUrl } from '../apiClient';

export default function GrantsProjectsView({ 
  grants = [], 
  projects = [], 
  onRefreshData,
  onSelectAgent,
  onNavigateTab
}) {
  const { language, t, isRtl } = useLanguage();
  const [subTab, setSubTab] = useState("internet_search"); // "internet_search", "grants", "projects"
  const [showAddGrantModal, setShowAddGrantModal] = useState(false);
  const [showAddProjectModal, setShowAddProjectModal] = useState(false);

  // Internet Search State
  const [searchKeywords, setSearchKeywords] = useState("");
  const [searchCategory, setSearchCategory] = useState("all");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [donorPortals, setDonorPortals] = useState([]);
  const [importSuccessMsg, setImportSuccessMsg] = useState("");

  // New Grant Form State
  const [newGrant, setNewGrant] = useState({
    title: "",
    donor: "GEF Small Grants Programme (PNUD Maroc)",
    funding_program: "Appel à Projets Biodiversité 2026",
    amount_requested: 500000,
    currency: "MAD",
    strategic_axis: "Forest ecosystems conservation and biodiversity monitoring in the Middle Atlas",
    status: "Draft",
    deadline: "2026-12-31",
    focal_point: "Coordonnateur AFMI",
    summary: ""
  });

  // New Project Form State
  const [newProject, setNewProject] = useState({
    code: `AFMI-2026-${Math.floor(10 + Math.random() * 90)}`,
    title: "",
    donor: "Agence Nationale des Eaux et Forêts (ANEF)",
    total_budget: 400000,
    spent_budget: 0,
    currency: "MAD",
    start_date: "2026-10-01",
    end_date: "2027-09-30",
    status: "In Progress",
    location: "Azrou / Timahdite",
    beneficiaries: "Coopératives locales et éleveurs",
    strategic_axis: "Rangeland restoration and traditional pastoral management (Agdal practices)"
  });

  // Load official donor portals and run initial smart search
  useEffect(() => {
    apiFetch('/api/grants/donor-portals')
      .then(r => r.json())
      .then(data => setDonorPortals(data || []))
      .catch(err => console.error(err));

    handleInternetSearch("Environnement Forêt Moyen Atlas Maroc");
  }, []);

  const handleInternetSearch = async (kw) => {
    const query = kw !== undefined ? kw : searchKeywords;
    setIsSearching(true);
    setImportSuccessMsg("");

    try {
      const res = await apiFetch('/api/grants/search-internet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          keywords: query,
          category: searchCategory,
          theme: "all"
        })
      });

      if (!res.ok) throw new Error("Erreur de recherche");
      const data = await res.json();
      setSearchResults(data.opportunities || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSearching(false);
    }
  };

  const handleImportOpportunity = async (opp) => {
    try {
      const res = await apiFetch('/api/grants/import-opportunity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: opp.title,
          donor: opp.donor,
          portal_url: opp.portal_url,
          amount_mad: opp.amount_mad,
          currency: opp.currency || "MAD",
          deadline: opp.deadline,
          strategic_axis: opp.strategic_axis,
          eligibility_summary: opp.eligibility_summary,
          action_recommendation: opp.action_recommendation
        })
      });

      if (res.ok) {
        setImportSuccessMsg(`تمت إضافة فرصة "${opp.title}" مباشرة إلى محفظة طلبات التمويل.`);
        if (onRefreshData) onRefreshData();
        setTimeout(() => setImportSuccessMsg(""), 5000);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleDraftWithAi = (opp) => {
    // If agent navigator provided, select grant writer and pass context
    if (onSelectAgent) {
      onSelectAgent("agent_grant_writer");
    } else if (onNavigateTab) {
      onNavigateTab("agents");
    }
  };

  const handleCreateGrant = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch("/api/grants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newGrant)
      });
      if (res.ok) {
        setShowAddGrantModal(false);
        if (onRefreshData) onRefreshData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateProject = async (e) => {
    e.preventDefault();
    try {
      const res = await apiFetch("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newProject)
      });
      if (res.ok) {
        setShowAddProjectModal(false);
        if (onRefreshData) onRefreshData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner & SubTab Navigation */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-afmi-lightmint text-afmi-forest font-bold">🌐</span>
            <h2 className="text-xl font-extrabold text-afmi-dark">
              {t('grantsTitle')}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t('grantsSubtitle')}
          </p>
        </div>

        {/* Tab Switcher & Action Buttons */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-100 p-1 rounded-xl flex items-center">
            
            <button
              onClick={() => setSubTab("internet_search")}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                subTab === "internet_search"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <Globe className="w-3.5 h-3.5 text-afmi-gold" />
              <span>{t('tabInternetSearch')} ({searchResults.length})</span>
            </button>

            <button
              onClick={() => setSubTab("grants")}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                subTab === "grants"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t('tabGrantsPipeline')} ({grants.length})
            </button>

            <button
              onClick={() => setSubTab("projects")}
              className={`px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
                subTab === "projects"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t('tabProjectsMe')} ({projects.length})
            </button>

            <button
              onClick={() => onNavigateTab ? onNavigateTab("radar") : null}
              className="px-3.5 py-2 rounded-lg text-xs font-bold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 transition-all flex items-center gap-1.5 ml-1"
              title={t('radarSubtitle')}
            >
              <Rss className="w-3.5 h-3.5 text-amber-600" />
              <span>{t('tabRssRadarNav')}</span>
            </button>

          </div>

          {subTab === "grants" && (
            <button
              onClick={() => setShowAddGrantModal(true)}
              className="px-3.5 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t('addGrantManual')}</span>
            </button>
          )}

          {subTab === "projects" && (
            <button
              onClick={() => setShowAddProjectModal(true)}
              className="px-3.5 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>{t('addProjectManual')}</span>
            </button>
          )}
        </div>
      </div>

      {importSuccessMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{importSuccessMsg}</span>
        </div>
      )}

      {/* SUBTAB 1: LIVE INTERNET GRANT SEARCH */}
      {subTab === "internet_search" && (
        <div className="space-y-5">
          
          {/* Search Box Card */}
          <div className="afmi-card p-5 space-y-4">
            
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className={`w-4 h-4 text-slate-400 absolute ${isRtl ? 'right-3.5' : 'left-3.5'} top-3.5 pointer-events-none`} />
                <input
                  type="text"
                  value={searchKeywords}
                  onChange={(e) => setSearchKeywords(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleInternetSearch()}
                  placeholder={t('searchKwPlaceholder')}
                  className={`w-full ${isRtl ? 'pr-10 pl-4' : 'pl-10 pr-4'} py-2.5 bg-slate-50 border border-slate-200 focus:border-afmi-forest rounded-xl text-xs font-medium outline-none`}
                />
              </div>

              {/* Category Filter */}
              <select
                value={searchCategory}
                onChange={(e) => setSearchCategory(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-700 outline-none"
              >
                <option value="all">{t('allDonorsOption')}</option>
                <option value="national">{t('nationalDonorsOption')}</option>
                <option value="international">{t('internationalDonorsOption')}</option>
                <option value="marches_publics">{t('publicTendersOption')}</option>
              </select>

              <button
                onClick={() => handleInternetSearch()}
                disabled={isSearching}
                className="px-5 py-2.5 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center gap-2 shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-afmi-gold ${isSearching ? 'animate-spin' : ''}`} />
                <span>{isSearching ? t('scanningInternet') : t('scanInternetBtn')}</span>
              </button>
            </div>

            {/* Quick Themes Suggestion Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100 text-xs">
              <span className="text-[11px] font-bold text-slate-400">{t('quickSearchesTitle')}</span>
              {(language === 'fr' ? [
                "🌲 Conservation du cèdre et biodiversité",
                "🏞️ Écotourisme et sentiers botaniques",
                "🎓 Renforcement des capacités associatives",
                "📚 Éducation environnementale en milieu scolaire",
                "☀️ Énergies renouvelables et efficacité rurale",
                "🌍 Développement durable et coopératives vertes",
                "💧 Surveillance des ressources en eau",
                "🐑 Gestion pastorale concertée et système Agdal"
              ] : language === 'en' ? [
                "🌲 Cedar conservation and biodiversity monitoring",
                "🏞️ Ecotourism and botanical nature trails",
                "🎓 NGO capacity building and empowerment",
                "📚 Environmental education in local schools",
                "☀️ Renewable energy and clean rural power",
                "🌍 Sustainable development and circular economy",
                "💧 Surface water monitoring and lake protection",
                "🐑 Community pastoral management and Agdal"
              ] : [
                "🌲 حماية غابات الأرز والتنوع البيولوجي",
                "🏞️ السياحة الإيكولوجية ومسارات الطبيعة بالأطلس",
                "🎓 تقوية القدرات والتمكين المؤسساتي للجمعيات",
                "📚 التربية البيئية والمواطنة الإيكولوجية بالمدارس",
                "☀️ الطاقات المتجددة والنجاعة الطاقية بالعالم القروي",
                "🌍 التنمية المستدامة والاقتصاد الدائري والمقاولات الخضراء",
                "💧 حماية المناطق الرطبة وبحيرات الأطلس المتوسط",
                "🐑 التدبير الرعوي التشاركي ونظام أكدال بتمحضيت"
              ]).map((pill, pIdx) => (
                <button
                  key={pIdx}
                  onClick={() => {
                    setSearchKeywords(pill);
                    handleInternetSearch(pill);
                  }}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-afmi-lightmint hover:text-afmi-forest text-slate-600 text-[11px] font-medium transition-colors"
                >
                  {pill}
                </button>
              ))}
            </div>

          </div>

          {/* Search Results Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {searchResults.map((opp, idx) => (
              <div 
                key={idx}
                className="afmi-card p-5 border-t-4 border-t-afmi-forest flex flex-col justify-between hover:shadow-md transition-shadow"
              >
                <div>
                  
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3 mb-2.5">
                    <span className="text-xs font-extrabold text-afmi-forest bg-afmi-lightmint px-2.5 py-1 rounded-lg">
                      🏛️ {opp.donor}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        opp.status === 'Ouvert' ? 'bg-emerald-100 text-emerald-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {opp.status === 'Ouvert' ? (language === 'ar' ? '● مفتوح حالياً' : (language === 'en' ? '● Open' : '● Ouvert')) : (language === 'ar' ? '● دوري سنوي' : (language === 'en' ? '● Periodic' : '● Récurrent'))}
                      </span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-amber-50 text-amber-800 border border-amber-200">
                        {t('matchScore')} {opp.match_score || 95}%
                      </span>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="font-bold text-sm md:text-base text-slate-800 leading-snug mb-2">
                    {opp.title}
                  </h3>

                  {/* Eligibility & Recommendation */}
                  <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-xl border border-slate-100 mb-3">
                    <strong className="text-slate-700 block mb-1">{t('eligibilitySummary')}</strong>
                    {opp.eligibility_summary}
                    {opp.action_recommendation && (
                      <span className="block mt-1.5 text-afmi-forest font-semibold text-[11px]">
                        {t('actionTip')} {opp.action_recommendation}
                      </span>
                    )}
                  </p>

                  {/* Financial & Deadline Stats */}
                  <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                    <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">{t('maxGrantExpected')}</span>
                      <span className="font-black text-afmi-forest text-sm font-mono">
                        {opp.amount_mad ? opp.amount_mad.toLocaleString() : '500,000'} {opp.currency || t('currencyMAD')}
                      </span>
                    </div>
                    <div className="bg-slate-50/80 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-[10px] text-slate-400 block font-semibold">{t('deadline')}</span>
                      <span className="font-bold text-slate-700 text-xs flex items-center gap-1 mt-0.5 font-mono">
                        <Clock className="w-3 h-3 text-amber-600" />
                        {opp.deadline || (language === 'ar' ? 'مستمر' : (language === 'en' ? 'Rolling' : 'Continu'))}
                      </span>
                    </div>
                  </div>

                </div>

                {/* Bottom Actions */}
                <div className="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                  
                  {opp.portal_url && (
                    <a
                      href={opp.portal_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] font-bold text-slate-500 hover:text-afmi-forest flex items-center gap-1"
                    >
                      <span>{t('visitPortal')}</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleImportOpportunity(opp)}
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
                      <span>{t('draftWithAi')}</span>
                    </button>
                  </div>

                </div>

              </div>
            ))}
          </div>

          {/* Official Donor Portals Directory Carousel */}
          <div className="afmi-card p-5 mt-6">
            <h3 className="font-bold text-slate-800 text-sm mb-3 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-afmi-forest" />
              <span>{t('donorPortalsDirectory')}</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {donorPortals.map((portal) => (
                <a
                  key={portal.id}
                  href={portal.portal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-3 rounded-xl border border-slate-200 hover:border-afmi-mint bg-slate-50/60 hover:bg-white transition-all group block text-right"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-xs text-afmi-forest group-hover:text-emerald-700">
                      {portal.acronym}
                    </span>
                    <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-afmi-forest" />
                  </div>
                  <h4 className="text-[11px] font-semibold text-slate-700 line-clamp-1">{portal.name}</h4>
                  <div className="flex items-center justify-between text-[10px] text-slate-400 mt-2">
                    <span>سقف: {portal.max_grant_mad ? (portal.max_grant_mad / 1000).toLocaleString() + ' kDH' : 'متغير'}</span>
                    <span className="text-emerald-600 font-bold">{portal.relevance_afmi}</span>
                  </div>
                </a>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* SUBTAB 2: EXISTING GRANTS PIPELINE */}
      {subTab === "grants" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {grants.map((grant) => (
            <div key={grant.id} className="afmi-card p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <span className="text-xs font-bold text-afmi-forest bg-afmi-lightmint px-2.5 py-1 rounded-lg">
                    {grant.donor}
                  </span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    grant.status === 'Approved' ? 'bg-emerald-100 text-emerald-800' :
                    grant.status === 'Under Review' ? 'bg-amber-100 text-amber-800' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {grant.status === 'Under Review' ? (language === 'ar' ? 'قيد الدراسة' : (language === 'en' ? 'Under Review' : 'En examen')) :
                     grant.status === 'Approved' ? (language === 'ar' ? 'تمت الموافقة' : (language === 'en' ? 'Approved' : 'Approuvé')) :
                     (language === 'ar' ? 'مسودة' : (language === 'en' ? 'Draft' : 'Brouillon'))}
                  </span>
                </div>

                <h3 className="font-bold text-base text-slate-800 mt-2 mb-1.5 leading-snug">
                  {grant.title}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed mb-4">
                  {grant.summary || (language === 'ar' ? "مشروع يهدف إلى دعم استدامة غابات الأرز وتنمية الاقتصاد الأخضر." : "Projet dédié à la résilience des forêts de cèdre et à l'économie verte locale.")}
                </p>

                <div className="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-100 mb-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t('requestedAmount')}</span>
                    <span className="font-bold text-afmi-forest font-mono">
                      {grant.amount_requested?.toLocaleString()} {grant.currency || t('currencyMAD')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t('submissionDeadline')}</span>
                    <span className="font-semibold text-slate-700 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {grant.deadline || (language === 'ar' ? 'مفتوح' : (language === 'en' ? 'Open' : 'Ouvert'))}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">{t('focalPoint')}</span>
                    <span className="font-semibold text-slate-700">{grant.focal_point || 'AFMI Team'}</span>
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                <span className="text-[11px] text-slate-400 font-medium truncate max-w-[240px]">
                  🎯 {grant.strategic_axis}
                </span>
                <button
                  onClick={() => handleDraftWithAi(grant)}
                  className="font-bold text-afmi-forest hover:underline flex items-center gap-1"
                >
                  <span>{t('draftWithExpert')}</span>
                  <ArrowRight className={`w-3 h-3 ${isRtl ? 'transform rotate-180' : ''}`} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* SUBTAB 3: PROJECTS & M&E KPIS */}
      {subTab === "projects" && (
        <div className="space-y-4">
          {projects.map((proj) => {
            const burnRate = Math.round((proj.spent_budget / (proj.total_budget || 1)) * 100);
            return (
              <div key={proj.id} className="afmi-card p-6">
                
                {/* Project Header */}
                <div className="flex flex-wrap items-start justify-between gap-4 mb-4 pb-4 border-b border-slate-100">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-afmi-lightmint text-afmi-forest">
                        {proj.code}
                      </span>
                      <span className="text-xs font-bold text-slate-600">
                        {proj.donor}
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                        {proj.status}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-slate-800">{proj.title}</h3>
                    <p className="text-xs text-slate-500 mt-1">
                      {t('location')}: <span className="font-semibold text-slate-700">{proj.location}</span> | {t('beneficiaries')}: <span className="font-semibold text-slate-700">{proj.beneficiaries}</span>
                    </p>
                  </div>

                  {/* Financial Metrics */}
                  <div className="text-start bg-slate-50 px-4 py-3 rounded-xl border border-slate-200 shrink-0">
                    <span className="text-[10px] font-bold text-slate-400 block uppercase">{t('totalProjectBudget')}</span>
                    <span className="text-base font-black text-afmi-forest">
                      {proj.total_budget?.toLocaleString()} {proj.currency || t('currencyMAD')}
                    </span>
                    <div className="text-[11px] text-slate-500 mt-1">
                      {t('projectExpenses')}: <span className="font-bold text-blue-600">{proj.spent_budget?.toLocaleString()} {proj.currency || t('currencyMAD')}</span> ({burnRate}%)
                    </div>
                  </div>
                </div>

                {/* Burn Rate Bar */}
                <div className="mb-5">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-600 mb-1">
                    <span>{t('burnRateLabel')}</span>
                    <span className="font-mono text-blue-600">{burnRate}%</span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-afmi-forest h-2 rounded-full" 
                      style={{ width: `${Math.min(100, burnRate)}%` }}
                    ></div>
                  </div>
                </div>

                {/* KPIs Grid */}
                {proj.kpis && proj.kpis.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <Target className="w-3.5 h-3.5 text-afmi-forest" />
                      <span>{t('meKpisLabel')}</span>
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {proj.kpis.map((kpi, kIdx) => {
                        const progress = Math.round((kpi.achieved / (kpi.target || 1)) * 100);
                        return (
                          <div key={kIdx} className="p-3 bg-slate-50/80 rounded-xl border border-slate-200/80">
                            <span className="text-xs font-semibold text-slate-700 block mb-1">
                              {kpi.name}
                            </span>
                            <div className="flex items-baseline justify-between text-xs mb-1">
                              <span className="font-bold text-afmi-forest text-sm font-mono">
                                {kpi.achieved} <span className="text-[10px] text-slate-400 font-normal">{kpi.unit}</span>
                              </span>
                              <span className="text-[11px] text-slate-400">
                                {t('target')}: {kpi.target} {kpi.unit}
                              </span>
                            </div>
                            <div className="w-full bg-slate-200 rounded-full h-1 overflow-hidden">
                              <div 
                                className="bg-emerald-600 h-1 rounded-full" 
                                style={{ width: `${Math.min(100, progress)}%` }}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Add Grant */}
      {showAddGrantModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <h3 className="font-bold text-base text-slate-800">
                {language === 'fr' ? "Ajouter une Opportunité de Financement" : (language === 'en' ? "Add New Funding Opportunity" : "إضافة طلب تمويل جديد (Nouvelle Subvention)")}
              </h3>
              <button onClick={() => setShowAddGrantModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateGrant} className="space-y-3 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  {language === 'fr' ? "Titre du projet proposé" : (language === 'en' ? "Proposed Project Title" : "عنوان المشروع المقترح")}
                </label>
                <input
                  type="text"
                  required
                  value={newGrant.title}
                  onChange={(e) => setNewGrant({ ...newGrant, title: e.target.value })}
                  placeholder={language === 'ar' ? "مثال: حماية التنوع البيولوجي وتأهيل المسالك الإيكولوجية" : "Ex: Préservation de la biodiversité et sentiers écotouristiques"}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Bailleur ciblé" : (language === 'en' ? "Target Donor" : "الجهة المانحة المستهدفة")}
                  </label>
                  <input
                    type="text"
                    required
                    value={newGrant.donor}
                    onChange={(e) => setNewGrant({ ...newGrant, donor: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Montant sollicité (DH)" : (language === 'en' ? "Requested Amount (MAD)" : "المبلغ المطلوب (درهم)")}
                  </label>
                  <input
                    type="number"
                    required
                    value={newGrant.amount_requested}
                    onChange={(e) => setNewGrant({ ...newGrant, amount_requested: parseFloat(e.target.value) || 0 })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  {language === 'fr' ? "Échéance de soumission (Deadline)" : (language === 'en' ? "Submission Deadline" : "الموعد النهائي للتقديم (Deadline)")}
                </label>
                <input
                  type="date"
                  value={newGrant.deadline}
                  onChange={(e) => setNewGrant({ ...newGrant, deadline: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-mono"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  {language === 'fr' ? "Résumé du concept" : (language === 'en' ? "Concept Summary" : "ملخص الفكرة التنموية")}
                </label>
                <textarea
                  rows="3"
                  value={newGrant.summary}
                  onChange={(e) => setNewGrant({ ...newGrant, summary: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                  placeholder={language === 'ar' ? "وصف موجز للمخرجات والأثر الميداني المتوقع..." : "Description concise des livrables et impacts terrain..."}
                ></textarea>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddGrantModal(false)}
                  className="px-4 py-2 rounded-lg text-slate-600 font-bold hover:bg-slate-100"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-afmi-forest text-white font-bold hover:bg-afmi-emerald shadow-sm"
                >
                  {language === 'fr' ? "Enregistrer" : (language === 'en' ? "Save Opportunity" : "حفظ الفرصة")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Add Project */}
      {showAddProjectModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
              <h3 className="font-bold text-base text-slate-800">
                {language === 'fr' ? "Ajouter un Projet de Terrain" : (language === 'en' ? "Add New Field Project" : "إضافة مشروع ميداني جديد (Nouveau Projet)")}
              </h3>
              <button onClick={() => setShowAddProjectModal(false)} className="text-slate-400 hover:text-slate-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Code Projet" : (language === 'en' ? "Project Code" : "رمز المشروع (Code)")}
                  </label>
                  <input
                    type="text"
                    required
                    value={newProject.code}
                    onChange={(e) => setNewProject({ ...newProject, code: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-mono font-bold"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Bailleur / Partenaire" : (language === 'en' ? "Donor / Partner" : "المانح / الشريك المالي")}
                  </label>
                  <input
                    type="text"
                    required
                    value={newProject.donor}
                    onChange={(e) => setNewProject({ ...newProject, donor: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                  />
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">
                  {language === 'fr' ? "Intitulé du Projet" : (language === 'en' ? "Project Title" : "عنوان المشروع")}
                </label>
                <input
                  type="text"
                  required
                  value={newProject.title}
                  onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                  className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Budget Alloué (DH)" : (language === 'en' ? "Allocated Budget (MAD)" : "الميزانية المخصصة (درهم)")}
                  </label>
                  <input
                    type="number"
                    required
                    value={newProject.total_budget}
                    onChange={(e) => setNewProject({ ...newProject, total_budget: parseFloat(e.target.value) || 0 })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest font-mono"
                  />
                </div>
                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {language === 'fr' ? "Localisation au Moyen Atlas" : (language === 'en' ? "Middle Atlas Location" : "موقع التدخل بالأطلس")}
                  </label>
                  <input
                    type="text"
                    value={newProject.location}
                    onChange={(e) => setNewProject({ ...newProject, location: e.target.value })}
                    className="w-full border border-slate-200 rounded-lg p-2.5 outline-none focus:border-afmi-forest"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowAddProjectModal(false)}
                  className="px-4 py-2 rounded-lg text-slate-600 font-bold hover:bg-slate-100"
                >
                  {t('cancel')}
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-lg bg-afmi-forest text-white font-bold hover:bg-afmi-emerald shadow-sm"
                >
                  {language === 'fr' ? "Enregistrer le Projet" : (language === 'en' ? "Register Project" : "تسجيل المشروع")}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
