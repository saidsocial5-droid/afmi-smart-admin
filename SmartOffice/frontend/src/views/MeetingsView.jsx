import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ClipboardList, Plus, Save, FilePenLine, Wand2, CheckCircle2, Trash2, ListTodo, AlertTriangle, Loader2, Users } from 'lucide-react';
import { apiFetch } from '../apiClient';
import DocumentEditor from '../editor/DocumentEditor';

// Comptes rendus et procès-verbaux (Lot 9) : réunions, COPIL, AG, CA, rencontres, visites, activités.
// Décisions et actions structurées et suivies ; texte rédigé dans l'éditeur ; validation = archivage dans la GED.

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const readError = async (res) => { try { return (await res.json()).detail || `Erreur ${res.status}`; } catch { return `Erreur ${res.status}`; } };
const EMPTY = { kind: 'Réunion', title: '', date: new Date().toISOString().slice(0, 10), start_time: '', location: '', project_id: '', task_id: '',
  organizer: '', secretary: '', agenda: '', summary: '', status: 'Brouillon', participants: [], decisions: [], actions: [] };
const fmtDate = (d) => (d ? d.split('-').reverse().join('/') : '');

export default function MeetingsView({ fixedProjectId = null, embedded = false }) {
  const [ctx, setCtx] = useState(null);
  const [list, setList] = useState([]);
  const [filter, setFilter] = useState({ project: fixedProjectId ? String(fixedProjectId) : '', year: '', kind: '' });
  const [form, setForm] = useState(null);
  const [proposals, setProposals] = useState(null);
  const [openActions, setOpenActions] = useState([]);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState('');

  const notify = (kind, text) => setMessage({ kind, text });
  const load = useCallback(async () => {
    const q = new URLSearchParams();
    if (filter.project === 'gov') q.set('governance', 'true'); else if (filter.project) q.set('project_id', filter.project);
    if (filter.year) q.set('year', filter.year);
    if (filter.kind) q.set('kind', filter.kind);
    const [l, a] = await Promise.all([
      apiFetch(`/api/meetings?${q}`).then((r) => (r.ok ? r.json() : [])),
      apiFetch(`/api/meetings/actions/open${filter.project && filter.project !== 'gov' ? `?project_id=${filter.project}` : ''}`).then((r) => (r.ok ? r.json() : [])),
    ]);
    setList(l);
    setOpenActions(a);
  }, [filter]);
  useEffect(() => { apiFetch('/api/meetings/context').then((r) => r.json()).then(setCtx).catch(() => notify('error', 'Base indisponible.')); }, []);
  useEffect(() => { load(); }, [load]);

  const years = useMemo(() => { const y = new Date().getFullYear(); return [y + 1, y, y - 1, y - 2, y - 3]; }, []);
  const tasks = (ctx?.tasks || []).filter((t) => String(t.project_id) === String(form?.project_id));
  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const setRow = (key, i, patch) => setForm((f) => ({ ...f, [key]: f[key].map((r, k) => (k === i ? { ...r, ...patch } : r)) }));
  const addRow = (key, row) => setForm((f) => ({ ...f, [key]: [...f[key], row] }));
  const delRow = (key, i) => setForm((f) => ({ ...f, [key]: f[key].filter((_, k) => k !== i) }));

  const openMeeting = async (id) => {
    const res = await apiFetch(`/api/meetings/${id}`);
    if (!res.ok) { notify('error', await readError(res)); return; }
    const m = await res.json();
    setForm({ ...m, project_id: m.project_id ?? '', task_id: m.task_id ?? '' });
    setProposals(null);
  };
  const newMeeting = () => {
    setForm({ ...EMPTY, project_id: fixedProjectId || (filter.project && filter.project !== 'gov' ? filter.project : '') });
    setProposals(null);
  };
  const save = async () => {
    setBusy('save');
    const res = await apiFetch('/api/meetings', json('POST', { ...form, project_id: form.project_id ? Number(form.project_id) : null,
      task_id: form.task_id ? Number(form.task_id) : null }));
    setBusy('');
    if (!res.ok) { notify('error', await readError(res)); return null; }
    const m = await res.json();
    setForm({ ...m, project_id: m.project_id ?? '', task_id: m.task_id ?? '' });
    notify('ok', 'Compte rendu enregistré.');
    load();
    return m;
  };
  const write = async () => {
    const m = form.id ? form : await save();
    if (!m) return;
    const res = await apiFetch(`/api/meetings/${m.id}/document`, { method: 'POST' });
    if (!res.ok) { notify('error', await readError(res)); return; }
    const r = await res.json();
    set({ editor_document_id: r.editor_document_id });
    notify('ok', r.created ? 'Texte pré-rempli créé dans l\'éditeur (participants, ordre du jour, actions de la réunion précédente…).' : 'Texte du compte rendu ouvert.');
  };
  const extract = async () => {
    setBusy('extract');
    const res = await apiFetch(`/api/meetings/${form.id}/extract`, { method: 'POST' });
    setBusy('');
    if (!res.ok) { notify('error', await readError(res)); return; }
    const p = await res.json();
    setProposals({ decisions: p.decisions.map((d) => ({ ...d, keep: true })), actions: p.actions.map((a) => ({ ...a, keep: true })) });
    if (!p.decisions.length && !p.actions.length) notify('ok', 'Aucune nouvelle décision ni action repérée dans le texte.');
  };
  const acceptProposals = () => {
    setForm((f) => ({ ...f, decisions: [...f.decisions, ...proposals.decisions.filter((d) => d.keep).map(({ text }) => ({ text }))],
      actions: [...f.actions, ...proposals.actions.filter((a) => a.keep).map(({ text, responsible, due_date }) => ({ text, responsible, due_date, status: 'À faire' }))] }));
    setProposals(null);
    notify('ok', 'Ajoutées au compte rendu : enregistrez pour confirmer.');
  };
  const validate = async () => {
    if (!(await save())) return;
    setBusy('validate');
    const res = await apiFetch(`/api/meetings/${form.id}/validate`, { method: 'POST' });
    setBusy('');
    if (!res.ok) { notify('error', await readError(res)); return; }
    const r = await res.json();
    setForm({ ...r.meeting, project_id: r.meeting.project_id ?? '', task_id: r.meeting.task_id ?? '' });
    notify('ok', `Compte rendu validé${r.archived_document_id ? ' et archivé dans les documents du projet' : ''}${r.activity_report_id ? ' ; rapport d\'activité mis à jour' : ''}. ${r.note || ''}`);
    load();
  };
  const toTask = async (action) => {
    const res = await apiFetch(`/api/meetings/actions/${action.id}/task`, { method: 'POST' });
    if (!res.ok) { notify('error', await readError(res)); return; }
    notify('ok', 'Tâche créée dans le planning du projet.');
    if (form?.id) openMeeting(form.id);
    load();
  };
  const actionStatus = async (id, status) => {
    await apiFetch(`/api/meetings/actions/${id}/status`, json('PUT', { status }));
    if (form?.id) openMeeting(form.id);
    load();
  };
  const remove = async () => {
    if (!window.confirm('Supprimer ce compte rendu ? Il reste dans l\'historique (suppression logique).')) return;
    await apiFetch(`/api/meetings/${form.id}`, { method: 'DELETE' });
    setForm(null);
    load();
  };

  if (!ctx) return <div className="text-sm text-slate-500">{message?.text || 'Chargement…'}</div>;
  const kindLabel = (k) => ctx.kinds[k]?.label || k;
  const isActivity = form && (form.kind === 'Activité' || form.kind === 'Visite');

  return (
    <div className="space-y-4">
      {!embedded && (
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><ClipboardList className="w-6 h-6" />Comptes rendus & PV</h1>
          <p className="text-sm text-slate-500">Réunions, comités de pilotage, assemblées générales, conseils d'administration, rencontres, visites et activités :
            décisions et actions suivies, texte rédigé dans l'éditeur, archivage dans les documents du projet.</p>
        </div>
      )}
      {message && (
        <div role="status" className={`rounded px-3 py-2 text-sm ${message.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>
          {message.text} <button className="ms-2 underline text-xs" onClick={() => setMessage(null)}>fermer</button></div>
      )}

      <div className="grid grid-cols-12 gap-4">
        <aside className="col-span-12 lg:col-span-4 space-y-3">
          <div className="bg-white border rounded-xl p-3 space-y-2 text-sm">
            {!fixedProjectId && (
              <select aria-label="Projet" className="border rounded px-2 py-1.5 w-full" value={filter.project} onChange={(e) => setFilter({ ...filter, project: e.target.value })}>
                <option value="">Tous les projets et la vie associative</option>
                <option value="gov">Vie associative (AG, CA…)</option>
                {ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
              </select>
            )}
            <div className="flex gap-2">
              <select aria-label="Année" className="border rounded px-2 py-1.5 flex-1 min-w-0" value={filter.year} onChange={(e) => setFilter({ ...filter, year: e.target.value })}>
                <option value="">Toutes les années</option>{years.map((y) => <option key={y}>{y}</option>)}
              </select>
              <select aria-label="Type" className="border rounded px-2 py-1.5 flex-1 min-w-0" value={filter.kind} onChange={(e) => setFilter({ ...filter, kind: e.target.value })}>
                <option value="">Tous les types</option>{Object.keys(ctx.kinds).map((k) => <option key={k} value={k}>{kindLabel(k)}</option>)}
              </select>
            </div>
            <button className="w-full bg-afmi-forest text-white rounded px-3 py-2 flex items-center justify-center gap-2" onClick={newMeeting}>
              <Plus className="w-4 h-4" /> Nouveau compte rendu</button>
          </div>
          <ul className="bg-white border rounded-xl divide-y max-h-[28rem] overflow-auto text-sm" aria-label="Comptes rendus">
            {list.map((m) => (
              <li key={m.id}>
                <button className={`w-full text-start px-3 py-2 hover:bg-slate-50 ${form?.id === m.id ? 'bg-emerald-50' : ''}`} onClick={() => openMeeting(m.id)}>
                  <div className="font-medium">{m.title}</div>
                  <div className="text-xs text-slate-500">{fmtDate(m.date)} · {kindLabel(m.kind)} · {m.project} · {m.status}
                    {m.actions.some((a) => a.late) && <span className="text-red-700"> · action en retard</span>}</div>
                </button>
              </li>
            ))}
            {list.length === 0 && <li className="px-3 py-3 text-slate-400">Aucun compte rendu.</li>}
          </ul>
          <div className="bg-white border rounded-xl p-3 text-sm">
            <h2 className="font-semibold flex items-center gap-2 mb-2"><ListTodo className="w-4 h-4" />Actions en cours ({openActions.length})</h2>
            <ul className="space-y-1 max-h-64 overflow-auto">
              {openActions.map((a) => (
                <li key={a.id} className="text-xs border-b pb-1">
                  <div className={a.late ? 'text-red-700 font-medium' : ''}>{a.late && <AlertTriangle className="inline w-3 h-3 me-1" />}{a.text}</div>
                  <div className="text-slate-500 flex gap-2 items-center">{a.responsible || '—'} · {a.due_date ? fmtDate(a.due_date) : 'sans échéance'} · {a.meeting}
                    <select aria-label="Statut de l'action" className="ms-auto border rounded px-1" value={a.status} onChange={(e) => actionStatus(a.id, e.target.value)}>
                      {ctx.action_statuses.map((s) => <option key={s}>{s}</option>)}</select></div>
                </li>
              ))}
              {openActions.length === 0 && <li className="text-xs text-slate-400">Aucune action en attente.</li>}
            </ul>
          </div>
        </aside>

        <section className="col-span-12 lg:col-span-8 space-y-3">
          {!form && <div className="bg-white border rounded-xl p-6 text-sm text-slate-500">Choisissez un compte rendu ou créez-en un nouveau.</div>}
          {form && (
            <>
              <div className="bg-white border rounded-xl p-4 grid md:grid-cols-3 gap-3 text-sm">
                <label className="flex flex-col gap-1">Type
                  <select className="border rounded px-2 py-1.5" value={form.kind} onChange={(e) => set({ kind: e.target.value })}>
                    {Object.keys(ctx.kinds).map((k) => <option key={k} value={k}>{kindLabel(k)}</option>)}</select></label>
                <label className="flex flex-col gap-1 md:col-span-2">Intitulé
                  <input className="border rounded px-2 py-1.5" value={form.title} onChange={(e) => set({ title: e.target.value })} placeholder="Ex. : Comité de pilotage n° 2" /></label>
                <label className="flex flex-col gap-1">Date<input type="date" className="border rounded px-2 py-1.5" value={form.date} onChange={(e) => set({ date: e.target.value })} /></label>
                <label className="flex flex-col gap-1">Heure<input type="time" className="border rounded px-2 py-1.5" value={form.start_time} onChange={(e) => set({ start_time: e.target.value })} /></label>
                <label className="flex flex-col gap-1">Lieu<input className="border rounded px-2 py-1.5" value={form.location} onChange={(e) => set({ location: e.target.value })} /></label>
                <label className="flex flex-col gap-1">Projet
                  <select className="border rounded px-2 py-1.5" disabled={!!fixedProjectId} value={form.project_id} onChange={(e) => set({ project_id: e.target.value, task_id: '' })}>
                    <option value="">Vie associative (sans projet)</option>
                    {ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}</select></label>
                {isActivity && (
                  <label className="flex flex-col gap-1">Activité du projet (planning)
                    <select className="border rounded px-2 py-1.5" value={form.task_id} onChange={(e) => set({ task_id: e.target.value })}>
                      <option value="">—</option>{tasks.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
                )}
                <label className="flex flex-col gap-1">{form.kind === 'AG' || form.kind === 'CA' ? 'Président(e) de séance' : 'Organisateur'}
                  <input className="border rounded px-2 py-1.5" value={form.organizer} onChange={(e) => set({ organizer: e.target.value })} /></label>
                <label className="flex flex-col gap-1">Secrétaire / rédacteur<input className="border rounded px-2 py-1.5" value={form.secretary} onChange={(e) => set({ secretary: e.target.value })} /></label>
                <label className="flex flex-col gap-1 md:col-span-3">{isActivity ? 'Objectifs (un par ligne)' : 'Ordre du jour (un point par ligne)'}
                  <textarea rows={3} className="border rounded px-2 py-1.5" value={form.agenda} onChange={(e) => set({ agenda: e.target.value })} /></label>
                <label className="flex flex-col gap-1 md:col-span-3">Résumé
                  <textarea rows={3} className="border rounded px-2 py-1.5" value={form.summary} onChange={(e) => set({ summary: e.target.value })} /></label>
              </div>

              <div className="bg-white border rounded-xl p-4 text-sm space-y-2">
                <h2 className="font-semibold flex items-center gap-2"><Users className="w-4 h-4" />Participants
                  {form.attendance && <span className="text-xs font-normal text-slate-500">— {form.attendance.present} présents ({form.attendance.women} F, {form.attendance.men} H), {form.attendance.excused} excusés</span>}</h2>
                <table className="w-full text-xs"><tbody>
                  {form.participants.map((p, i) => (
                    <tr key={i}>
                      <td><input aria-label="Nom" className="border rounded px-1 py-1 w-full" value={p.name} onChange={(e) => setRow('participants', i, { name: e.target.value })} placeholder="Nom" /></td>
                      <td><input aria-label="Structure" className="border rounded px-1 py-1 w-full" value={p.organization || ''} onChange={(e) => setRow('participants', i, { organization: e.target.value })} placeholder="Structure" /></td>
                      <td><input aria-label="Fonction" className="border rounded px-1 py-1 w-full" value={p.role || ''} onChange={(e) => setRow('participants', i, { role: e.target.value })} placeholder="Fonction" /></td>
                      <td><select aria-label="Sexe" className="border rounded px-1 py-1" value={p.sex || ''} onChange={(e) => setRow('participants', i, { sex: e.target.value })}><option value="">—</option><option value="F">F</option><option value="M">H</option></select></td>
                      <td className="text-center"><label className="flex items-center gap-1"><input type="checkbox" checked={p.present !== false} onChange={(e) => setRow('participants', i, { present: e.target.checked })} />présent</label></td>
                      <td><button aria-label="Retirer" className="text-red-700" onClick={() => delRow('participants', i)}><Trash2 className="w-3.5 h-3.5" /></button></td>
                    </tr>
                  ))}
                </tbody></table>
                <button className="text-xs bg-slate-100 rounded px-2 py-1" onClick={() => addRow('participants', { name: '', organization: '', role: '', sex: '', present: true })}>+ Participant</button>
              </div>

              <div className="grid md:grid-cols-2 gap-3">
                <div className="bg-white border rounded-xl p-4 text-sm space-y-2">
                  <h2 className="font-semibold">Décisions</h2>
                  {form.decisions.map((d, i) => (
                    <div key={i} className="flex gap-1"><span className="text-xs text-slate-400 pt-1">{i + 1}.</span>
                      <textarea aria-label="Décision" rows={2} className="border rounded px-1 py-1 flex-1 text-xs" value={d.text} onChange={(e) => setRow('decisions', i, { text: e.target.value })} />
                      <button aria-label="Retirer" className="text-red-700" onClick={() => delRow('decisions', i)}><Trash2 className="w-3.5 h-3.5" /></button></div>
                  ))}
                  <button className="text-xs bg-slate-100 rounded px-2 py-1" onClick={() => addRow('decisions', { text: '' })}>+ Décision</button>
                </div>
                <div className="bg-white border rounded-xl p-4 text-sm space-y-2">
                  <h2 className="font-semibold">Actions à mener</h2>
                  {form.actions.map((a, i) => (
                    <div key={i} className={`border rounded p-2 space-y-1 ${a.late ? 'border-red-300 bg-red-50' : ''}`}>
                      <input aria-label="Action" className="border rounded px-1 py-1 w-full text-xs" value={a.text} onChange={(e) => setRow('actions', i, { text: e.target.value })} placeholder="Action" />
                      <div className="flex gap-1 text-xs items-center">
                        <input aria-label="Responsable" className="border rounded px-1 py-1 flex-1" value={a.responsible || ''} onChange={(e) => setRow('actions', i, { responsible: e.target.value })} placeholder="Responsable" />
                        <input aria-label="Échéance" type="date" className="border rounded px-1 py-1" value={a.due_date || ''} onChange={(e) => setRow('actions', i, { due_date: e.target.value || null })} />
                        <select aria-label="Statut" className="border rounded px-1 py-1" value={a.status || 'À faire'} onChange={(e) => setRow('actions', i, { status: e.target.value })}>
                          {ctx.action_statuses.map((s) => <option key={s}>{s}</option>)}</select>
                        <button aria-label="Retirer" className="text-red-700" onClick={() => delRow('actions', i)}><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                      {a.id && form.project_id && (a.task_id
                        ? <div className="text-[11px] text-emerald-700">✔ tâche du planning du projet</div>
                        : <button className="text-[11px] underline text-afmi-forest" onClick={() => toTask(a)}>→ Créer la tâche dans le planning du projet</button>)}
                    </div>
                  ))}
                  <button className="text-xs bg-slate-100 rounded px-2 py-1" onClick={() => addRow('actions', { text: '', responsible: '', due_date: null, status: 'À faire' })}>+ Action</button>
                </div>
              </div>

              {proposals && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-sm space-y-1">
                  <strong>Repéré dans le texte (à vérifier)</strong>
                  {proposals.decisions.map((d, i) => (
                    <label key={`d${i}`} className="flex gap-2 text-xs"><input type="checkbox" checked={d.keep} onChange={(e) => setProposals({ ...proposals, decisions: proposals.decisions.map((x, k) => (k === i ? { ...x, keep: e.target.checked } : x)) })} />Décision : {d.text}</label>
                  ))}
                  {proposals.actions.map((a, i) => (
                    <label key={`a${i}`} className="flex gap-2 text-xs"><input type="checkbox" checked={a.keep} onChange={(e) => setProposals({ ...proposals, actions: proposals.actions.map((x, k) => (k === i ? { ...x, keep: e.target.checked } : x)) })} />
                      Action : {a.text}{a.responsible ? ` — ${a.responsible}` : ''}{a.due_date ? ` — ${fmtDate(a.due_date)}` : ''}</label>
                  ))}
                  <button className="bg-afmi-forest text-white rounded px-3 py-1 text-xs" onClick={acceptProposals}>Ajouter la sélection</button>
                </div>
              )}

              <div className="flex flex-wrap gap-2 text-sm">
                <button className="bg-afmi-forest text-white rounded px-3 py-2 flex items-center gap-2" onClick={save} disabled={!!busy}>
                  {busy === 'save' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Enregistrer</button>
                <button className="bg-slate-100 rounded px-3 py-2 flex items-center gap-2" onClick={write}><FilePenLine className="w-4 h-4" />
                  {form.editor_document_id ? 'Texte du compte rendu' : 'Rédiger dans l\'éditeur'}</button>
                {form.editor_document_id && (
                  <button className="bg-slate-100 rounded px-3 py-2 flex items-center gap-2" onClick={extract} disabled={!!busy}>
                    {busy === 'extract' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} Repérer décisions et actions dans le texte</button>
                )}
                {form.id && (
                  <button className="bg-emerald-700 text-white rounded px-3 py-2 flex items-center gap-2" onClick={validate} disabled={!!busy}>
                    {busy === 'validate' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Valider et archiver</button>
                )}
                {form.id && <button className="ms-auto text-red-700 flex items-center gap-1" onClick={remove}><Trash2 className="w-4 h-4" /> Supprimer</button>}
                <span className="text-xs text-slate-500 self-center">Statut : {form.status}</span>
              </div>

              {form.editor_document_id && (
                <div className="border-t pt-3">
                  <DocumentEditor key={form.editor_document_id} initialDocumentId={form.editor_document_id} embedded />
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
