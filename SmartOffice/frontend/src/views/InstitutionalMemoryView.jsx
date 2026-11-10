import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Cpu, 
  Save, 
  CheckCircle, 
  AlertCircle, 
  Key, 
  Server, 
  Plus, 
  Trash2, 
  Trees, 
  Globe, 
  ShieldCheck, 
  RefreshCw,
  Sparkles,
  Handshake,
  Coins
} from 'lucide-react';

import { apiFetch } from '../apiClient';
import { useLanguage } from '../context/LanguageContext';

export default function InstitutionalMemoryView({ onConfigUpdated }) {
  const { t, language } = useLanguage();
  const [activeSubTab, setActiveSubTab] = useState("memory"); // "memory" or "llm"
  const [profile, setProfile] = useState(null);
  const [newAxisText, setNewAxisText] = useState("");
  const [newDonorText, setNewDonorText] = useState("");

  const [llmConfig, setLlmConfig] = useState({
    provider: "gemini",
    gemini_key: "",
    gemini_model: "gemini-2.5-flash",
    ollama_url: "http://localhost:11434",
    ollama_model: "llama3.1"
  });

  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState("");

  const fetchProfile = () => {
    apiFetch('/api/settings/ngo-profile')
      .then(res => res.json())
      .then(data => setProfile(data))
      .catch(err => console.error(err));

    apiFetch('/api/settings/llm-config')
      .then(res => res.json())
      .then(data => {
        setLlmConfig(prev => ({
          ...prev,
          provider: data.current_provider || "gemini",
          gemini_model: data.gemini_model || "gemini-2.5-flash",
          ollama_url: data.ollama_url || "http://localhost:11434",
          ollama_model: data.ollama_model || "llama3.1"
        }));
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setSaveSuccessMsg("");
    try {
      const res = await apiFetch('/api/settings/ngo-profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile)
      });
      if (res.ok) {
        setSaveSuccessMsg(t('memorySavedSuccess'));
        if (onConfigUpdated) onConfigUpdated();
        setTimeout(() => setSaveSuccessMsg(""), 4000);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddAxis = () => {
    if (!newAxisText.trim()) return;
    const currentAxes = profile.strategic_axes || [];
    setProfile({
      ...profile,
      strategic_axes: [...currentAxes, newAxisText.trim()]
    });
    setNewAxisText("");
  };

  const handleDeleteAxis = (index) => {
    const updated = profile.strategic_axes.filter((_, i) => i !== index);
    setProfile({ ...profile, strategic_axes: updated });
  };

  const handleAddDonor = () => {
    if (!newDonorText.trim()) return;
    const currentDonors = profile.target_donors || [];
    setProfile({
      ...profile,
      target_donors: [...currentDonors, newDonorText.trim()]
    });
    setNewDonorText("");
  };

  const handleDeleteDonor = (index) => {
    const updated = profile.target_donors.filter((_, i) => i !== index);
    setProfile({ ...profile, target_donors: updated });
  };

  const handleSaveLlmConfig = async () => {
    setIsSaving(true);
    setSaveSuccessMsg("");
    try {
      const res = await apiFetch('/api/settings/llm-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(llmConfig)
      });
      if (res.ok) {
        setSaveSuccessMsg(t('llmSavedSuccess'));
        if (onConfigUpdated) onConfigUpdated();
        setTimeout(() => setSaveSuccessMsg(""), 4000);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnection = async (provider) => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await apiFetch('/api/settings/llm-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: provider,
          api_key: provider === 'gemini' ? llmConfig.gemini_key : undefined,
          url: provider === 'ollama' ? llmConfig.ollama_url : undefined
        })
      });
      const data = await res.json();
      setTestResult(data);
    } catch (err) {
      setTestResult({ status: "error", message: t('connError') });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-2 rounded-xl bg-afmi-lightmint text-afmi-forest font-bold">🏛️</span>
            <h2 className="text-xl font-extrabold text-afmi-dark">
              {t('memoryTitle')}
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {t('memorySubtitle')}
          </p>
        </div>

        {/* Tab Switcher & Quick Save */}
        <div className="flex items-center gap-3">
          <div className="bg-slate-100 p-1 rounded-xl flex items-center">
            <button
              onClick={() => setActiveSubTab("memory")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                activeSubTab === "memory"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t('tabOrgMemory')} ({profile?.strategic_axes?.length || 0})
            </button>
            <button
              onClick={() => setActiveSubTab("llm")}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                activeSubTab === "llm"
                  ? "bg-afmi-forest text-white shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t('tabLlmRouter')}
            </button>
          </div>

          <button
            onClick={activeSubTab === 'memory' ? handleSaveProfile : handleSaveLlmConfig}
            disabled={isSaving}
            className="px-4 py-2.5 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
          >
            <Save className="w-4 h-4 text-afmi-gold" />
            <span>{isSaving ? t('savingChanges') : t('saveChangesBtn')}</span>
          </button>
        </div>
      </div>

      {saveSuccessMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs font-bold text-emerald-800 flex items-center gap-2">
          <CheckCircle className="w-4 h-4 shrink-0" />
          <span>{saveSuccessMsg}</span>
        </div>
      )}

      {/* SubTab 1: NGO Profile Memory */}
      {activeSubTab === "memory" && profile && (
        <div className="space-y-6">
          
          {/* Organization Legal & Headquarters */}
          <div className="afmi-card p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-afmi-forest" />
                <span>{t('legalBankData')}</span>
              </h3>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgNameAr')}</label>
                <input
                  type="text"
                  value={profile.organization?.name_ar || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, name_ar: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-bold text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgNameFr')}</label>
                <input
                  type="text"
                  value={profile.organization?.name_fr || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, name_fr: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-semibold text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgIce')}</label>
                <input
                  type="text"
                  value={profile.organization?.ice || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, ice: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono font-bold text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgHeadquarters')}</label>
                <input
                  type="text"
                  value={profile.organization?.headquarters || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, headquarters: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgRib')}</label>
                <input
                  type="text"
                  value={profile.organization?.rib_banque || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, rib_banque: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 font-mono font-bold text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">{t('orgBank')}</label>
                <input
                  type="text"
                  value={profile.organization?.banque_nom || ""}
                  onChange={(e) => setProfile({
                    ...profile,
                    organization: { ...profile.organization, banque_nom: e.target.value }
                  })}
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 outline-none focus:border-afmi-forest"
                />
              </div>
            </div>
          </div>

          {/* Strategic Axes - Open & Extensible List */}
          <div className="afmi-card p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Trees className="w-4 h-4 text-afmi-forest" />
                  <span>{t('strategicAxesTitle')} ({profile.strategic_axes?.length || 0})</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {t('strategicAxesSubtitle')}
                </p>
              </div>

              <span className="text-xs bg-afmi-lightmint text-afmi-forest font-bold px-2.5 py-1 rounded-full border border-afmi-mint/30">
                {t('openExtensibleBadge')}
              </span>
            </div>

            {/* Add New Axis Input Bar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newAxisText}
                onChange={(e) => setNewAxisText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddAxis()}
                placeholder={t('addAxisPlaceholder')}
                className="flex-1 text-xs bg-slate-50 border border-slate-200 focus:border-afmi-forest rounded-xl p-3 outline-none"
              />
              <button
                type="button"
                onClick={handleAddAxis}
                className="px-4 py-2.5 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1 shrink-0"
              >
                <Plus className="w-4 h-4" />
                <span>{t('addAxisBtn')}</span>
              </button>
            </div>

            {/* Axes List */}
            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {profile.strategic_axes?.map((axis, aIdx) => (
                <div key={aIdx} className="flex items-center gap-2 bg-slate-50/70 p-2 rounded-xl border border-slate-200/70 hover:bg-slate-50 transition-colors">
                  <span className="w-6 h-6 rounded-full bg-afmi-lightmint text-afmi-forest font-bold flex items-center justify-center text-xs shrink-0 font-mono">
                    {aIdx + 1}
                  </span>
                  
                  <input
                    type="text"
                    value={axis}
                    onChange={(e) => {
                      const updated = [...profile.strategic_axes];
                      updated[aIdx] = e.target.value;
                      setProfile({ ...profile, strategic_axes: updated });
                    }}
                    className="flex-1 text-xs bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded p-1 text-slate-800 font-semibold"
                  />

                  <button
                    onClick={() => handleDeleteAxis(aIdx)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors shrink-0"
                    title={t('deleteAxis')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Target Donors - Open & Extensible List */}
          <div className="afmi-card p-6 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                  <Handshake className="w-4 h-4 text-afmi-forest" />
                  <span>{t('targetDonorsTitle')} ({profile.target_donors?.length || 0})</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {t('targetDonorsSubtitle')}
                </p>
              </div>

              <span className="text-xs bg-purple-50 text-purple-700 font-bold px-2.5 py-1 rounded-full border border-purple-200">
                {t('natIntlProgramsBadge')}
              </span>
            </div>

            {/* Add New Donor Input Bar */}
            <div className="flex gap-2">
              <input
                type="text"
                value={newDonorText}
                onChange={(e) => setNewDonorText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddDonor()}
                placeholder={t('addDonorPlaceholder')}
                className="flex-1 text-xs bg-slate-50 border border-slate-200 focus:border-afmi-forest rounded-xl p-3 outline-none"
              />
              <button
                type="button"
                onClick={handleAddDonor}
                className="px-4 py-2.5 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1 shrink-0"
              >
                <Plus className="w-4 h-4" />
                <span>{t('addDonorBtn')}</span>
              </button>
            </div>

            {/* Donors List */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-96 overflow-y-auto pr-1">
              {profile.target_donors?.map((donor, dIdx) => (
                <div key={dIdx} className="flex items-center justify-between gap-2 bg-slate-50/70 p-2.5 rounded-xl border border-slate-200/70 hover:bg-slate-50 transition-colors">
                  <div className="flex items-center gap-2 flex-1">
                    <span className="text-afmi-forest font-bold text-xs shrink-0 font-mono">
                      #{dIdx + 1}
                    </span>
                    <input
                      type="text"
                      value={donor}
                      onChange={(e) => {
                        const updated = [...profile.target_donors];
                        updated[dIdx] = e.target.value;
                        setProfile({ ...profile, target_donors: updated });
                      }}
                      className="flex-1 text-xs bg-transparent border-0 focus:ring-1 focus:ring-afmi-forest rounded p-1 text-slate-800 font-semibold"
                    />
                  </div>

                  <button
                    onClick={() => handleDeleteDonor(dIdx)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 transition-colors shrink-0"
                    title={t('deleteDonor')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

        </div>
      )}

      {/* SubTab 2: LLM Router Configuration */}
      {activeSubTab === "llm" && (
        <div className="space-y-6">
          
          <div className="afmi-card p-6 space-y-6">
            
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
                <Cpu className="w-4 h-4 text-afmi-forest" />
                <span>{t('llmEnginesTitle')}</span>
              </h3>
              <button
                onClick={handleSaveLlmConfig}
                disabled={isSaving}
                className="px-4 py-2 bg-afmi-forest hover:bg-afmi-emerald text-white rounded-xl text-xs font-bold transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{t('saveLlmSettingsBtn')}</span>
              </button>
            </div>

            {/* Provider Selection */}
            <div className="text-xs">
              <label className="font-bold text-slate-700 block mb-2">{t('defaultProviderLabel')}</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                
                <div 
                  onClick={() => setLlmConfig({ ...llmConfig, provider: "gemini" })}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    llmConfig.provider === "gemini"
                      ? "border-afmi-forest bg-afmi-lightmint/30"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-800">Google Gemini API</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800">
                      {t('cloudFast')}
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px] leading-relaxed">
                    {t('cloudDesc')}
                  </p>
                </div>

                <div 
                  onClick={() => setLlmConfig({ ...llmConfig, provider: "ollama" })}
                  className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                    llmConfig.provider === "ollama"
                      ? "border-afmi-forest bg-afmi-lightmint/30"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-slate-800">Ollama Local Engine</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                      {t('localSecure')}
                    </span>
                  </div>
                  <p className="text-slate-500 text-[11px] leading-relaxed">
                    {t('localDesc')}
                  </p>
                </div>

              </div>
            </div>

            {/* Gemini Settings */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-xs">
              <h4 className="font-bold text-slate-800 flex items-center justify-between">
                <span>Google Gemini (Cloud Vision)</span>
                <button
                  type="button"
                  onClick={() => handleTestConnection("gemini")}
                  disabled={isTesting}
                  className="text-xs font-bold text-afmi-forest hover:underline flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${isTesting ? 'animate-spin' : ''}`} />
                  <span>{t('geminiTestBtn')}</span>
                </button>
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-600 block mb-1">{t('geminiApiKeyLabel')}</label>
                  <input
                    type="password"
                    value={llmConfig.gemini_key}
                    onChange={(e) => setLlmConfig({ ...llmConfig, gemini_key: e.target.value })}
                    placeholder="AIzaSy..."
                    className="w-full bg-white border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 outline-none focus:border-afmi-forest"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-600 block mb-1">{t('modelNameLabel')}</label>
                  <input
                    type="text"
                    value={llmConfig.gemini_model}
                    onChange={(e) => setLlmConfig({ ...llmConfig, gemini_model: e.target.value })}
                    placeholder="gemini-2.5-flash"
                    className="w-full bg-white border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 outline-none focus:border-afmi-forest"
                  />
                </div>
              </div>
            </div>

            {/* Ollama Settings */}
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3 text-xs">
              <h4 className="font-bold text-slate-800 flex items-center justify-between">
                <span>Ollama (Local Engine)</span>
                <button
                  type="button"
                  onClick={() => handleTestConnection("ollama")}
                  disabled={isTesting}
                  className="text-xs font-bold text-afmi-forest hover:underline flex items-center gap-1"
                >
                  <RefreshCw className={`w-3 h-3 ${isTesting ? 'animate-spin' : ''}`} />
                  <span>{t('ollamaTestBtn')}</span>
                </button>
              </h4>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-600 block mb-1">{t('ollamaUrlLabel')}</label>
                  <input
                    type="text"
                    value={llmConfig.ollama_url}
                    onChange={(e) => setLlmConfig({ ...llmConfig, ollama_url: e.target.value })}
                    placeholder="http://localhost:11434"
                    className="w-full bg-white border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 outline-none focus:border-afmi-forest"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-600 block mb-1">{t('ollamaModelLabel')}</label>
                  <input
                    type="text"
                    value={llmConfig.ollama_model}
                    onChange={(e) => setLlmConfig({ ...llmConfig, ollama_model: e.target.value })}
                    placeholder="llama3.1"
                    className="w-full bg-white border border-slate-200 rounded-lg p-2.5 font-mono text-slate-700 outline-none focus:border-afmi-forest"
                  />
                </div>
              </div>
            </div>

            {/* Test Connectivity Result */}
            {testResult && (
              <div className={`p-4 rounded-xl border text-xs font-semibold flex items-center gap-2 ${
                testResult.status === 'success'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : testResult.status === 'warning'
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-rose-50 border-rose-200 text-rose-800'
              }`}>
                {testResult.status === 'success' ? (
                  <CheckCircle className="w-4 h-4 shrink-0 text-emerald-600" />
                ) : (
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
                )}
                <div>
                  <span>{testResult.message}</span>
                  {testResult.models && (
                    <span className="block text-[11px] font-mono mt-1 text-slate-600">
                      {t('availableModels')} {testResult.models.join(", ")}
                    </span>
                  )}
                </div>
              </div>
            )}

          </div>

        </div>
      )}

    </div>
  );
}
