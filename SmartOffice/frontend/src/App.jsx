import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardView from './views/DashboardView';
import AgentsWorkspaceView from './views/AgentsWorkspaceView';
import OcrFinanceLabView from './views/OcrFinanceLabView';
import GrantsProjectsView from './views/GrantsProjectsView';
import AgentStudioView from './views/AgentStudioView';
import InstitutionalMemoryView from './views/InstitutionalMemoryView';
import ProjectRadarView from './views/ProjectRadarView';
import WorkflowsView from './views/WorkflowsView';
import PayrollView from './views/PayrollView';
import StatementsView from './views/StatementsView';
import DocumentEditor from './editor/DocumentEditor';
import ChartsTemplatesView from './views/ChartsTemplatesView';
import PhotosView from './views/PhotosView';
import AnnualReportsView from './views/AnnualReportsView';
import IndicatorsView from './views/IndicatorsView';
import ProjectDocumentsView from './views/ProjectDocumentsView';
import SettingsView, { applyAppearance } from './views/SettingsView';
import MeetingsView from './views/MeetingsView';
import FoldersView from './views/FoldersView';
import Project360View from './views/Project360View';
import { apiFetch } from './apiClient';
import { useLanguage } from './context/LanguageContext';


export default function App() {
  // Onglet ouvert par le fragment d'URL (#settings…) : l'application de bureau ouvre ainsi directement une page
  const tabFromHash = () => (typeof window !== 'undefined' && window.location.hash.length > 1 ? decodeURIComponent(window.location.hash.slice(1)) : 'dashboard');
  const [activeTab, setActiveTab] = useState(tabFromHash);
  useEffect(() => {
    const onHash = () => setActiveTab(tabFromHash());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  // L'onglet courant est reflété dans l'URL (sans recharger) : l'application de bureau peut y revenir
  useEffect(() => { if (window.location.hash.slice(1) !== activeTab) window.history.replaceState(null, '', `#${activeTab}`); }, [activeTab]);
  const [selectedAgentId, setSelectedAgentId] = useState("agent_grant_writer");
  
  // App Global State
  const [projects, setProjects] = useState([]);
  const [grants, setGrants] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [financeSummary, setFinanceSummary] = useState({});
  const [llmConfig, setLlmConfig] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [editorDocumentId, setEditorDocumentId] = useState(null);   // document à ouvrir dans l'éditeur (rapports générés)

  const fetchGlobalData = async () => {
    setIsRefreshing(true);
    try {
      const [pRes, gRes, tRes, sRes, lRes] = await Promise.all([
        apiFetch('/api/projects').then(r => r.json()).catch(() => []),
        apiFetch('/api/grants').then(r => r.json()).catch(() => []),
        apiFetch('/api/finance/transactions').then(r => r.json()).catch(() => []),
        apiFetch('/api/finance/summary').then(r => r.json()).catch(() => ({})),
        apiFetch('/api/settings/llm-config').then(r => r.json()).catch(() => null)
      ]);

      setProjects(pRes || []);
      setGrants(gRes || []);
      setTransactions(tRes || []);
      setFinanceSummary(sRes || {});
      setLlmConfig(lRes);
    } catch (err) {
      console.error("Error fetching global data:", err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchGlobalData();
    // Apparence enregistrée (Paramètres › Apparence) : taille du texte, couleur principale
    apiFetch('/api/settings/registry').then((r) => (r.ok ? r.json() : null)).then((snap) => {
      if (!snap) return;
      const values = Object.fromEntries(snap.sections.flatMap((s) => s.fields).filter((f) => f.key.startsWith('ui.')).map((f) => [f.key, f.value]));
      applyAppearance(values);
      // Langue réglée dans les paramètres, tant que l'utilisateur n'en a pas choisi une lui-même
      let chosen = null;
      try { chosen = localStorage.getItem('afmi_lang'); } catch { /* stockage indisponible */ }
      if (!chosen && values['ui.language']) setLanguage(values['ui.language']);
    }).catch(() => {});
  }, []);

  const { language, dir, isRtl, setLanguage } = useLanguage();

  const handleSelectAgentFromDashboard = (agentId) => {
    setSelectedAgentId(agentId);
    setActiveTab("agents");
  };

  // Mode intégré (#editor-embed/<id>) : l'application de bureau affiche l'éditeur seul dans l'onglet Projet › Rapports
  const p360Embed = activeTab.match(/^project360-embed\/(\d+)/);
  if (p360Embed) {
    return (
      <div dir={dir} className={`min-h-screen bg-afmi-slate p-3 ${isRtl ? 'font-arabic' : 'font-sans'} text-slate-800`}>
        <Project360View fixedProjectId={Number(p360Embed[1])} onNavigate={(tab) => { window.location.hash = tab; }} />
      </div>
    );
  }
  const meetingsEmbed = activeTab.match(/^meetings-embed\/(\d+)/);
  if (meetingsEmbed) {
    return (
      <div dir={dir} className={`min-h-screen bg-afmi-slate p-3 ${isRtl ? 'font-arabic' : 'font-sans'} text-slate-800`}>
        <MeetingsView fixedProjectId={Number(meetingsEmbed[1])} embedded />
      </div>
    );
  }
  const embed = activeTab.match(/^editor-embed\/(\d+)/);
  if (embed) {
    return (
      <div dir={dir} className={`min-h-screen bg-afmi-slate p-3 ${isRtl ? 'font-arabic' : 'font-sans'} text-slate-800`}>
        <DocumentEditor key={embed[1]} initialDocumentId={Number(embed[1])} embedded />
      </div>
    );
  }

  return (
    <div 
      dir={dir}
      className={`min-h-screen bg-afmi-slate flex flex-col ${isRtl ? 'font-arabic' : 'font-sans'} text-slate-800 selection:bg-afmi-lightmint selection:text-afmi-forest`}
    >
      
      {/* Institutional Top Header */}
      <Header 
        activeTab={activeTab}
        onNavigate={setActiveTab}
        onRefresh={fetchGlobalData}
        llmConfig={llmConfig}
        totalBudget={projects.reduce((acc, p) => acc + (p.total_budget || 0), 0)}
        totalBalance={financeSummary.current_balance}
      />

      <div className="flex flex-1">
        
        {/* Right-To-Left Sidebar */}
        <Sidebar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
        />

        {/* Main Content Area */}
        <main className={`flex-1 p-4 md:p-6 lg:p-8 mx-auto w-full overflow-y-auto ${["statements", "editor", "meetings"].includes(activeTab) ? "max-w-none min-w-0" : "max-w-7xl"}`}>
          {activeTab === "dashboard" && (
            <DashboardView 
              projects={projects}
              grants={grants}
              transactions={transactions}
              financeSummary={financeSummary}
              onSelectAgent={handleSelectAgentFromDashboard}
              onNavigateTab={setActiveTab}
            />
          )}

          {activeTab === "agents" && (
            <AgentsWorkspaceView 
              selectedAgentId={selectedAgentId}
              onSelectAgent={setSelectedAgentId}
            />
          )}

          {activeTab === "workflows" && (
            <WorkflowsView />
          )}

          {activeTab === "payroll" && (
            <PayrollView />
          )}

          {activeTab === "editor" && (
            <DocumentEditor initialDocumentId={editorDocumentId} />
          )}

          {activeTab === "reports" && (
            <AnnualReportsView onOpenDocument={(id) => { setEditorDocumentId(id); setActiveTab("editor"); }} />
          )}

          {activeTab === "indicators" && (
            <IndicatorsView />
          )}

          {activeTab === "ged" && (
            <ProjectDocumentsView />
          )}

          {activeTab === "charts" && (
            <ChartsTemplatesView />
          )}

          {activeTab === "photos" && (
            <PhotosView />
          )}

          {activeTab === "statements" && (
            <StatementsView />
          )}

          {activeTab === "ocr" && (
            <OcrFinanceLabView 
              onTransactionsUpdated={fetchGlobalData}
            />
          )}

          {activeTab === "grants" && (
            <GrantsProjectsView 
              grants={grants}
              projects={projects}
              onRefreshData={fetchGlobalData}
              onSelectAgent={handleSelectAgentFromDashboard}
              onNavigateTab={setActiveTab}
            />
          )}

          {activeTab === "radar" && (
            <ProjectRadarView 
              onSelectAgent={handleSelectAgentFromDashboard}
              onNavigateTab={setActiveTab}
              onRefreshGlobal={fetchGlobalData}
            />
          )}

          {activeTab === "studio" && (
            <AgentStudioView />
          )}

          {activeTab === "project360" && (
            <Project360View onNavigate={setActiveTab} />
          )}

          {activeTab === "folders" && (
            <FoldersView />
          )}

          {activeTab === "meetings" && (
            <MeetingsView />
          )}

          {activeTab === "settings" && (
            <SettingsView onNavigate={setActiveTab} />
          )}

          {activeTab === "memory" && (
            <InstitutionalMemoryView 
              onConfigUpdated={fetchGlobalData}
            />
          )}
        </main>

      </div>

    </div>
  );
}
