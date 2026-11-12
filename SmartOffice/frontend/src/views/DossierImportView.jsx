import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileInput, UploadCloud, Loader2, AlertTriangle, Info, XCircle, CheckCircle2, FileText, ChevronDown, ChevronRight, Sparkles, History } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Import intelligent d'un dossier de projet (Lot 10) : convention, formulaire, budget, avenant → fiche, budget, activités,
// cadre logique, indicateurs, échéances, cofinancement. Tout est proposé avec sa source et vérifié avant application.

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const readError = async (res) => { try { return (await res.json()).detail || `Erreur ${res.status}`; } catch { return `Erreur ${res.status}`; } };
const num = (v) => (v == null || v === '' ? '' : Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 }));
const val = (x) => (x && typeof x === 'object' && 'value' in x ? x.value : x);
const LEVEL = {
  erreur: { icon: XCircle, cls: 'bg-red-50 text-red-800 border-red-200' },
  attention: { icon: AlertTriangle, cls: 'bg-amber-50 text-amber-900 border-amber-200' },
  info: { icon: Info, cls: 'bg-sky-50 text-sky-900 border-sky-200' },
};
const SECTIONS = [
  ['project', 'Fiche du projet'], ['funding', 'Financement et tranches'], ['budget', 'Budget'], ['cofinancing', 'Cofinancement'],
  ['activities', 'Activités et calendrier'], ['logframe', 'Cadre logique'], ['indicators', 'Indicateurs'], ['reports', 'Rapports à remettre'],
  ['rules', 'Règles du bailleur'], ['risks', 'Risques'], ['documents', 'Archiver les pièces dans la GED'],
];
const PROJECT_FIELDS = [
  ['code', 'Code / référence'], ['title', 'Intitulé complet'], ['donor', 'Bailleur'], ['start', 'Début'], ['end', 'Fin'],
  ['duration_months', 'Durée (mois)'], ['manager', 'Responsable'], ['location', 'Lieu'], ['objective', 'Objectif'],
];

function Source({ src }) {
  if (!src || (!src.file && !src.excerpt)) return null;
  return (
    <span className="text-[11px] text-slate-500" title={src.excerpt || ''}>
      <FileText className="inline w-3 h-3 me-0.5" />{src.file ? `${src.file}${src.page !== '' && src.page != null ? ` · p. ${src.page}` : ''}` : src.excerpt}
    </span>
  );
}

function Section({ id, title, count, open, onToggle, apply, setApply, children }) {
  return (
    <div className="bg-white border rounded-xl">
      <div className="flex items-center gap-2 px-3 py-2 border-b">
        <button className="flex items-center gap-1 font-semibold text-sm" onClick={onToggle}>
          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}{title}
          {count != null && <span className="text-xs text-slate-500 font-normal">({count})</span>}
        </button>
        <label className="ms-auto text-xs flex items-center gap-1"><input type="checkbox" checked={apply} onChange={(e) => setApply(id, e.target.checked)} /> Appliquer</label>
      </div>
      {open && <div className="p-3 overflow-x-auto">{children}</div>}
    </div>
  );
}

const Cell = ({ value, onChange, type = 'text', w = '' }) => (
  <input className={`border rounded px-1 py-0.5 text-xs w-full ${w}`} type={type} value={value ?? ''} onChange={(e) => onChange(type === 'number' ? (e.target.value === '' ? null : Number(e.target.value)) : e.target.value)} />
);

export default function DossierImportView({ fixedProjectId = null, embedded = false, onNavigate }) {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(fixedProjectId ? String(fixedProjectId) : '');
  const [files, setFiles] = useState([]);
  const [useAi, setUseAi] = useState(true);
  const [imp, setImp] = useState(null);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState(null);
  const [open, setOpen] = useState({ project: true, funding: true, budget: true });
  const [apply, setApplyState] = useState(Object.fromEntries(SECTIONS.map(([k]) => [k, true])));
  const [fieldsOn, setFieldsOn] = useState({ title: false, description: true, manager: true, start: true, end: true, budget_global: true, funder: true });
  const [create, setCreate] = useState({ code: '', name: '' });
  const [funder, setFunder] = useState('');
  const [inKind, setInKind] = useState('Suivi');
  const [done, setDone] = useState(null);

  const notify = (kind, text) => setMessage({ kind, text });
  const loadHistory = useCallback(() => apiFetch(`/api/dossier/imports${fixedProjectId ? `?project_id=${fixedProjectId}` : ''}`)
    .then((r) => (r.ok ? r.json() : [])).then(setHistory).catch(() => {}), [fixedProjectId]);
  useEffect(() => {
    apiFetch('/api/dossier/projects').then((r) => r.json()).then(setProjects).catch(() => notify('error', 'Base indisponible.'));
    loadHistory();
  }, [loadHistory]);

  const show = (data) => {
    setImp(data);
    setResult(data.result);
    setDone(data.status === 'Appliqué' ? { text: data.applied_summary, project_id: data.project_id } : null);
    const d = data.result.defaults || {};
    setCreate({ code: d.code || '', name: d.name || '' });
    setFunder(d.funder || '');
    if (data.project_id) setProjectId(String(data.project_id));
  };

  const analyze = async () => {
    if (!files.length) return notify('error', 'Ajoutez au moins un document du projet.');
    setBusy('analyze');
    setMessage(null);
    const fd = new FormData();
    files.forEach((f) => fd.append('files', f));
    if (projectId) fd.append('project_id', projectId);
    fd.append('use_ai', useAi ? 'true' : 'false');
    try {
      const res = await apiFetch('/api/dossier/analyze', { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await readError(res));
      show(await res.json());
      loadHistory();
    } catch (e) {
      notify('error', e.message);
    } finally {
      setBusy('');
    }
  };

  const reopen = async (id) => {
    const res = await apiFetch(`/api/dossier/imports/${id}`);
    if (res.ok) show(await res.json());
  };

  // --- modifications locales de la proposition
  const setPath = (fn) => setResult((r) => { const copy = JSON.parse(JSON.stringify(r)); fn(copy); return copy; });
  const setField = (sec, key, v) => setPath((r) => {
    r[sec] = r[sec] || {};
    const cur = r[sec][key];
    r[sec][key] = cur && typeof cur === 'object' && 'value' in cur ? { ...cur, value: v, engine: 'corrigé' } : { value: v, source: null, engine: 'saisi' };
  });
  const setItem = (list, i, key, v) => setPath((r) => { r[list][i][key] = v; });
  const delItem = (list, i) => setPath((r) => { r[list].splice(i, 1); });
  const setLine = (i, key, v) => setPath((r) => { r.budget.lines[i][key] = v; });
  const setApply = (k, v) => setApplyState((a) => ({ ...a, [k]: v }));

  const applyNow = async () => {
    if (!projectId && (!create.code || !create.name)) return notify('error', 'Choisissez le projet, ou donnez le code et le nom du projet à créer.');
    if (!window.confirm(projectId ? 'Appliquer les sections cochées au projet choisi ? Les éléments existants de même code sont mis à jour, rien n\'est supprimé.'
      : `Créer le projet « ${create.name} » et y appliquer les sections cochées ?`)) return;
    setBusy('apply');
    try {
      let res = await apiFetch(`/api/dossier/imports/${imp.id}`, json('PUT', { result, project_id: projectId ? Number(projectId) : null }));
      if (!res.ok) throw new Error(await readError(res));
      const fields = Object.entries(fieldsOn).filter(([, on]) => on).map(([k]) => k);
      res = await apiFetch(`/api/dossier/imports/${imp.id}/apply`, json('POST', {
        project_id: projectId ? Number(projectId) : null, create: projectId ? null : create, funder, in_kind: inKind,
        sections: Object.entries(apply).filter(([, on]) => on).map(([k]) => k), project_fields: fields, rename: fieldsOn.title,
      }));
      if (!res.ok) throw new Error(await readError(res));
      const out = await res.json();
      setDone(out);
      notify('success', `Dossier appliqué : ${out.text}.`);
      loadHistory();
      apiFetch('/api/dossier/projects').then((r) => r.json()).then(setProjects).catch(() => {});
    } catch (e) {
      notify('error', e.message);
    } finally {
      setBusy('');
    }
  };

  const issues = result?.issues || [];
  const budget = result?.budget;
  const budgetTotal = useMemo(() => (budget?.lines || []).reduce((s, l) => s + (Number(l.total) || 0), 0), [budget]);
  const sourcesTotal = useMemo(() => Object.fromEntries((budget?.sources || []).map((c) => [c, (budget.lines || []).reduce((s, l) => s + (Number(l.by_source?.[c]) || 0), 0)])), [budget]);
  const counts = { erreur: issues.filter((i) => i.level === 'erreur').length, attention: issues.filter((i) => i.level === 'attention').length };

  return (
    <div className="space-y-4">
      {!embedded && (
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><FileInput className="w-6 h-6" />Importer un dossier de projet</h1>
          <p className="text-sm text-slate-500">Déposez les documents du bailleur (convention, formulaire, budget Excel, avenant…) : l'application propose la fiche,
            le budget, les activités, le cadre logique, les indicateurs, les échéances et le cofinancement, avec leur source. Vous vérifiez, corrigez, puis appliquez.</p>
        </div>
      )}
      {message && <div role="status" className={`rounded px-3 py-2 text-sm ${message.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{message.text}</div>}

      {!result && (
        <div className="grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2 bg-white border rounded-xl p-4 space-y-3">
            <label className="block border-2 border-dashed rounded-xl p-6 text-center cursor-pointer hover:bg-slate-50"
              onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); setFiles((f) => [...f, ...e.dataTransfer.files]); }}>
              <UploadCloud className="w-8 h-8 mx-auto text-afmi-forest" />
              <div className="text-sm font-medium mt-1">Déposez ici les documents du projet, ou cliquez pour les choisir</div>
              <div className="text-xs text-slate-500">PDF, Word (.docx), Excel (.xlsx), texte — un seul document complet ou plusieurs pièces</div>
              <input type="file" multiple className="hidden" accept=".pdf,.docx,.xlsx,.xlsm,.txt,.md,.csv" onChange={(e) => setFiles((f) => [...f, ...e.target.files])} />
            </label>
            {files.length > 0 && (
              <ul className="text-sm space-y-1">{files.map((f, i) => (
                <li key={i} className="flex items-center gap-2"><FileText className="w-4 h-4 text-slate-400" />{f.name}
                  <span className="text-xs text-slate-400">{Math.round(f.size / 1024)} Ko</span>
                  <button className="ms-auto text-xs text-red-700" onClick={() => setFiles((fs) => fs.filter((_, j) => j !== i))}>Retirer</button></li>))}
              </ul>
            )}
            <div className="flex flex-wrap items-center gap-3 text-sm">
              {!fixedProjectId && (
                <select aria-label="Projet" className="border rounded px-2 py-1.5 min-w-0" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                  <option value="">Nouveau projet (créé à partir du dossier)</option>
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                </select>
              )}
              <label className="flex items-center gap-1"><input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
                <Sparkles className="w-4 h-4 text-afmi-gold" />Compléter avec l'IA si elle est autorisée</label>
              <button className="ms-auto bg-afmi-forest text-white rounded px-4 py-2 flex items-center gap-2 disabled:opacity-50" disabled={busy === 'analyze'} onClick={analyze}>
                {busy === 'analyze' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileInput className="w-4 h-4" />}Analyser le dossier</button>
            </div>
            <p className="text-xs text-slate-500">La lecture se fait sur ce poste. L'IA n'est utilisée que si elle est activée dans Paramètres › IA (tâche « Lecture des dossiers
              de projet ») ; les RIB, CIN et salaires sont alors masqués, et tout chiffre qu'elle propose est comparé au texte des documents.</p>
          </div>
          <div className="bg-white border rounded-xl p-4 text-sm">
            <h2 className="font-semibold flex items-center gap-1 mb-2"><History className="w-4 h-4" />Imports précédents</h2>
            {history.length === 0 && <p className="text-xs text-slate-400">Aucun import.</p>}
            {history.map((h) => (
              <button key={h.id} className="block w-full text-start border-t py-1.5 hover:bg-slate-50" onClick={() => reopen(h.id)}>
                <div className="text-xs font-medium">n° {h.id} · {h.status} · {h.created?.slice(0, 10)}</div>
                <div className="text-xs text-slate-500 truncate">{h.files.join(', ')}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {result && (
        <>
          <div className="bg-white border rounded-xl p-3 text-sm flex flex-wrap items-center gap-3">
            <div><span className="font-semibold">Import n° {imp.id}</span> · lu par {imp.engine} · {imp.files.map((f) => f.name).join(', ')}</div>
            <span className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-800">{counts.erreur} incohérence(s)</span>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-900">{counts.attention} point(s) à vérifier</span>
            <button className="ms-auto text-xs underline" onClick={() => { setResult(null); setImp(null); setFiles([]); setDone(null); }}>Nouvel import</button>
          </div>

          {issues.length > 0 && (
            <div className="space-y-1">
              {issues.map((i, k) => {
                const L = LEVEL[i.level] || LEVEL.info;
                return (
                  <div key={k} className={`border rounded px-3 py-1.5 text-sm flex items-start gap-2 ${L.cls}`}>
                    <L.icon className="w-4 h-4 mt-0.5 shrink-0" /><div className="min-w-0">{i.message} <Source src={i.source} /></div>
                  </div>
                );
              })}
            </div>
          )}

          <Section id="project" title="Fiche du projet" open={open.project} onToggle={() => setOpen((o) => ({ ...o, project: !o.project }))} apply={apply.project} setApply={setApply}>
            <table className="w-full text-sm">
              <tbody>
                {PROJECT_FIELDS.map(([k, label]) => {
                  const f = result.project?.[k];
                  return (
                    <tr key={k} className="border-t align-top">
                      <td className="py-1 pe-2 w-40 text-slate-600">{label}</td>
                      <td className="py-1 pe-2">{k === 'objective' || k === 'title'
                        ? <textarea className="border rounded px-1 py-0.5 text-xs w-full" rows={2} value={val(f) ?? ''} onChange={(e) => setField('project', k, e.target.value)} />
                        : <Cell value={val(f)} type={k === 'duration_months' ? 'number' : k === 'start' || k === 'end' ? 'date' : 'text'} onChange={(v) => setField('project', k, v)} />}
                        {f?.alternatives?.length > 0 && <div className="text-[11px] text-amber-800">Autre lecture : {f.alternatives.map((a) => JSON.stringify(a.value)).join(' · ')}</div>}
                      </td>
                      <td className="py-1 w-64"><Source src={f?.source} />{f?.engine && f.engine !== 'règles' && <span className="ms-1 text-[11px] text-afmi-forest">{f.engine}</span>}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="mt-2 text-xs text-slate-600 flex flex-wrap gap-3">
              <span>Écrire dans la fiche :</span>
              {[['title', 'remplacer le nom par l\'intitulé complet'], ['description', 'description (si vide)'], ['manager', 'responsable'], ['start', 'début'],
                ['end', 'fin'], ['budget_global', 'budget global'], ['funder', 'bailleur']].map(([k, l]) => (
                <label key={k} className="flex items-center gap-1"><input type="checkbox" checked={!!fieldsOn[k]} onChange={(e) => setFieldsOn((s) => ({ ...s, [k]: e.target.checked }))} />{l}</label>
              ))}
            </div>
          </Section>

          <Section id="funding" title="Financement et tranches" count={result.tranches?.length} open={open.funding} onToggle={() => setOpen((o) => ({ ...o, funding: !o.funding }))} apply={apply.funding} setApply={setApply}>
            <div className="grid md:grid-cols-3 gap-2 text-sm mb-3">
              {[['grant', 'Subvention'], ['grant_mad', 'Subvention en MAD'], ['cofinancing', 'Cofinancement annoncé'], ['total_cost', 'Coût total']].map(([k, l]) => {
                const f = result.funding?.[k];
                if (!f) return null;
                return (
                  <div key={k} className="border rounded p-2">
                    <div className="text-xs text-slate-500">{l}</div>
                    <div className="flex gap-1"><Cell type="number" value={val(f)?.amount} onChange={(v) => setField('funding', k, { ...val(f), amount: v })} />
                      <Cell w="w-16" value={val(f)?.currency} onChange={(v) => setField('funding', k, { ...val(f), currency: v.toUpperCase().slice(0, 3) })} /></div>
                    <Source src={f.source} />
                  </div>
                );
              })}
              {result.funding?.exchange_rate && (
                <div className="border rounded p-2"><div className="text-xs text-slate-500">Taux de change de la convention</div>
                  <Cell type="number" value={val(result.funding.exchange_rate)} onChange={(v) => setField('funding', 'exchange_rate', v)} /><Source src={result.funding.exchange_rate.source} /></div>
              )}
            </div>
            <table className="w-full text-xs">
              <thead><tr className="text-slate-500 text-start"><th className="text-start">Tranche</th><th>%</th><th>Montant</th><th>Date prévue</th><th className="text-start">Condition</th><th></th></tr></thead>
              <tbody>{(result.tranches || []).map((t, i) => (
                <tr key={i} className="border-t">
                  <td className="w-28"><Cell value={t.label} onChange={(v) => setItem('tranches', i, 'label', v)} /></td>
                  <td className="w-16"><Cell type="number" value={t.percent} onChange={(v) => setItem('tranches', i, 'percent', v)} /></td>
                  <td className="w-28"><Cell type="number" value={t.amount} onChange={(v) => setItem('tranches', i, 'amount', v)} /></td>
                  <td className="w-32"><Cell type="date" value={t.date} onChange={(v) => setItem('tranches', i, 'date', v)} /></td>
                  <td><Cell value={t.condition} onChange={(v) => setItem('tranches', i, 'condition', v)} /></td>
                  <td><button className="text-red-700" onClick={() => delItem('tranches', i)}>×</button></td>
                </tr>))}
              </tbody>
            </table>
          </Section>

          <Section id="budget" title={`Budget${budget ? ` — ${budget.origin}` : ''}`} count={budget?.lines?.length} open={open.budget} onToggle={() => setOpen((o) => ({ ...o, budget: !o.budget }))} apply={apply.budget} setApply={setApply}>
            {!budget ? <p className="text-sm text-slate-500">Aucun budget reconnu.</p> : (
              <table className="w-full text-xs">
                <thead><tr className="text-slate-500"><th className="text-start">Code</th><th className="text-start">Rubrique</th><th className="text-start">Libellé</th>
                  <th className="text-end">{budget.total_column} ({budget.currency || '?'})</th>{budget.sources.map((c) => <th key={c} className="text-end max-w-[9rem]">{c}</th>)}<th></th></tr></thead>
                <tbody>
                  {budget.lines.map((l, i) => (
                    <tr key={i} className={`border-t ${l.unverified ? 'bg-amber-50' : ''}`} title={l.source?.excerpt || ''}>
                      <td className="w-14"><Cell value={l.code} onChange={(v) => setLine(i, 'code', v)} /></td>
                      <td className="w-40"><Cell value={l.category} onChange={(v) => setLine(i, 'category', v)} /></td>
                      <td className="min-w-[14rem]"><Cell value={l.label} onChange={(v) => setLine(i, 'label', v)} /></td>
                      <td className="w-28"><Cell type="number" value={l.total} onChange={(v) => setLine(i, 'total', v)} /></td>
                      {budget.sources.map((c) => <td key={c} className="text-end pe-1">{num(l.by_source?.[c])}</td>)}
                      <td><button className="text-red-700" onClick={() => setPath((r) => { r.budget.lines.splice(i, 1); })}>×</button></td>
                    </tr>
                  ))}
                  <tr className="border-t font-semibold"><td colSpan={3}>Total des lignes{budget.declared_total != null ? ` (tableau : ${num(budget.declared_total)})` : ''}</td>
                    <td className="text-end pe-1">{num(budgetTotal)}</td>{budget.sources.map((c) => <td key={c} className="text-end pe-1">{num(sourcesTotal[c])}</td>)}<td /></tr>
                </tbody>
              </table>
            )}
          </Section>

          <Section id="cofinancing" title="Cofinancement" count={result.cofinancing?.length} open={open.cofinancing} onToggle={() => setOpen((o) => ({ ...o, cofinancing: !o.cofinancing }))} apply={apply.cofinancing} setApply={setApply}>
            <table className="w-full text-xs mb-2">
              <thead><tr className="text-slate-500"><th className="text-start">Cofinanceur (colonne du budget)</th><th>Type</th><th>Nature</th><th className="text-end">Prévu</th></tr></thead>
              <tbody>{(result.cofinancing || []).map((c, i) => (
                <tr key={i} className="border-t">
                  <td>{c.source_name}</td>
                  <td className="w-36"><select className="border rounded text-xs w-full" value={c.source_type} onChange={(e) => setItem('cofinancing', i, 'source_type', e.target.value)}>
                    {['Communauté', 'Association', 'Autre bailleur', 'Partenaire'].map((x) => <option key={x}>{x}</option>)}</select></td>
                  <td className="w-28"><select className="border rounded text-xs w-full" value={['Espèces', 'Nature'].includes(c.nature) ? c.nature : ''} onChange={(e) => setItem('cofinancing', i, 'nature', e.target.value)}>
                    <option value="">Espèces et nature (à préciser)</option><option>Espèces</option><option>Nature</option></select></td>
                  <td className="text-end">{num(c.amount)} {c.currency}</td>
                </tr>))}</tbody>
            </table>
            <p className="text-xs text-slate-500">Une contribution est créée par ligne budgétaire et par cofinanceur ; ses réalisations (heures, local, matériel…) se saisissent ensuite dans la Vue 360°.</p>
          </Section>

          <Section id="activities" title="Activités et calendrier" count={result.activities?.length} open={open.activities} onToggle={() => setOpen((o) => ({ ...o, activities: !o.activities }))} apply={apply.activities} setApply={setApply}>
            <table className="w-full text-xs">
              <thead><tr className="text-slate-500"><th className="text-start">Code</th><th className="text-start">Activité</th><th className="text-start">Responsable</th><th>Début</th><th>Fin</th><th /></tr></thead>
              <tbody>{(result.activities || []).map((a, i) => (
                <tr key={i} className="border-t" title={a.source?.excerpt || ''}>
                  <td className="w-16"><Cell value={a.code} onChange={(v) => setItem('activities', i, 'code', v)} /></td>
                  <td className="min-w-[18rem]"><Cell value={a.title} onChange={(v) => setItem('activities', i, 'title', v)} /></td>
                  <td className="w-32"><Cell value={a.responsible} onChange={(v) => setItem('activities', i, 'responsible', v)} /></td>
                  <td className="w-32"><Cell type="date" value={a.start} onChange={(v) => setItem('activities', i, 'start', v)} /></td>
                  <td className="w-32"><Cell type="date" value={a.end} onChange={(v) => setItem('activities', i, 'end', v)} /></td>
                  <td><button className="text-red-700" onClick={() => delItem('activities', i)}>×</button></td>
                </tr>))}</tbody>
            </table>
          </Section>

          <Section id="logframe" title="Cadre logique" count={result.logframe?.length} open={open.logframe} onToggle={() => setOpen((o) => ({ ...o, logframe: !o.logframe }))} apply={apply.logframe} setApply={setApply}>
            <table className="w-full text-xs"><tbody>{(result.logframe || []).map((n, i) => (
              <tr key={i} className="border-t">
                <td className="w-36"><select className="border rounded text-xs w-full" value={n.level} onChange={(e) => setItem('logframe', i, 'level', e.target.value)}>
                  {['Objectif global', 'Objectif spécifique', 'Résultat', 'Produit'].map((x) => <option key={x}>{x}</option>)}</select></td>
                <td className="w-16"><Cell value={n.code} onChange={(v) => setItem('logframe', i, 'code', v)} /></td>
                <td><Cell value={n.statement} onChange={(v) => setItem('logframe', i, 'statement', v)} /></td>
                <td><button className="text-red-700" onClick={() => delItem('logframe', i)}>×</button></td>
              </tr>))}</tbody></table>
          </Section>

          <Section id="indicators" title="Indicateurs" count={result.indicators?.length} open={open.indicators} onToggle={() => setOpen((o) => ({ ...o, indicators: !o.indicators }))} apply={apply.indicators} setApply={setApply}>
            <table className="w-full text-xs">
              <thead><tr className="text-slate-500"><th className="text-start">Code</th><th className="text-start">Indicateur</th><th>Cible</th><th>Unité</th><th>Résultat</th><th /></tr></thead>
              <tbody>{(result.indicators || []).map((d, i) => (
                <tr key={i} className={`border-t ${d.unverified ? 'bg-amber-50' : ''}`}>
                  <td className="w-16"><Cell value={d.code} onChange={(v) => setItem('indicators', i, 'code', v)} /></td>
                  <td className="min-w-[16rem]"><Cell value={d.name} onChange={(v) => setItem('indicators', i, 'name', v)} /></td>
                  <td className="w-20"><Cell type="number" value={d.target} onChange={(v) => setItem('indicators', i, 'target', v)} /></td>
                  <td className="w-24"><Cell value={d.unit} onChange={(v) => setItem('indicators', i, 'unit', v)} /></td>
                  <td className="w-16"><Cell value={d.result_code} onChange={(v) => setItem('indicators', i, 'result_code', v)} /></td>
                  <td><button className="text-red-700" onClick={() => delItem('indicators', i)}>×</button></td>
                </tr>))}</tbody>
            </table>
          </Section>

          <Section id="reports" title="Rapports à remettre" count={result.reports?.length} open={open.reports} onToggle={() => setOpen((o) => ({ ...o, reports: !o.reports }))} apply={apply.reports} setApply={setApply}>
            <table className="w-full text-xs"><tbody>{(result.reports || []).map((d, i) => (
              <tr key={i} className="border-t">
                <td><Cell value={d.title} onChange={(v) => setItem('reports', i, 'title', v)} /></td>
                <td className="w-36"><Cell type="date" value={d.due} onChange={(v) => setItem('reports', i, 'due', v)} /></td>
                <td className="text-slate-500 w-64">{d.note}</td>
                <td><button className="text-red-700" onClick={() => delItem('reports', i)}>×</button></td>
              </tr>))}</tbody></table>
          </Section>

          <Section id="rules" title="Règles du bailleur" count={result.rules?.length} open={open.rules} onToggle={() => setOpen((o) => ({ ...o, rules: !o.rules }))} apply={apply.rules} setApply={setApply}>
            <ul className="text-xs space-y-1">{(result.rules || []).map((r, i) => <li key={i}><b>{r.kind}</b>{r.value != null ? ` = ${r.value}` : ''} — {r.text} <Source src={r.source} /></li>)}</ul>
            {!result.rules?.length && <p className="text-xs text-slate-500">Aucune règle chiffrée repérée.</p>}
          </Section>

          <Section id="risks" title="Risques" count={result.risks?.length} open={open.risks} onToggle={() => setOpen((o) => ({ ...o, risks: !o.risks }))} apply={apply.risks} setApply={setApply}>
            {!result.risks?.length ? <p className="text-xs text-slate-500">Les risques sont lus par l'IA (paramètres › IA) ; sans IA, saisissez-les dans la fiche du projet.</p> : (
              <ul className="text-xs space-y-1">{result.risks.map((r, i) => <li key={i}>{r.description} — <i>{r.mitigation}</i></li>)}</ul>)}
          </Section>

          <div className="bg-white border rounded-xl p-4 space-y-3 text-sm">
            <h2 className="font-semibold">Appliquer</h2>
            <div className="flex flex-wrap gap-3 items-end">
              {!fixedProjectId && (
                <label className="flex flex-col text-xs">Projet
                  <select className="border rounded px-2 py-1.5 text-sm min-w-0" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                    <option value="">Créer un nouveau projet</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                  </select></label>
              )}
              {!projectId && <>
                <label className="flex flex-col text-xs">Code<input className="border rounded px-2 py-1.5 text-sm" value={create.code} onChange={(e) => setCreate((c) => ({ ...c, code: e.target.value }))} /></label>
                <label className="flex flex-col text-xs grow">Nom court<input className="border rounded px-2 py-1.5 text-sm" value={create.name} onChange={(e) => setCreate((c) => ({ ...c, name: e.target.value }))} /></label>
              </>}
              <label className="flex flex-col text-xs">Bailleur<input className="border rounded px-2 py-1.5 text-sm" value={funder} onChange={(e) => setFunder(e.target.value)} /></label>
              <label className="flex flex-col text-xs">Contributions en nature de ce bailleur
                <select className="border rounded px-2 py-1.5 text-sm" value={inKind} onChange={(e) => setInKind(e.target.value)}>
                  <option value="Suivi">Suivi seulement (tableau de cofinancement)</option>
                  <option value="Comptabilité">Suivi + écriture comptable de valorisation</option>
                </select></label>
            </div>
            <label className="text-xs flex items-center gap-1"><input type="checkbox" checked={apply.documents} onChange={(e) => setApply('documents', e.target.checked)} />
              Archiver les pièces dans la GED du projet (et dans ses dossiers locaux)</label>
            <div className="flex items-center gap-3">
              <button className="bg-afmi-forest text-white rounded px-4 py-2 flex items-center gap-2 disabled:opacity-50" disabled={busy === 'apply' || imp.status === 'Appliqué'} onClick={applyNow}>
                {busy === 'apply' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}Appliquer au projet</button>
              {counts.erreur > 0 && <span className="text-xs text-red-800">{counts.erreur} incohérence(s) signalée(s) : vérifiez-les avant d'appliquer.</span>}
            </div>
            {done && (
              <div className="bg-emerald-50 text-emerald-900 rounded p-3 text-sm">
                <div className="font-semibold">Appliqué : {done.text}</div>
                {onNavigate && <button className="underline text-xs mt-1" onClick={() => onNavigate('project360')}>Voir la Vue 360° du projet</button>}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
