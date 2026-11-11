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
import { apiFetch } from './apiClient';
import { useLanguage } from './context/LanguageContext';


export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedAgentId, setSelectedAgentId] = useState("agent_grant_writer");
  
  // App Global State
  const [projects, setProjects] = useState([]);
  const [grants, setGrants] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [financeSummary, setFinanceSummary] = useState({});
  const [llmConfig, setLlmConfig] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

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
  }, []);

  const { language, dir, isRtl } = useLanguage();

  const handleSelectAgentFromDashboard = (agentId) => {
    setSelectedAgentId(agentId);
    setActiveTab("agents");
  };

  return (
    <div 
      dir={dir}
      className={`min-h-screen bg-afmi-slate flex flex-col ${isRtl ? 'font-arabic' : 'font-sans'} text-slate-800 selection:bg-afmi-lightmint selection:text-afmi-forest`}
    >
      
      {/* Institutional Top Header */}
      <Header 
        activeTab={activeTab}
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
        <main className={`flex-1 p-4 md:p-6 lg:p-8 mx-auto w-full overflow-y-auto ${["statements", "editor"].includes(activeTab) ? "max-w-none min-w-0" : "max-w-7xl"}`}>
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
            <DocumentEditor />
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
