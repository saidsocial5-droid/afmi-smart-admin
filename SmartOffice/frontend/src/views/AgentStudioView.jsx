import React, { useState, useEffect } from 'react';
import { 
  Sliders, 
  Bot, 
  Cpu, 
  Save, 
  CheckCircle, 
  RefreshCw, 
  Puzzle, 
  Sparkles, 
  Code,
  ShieldAlert,
  Layers
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch } from '../apiClient';

export default function AgentStudioView() {
  const { language, t, isRtl } = useLanguage();
  const [agents, setAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState("agent_grant_writer");
  const [pluginsData, setPluginsData] = useState({ plugins: [], total_active: 0 });
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");
  const [reloadMsg, setReloadMsg] = useState("");

  const getAgentTitle = (ag) => {
    if (!ag) return "";
    if (ag.id === "agent_grant_writer") return t("agentGrantWriterTitle");
    if (ag.id === "agent_project_manager") return t("agentProjectManagerTitle");
    if (ag.id === "agent_finance_auditor") return t("agentFinanceAuditorTitle");
    if (ag.id === "agent_communications") return t("agentCommunicationsTitle");
    return language === "ar" ? ag.name_ar : (language === "en" ? (ag.name_en || ag.name_fr) : ag.name_fr);
  };

  // Editable config state
  const [currentConfig, setCurrentConfig] = useState({
    system_prompt: "",
    temperature: 0.4,
    model_provider: "gemini",
    model_name: "gemini-2.5-flash",
    custom_instructions: "",
    active_tools: [],
    registered_tools: []
  });

  const fetchAgentsAndPlugins = () => {
    apiFetch('/api/agents')
      .then(res => res.json())
      .then(data => {
        setAgents(data);
        const cur = data.find(a => a.id === selectedAgentId) || data[0];
        if (cur) {
          setCurrentConfig({
            system_prompt: cur.system_prompt || "",
            temperature: cur.temperature || 0.4,
            model_provider: cur.model_provider || "gemini",
            model_name: cur.model_name || "gemini-2.5-flash",
            custom_instructions: cur.custom_instructions || "",
            active_tools: cur.active_tools || [],
            registered_tools: cur.registered_tools || []
          });
        }
      });

    apiFetch('/api/plugins')
      .then(res => res.json())
      .then(data => setPluginsData(data))
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchAgentsAndPlugins();
  }, [selectedAgentId]);

  const handleSelectAgent = (agentId) => {
    setSelectedAgentId(agentId);
    const cur = agents.find(a => a.id === agentId);
    if (cur) {
      setCurrentConfig({
        system_prompt: cur.system_prompt || "",
        temperature: cur.temperature || 0.4,
        model_provider: cur.model_provider || "gemini",
        model_name: cur.model_name || "gemini-2.5-flash",
        custom_instructions: cur.custom_instructions || "",
        active_tools: cur.active_tools || [],
        registered_tools: cur.registered_tools || []
      });
    }
  };

  const handleToggleTool = (toolName) => {
    const active = [...currentConfig.active_tools];
    const index = active.indexOf(toolName);
    if (index > -1) {
      active.splice(index, 1);
    } else {
      active.push(toolName);
    }
    setCurrentConfig({ ...currentConfig, active_tools: active });
  };

  const handleSaveConfig = async () => {
    setIsSaving(true);
    setSaveSuccessMsg("");
    try {
      const res = await apiFetch(`/api/agents/${selectedAgentId}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          system_prompt: currentConfig.system_prompt,
          temperature: currentConfig.temperature,
          model_provider: currentConfig.model_provider,
          model_name: currentConfig.model_name,
          active_tools: currentConfig.active_tools,
          custom_instructions: currentConfig.custom_instructions
        })
      });
      if (res.ok) {
        setSaveSuccessMsg(language === 'fr' 
          ? "Configuration enregistrée et agent mis à jour avec succès." 
          : (language === 'en' 
            ? "Configuration saved and agent updated immediately." 
            : "تم حفظ الإعدادات وتحديث الوكيل الذكي فورياً بنجاح."));
        setTimeout(() => setSaveSuccessMsg(""), 4000);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReloadPlugins = async () => {
    try {
      const res = await apiFetch('/api/plugins/reload', { method: 'POST' });
      const data = await res.json();
      setReloadMsg(data.message || (language === 'ar' ? "تمت إعادة تحميل الإضافات." : "Plugins rechargés."));
      fetchAgentsAndPlugins();
      setTimeout(() => setReloadMsg(""), 4000);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-afmi-lightmint text-afmi-forest font-bold">⚙️</span>
            <h2 className="text-xl font-extrabold text-afmi-dark">
              {t('studioTitle')}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t('studioSubtitle')}
          </p>
        </div>

        <button
          onClick={handleReloadPlugins}
          className="px-3.5 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-xs font-bold text-slate-700 flex items-center gap-1.5 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{t('reloadPluginsBtn')}</span>
        </button>
      </div>

      {reloadMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{reloadMsg}</span>
        </div>
      )}

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Col: Agent Selector & Plugins Overview */}
        <div className="space-y-6">
          
          {/* Agent Picker Card */}
          <div className="afmi-card p-5">
            <h3 className="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
              <Bot className="w-4 h-4 text-afmi-forest" />
              <span>{t('selectAgentCustomize')}</span>
            </h3>

            <div className="space-y-2">
              {agents.map((ag) => {
                const isSelected = selectedAgentId === ag.id;
                return (
                  <button
                    key={ag.id}
                    onClick={() => handleSelectAgent(ag.id)}
                    className={`w-full p-3 rounded-xl text-start text-xs font-bold transition-all border flex items-center justify-between ${
                      isSelected
                        ? "bg-afmi-forest text-white border-afmi-forest shadow-sm"
                        : "bg-slate-50 text-slate-700 border-slate-200 hover:bg-white"
                    }`}
                  >
                    <div>
                      <span className="block">{getAgentTitle(ag)}</span>
                      <span className={`text-[10px] block font-normal mt-0.5 ${
                        isSelected ? "text-emerald-200" : "text-slate-400"
                      }`}>
                        {ag.id}
                      </span>
                    </div>
                    <span className="text-lg">
                      {ag.id === 'agent_grant_writer' ? '📑' : ag.id === 'agent_project_manager' ? '🌲' : ag.id === 'agent_finance_auditor' ? '🔍' : '📢'}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active Plugins List */}
          <div className="afmi-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Puzzle className="w-4 h-4 text-afmi-forest" />
                <span>{t('activePluginsTitle')}</span>
              </h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                {pluginsData.total_active} {language === 'ar' ? 'نشطة' : 'active'}
              </span>
            </div>

            <p className="text-[11px] text-slate-500 mb-3 leading-relaxed">
              {t('activePluginsDesc')}
            </p>

            <div className="space-y-2">
              {pluginsData.plugins?.map((plugin, pIdx) => (
                <div key={pIdx} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
                  <div className="flex items-center justify-between font-mono font-bold text-afmi-forest">
                    <span>{plugin.filename}</span>
                    <span className="text-[10px] text-emerald-600 font-sans font-semibold">{t('pluginReady')}</span>
                  </div>
                  <span className="text-[10px] text-slate-400 block mt-1 font-mono">
                    {plugin.size_bytes} bytes
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Col (2 Spans): Prompt & Hyperparameter Editor */}
        <div className="lg:col-span-2 afmi-card p-6 space-y-5">
          
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-base font-bold text-slate-800">
                {t('customPromptsTitle')}
              </h3>
              <p className="text-xs text-slate-400">
                {t('customPromptsSubtitle')}
              </p>
            </div>

            <button
              onClick={handleSaveConfig}
              disabled={isSaving}
              className="px-4 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Save className="w-4 h-4" />
              <span>{isSaving ? t('savingChanges') : t('saveChangesBtn')}</span>
            </button>
          </div>

          {saveSuccessMsg && (
            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 shrink-0" />
              <span>{saveSuccessMsg}</span>
            </div>
          )}

          {/* Model Engine & Hyperparameters */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            
            {/* Provider */}
            <div>
              <label className="font-bold text-slate-700 block mb-1">{t('llmProviderLabel')}</label>
              <select
                value={currentConfig.model_provider}
                onChange={(e) => setCurrentConfig({ ...currentConfig, model_provider: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-semibold text-slate-700 outline-none focus:border-afmi-forest"
              >
                <option value="gemini">Google Gemini 2.5 Flash</option>
                <option value="ollama">Ollama Local Engine</option>
                <option value="heuristic">Heuristic AFMI Core</option>
              </select>
            </div>

            {/* Model Name */}
            <div>
              <label className="font-bold text-slate-700 block mb-1">{t('modelNameLabel')}</label>
              <input
                type="text"
                value={currentConfig.model_name}
                onChange={(e) => setCurrentConfig({ ...currentConfig, model_name: e.target.value })}
                placeholder="gemini-2.5-flash / llama3.1"
                className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 outline-none focus:border-afmi-forest"
              />
            </div>

            {/* Temperature Slider */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-bold text-slate-700">{t('temperatureLabel')}</label>
                <span className="font-mono font-bold text-afmi-forest">{currentConfig.temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={currentConfig.temperature}
                onChange={(e) => setCurrentConfig({ ...currentConfig, temperature: parseFloat(e.target.value) })}
                className="w-full accent-afmi-forest cursor-pointer mt-2"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-1">
                <span>0.0 (Strict / Audit)</span>
                <span>1.0 (Creative)</span>
              </div>
            </div>

          </div>

          {/* System Prompt Textarea */}
          <div className="text-xs">
            <div className="flex items-center justify-between mb-1.5">
              <label className="font-bold text-slate-700">
                {t('systemPromptLabel')}
              </label>
              <span className="text-[11px] text-slate-400 font-mono">
                {currentConfig.system_prompt.length} chars
              </span>
            </div>
            <textarea
              rows="9"
              value={currentConfig.system_prompt}
              onChange={(e) => setCurrentConfig({ ...currentConfig, system_prompt: e.target.value })}
              className="w-full font-mono text-xs bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-800 outline-none focus:border-afmi-forest leading-relaxed"
            ></textarea>
          </div>

          {/* Custom Instructions */}
          <div className="text-xs">
            <label className="font-bold text-slate-700 block mb-1">
              {t('customInstructionsLabel')}
            </label>
            <input
              type="text"
              value={currentConfig.custom_instructions}
              onChange={(e) => setCurrentConfig({ ...currentConfig, custom_instructions: e.target.value })}
              placeholder={language === 'ar' ? "مثال: التركيز دائماً على سلاسل القيمة لتعاونيات إقليم إفران وإبراز معايير ODD..." : "Ex: Prioriser la résilience territoriale du Moyen Atlas et les ODD..."}
              className="w-full bg-slate-50 border border-slate-200 rounded-xl p-2.5 text-slate-800 outline-none focus:border-afmi-forest"
            />
          </div>

          {/* Registered Tools Checkbox List */}
          <div className="text-xs">
            <label className="font-bold text-slate-700 block mb-2">
              {t('activeSkillsLabel')}
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {currentConfig.registered_tools?.map((tool, tIdx) => {
                const isChecked = currentConfig.active_tools?.includes(tool);
                return (
                  <label
                    key={tIdx}
                    className={`flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                      isChecked
                        ? "bg-afmi-lightmint/50 border-afmi-mint text-afmi-forest font-bold"
                        : "bg-slate-50 border-slate-200 text-slate-600"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => handleToggleTool(tool)}
                      className="accent-afmi-forest rounded"
                    />
                    <span className="font-mono text-[11px]">{tool}</span>
                  </label>
                );
              })}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
