import React, { useEffect, useMemo, useState } from 'react';
import { FolderKanban, Upload, Search, MessageCircleQuestion, CalendarClock, AlertTriangle, Bell, Check, X, Trash2, Download, RefreshCw } from 'lucide-react';
import { apiFetch } from '../apiClient';

// GED des projets et cycle de vie (Lot 6) : documents classés par phase, échéances, frise, alertes, recherche et questions.

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const readError = async (r) => { try { const j = await r.json(); return typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch { return `Erreur ${r.status}`; } };
const fr = (iso) => (iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('fr-FR') : '');
const LANE_COLORS = { Projet: '#1B4332', Jalons: '#2563EB', 'Rapports dus': '#B45309', Tranches: '#7C3AED', Documents: '#0F766E' };
const STATUS_STYLE = { done: { fill: '#10B981' }, todo: { fill: '#F8FAFC', stroke: '#64748B' }, late: { fill: '#DC2626' }, proposed: { fill: '#FDE68A', stroke: '#B45309' }, info: { fill: '#94A3B8' } };

function Timeline({ data }) {
  const items = data.items;
  if (!items.length) return <p className="text-sm text-slate-500">Rien à afficher : ajoutez des dates au projet, des jalons ou des documents.</p>;
  const lanes = Object.keys(LANE_COLORS).filter((l) => items.some((i) => i.lane === l));
  const t = (iso) => new Date(`${iso}T00:00:00`).getTime();
  const min = Math.min(...items.map((i) => t(i.date))), max = Math.max(...items.map((i) => t(i.date)), min + 86400000 * 30);
  const today = Date.now();
  const W = 1000, left = 120, laneH = 46, top = 30;
  const x = (iso) => left + ((t(iso) - min) / (max - min)) * (W - left - 30);
  const years = [];
  for (let y = new Date(min).getFullYear(); y <= new Date(max).getFullYear(); y += 1) years.push(y);
  return (
    <svg viewBox={`0 0 ${W} ${top + lanes.length * laneH + 20}`} className="w-full" role="img" aria-label="Frise du cycle de vie">
      {years.map((y) => {
        const yx = left + ((new Date(y, 0, 1).getTime() - min) / (max - min)) * (W - left - 30);
        return yx >= left ? <g key={y}><line x1={yx} x2={yx} y1={top - 10} y2={top + lanes.length * laneH} stroke="#E2E8F0" /><text x={yx + 3} y={top - 14} fontSize="11" fill="#64748B">{y}</text></g> : null;
      })}
      {today >= min && today <= max && (
        <g><line x1={left + ((today - min) / (max - min)) * (W - left - 30)} x2={left + ((today - min) / (max - min)) * (W - left - 30)} y1={top - 10} y2={top + lanes.length * laneH} stroke="#DC2626" strokeDasharray="4 3" />
          <text x={left + ((today - min) / (max - min)) * (W - left - 30) + 3} y={top + lanes.length * laneH + 14} fontSize="10" fill="#DC2626">aujourd'hui</text></g>
      )}
      {lanes.map((lane, li) => (
        <g key={lane}>
          <text x="6" y={top + li * laneH + 26} fontSize="12" fontWeight="600" fill={LANE_COLORS[lane]}>{lane}</text>
          <line x1={left} x2={W - 20} y1={top + li * laneH + 22} y2={top + li * laneH + 22} stroke="#E2E8F0" />
          {items.filter((i) => i.lane === lane).map((i, k) => {
            const st = STATUS_STYLE[i.status] || STATUS_STYLE.info;
            return (
              <g key={k}>
                <circle cx={x(i.date)} cy={top + li * laneH + 22} r="7" fill={st.fill} stroke={st.stroke || LANE_COLORS[lane]} strokeWidth="2">
                  <title>{`${fr(i.date)} — ${i.label}`}</title>
                </circle>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

export default function ProjectDocumentsView() {
  const [cfg, setCfg] = useState({ phases: [], types: [] });
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState('');
  const [tab, setTab] = useState('documents');
  const [docs, setDocs] = useState([]);
  const [obligations, setObligations] = useState([]);
  const [timeline, setTimeline] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [newObl, setNewObl] = useState({ title: '', kind: 'Rapport narratif', due: '' });
  const [newMs, setNewMs] = useState({ title: '', date: '', phase: '' });

  useEffect(() => {
    apiFetch('/api/ged/config').then((r) => r.json()).then(setCfg).catch(() => {});
    apiFetch('/api/editor/context').then((r) => r.json()).then((c) => setProjects(c.projects || [])).catch(() => setMsg({ kind: 'error', text: 'Base indisponible : ouvrez l\'application de bureau.' }));
  }, []);

  const loadAll = async () => {
    const q = projectId ? `?project_id=${projectId}` : '';
    const a = await apiFetch(`/api/ged/alerts${q}`);
    if (a.ok) setAlerts(await a.json());
    if (!projectId) { setDocs([]); setObligations([]); setTimeline(null); return; }
    const [d, o, t] = await Promise.all([apiFetch(`/api/ged/documents${q}`), apiFetch(`/api/ged/obligations${q}`), apiFetch(`/api/ged/timeline/${projectId}`)]);
    if (d.ok) setDocs(await d.json());
    if (o.ok) setObligations(await o.json());
    if (t.ok) setTimeline(await t.json());
  };
  useEffect(() => { loadAll(); setResults(null); setAnswer(null); }, [projectId]);

  const upload = async () => {
    if (!projectId || !files.length) { setMsg({ kind: 'error', text: 'Choisissez le projet et les fichiers.' }); return; }
    setBusy('upload'); setMsg(null);
    const form = new FormData();
    form.append('project_id', projectId);
    files.forEach((f) => form.append('files', f));
    const res = await apiFetch('/api/ged/documents', { method: 'POST', body: form });
    setBusy('');
    if (!res.ok) { setMsg({ kind: 'error', text: await readError(res) }); return; }
    const { results: rs } = await res.json();
    const ok = rs.filter((r) => r.document);
    const proposed = ok.reduce((n, r) => n + (r.proposed_obligations?.length || 0), 0);
    const errors = rs.filter((r) => r.error);
    setMsg({ kind: errors.length ? 'error' : 'ok', text: `${ok.length} document(s) classé(s) et indexé(s)${proposed ? `, ${proposed} échéance(s) de rapport proposée(s) à confirmer` : ''}.`
      + (errors.length ? ' ' + errors.map((e) => `${e.file} : ${e.error}`).join(' · ') : '') });
    setFiles([]);
    loadAll();
  };

  const updateDoc = async (id, patch) => { const r = await apiFetch(`/api/ged/documents/${id}`, json('PUT', patch)); if (!r.ok) setMsg({ kind: 'error', text: await readError(r) }); loadAll(); };
  const saveObl = async (body) => { const r = await apiFetch('/api/ged/obligations', json('POST', body)); if (!r.ok) setMsg({ kind: 'error', text: await readError(r) }); loadAll(); };

  const byPhase = useMemo(() => {
    const g = {};
    cfg.phases.forEach((p) => { g[p] = []; });
    docs.forEach((d) => { (g[d.phase] = g[d.phase] || []).push(d); });
    return g;
  }, [docs, cfg.phases]);

  const search = async () => {
    if (!query.trim()) return;
    const r = await apiFetch(`/api/ged/search?q=${encodeURIComponent(query)}${projectId ? `&project_id=${projectId}` : ''}`);
    setResults(r.ok ? await r.json() : { mode: '', results: [], error: await readError(r) });
  };
  const ask = async () => {
    if (!question.trim()) return;
    setBusy('ask');
    const r = await apiFetch('/api/ged/ask', json('POST', { question, project_id: projectId ? Number(projectId) : null }));
    setBusy('');
    setAnswer(r.ok ? await r.json() : { answer: await readError(r), sources: [] });
  };
  const levelIcon = { critical: <AlertTriangle className="w-4 h-4 text-red-600" />, warning: <AlertTriangle className="w-4 h-4 text-amber-600" />, info: <Bell className="w-4 h-4 text-slate-500" /> };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><FolderKanban className="w-6 h-6" />Documents et cycle de vie des projets</h1>
        <p className="text-sm text-slate-500">Chaque document importé est classé (type, phase), analysé (dates, montants, parties, échéances de rapports) et indexé pour la recherche.
          Les documents de l'application de bureau sont partagés.</p>
      </div>
      {msg && <div role="status" className={`rounded px-3 py-2 text-sm ${msg.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{msg.text}</div>}

      <div className="flex flex-wrap items-center gap-3">
        <select aria-label="Projet" className="border rounded px-2 py-1.5 text-sm min-w-[18rem]" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
          <option value="">Tous les projets (alertes)</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
        </select>
        {projectId && timeline && <span className="text-sm">Phase atteinte : <strong className="text-afmi-forest">{timeline.phase}</strong></span>}
        <button className="text-xs text-afmi-forest flex items-center gap-1 ms-auto" onClick={async () => {
          setBusy('reindex');
          const r = await apiFetch(`/api/ged/reindex${projectId ? `?project_id=${projectId}` : ''}`, { method: 'POST' });
          setBusy('');
          const d = await r.json();
          setMsg(r.ok ? { kind: 'ok', text: `${d.indexed} document(s) existant(s) analysé(s) et indexé(s)${d.skipped.length ? ` ; sans texte lisible : ${d.skipped.join(', ')}` : ''}.` } : { kind: 'error', text: d.detail });
          loadAll();
        }}><RefreshCw size={12} className={busy === 'reindex' ? 'animate-spin' : ''} />Analyser les documents existants</button>
      </div>

      {alerts.length > 0 && (
        <section className="bg-white border rounded-xl p-3 text-sm" aria-label="Alertes">
          <h2 className="font-semibold mb-1 flex items-center gap-2"><Bell className="w-4 h-4" />Alertes ({alerts.length})</h2>
          <ul className="space-y-1 max-h-48 overflow-y-auto">{alerts.map((a, i) => <li key={i} className="flex items-start gap-2">{levelIcon[a.level]}<span>{a.message}</span></li>)}</ul>
        </section>
      )}

      {projectId && (
        <>
          <div className="flex gap-1 text-sm">
            {[['documents', 'Documents', FolderKanban], ['timeline', 'Frise du cycle de vie', CalendarClock], ['obligations', `Échéances (${obligations.filter((o) => o.status !== 'Remise').length})`, Bell],
              ['search', 'Recherche et questions', Search]].map(([id, label, Icon]) => (
              <button key={id} onClick={() => setTab(id)} className={`px-3 py-1.5 rounded-lg flex items-center gap-1 ${tab === id ? 'bg-afmi-forest text-white' : 'bg-white border'}`}><Icon size={14} />{label}</button>
            ))}
          </div>

          {tab === 'documents' && (
            <section className="space-y-3">
              <div className="bg-white border rounded-xl p-3 flex flex-wrap items-center gap-2 text-sm">
                <input type="file" multiple accept=".pdf,.docx,.xlsx,.txt,.md,.csv,.jpg,.jpeg,.png,.tif,.tiff" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
                <button className="bg-afmi-forest text-white rounded px-3 py-1.5 flex items-center gap-1" disabled={busy === 'upload'} onClick={upload}><Upload size={14} />{busy === 'upload' ? 'Analyse…' : 'Importer et analyser'}</button>
                <span className="text-xs text-slate-500">PDF (natif ou scanné), Word .docx, Excel, texte, images.</span>
              </div>
              {cfg.phases.map((phase) => {
                const expected = (timeline?.expected || []).filter((e) => e.phase === phase);
                const list = byPhase[phase] || [];
                if (!list.length && !expected.some((e) => e.reached)) return null;
                return (
                  <div key={phase} className="bg-white border rounded-xl p-3">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <h3 className="font-semibold">{phase}</h3>
                      {expected.map((e) => (
                        <span key={e.doc_type} className={`text-[11px] px-2 py-0.5 rounded-full ${e.count ? 'bg-emerald-50 text-emerald-800' : e.reached ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-500'}`}>
                          {e.count ? '✔' : e.reached ? '✗' : '○'} {e.doc_type}
                        </span>
                      ))}
                    </div>
                    {list.length === 0 && <p className="text-xs text-slate-500">Aucun document.</p>}
                    <table className="w-full text-sm"><tbody>
                      {list.map((d) => (
                        <tr key={d.id} className="border-t align-top">
                          <td className="py-1 pe-2">
                            <div className="font-medium" dir="auto">{d.title}</div>
                            <div className="text-xs text-slate-500">{d.file_name} · {d.signature_date ? `signé le ${fr(d.signature_date)}` : `importé le ${d.uploaded.slice(0, 10)}`}
                              {d.end_date ? ` · fin ${fr(d.end_date)}` : ''}{d.metadata?.max_amount ? ` · ${d.metadata.max_amount.text}` : ''}{!d.indexed ? ' · non indexé' : ''}</div>
                            {(d.metadata?.parties || []).length > 0 && <div className="text-xs text-slate-500">Parties : {d.metadata.parties.join(' ; ')}</div>}
                          </td>
                          <td className="py-1 w-48">
                            <select aria-label="Type de document" className={`border rounded text-xs py-0.5 w-full ${d.confidence < 60 ? 'border-amber-400 bg-amber-50' : ''}`} value={d.doc_type} onChange={(e) => updateDoc(d.id, { doc_type: e.target.value })}>
                              {cfg.types.map((t) => <option key={t}>{t}</option>)}
                            </select>
                            <div className="text-[10px] text-slate-500">{d.confidence >= 100 ? 'confirmé' : `classé automatiquement (${Math.round(d.confidence)} %)`}</div>
                          </td>
                          <td className="py-1 w-40">
                            <select aria-label="Phase" className="border rounded text-xs py-0.5 w-full" value={d.phase} onChange={(e) => updateDoc(d.id, { phase: e.target.value })}>
                              {cfg.phases.map((p) => <option key={p}>{p}</option>)}
                            </select>
                          </td>
                          <td className="py-1 text-end whitespace-nowrap">
                            {d.has_file && <a className="inline-block me-2 text-afmi-forest" title="Télécharger" href={`/api/ged/documents/${d.id}/file`}><Download size={14} /></a>}
                            <button title="Supprimer" className="text-red-600" onClick={async () => { if (window.confirm(`Supprimer « ${d.title} » ? (suppression logique)`)) { await apiFetch(`/api/ged/documents/${d.id}`, { method: 'DELETE' }); loadAll(); } }}><Trash2 size={14} /></button>
                          </td>
                        </tr>
                      ))}
                    </tbody></table>
                  </div>
                );
              })}
            </section>
          )}

          {tab === 'timeline' && timeline && (
            <section className="bg-white border rounded-xl p-3 space-y-3">
              <div className="flex flex-wrap gap-1 text-xs">
                {timeline.phases.map((p, i) => (
                  <span key={p} className={`px-2 py-1 rounded ${p === timeline.phase ? 'bg-afmi-forest text-white' : timeline.phases.indexOf(timeline.phase) > i ? 'bg-emerald-100 text-emerald-900' : 'bg-slate-100 text-slate-500'}`}>{i + 1}. {p}</span>
                ))}
              </div>
              <Timeline data={timeline} />
              <div className="flex flex-wrap gap-3 text-xs text-slate-600">
                <span><span className="inline-block w-3 h-3 rounded-full bg-emerald-500 align-middle" /> fait / remis / reçu</span>
                <span><span className="inline-block w-3 h-3 rounded-full border-2 border-slate-500 align-middle" /> à venir</span>
                <span><span className="inline-block w-3 h-3 rounded-full bg-red-600 align-middle" /> en retard</span>
                <span><span className="inline-block w-3 h-3 rounded-full bg-amber-200 border-2 border-amber-700 align-middle" /> proposé, à confirmer</span>
              </div>
              <div className="flex flex-wrap items-end gap-2 text-sm border-t pt-2">
                <span className="font-medium">Nouveau jalon :</span>
                <input aria-label="Titre du jalon" className="border rounded px-2 py-1" placeholder="Comité de pilotage…" value={newMs.title} onChange={(e) => setNewMs({ ...newMs, title: e.target.value })} />
                <input aria-label="Date du jalon" type="date" className="border rounded px-2 py-1" value={newMs.date} onChange={(e) => setNewMs({ ...newMs, date: e.target.value })} />
                <select aria-label="Phase du jalon" className="border rounded px-2 py-1" value={newMs.phase} onChange={(e) => setNewMs({ ...newMs, phase: e.target.value })}>
                  <option value="">Phase…</option>{cfg.phases.map((p) => <option key={p}>{p}</option>)}
                </select>
                <button className="bg-afmi-forest text-white rounded px-3 py-1" onClick={async () => {
                  const r = await apiFetch('/api/ged/milestones', json('POST', { ...newMs, project_id: Number(projectId) }));
                  if (!r.ok) setMsg({ kind: 'error', text: await readError(r) }); else setNewMs({ title: '', date: '', phase: '' });
                  loadAll();
                }}>Ajouter</button>
              </div>
              <ul className="text-xs max-h-64 overflow-y-auto">
                {timeline.items.map((i, k) => <li key={k} className="border-t py-0.5"><span className="inline-block w-24">{fr(i.date)}</span><span className="inline-block w-28 font-medium" style={{ color: LANE_COLORS[i.lane] }}>{i.lane}</span>{i.label}</li>)}
              </ul>
            </section>
          )}

          {tab === 'obligations' && (
            <section className="bg-white border rounded-xl p-3 text-sm space-y-2">
              <p className="text-xs text-slate-500">Les échéances « proposées » ont été déduites d'une convention : vérifiez la phrase source, puis confirmez-les ou supprimez-les.
                Un rapport importé dans la GED solde automatiquement la prochaine échéance du même type.</p>
              <table className="w-full"><thead className="text-xs text-slate-500"><tr><th className="text-start">Échéance</th><th className="text-start">Rapport</th><th className="text-start">Statut</th><th className="text-start">Source</th><th /></tr></thead>
                <tbody>
                  {obligations.map((o) => (
                    <tr key={o.id} className="border-t align-top">
                      <td className="py-1">{fr(o.due)}</td><td>{o.title}</td>
                      <td><span className={`text-xs px-2 rounded-full ${o.status === 'Remise' ? 'bg-emerald-50 text-emerald-800' : o.status === 'Proposée' ? 'bg-amber-50 text-amber-800' : 'bg-slate-100'}`}>{o.status}</span></td>
                      <td className="text-xs text-slate-500 max-w-md" dir="auto">{o.excerpt ? `« ${o.excerpt} »` : 'saisie'}</td>
                      <td className="text-end whitespace-nowrap">
                        {o.status === 'Proposée' && <button title="Confirmer" className="text-emerald-700 me-2" onClick={() => saveObl({ id: o.id, status: 'À venir' })}><Check size={14} /></button>}
                        {o.status === 'À venir' && (
                          <select aria-label="Remis par le document" className="border rounded text-xs me-2 max-w-[12rem]" value=""
                                  onChange={(e) => e.target.value && saveObl({ id: o.id, status: 'Remise', delivered_document_id: e.target.value === 'none' ? null : Number(e.target.value) })}>
                            <option value="">Marquer remis…</option>
                            {docs.filter((d) => d.doc_type.startsWith('Rapport')).map((d) => <option key={d.id} value={d.id}>par « {d.title} »</option>)}
                            <option value="none">remis (hors GED)</option>
                          </select>
                        )}
                        {o.status === 'Remise' && o.delivered_document_id && <span className="text-[10px] text-slate-500 me-2">{docs.find((d) => d.id === o.delivered_document_id)?.title}</span>}
                        <button title="Supprimer" className="text-red-600" onClick={async () => { await apiFetch(`/api/ged/obligations/${o.id}`, { method: 'DELETE' }); loadAll(); }}><X size={14} /></button>
                      </td>
                    </tr>
                  ))}
                </tbody></table>
              <div className="flex flex-wrap items-end gap-2 border-t pt-2">
                <input aria-label="Titre de l'échéance" className="border rounded px-2 py-1" placeholder="Rapport intermédiaire…" value={newObl.title} onChange={(e) => setNewObl({ ...newObl, title: e.target.value })} />
                <select aria-label="Genre de rapport" className="border rounded px-2 py-1" value={newObl.kind} onChange={(e) => setNewObl({ ...newObl, kind: e.target.value })}>
                  <option>Rapport narratif</option><option>Rapport financier</option><option>Rapports narratif et financier</option><option>Rapport final</option>
                </select>
                <input aria-label="Date d'échéance" type="date" className="border rounded px-2 py-1" value={newObl.due} onChange={(e) => setNewObl({ ...newObl, due: e.target.value })} />
                <button className="bg-afmi-forest text-white rounded px-3 py-1" onClick={async () => { await saveObl({ ...newObl, project_id: Number(projectId) }); setNewObl({ title: '', kind: 'Rapport narratif', due: '' }); }}>Ajouter</button>
              </div>
            </section>
          )}

          {tab === 'search' && (
            <section className="grid lg:grid-cols-2 gap-3">
              <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
                <h3 className="font-semibold flex items-center gap-1"><Search size={14} />Recherche dans les documents</h3>
                <div className="flex gap-2"><input aria-label="Recherche" className="border rounded px-2 py-1 flex-1" placeholder="ex. visibilité logo" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
                  <button className="bg-afmi-forest text-white rounded px-3" onClick={search}>Chercher</button></div>
                {results && <div className="text-xs text-slate-500">Mode : {results.mode || '—'}{results.error ? ` — ${results.error}` : ''}</div>}
                {results?.results?.length === 0 && <p className="text-xs">Aucun résultat.</p>}
                <ul className="space-y-2">
                  {(results?.results || []).map((r, i) => (
                    <li key={i} className="border rounded p-2"><div className="font-medium">{r.title} <span className="text-xs text-slate-500">({r.doc_type}, p. {r.page})</span></div>
                      <div className="text-xs" dir="auto">{r.snippet.split(/(\[[^\]]*\])/).map((part, k) => (part.startsWith('[') ? <mark key={k}>{part.slice(1, -1)}</mark> : part))}</div></li>
                  ))}
                </ul>
              </div>
              <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
                <h3 className="font-semibold flex items-center gap-1"><MessageCircleQuestion size={14} />Poser une question</h3>
                <div className="flex gap-2"><input aria-label="Question" className="border rounded px-2 py-1 flex-1" placeholder="Quand le rapport final doit-il être remis ?" value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && ask()} />
                  <button className="bg-afmi-forest text-white rounded px-3" disabled={busy === 'ask'} onClick={ask}>{busy === 'ask' ? '…' : 'Demander'}</button></div>
                {answer && (
                  <div className="space-y-2">
                    <div className="border rounded p-2 whitespace-pre-wrap" dir="auto">{answer.answer}</div>
                    <div className="text-[11px] text-slate-500">Moteur : {answer.engine} · recherche : {answer.search}. Vérifiez la réponse dans les sources.</div>
                    <ol className="space-y-1">
                      {answer.sources.map((s) => <li key={s.n} className="text-xs border-t pt-1"><strong>[{s.n}] {s.title}</strong>, p. {s.page} — <span dir="auto">{s.excerpt.slice(0, 220)}…</span></li>)}
                    </ol>
                  </div>
                )}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
