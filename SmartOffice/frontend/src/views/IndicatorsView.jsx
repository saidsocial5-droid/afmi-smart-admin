import React, { useEffect, useState } from 'react';
import { Target, Plus, Trash2 } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Indicateurs GAR par projet : niveau, référence, cible, mode de cumul ; mesures datées et désagrégées.

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const EMPTY_M = { period_end: '', value: '', sex: '', age_group: '', zone: '', source: '' };

export default function IndicatorsView() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState('');
  const [items, setItems] = useState([]);
  const [newInd, setNewInd] = useState({ name: '', unit: '', target: '', level: 'Extrant', baseline: '', aggregation: 'Somme' });
  const [forms, setForms] = useState({});
  const [msg, setMsg] = useState(null);

  useEffect(() => { apiFetch('/api/editor/context').then((r) => r.json()).then((c) => setProjects(c.projects || [])).catch(() => {}); }, []);
  const load = async () => {
    if (!projectId) { setItems([]); return; }
    const res = await apiFetch(`/api/indicators?project_id=${projectId}`);
    if (res.ok) setItems(await res.json());
  };
  useEffect(() => { load(); }, [projectId]);

  const call = async (res, ok) => {
    if (!res.ok) { setMsg({ kind: 'error', text: (await res.json()).detail }); return false; }
    setMsg(ok ? { kind: 'ok', text: ok } : null);
    await load();
    return true;
  };
  const saveIndicator = (ind) => apiFetch('/api/indicators', json('POST', { ...ind, project_id: Number(projectId) }));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><Target className="w-6 h-6" />Indicateurs et bénéficiaires</h1>
        <p className="text-sm text-slate-500">Les mesures datées alimentent les rapports (valeur de l'exercice). Une mesure désagrégée (sexe, âge, zone) détaille les bénéficiaires ;
          une mesure sans désagrégation est un total.</p>
      </div>
      {msg && <div role="status" className={`rounded px-3 py-2 text-sm ${msg.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{msg.text}</div>}
      <select aria-label="Projet" className="border rounded px-2 py-1.5 text-sm" value={projectId} onChange={(e) => setProjectId(e.target.value)}>
        <option value="">Choisir un projet…</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
      </select>

      {projectId && (
        <section className="bg-white border rounded-xl p-3 flex flex-wrap items-end gap-2 text-sm">
          <Plus className="w-4 h-4" />
          <input aria-label="Nom du nouvel indicateur" className="border rounded px-2 py-1" placeholder="Nouvel indicateur" value={newInd.name} onChange={(e) => setNewInd({ ...newInd, name: e.target.value })} />
          <input aria-label="Unité" className="border rounded px-2 py-1 w-24" placeholder="Unité" value={newInd.unit} onChange={(e) => setNewInd({ ...newInd, unit: e.target.value })} />
          <input aria-label="Cible" type="number" className="border rounded px-2 py-1 w-24" placeholder="Cible" value={newInd.target} onChange={(e) => setNewInd({ ...newInd, target: e.target.value })} />
          <select aria-label="Niveau" className="border rounded px-2 py-1" value={newInd.level} onChange={(e) => setNewInd({ ...newInd, level: e.target.value })}>
            <option>Impact</option><option>Effet</option><option>Extrant</option></select>
          <button className="bg-afmi-forest text-white rounded px-3 py-1" onClick={async () => {
            if (await call(await saveIndicator(newInd), 'Indicateur ajouté.')) setNewInd({ name: '', unit: '', target: '', level: 'Extrant', baseline: '', aggregation: 'Somme' });
          }}>Ajouter</button>
        </section>
      )}

      {items.map((ind) => {
        const f = forms[ind.id] || EMPTY_M;
        const setF = (patch) => setForms({ ...forms, [ind.id]: { ...f, ...patch } });
        return (
          <section key={ind.id} className="bg-white border rounded-xl p-3 text-sm space-y-2">
            <div className="flex flex-wrap items-end gap-2">
              <div className="font-semibold me-2">{ind.name} <span className="text-xs text-slate-500">({ind.unit}) · valeur courante {ind.current?.toLocaleString('fr-FR')}</span></div>
              <label className="text-xs flex flex-col">Niveau<select className="border rounded px-1 py-1" value={ind.level} onChange={(e) => call(saveIndicator({ ...ind, level: e.target.value }))}><option>Impact</option><option>Effet</option><option>Extrant</option></select></label>
              <label className="text-xs flex flex-col">Référence<input type="number" className="border rounded px-1 py-1 w-20" defaultValue={ind.baseline ?? ''} onBlur={(e) => call(saveIndicator({ ...ind, baseline: e.target.value }))} /></label>
              <label className="text-xs flex flex-col">Cible<input type="number" className="border rounded px-1 py-1 w-20" defaultValue={ind.target} onBlur={(e) => call(saveIndicator({ ...ind, target: e.target.value }))} /></label>
              <label className="text-xs flex flex-col">Cumul sur la période<select className="border rounded px-1 py-1" value={ind.aggregation} onChange={(e) => call(saveIndicator({ ...ind, aggregation: e.target.value }))}>
                <option value="Somme">Somme des mesures</option><option value="Dernière">Dernière mesure</option></select></label>
            </div>
            <table className="w-full text-xs">
              <thead className="text-slate-500"><tr><th className="text-start">Fin de période</th><th className="text-end">Valeur</th><th className="text-start">Sexe</th><th className="text-start">Âge</th><th className="text-start">Zone</th><th className="text-start">Source</th><th /></tr></thead>
              <tbody>
                {ind.measurements.map((m) => (
                  <tr key={m.id} className="border-t"><td>{m.period_end}</td><td className="text-end">{m.value.toLocaleString('fr-FR')}</td>
                    <td>{m.sex === 'F' ? 'Femmes' : m.sex === 'M' ? 'Hommes' : '—'}</td><td>{m.age_group || '—'}</td><td>{m.zone || '—'}</td><td>{m.source}</td>
                    <td className="text-end"><button aria-label="Supprimer la mesure" className="text-red-600" onClick={async () => { if (window.confirm('Supprimer cette mesure ?')) call(await apiFetch(`/api/indicators/${ind.id}/measurements/${m.id}`, { method: 'DELETE' })); }}><Trash2 size={12} /></button></td></tr>
                ))}
                <tr className="border-t bg-slate-50">
                  <td><input aria-label="Fin de période" type="date" className="border rounded px-1" value={f.period_end} onChange={(e) => setF({ period_end: e.target.value })} /></td>
                  <td><input aria-label="Valeur" type="number" className="border rounded px-1 w-20 text-end" value={f.value} onChange={(e) => setF({ value: e.target.value })} /></td>
                  <td><select aria-label="Sexe" className="border rounded" value={f.sex} onChange={(e) => setF({ sex: e.target.value })}><option value="">Total</option><option value="F">Femmes</option><option value="M">Hommes</option></select></td>
                  <td><input aria-label="Tranche d'âge" className="border rounded px-1 w-24" placeholder="ex. 15-24 ans" value={f.age_group} onChange={(e) => setF({ age_group: e.target.value })} /></td>
                  <td><input aria-label="Zone" className="border rounded px-1 w-24" value={f.zone} onChange={(e) => setF({ zone: e.target.value })} /></td>
                  <td><input aria-label="Source" className="border rounded px-1 w-28" placeholder="liste de présence…" value={f.source} onChange={(e) => setF({ source: e.target.value })} /></td>
                  <td className="text-end"><button className="bg-afmi-forest text-white rounded px-2 py-0.5" onClick={async () => {
                    if (!f.period_end || f.value === '') { setMsg({ kind: 'error', text: 'Date de fin de période et valeur obligatoires.' }); return; }
                    if (await call(await apiFetch(`/api/indicators/${ind.id}/measurements`, json('POST', f)), 'Mesure enregistrée.')) setForms({ ...forms, [ind.id]: EMPTY_M });
                  }}>Ajouter</button></td>
                </tr>
              </tbody>
            </table>
          </section>
        );
      })}
    </div>
  );
}
