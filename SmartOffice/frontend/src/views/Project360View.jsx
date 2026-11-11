import React, { useEffect, useState } from 'react';
import { Orbit, Wallet, Target, ClipboardList, FolderOpen, FileText, AlertTriangle, Images, ListTodo, Landmark, ArrowRight } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Vue 360° d'un projet (Lot 9) : tout ce qui le concerne, depuis la base unique, avec un lien vers chaque module.

const mad = (cents) => (cents == null ? '—' : (cents / 100).toLocaleString('fr-FR', { maximumFractionDigits: 0 }));
const fr = (d) => (d ? d.slice(0, 10).split('-').reverse().join('/') : '');

function Card({ icon: Icon, title, onOpen, children }) {
  return (
    <div className="bg-white border rounded-xl p-4 text-sm space-y-2">
      <div className="flex items-center gap-2"><Icon className="w-4 h-4 text-afmi-forest" /><h2 className="font-semibold">{title}</h2>
        {onOpen && <button className="ms-auto text-xs text-afmi-forest flex items-center gap-1" onClick={onOpen}>Ouvrir <ArrowRight className="w-3 h-3" /></button>}</div>
      {children}
    </div>
  );
}

export default function Project360View({ fixedProjectId = null, onNavigate }) {
  const [projects, setProjects] = useState([]);
  const [pid, setPid] = useState(fixedProjectId || '');
  const [o, setO] = useState(null);
  const [error, setError] = useState('');
  const go = (tab) => (onNavigate ? onNavigate(tab) : undefined);

  useEffect(() => {
    if (fixedProjectId) return;
    apiFetch('/api/meetings/context').then((r) => r.json()).then((c) => { setProjects(c.projects); if (!pid && c.projects[0]) setPid(c.projects[0].id); }).catch(() => {});
  }, [fixedProjectId]);
  useEffect(() => {
    if (!pid) return;
    setO(null);
    apiFetch(`/api/overview/project/${pid}`).then(async (r) => (r.ok ? setO(await r.json()) : setError((await r.json()).detail))).catch(() => setError('Base indisponible.'));
  }, [pid]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="me-auto">
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><Orbit className="w-6 h-6" />Vue 360° du projet</h1>
          <p className="text-sm text-slate-500">Budget, trésorerie, indicateurs, activités, comptes rendus, actions, documents, échéances et alertes, en un seul endroit.</p>
        </div>
        {!fixedProjectId && (
          <select aria-label="Projet" className="border rounded px-2 py-1.5 text-sm" value={pid} onChange={(e) => setPid(e.target.value)}>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select>
        )}
      </div>
      {error && <div className="bg-red-50 text-red-800 rounded px-3 py-2 text-sm">{error}</div>}
      {o && (
        <>
          <div className="bg-afmi-forest text-white rounded-xl p-4 flex flex-wrap gap-6 text-sm">
            <div><div className="text-lg font-bold">{o.project.code} — {o.project.name}</div>
              <div className="opacity-80">{o.project.status} · {o.project.manager || 'responsable à préciser'}{o.project.funder ? ` · ${o.project.funder}` : ''}</div></div>
            <div><div className="opacity-70 text-xs">Période</div>{fr(o.project.start)} → {fr(o.project.end)}</div>
            <div><div className="opacity-70 text-xs">Avancement des tâches</div>{o.tasks.done}/{o.tasks.count} terminées · {o.tasks.progress} %</div>
            {o.project.local_folder && <div className="text-xs opacity-80 self-end">Dossier local : {o.project.local_folder}</div>}
          </div>

          {o.alerts.length > 0 && (
            <Card icon={AlertTriangle} title={`Alertes (${o.alerts.length})`} onOpen={() => go('ged')}>
              <ul className="space-y-1">{o.alerts.map((a, i) => <li key={i} className={a.level === 'critical' ? 'text-red-700' : 'text-amber-800'}>{a.message}</li>)}</ul>
            </Card>
          )}

          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            <Card icon={Wallet} title="Budget et réalisé (MAD)" onOpen={() => go('reports')}>
              <div className="text-2xl font-bold">{o.budget.rate == null ? '—' : `${o.budget.rate.toLocaleString('fr-FR')} %`}</div>
              <div className="text-xs text-slate-500">{mad(o.budget.realized)} réalisés sur {mad(o.budget.planned)} prévus · {o.budget.lines} lignes</div>
              <div className="h-2 bg-slate-100 rounded"><div className="h-2 bg-afmi-forest rounded" style={{ width: `${Math.min(100, o.budget.rate || 0)}%` }} /></div>
              {o.budget.draft_operations > 0 && <div className="text-xs text-amber-800">{o.budget.draft_operations} opération(s) en brouillon à valider (Trésorerie).</div>}
            </Card>
            <Card icon={Landmark} title="Trésorerie et conventions" onOpen={() => go('statements')}>
              {o.treasury.map((a) => <div key={a.id} className="flex justify-between text-xs"><span>{a.title}</span><span>{mad(a.balance)} {a.currency} · {a.reconciliation === 'ok' ? '✔ rapproché' : 'à rapprocher'}</span></div>)}
              {o.agreements.map((g) => <div key={g.reference} className="text-xs text-slate-600">Convention {g.reference} : {mad(g.received)} / {mad(g.amount)} {g.currency} reçus{g.end ? ` · fin ${fr(g.end)}` : ''}</div>)}
              {!o.treasury.length && !o.agreements.length && <div className="text-xs text-slate-400">Aucun compte ni convention liés.</div>}
            </Card>
            <Card icon={Target} title="Indicateurs" onOpen={() => go('indicators')}>
              {o.indicators.map((i) => (
                <div key={i.name} className="text-xs"><div className="flex justify-between"><span>{i.name}</span><span>{i.current?.toLocaleString('fr-FR')} / {i.target?.toLocaleString('fr-FR')} {i.unit}</span></div>
                  <div className="h-1.5 bg-slate-100 rounded"><div className="h-1.5 bg-afmi-gold rounded" style={{ width: `${Math.min(100, i.rate || 0)}%` }} /></div></div>
              ))}
              {!o.indicators.length && <div className="text-xs text-slate-400">Aucun indicateur.</div>}
            </Card>
            <Card icon={ClipboardList} title={`Comptes rendus & activités (${o.meetings.count})`} onOpen={() => go('meetings')}>
              <div className="text-xs text-slate-600">{o.activities.count} activité(s) · {o.activities.participants} participants</div>
              {o.meetings.last.map((m) => <div key={m.id} className="text-xs">{fr(m.date)} — {m.title} <span className="text-slate-400">({m.kind}, {m.status})</span></div>)}
            </Card>
            <Card icon={ListTodo} title={`Actions en cours (${o.meetings.open_actions.length})`} onOpen={() => go('meetings')}>
              {o.meetings.open_actions.map((a) => <div key={a.id} className={`text-xs ${a.late ? 'text-red-700' : ''}`}>{a.text} — {a.responsible || '?'}{a.due_date ? ` · ${fr(a.due_date)}` : ''}</div>)}
              {!o.meetings.open_actions.length && <div className="text-xs text-slate-400">Aucune action en attente.</div>}
            </Card>
            <Card icon={FolderOpen} title={`Documents (${o.documents.total})`} onOpen={() => go('folders')}>
              <div className="flex flex-wrap gap-1">{Object.entries(o.documents.by_type).map(([t, n]) => <span key={t} className="text-xs bg-slate-100 rounded px-1.5">{t} : {n}</span>)}</div>
              {o.documents.obligations.map((ob, i) => <div key={i} className="text-xs text-slate-600">Échéance : {ob.title} — {fr(ob.due)} ({ob.status})</div>)}
            </Card>
            <Card icon={FileText} title="Rapports et documents rédigés" onOpen={() => go('editor')}>
              {o.editor_documents.map((d) => <div key={d.id} className="text-xs">{d.title}</div>)}
              {!o.editor_documents.length && <div className="text-xs text-slate-400">Aucun document rédigé.</div>}
            </Card>
            <Card icon={Images} title={`Photos (${o.photos})`} onOpen={() => go('photos')}>
              <div className="text-xs text-slate-500">Photos d'activités du projet, utilisables dans les rapports (consentement requis).</div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
