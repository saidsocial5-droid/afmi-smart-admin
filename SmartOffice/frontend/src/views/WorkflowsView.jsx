import React, { useState, useEffect, useRef } from 'react';
import {
  Workflow as WorkflowIcon,
  Play,
  Loader2,
  CheckCircle2,
  XCircle,
  MinusCircle,
  Clock,
  Download,
  ChevronDown,
  ChevronUp,
  History,
  Info
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { apiFetch, getApiBaseUrl } from '../apiClient';

const STATUS_STYLES = {
  pending: 'bg-slate-100 text-slate-500',
  running: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-red-100 text-red-700',
  skipped: 'bg-slate-100 text-slate-400',
  partial: 'bg-amber-100 text-amber-700',
  interrupted: 'bg-slate-200 text-slate-600'
};

function StatusIcon({ status }) {
  if (status === 'running') return <Loader2 className="w-5 h-5 text-amber-500 animate-spin" />;
  if (status === 'completed') return <CheckCircle2 className="w-5 h-5 text-emerald-600" />;
  if (status === 'failed') return <XCircle className="w-5 h-5 text-red-600" />;
  if (status === 'skipped') return <MinusCircle className="w-5 h-5 text-slate-400" />;
  return <Clock className="w-5 h-5 text-slate-400" />;
}

export default function WorkflowsView() {
  const { language, t, isRtl } = useLanguage();
  const [workflows, setWorkflows] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [inputs, setInputs] = useState({});
  const [run, setRun] = useState(null);
  const [runs, setRuns] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const pollRef = useRef(null);

  const loc = (obj, base) => obj ? (obj[`${base}_${language}`] || obj[`${base}_fr`] || "") : "";
  const selected = workflows.find(w => w.id === selectedId);
  const isActive = run && (run.status === 'pending' || run.status === 'running');

  const fetchRuns = () => apiFetch('/api/workflows/runs').then(r => r.json()).then(setRuns).catch(() => {});

  useEffect(() => {
    apiFetch('/api/workflows')
      .then(r => r.json())
      .then(data => {
        setWorkflows(data);
        if (data.length) setSelectedId(data[0].id);
      })
      .catch(() => setError("Backend indisponible."));
    fetchRuns();
    return () => clearTimeout(pollRef.current);
  }, []);

  const pollRun = (runId) => {
    clearTimeout(pollRef.current);
    apiFetch(`/api/workflows/runs/${runId}`)
      .then(r => r.json())
      .then(data => {
        setRun(data);
        if (data.status === 'pending' || data.status === 'running') {
          pollRef.current = setTimeout(() => pollRun(runId), 1500);
        } else {
          fetchRuns();
        }
      })
      .catch(() => { pollRef.current = setTimeout(() => pollRun(runId), 3000); });
  };

  const handleSelectWorkflow = (id) => {
    setSelectedId(id);
    setInputs({});
    setError("");
  };

  const handleLaunch = async () => {
    if (!selected) return;
    const missing = selected.inputs.filter(i => i.required && !String(inputs[i.key] || "").trim());
    if (missing.length) {
      setError(`${t('wfRequired')} : ${missing.map(i => loc(i, 'label')).join(', ')}`);
      return;
    }
    setError("");
    setIsStarting(true);
    setExpanded({});
    try {
      const res = await apiFetch(`/api/workflows/${selected.id}/runs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ inputs, language })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      setRun(data);
      pollRun(data.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStarting(false);
    }
  };

  const handleOpenRun = (runId) => {
    setExpanded({});
    pollRun(runId);
  };

  const handleExport = async () => {
    if (!run) return;
    setIsExporting(true);
    try {
      const res = await apiFetch(`/api/workflows/runs/${run.id}/export-docx`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      window.open(`${getApiBaseUrl()}/exports/${data.filename}`, '_blank');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsExporting(false);
    }
  };

  const stepTitle = (stepId) => {
    const s = run?.steps?.find(x => x.id === stepId) || selected?.steps?.find(x => x.id === stepId);
    return s ? loc(s, 'title') : stepId;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-br from-afmi-forest to-afmi-emerald rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-3">
          <WorkflowIcon className="w-8 h-8 text-afmi-gold" />
          <div>
            <h1 className="text-2xl font-bold">{t('wfTitle')}</h1>
            <p className="text-emerald-100 text-sm mt-1">{t('wfSubtitle')}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: chain picker + brief */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
            <h2 className="text-sm font-bold text-slate-500 uppercase mb-3">{t('wfChooseChain')}</h2>
            <div className="space-y-2">
              {workflows.map(w => (
                <button
                  key={w.id}
                  onClick={() => handleSelectWorkflow(w.id)}
                  className={`w-full text-start p-3 rounded-xl border transition-all ${
                    selectedId === w.id
                      ? 'border-afmi-forest bg-afmi-lightmint/50'
                      : 'border-slate-200 hover:border-afmi-sage'
                  }`}
                >
                  <div className="font-bold text-afmi-forest text-sm">{loc(w, 'name')}</div>
                  <div className="text-xs text-slate-500 mt-1">{loc(w, 'description')}</div>
                  <div className="text-[10px] text-slate-400 mt-2">{w.steps.length} × 🤖</div>
                </button>
              ))}
            </div>
          </div>

          {selected && (
            <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm space-y-3">
              <h2 className="text-sm font-bold text-slate-500 uppercase">{t('wfBrief')}</h2>
              {selected.inputs.map(i => (
                <label key={i.key} className="block">
                  <span className="text-xs font-semibold text-slate-600">
                    {loc(i, 'label')} {i.required && <span className="text-red-500">*</span>}
                  </span>
                  {i.multiline ? (
                    <textarea
                      rows={4}
                      value={inputs[i.key] || ""}
                      onChange={e => setInputs({ ...inputs, [i.key]: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-afmi-forest focus:outline-none"
                    />
                  ) : (
                    <input
                      value={inputs[i.key] || ""}
                      onChange={e => setInputs({ ...inputs, [i.key]: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-afmi-forest focus:outline-none"
                    />
                  )}
                </label>
              ))}
              {error && <div className="text-xs text-red-600 bg-red-50 rounded-lg p-2">{error}</div>}
              <button
                onClick={handleLaunch}
                disabled={isStarting || isActive}
                className="w-full flex items-center justify-center gap-2 bg-afmi-forest hover:bg-afmi-emerald disabled:opacity-50 text-white font-bold py-2.5 rounded-xl"
              >
                {isStarting || isActive ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {isActive ? t('wfRunning') : t('wfLaunch')}
              </button>
              <p className="flex gap-1.5 text-[11px] text-slate-400">
                <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" /> {t('wfOfflineHint')}
              </p>
            </div>
          )}
        </div>

        {/* Right: live run timeline */}
        <div className="lg:col-span-2 space-y-4">
          {run ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <h2 className="font-bold text-afmi-forest">{run.title}</h2>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {run.progress.done}/{run.progress.total} · {new Date(run.created_at + 'Z').toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${STATUS_STYLES[run.status]}`}>
                    {t(`wfStatus_${run.status}`)}
                  </span>
                  {!isActive && run.steps.some(s => s.status === 'completed') && (
                    <button
                      onClick={handleExport}
                      disabled={isExporting}
                      className="flex items-center gap-1.5 text-xs font-bold bg-afmi-gold hover:bg-afmi-darkgold text-white px-3 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {isExporting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                      {t('wfExport')}
                    </button>
                  )}
                </div>
              </div>

              <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden mb-5">
                <div
                  className="h-full bg-afmi-sage transition-all duration-500"
                  style={{ width: `${(run.progress.done / Math.max(run.progress.total, 1)) * 100}%` }}
                />
              </div>

              <ol className={`space-y-3 ${isRtl ? 'border-r-2 pr-4' : 'border-l-2 pl-4'} border-slate-100`}>
                {run.steps.map((s, idx) => (
                  <li key={s.id} className="relative">
                    <div className="flex items-start gap-3">
                      <StatusIcon status={s.status} />
                      <div className="flex-1 min-w-0">
                        <button
                          className="w-full flex items-center justify-between gap-2 text-start"
                          onClick={() => setExpanded({ ...expanded, [s.id]: !expanded[s.id] })}
                          disabled={!s.output && !s.error}
                        >
                          <div>
                            <div className="text-sm font-bold text-slate-700">{idx + 1}. {loc(s, 'title')}</div>
                            <div className="text-[11px] text-slate-400">
                              {s.agent_id.replace('agent_', '').replace('_', ' ')}
                              {s.depends_on.length > 0 && ` · ${t('wfDependsOn')} : ${s.depends_on.map(stepTitle).join(', ')}`}
                              {s.duration_s > 0 && ` · ${s.duration_s}s`}
                              {s.attempts > 1 && ` · ${s.attempts} ${t('wfAttempts')}`}
                              {s.model_used && ` · ${s.model_used}`}
                            </div>
                          </div>
                          {(s.output || s.error) && (expanded[s.id]
                            ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                            : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />)}
                        </button>
                        {s.error && <div className="mt-1 text-xs text-red-600">{s.error}</div>}
                        {expanded[s.id] && s.output && (
                          <pre className="mt-2 whitespace-pre-wrap font-sans text-sm text-slate-700 bg-slate-50 rounded-xl p-3 max-h-96 overflow-y-auto">
                            {s.output}
                          </pre>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          ) : selected && (
            <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-6 text-center">
              <div className="flex flex-wrap items-center justify-center gap-2 text-sm text-slate-600">
                {selected.steps.map((s, idx) => (
                  <React.Fragment key={s.id}>
                    <span className="px-3 py-1.5 rounded-lg bg-afmi-lightmint/60 text-afmi-forest font-semibold">{loc(s, 'title')}</span>
                    {idx < selected.steps.length - 1 && <span className="text-slate-300">{isRtl ? '←' : '→'}</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm">
            <h2 className="flex items-center gap-2 text-sm font-bold text-slate-500 uppercase mb-3">
              <History className="w-4 h-4" /> {t('wfHistory')}
            </h2>
            {runs.length === 0 ? (
              <p className="text-sm text-slate-400">{t('wfNoRuns')}</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {runs.map(r => (
                  <li key={r.id}>
                    <button onClick={() => handleOpenRun(r.id)} className="w-full flex items-center justify-between gap-3 py-2 text-start hover:bg-slate-50 rounded-lg px-2">
                      <span className="text-sm text-slate-700 truncate">{r.title}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full shrink-0 ${STATUS_STYLES[r.status]}`}>
                        {t(`wfStatus_${r.status}`)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
