import React, { useEffect, useState } from 'react';
import { FileBarChart2, ShieldCheck, Loader2, XCircle, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Assistant de génération des rapports annuels moral et financier (Lot 5).

const json = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export default function AnnualReportsView({ onOpenDocument }) {
  const [ctx, setCtx] = useState({ years: [], projects: [], funders: [], templates: [] });
  const [form, setForm] = useState({ year: new Date().getFullYear() - 1, scope_type: 'association', scope_id: '', language: 'fr', kind: 'both', template_id: '', use_ai: false });
  const [checks, setChecks] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    apiFetch('/api/reports/context').then((r) => r.json()).then((c) => {
      setCtx(c);
      if (c.years?.length) setForm((f) => ({ ...f, year: c.years.includes(f.year) ? f.year : c.years[0] }));
    }).catch(() => setError('Base de données indisponible : ouvrez l\'application de bureau.'));
  }, []);

  const payload = () => ({ ...form, year: Number(form.year), scope_id: form.scope_id ? Number(form.scope_id) : null,
    template_id: form.template_id ? Number(form.template_id) : null });

  const runChecks = async () => {
    setBusy('checks'); setError('');
    const res = await apiFetch('/api/reports/checks', json(payload()));
    setBusy('');
    if (!res.ok) { setError((await res.json()).detail); return; }
    setChecks(await res.json());
  };

  const generate = async () => {
    setBusy('generate'); setError('');
    const res = await apiFetch('/api/reports/generate', json(payload()));
    setBusy('');
    const data = await res.json();
    if (res.status === 409) { setChecks({ checks: data.detail.checks, blocking: true }); setError(data.detail.message); return; }
    if (!res.ok) { setError(typeof data.detail === 'string' ? data.detail : 'Génération impossible.'); return; }
    onOpenDocument?.(data.document.id);
  };

  const needsId = form.scope_type !== 'association';
  const scopeOptions = form.scope_type === 'funder' ? ctx.funders.map((f) => ({ id: f.id, label: f.name }))
    : ctx.projects.filter((p) => form.scope_type !== 'programme' || p.has_children).map((p) => ({ id: p.id, label: `${p.code} — ${p.name}` }));
  const icon = { blocking: <XCircle className="w-4 h-4 text-red-600" />, warning: <AlertTriangle className="w-4 h-4 text-amber-600" /> };

  return (
    <div className="space-y-4 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><FileBarChart2 className="w-6 h-6" />Rapports annuels</h1>
        <p className="text-sm text-slate-500">
          Rapport moral (activités, indicateurs, bénéficiaires, partenaires, faits marquants) et rapport financier (compte d'emploi des ressources,
          recettes et dépenses, exécution budgétaire, trésorerie, reports, comparaison N-1), générés à partir de toutes les données de l'exercice,
          puis ouverts dans l'éditeur pour relecture.
        </p>
      </div>
      {error && <div role="alert" className="bg-red-50 text-red-800 rounded px-3 py-2 text-sm">{error}</div>}

      <section className="bg-white border rounded-xl p-4 grid md:grid-cols-3 gap-3 text-sm">
        <label className="flex flex-col gap-1">Exercice
          <select aria-label="Exercice" className="border rounded px-2 py-1.5" value={form.year} onChange={(e) => { setForm({ ...form, year: e.target.value }); setChecks(null); }}>
            {(ctx.years.length ? ctx.years : [form.year]).map((y) => <option key={y} value={y}>{y}</option>)}
          </select></label>
        <label className="flex flex-col gap-1">Périmètre
          <select aria-label="Périmètre" className="border rounded px-2 py-1.5" value={form.scope_type} onChange={(e) => { setForm({ ...form, scope_type: e.target.value, scope_id: '' }); setChecks(null); }}>
            <option value="association">Association entière</option><option value="programme">Programme (avec ses sous-projets)</option>
            <option value="project">Projet</option><option value="funder">Bailleur</option>
          </select></label>
        {needsId && (
          <label className="flex flex-col gap-1">{form.scope_type === 'funder' ? 'Bailleur' : 'Projet'}
            <select aria-label="Élément du périmètre" className="border rounded px-2 py-1.5" value={form.scope_id} onChange={(e) => { setForm({ ...form, scope_id: e.target.value }); setChecks(null); }}>
              <option value="">Choisir…</option>{scopeOptions.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select></label>
        )}
        <label className="flex flex-col gap-1">Rapport
          <select aria-label="Type de rapport" className="border rounded px-2 py-1.5" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
            <option value="both">Rapport annuel complet (moral + financier)</option><option value="moral">Rapport moral</option><option value="financial">Rapport financier</option>
          </select></label>
        <label className="flex flex-col gap-1">Langue
          <select aria-label="Langue du rapport" className="border rounded px-2 py-1.5" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
            <option value="fr">Français</option><option value="ar">العربية</option><option value="en">English</option>
          </select></label>
        <label className="flex flex-col gap-1">Mise en page
          <select aria-label="Modèle de mise en page" className="border rounded px-2 py-1.5" value={form.template_id} onChange={(e) => setForm({ ...form, template_id: e.target.value })}>
            <option value="">Charte du périmètre</option>{ctx.templates.map((t) => <option key={t.id} value={t.id}>Modèle : {t.name}</option>)}
          </select></label>
        <label className="flex items-center gap-2 md:col-span-3 text-xs">
          <input type="checkbox" checked={form.use_ai} onChange={(e) => setForm({ ...form, use_ai: e.target.checked })} />
          Ajouter une synthèse rédigée par l'IA (à partir des seules données ; les chiffres non retrouvés dans les données sont signalés).
          Une synthèse établie automatiquement à partir des données est toujours incluse.
        </label>
        <div className="md:col-span-3 flex gap-2">
          <button className="bg-slate-100 rounded px-4 py-2 flex items-center gap-2" disabled={!!busy || (needsId && !form.scope_id)} onClick={runChecks}>
            {busy === 'checks' ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />} Contrôler la cohérence
          </button>
          <button className="bg-afmi-forest text-white rounded px-4 py-2 flex items-center gap-2 disabled:opacity-50" disabled={!!busy || (needsId && !form.scope_id) || checks?.blocking} onClick={generate}>
            {busy === 'generate' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileBarChart2 className="w-4 h-4" />} Générer et ouvrir dans l'éditeur
          </button>
        </div>
      </section>

      {checks && (
        <section className="bg-white border rounded-xl p-4 text-sm space-y-2" aria-label="Contrôles de cohérence">
          <h2 className="font-semibold">Contrôles de cohérence {checks.period ? `(${checks.period.start} → ${checks.period.end})` : ''}</h2>
          {checks.checks.length === 0 && <p className="text-emerald-700 flex items-center gap-2"><CheckCircle2 className="w-4 h-4" />Aucune anomalie : le rapport peut être généré.</p>}
          {checks.blocking && <p className="text-red-700 font-semibold">Un contrôle bloquant doit être levé avant la génération (Trésorerie, relevés, indicateurs).</p>}
          {checks.checks.map((c) => (
            <details key={c.code} className={`border rounded p-2 ${c.level === 'blocking' ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`}>
              <summary className="flex items-center gap-2 cursor-pointer">{icon[c.level]}<span>{c.message}</span><span className="ms-auto text-xs">{c.count} · {c.level === 'blocking' ? 'bloquant' : 'avertissement'}</span></summary>
              <ul className="list-disc ps-6 text-xs mt-1">{c.items.map((i, k) => <li key={k}>{i}</li>)}</ul>
            </details>
          ))}
          <p className="text-xs text-slate-500">Le niveau de chaque contrôle (bloquant, avertissement, ignoré) se règle dans financial_report_layout.json (paramètres avancés au Lot 7).</p>
        </section>
      )}
    </div>
  );
}
