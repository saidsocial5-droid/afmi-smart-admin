import React, { useEffect, useState } from 'react';
import { Images, Upload, Sparkles, Check, Trash2 } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Galerie des photos d'activités : import par lot, métadonnées, légende (proposition IA à valider), crédit, consentement.

const readError = async (res) => { try { return (await res.json()).detail; } catch { return `Erreur ${res.status}`; } };

function PhotoCard({ photo, tasks, onChange, onDelete }) {
  const [caption, setCaption] = useState(photo.caption);
  const [credit, setCredit] = useState(photo.credit);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  useEffect(() => { setCaption(photo.caption); setCredit(photo.credit); }, [photo]);
  const put = (data) => apiFetch(`/api/photos/${photo.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    .then((r) => r.json()).then(onChange);
  const suggest = async () => {
    setBusy(true); setNote('');
    const res = await apiFetch(`/api/photos/${photo.id}/suggest-caption`, { method: 'POST' });
    const data = await res.json();
    setBusy(false);
    if (data.photo) onChange(data.photo);
    if (data.message) setNote(data.message);
  };
  return (
    <figure className="bg-white border rounded-lg overflow-hidden text-xs">
      <img src={photo.url} alt={photo.caption || 'Photo d\'activité'} className="w-full h-40 object-cover" loading="lazy" />
      <div className="p-2 space-y-1">
        <div className="text-slate-500">{photo.taken_at ? `Prise le ${photo.taken_at.slice(0, 16)}` : 'Date inconnue'}
          {photo.latitude != null && ` · ${photo.latitude.toFixed(4)}, ${photo.longitude.toFixed(4)}`}</div>
        <textarea aria-label="Légende" dir="auto" rows={2} className={`w-full border rounded px-1 ${photo.caption_validated ? '' : 'border-amber-400'}`}
                  placeholder="Légende" value={caption} onChange={(e) => setCaption(e.target.value)} onBlur={() => caption !== photo.caption && put({ caption })} />
        {photo.suggested_caption && !photo.caption_validated && (
          <div className="bg-amber-50 rounded p-1">Proposition : « {photo.suggested_caption} »
            <button className="ms-1 text-afmi-forest inline-flex items-center" onClick={() => put({ caption: photo.suggested_caption, caption_validated: true })}><Check size={12} />Valider</button></div>
        )}
        <input aria-label="Crédit photo" className="w-full border rounded px-1" placeholder="Crédit photo" value={credit} onChange={(e) => setCredit(e.target.value)} onBlur={() => credit !== photo.credit && put({ credit })} />
        <select aria-label="Activité liée" className="w-full border rounded px-1" value={photo.task_id ?? ''} onChange={(e) => put({ task_id: e.target.value ? Number(e.target.value) : null })}>
          <option value="">Activité liée…</option>{tasks.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <label className={`flex items-center gap-1 ${photo.consent ? 'text-emerald-700' : 'text-red-700'}`}>
          <input type="checkbox" checked={photo.consent} onChange={(e) => put({ consent: e.target.checked })} />
          Consentement au droit à l'image recueilli
        </label>
        <div className="flex gap-2">
          <button className="inline-flex items-center gap-1 text-afmi-forest" disabled={busy} onClick={suggest}><Sparkles size={12} />{busy ? 'Analyse…' : 'Proposer une légende'}</button>
          <button className="ms-auto text-red-700" title="Supprimer" onClick={onDelete}><Trash2 size={12} /></button>
        </div>
        {note && <div className="text-amber-800">{note}</div>}
      </div>
    </figure>
  );
}

export default function PhotosView() {
  const [ctx, setCtx] = useState({ projects: [], tasks: [] });
  const [filter, setFilter] = useState({ project_id: '', date_from: '', date_to: '' });
  const [photos, setPhotos] = useState([]);
  const [upload, setUpload] = useState({ files: [], credit: 'AFMI', consent: false });
  const [msg, setMsg] = useState(null);

  useEffect(() => { apiFetch('/api/editor/context').then((r) => r.json()).then(setCtx).catch(() => {}); }, []);
  const load = async () => {
    const q = new URLSearchParams(Object.entries(filter).filter(([, v]) => v));
    const res = await apiFetch(`/api/photos?${q}`);
    if (res.ok) setPhotos(await res.json()); else setMsg({ kind: 'error', text: await readError(res) });
  };
  useEffect(() => { load(); }, [filter]);

  const doUpload = async () => {
    if (!upload.files.length) return;
    const form = new FormData();
    if (filter.project_id) form.append('project_id', filter.project_id);
    form.append('credit', upload.credit);
    form.append('consent', upload.consent ? 'true' : 'false');
    upload.files.forEach((f) => form.append('files', f));
    const res = await apiFetch('/api/photos/upload', { method: 'POST', body: form });
    const data = res.ok ? await res.json() : { results: [{ error: await readError(res) }] };
    const errors = data.results.filter((r) => r.error);
    setMsg(errors.length ? { kind: 'error', text: errors.map((e) => `${e.file || ''} : ${e.error}`).join(' · ') }
      : { kind: 'ok', text: `${data.results.length} photo(s) importée(s). Complétez les légendes.` });
    load();
  };

  const tasks = ctx.tasks.filter((t) => !filter.project_id || t.project_id === Number(filter.project_id));
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><Images className="w-6 h-6" />Photos des activités</h1>
        <p className="text-sm text-slate-500">Les photos avec consentement et légende validée sont proposées automatiquement dans les galeries des rapports. La date et le lieu sont lus dans les métadonnées (EXIF) quand ils existent.</p>
      </div>
      {msg && <div role="status" className={`rounded px-3 py-2 text-sm ${msg.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{msg.text}</div>}
      <section className="bg-white border rounded-xl p-3 flex flex-wrap items-end gap-3 text-sm">
        <label className="flex flex-col text-xs">Projet
          <select className="border rounded px-2 py-1 text-sm" value={filter.project_id} onChange={(e) => setFilter({ ...filter, project_id: e.target.value })}>
            <option value="">Tous</option>{ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select></label>
        <label className="flex flex-col text-xs">Du<input type="date" className="border rounded px-2 py-1" value={filter.date_from} onChange={(e) => setFilter({ ...filter, date_from: e.target.value })} /></label>
        <label className="flex flex-col text-xs">Au<input type="date" className="border rounded px-2 py-1" value={filter.date_to} onChange={(e) => setFilter({ ...filter, date_to: e.target.value })} /></label>
        <span className="border-s ps-3 flex flex-wrap items-end gap-2">
          <input type="file" multiple accept="image/*" className="text-xs" onChange={(e) => setUpload({ ...upload, files: Array.from(e.target.files || []) })} />
          <label className="flex flex-col text-xs">Crédit<input className="border rounded px-2 py-1 w-28" value={upload.credit} onChange={(e) => setUpload({ ...upload, credit: e.target.value })} /></label>
          <label className="flex items-center gap-1 text-xs"><input type="checkbox" checked={upload.consent} onChange={(e) => setUpload({ ...upload, consent: e.target.checked })} />Consentements recueillis</label>
          <button className="bg-afmi-forest text-white rounded px-3 py-1.5 flex items-center gap-1" onClick={doUpload}><Upload size={14} />Importer{filter.project_id ? ' dans le projet' : ''}</button>
        </span>
      </section>
      <button className="text-xs text-afmi-forest underline" onClick={async () => {
        const res = await apiFetch('/api/photos/import-legacy', { method: 'POST' });
        const r = await res.json();
        setMsg(res.ok ? { kind: 'ok', text: `${r.imported} photo(s) reprise(s) des anciens rapports d'activité${r.missing_count ? `, ${r.missing_count} fichier(s) introuvable(s)` : ''}. Confirmez le consentement de chacune avant usage.` }
          : { kind: 'error', text: r.detail });
        load();
      }}>Reprendre les photos des anciens rapports d'activité (application de bureau)</button>
      {photos.length === 0 && <p className="text-sm text-slate-500">Aucune photo.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {photos.map((p) => (
          <PhotoCard key={p.id} photo={p} tasks={tasks}
                     onChange={(np) => setPhotos((list) => list.map((x) => (x.id === np.id ? np : x)))}
                     onDelete={async () => { if (window.confirm('Supprimer cette photo ?')) { await apiFetch(`/api/photos/${p.id}`, { method: 'DELETE' }); load(); } }} />
        ))}
      </div>
    </div>
  );
}
