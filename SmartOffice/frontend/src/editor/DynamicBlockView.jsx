import React, { useCallback, useEffect, useState } from 'react';
import { NodeViewWrapper } from '@tiptap/react';
import { RefreshCw, Settings2, ArrowUp, ArrowDown, X } from 'lucide-react';
import { apiFetch } from '../apiClient';
import { useDoc, fmtMad } from './context';
import BarChart from './BarChart';
import GenericTable from './GenericTable';

export const BLOCK_LABELS = {
  budget: 'Tableau budgétaire', indicators: 'Indicateurs', activities: 'Liste des activités',
  chart: 'Graphique', gallery: 'Galerie photos', annual: 'Tableau du rapport annuel',
};

/** Bloc alimenté par les données : relu depuis la base à l'ouverture et sur « Actualiser ». */
export default function DynamicBlockView({ node, updateAttributes, selected, editor }) {
  const doc = useDoc();
  const a = node.attrs;
  const projectId = a.projectId ?? doc.projectId;
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const editable = editor.isEditable;

  const load = useCallback(async () => {
    setError('');
    const q = new URLSearchParams();
    if (projectId) q.set('project_id', projectId);
    if (a.dateFrom) q.set('date_from', a.dateFrom);
    if (a.dateTo) q.set('date_to', a.dateTo);
    if (a.kind === 'chart') q.set('chart', a.chart || 'budget');
    if (a.kind === 'gallery') {
      q.set('limit', a.limit || 6);
      if (a.photoIds?.length) q.set('photo_ids', a.photoIds.join(','));
    }
    if (a.kind === 'annual') {
      q.delete('project_id');
      q.set('year', a.year);
      q.set('scope_type', a.scopeType || 'association');
      if (a.scopeId) q.set('scope_id', a.scopeId);
      q.set('lang', a.lang || 'fr');
    }
    try {
      const url = a.kind === 'annual' ? `/api/reports/table/${a.table}?${q}` : `/api/editor/blocks/${a.kind}?${q}`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error((await res.json()).detail || res.status);
      setData(await res.json());
    } catch (e) {
      setError(`Données indisponibles : ${e.message}`);
    }
  }, [a.kind, projectId, a.dateFrom, a.dateTo, a.chart, a.limit, JSON.stringify(a.photoIds), a.table, a.year, a.scopeType, a.scopeId, a.lang]);

  useEffect(() => { load(); }, [load]);

  const table = doc.style?.table || {};
  const thStyle = { background: table.header_bg, color: table.header_color };
  const perRow = a.perRow || doc.style?.photo_grid?.per_row || 2;

  const movePhoto = (id, delta) => {
    const ids = (a.photoIds?.length ? a.photoIds : (data?.photos || []).map((p) => p.id)).slice();
    const i = ids.indexOf(id);
    const j = i + delta;
    if (i < 0 || j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    updateAttributes({ photoIds: ids });
  };
  const removePhoto = (id) => {
    const ids = (a.photoIds?.length ? a.photoIds : (data?.photos || []).map((p) => p.id)).filter((x) => x !== id);
    updateAttributes({ photoIds: ids });
  };

  let body = null;
  if (error) body = <div className="block-empty">{error}</div>;
  else if (!data) body = <div className="block-empty">Chargement…</div>;
  else if (a.kind === 'annual') {
    body = <GenericTable data={data} style={doc.style} />;
  } else if (a.kind === 'budget') {
    body = (
      <table className="data-table">
        <thead><tr style={thStyle}><th>Ligne</th><th>Prévu</th><th>Réalisé (MAD)</th><th>Écart</th><th>Taux</th></tr></thead>
        <tbody>
          {data.rows.map((r, i) => (
            <tr key={i}><td>{r.code} {r.label}</td><td className="num">{fmtMad(r.planned)} {r.currency !== 'MAD' ? r.currency : ''}</td>
              <td className="num">{fmtMad(r.realized_mad)}</td><td className="num">{r.gap === null ? '—' : fmtMad(r.gap)}</td>
              <td className="num">{r.rate === null ? '—' : `${r.rate.toLocaleString('fr-FR')} %`}</td></tr>
          ))}
          <tr className="total"><td>Total</td><td className="num">{fmtMad(data.total.planned)}</td><td className="num">{fmtMad(data.total.realized_mad)}</td>
            <td className="num">{fmtMad(data.total.gap)}</td><td className="num">{data.total.rate === null ? '—' : `${data.total.rate.toLocaleString('fr-FR')} %`}</td></tr>
        </tbody>
      </table>
    );
  } else if (a.kind === 'indicators') {
    body = data.rows.length === 0 ? <div className="block-empty">Aucun indicateur pour ce projet.</div> : (
      <table className="data-table">
        <thead><tr style={thStyle}><th>Indicateur</th><th>Cible</th><th>Réalisé</th><th>Taux</th></tr></thead>
        <tbody>{data.rows.map((r, i) => (
          <tr key={i}><td>{r.name}</td><td className="num">{r.target?.toLocaleString('fr-FR')} {r.unit}</td>
            <td className="num">{r.current?.toLocaleString('fr-FR')} {r.unit}</td><td className="num">{r.rate === null ? '—' : `${r.rate.toLocaleString('fr-FR')} %`}</td></tr>
        ))}</tbody>
      </table>
    );
  } else if (a.kind === 'activities') {
    body = data.rows.length === 0 ? <div className="block-empty">Aucune activité sur la période.</div> : (
      <table className="data-table">
        <thead><tr style={thStyle}><th>Date</th><th>Activité</th><th>Lieu</th><th>Participants</th></tr></thead>
        <tbody>
          {data.rows.map((r, i) => <tr key={i}><td>{r.date}</td><td>{r.title}</td><td>{r.location}</td><td className="num">{r.participants}</td></tr>)}
          <tr className="total"><td colSpan={3}>Total des participants</td><td className="num">{data.total_participants}</td></tr>
        </tbody>
      </table>
    );
  } else if (a.kind === 'chart') {
    body = (<figure className="chart-figure"><figcaption className="chart-title">{a.title || data.title}</figcaption>
      <BarChart series={data.series} colors={doc.style?.colors} unit={data.unit} /></figure>);
  } else if (a.kind === 'gallery') {
    body = data.photos.length === 0
      ? <div className="block-empty">Aucune photo avec consentement pour ce projet et cette période.</div>
      : (
        <div className="photo-grid" style={{ gridTemplateColumns: `repeat(${perRow}, 1fr)` }}>
          {data.photos.map((p) => (
            <figure key={p.id} className="photo-figure">
              <img src={p.url} alt={p.caption || 'Photo d\'activité'} />
              <figcaption><span className="photo-num" />{p.caption || <em>Légende à saisir</em>}{p.credit ? <span className="photo-credit"> — © {p.credit}</span> : null}</figcaption>
              {selected && editable && (
                <div className="photo-tools no-print">
                  <button title="Avant" onClick={() => movePhoto(p.id, -1)}><ArrowUp size={12} /></button>
                  <button title="Après" onClick={() => movePhoto(p.id, 1)}><ArrowDown size={12} /></button>
                  <button title="Retirer" onClick={() => removePhoto(p.id)}><X size={12} /></button>
                </div>
              )}
            </figure>
          ))}
        </div>
      );
  }

  return (
    <NodeViewWrapper className={`dynamic-block-view ${selected ? 'is-selected' : ''}`} contentEditable={false} data-drag-handle>
      <div className="block-bar no-print">
        <span>{BLOCK_LABELS[a.kind] || a.kind} · données à jour{data?.source ? ` (${data.source})` : ''}</span>
        <button onClick={load} title="Actualiser depuis les données"><RefreshCw size={12} /></button>
        {editable && a.kind !== 'annual' && <button onClick={() => setShowSettings((v) => !v)} title="Paramètres du bloc"><Settings2 size={12} /></button>}
      </div>
      {showSettings && editable && (
        <div className="block-settings no-print">
          <label>Projet
            <select value={a.projectId ?? ''} onChange={(e) => updateAttributes({ projectId: e.target.value ? Number(e.target.value) : null, photoIds: null })}>
              <option value="">Projet du document</option>
              {doc.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
          </label>
          {(a.kind === 'activities' || a.kind === 'gallery') && (
            <>
              <label>Du <input type="date" value={a.dateFrom || ''} onChange={(e) => updateAttributes({ dateFrom: e.target.value || null, photoIds: null })} /></label>
              <label>Au <input type="date" value={a.dateTo || ''} onChange={(e) => updateAttributes({ dateTo: e.target.value || null, photoIds: null })} /></label>
            </>
          )}
          {a.kind === 'chart' && (
            <label>Données
              <select value={a.chart} onChange={(e) => updateAttributes({ chart: e.target.value })}>
                <option value="budget">Exécution budgétaire</option><option value="indicators">Indicateurs</option>
              </select>
            </label>
          )}
          {a.kind === 'gallery' && (
            <>
              <label>Photos par ligne
                <select value={perRow} onChange={(e) => updateAttributes({ perRow: Number(e.target.value) })}>
                  {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </label>
              <label>Nombre <input type="number" min="1" max="24" value={a.limit || 6} onChange={(e) => updateAttributes({ limit: Number(e.target.value), photoIds: null })} /></label>
              <button onClick={() => updateAttributes({ photoIds: null })}>Nouvelle sélection automatique</button>
            </>
          )}
        </div>
      )}
      {body}
    </NodeViewWrapper>
  );
}
