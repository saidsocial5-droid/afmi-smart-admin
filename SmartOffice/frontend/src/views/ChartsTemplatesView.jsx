import React, { useEffect, useState } from 'react';
import { Palette, Plus, Save, Trash2, Copy, Upload } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Chartes graphiques (héritage association → bailleur → projet) et bibliothèque de modèles de documents.

const POSITIONS = { 'header-left': 'En-tête gauche', 'header-center': 'En-tête centre', 'header-right': 'En-tête droite',
  'footer-left': 'Pied gauche', 'footer-center': 'Pied centre', 'footer-right': 'Pied droite', cover: 'Page de garde' };
const FONTS = ['', 'Calibri', 'Arial', 'Times New Roman', 'Cambria', 'Georgia', 'Verdana', 'Tahoma', 'Noto Naskh Arabic', 'Amiri'];
const readError = async (res) => { try { return (await res.json()).detail; } catch { return `Erreur ${res.status}`; } };

function ColorField({ label, value, onChange, inherited }) {
  return (
    <label className="flex items-center gap-2 text-xs">
      <input type="color" value={value || inherited || '#000000'} onChange={(e) => onChange(e.target.value)} />
      <span>{label}</span>
      {value ? <button className="text-slate-400" title="Revenir à la valeur héritée" onClick={() => onChange(null)}>↺</button> : <span className="text-slate-400">(hérité)</span>}
    </label>
  );
}

export default function ChartsTemplatesView() {
  const [charts, setCharts] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [ctx, setCtx] = useState({ projects: [], funders: [] });
  const [edit, setEdit] = useState(null);
  const [preview, setPreview] = useState({ project_id: '', result: null });
  const [msg, setMsg] = useState(null);
  const [inherited, setInherited] = useState({});   // valeurs héritées affichées (charte de l'association + défauts)

  const load = async () => {
    const [c, t, x] = await Promise.all([apiFetch('/api/charts'), apiFetch('/api/templates'), apiFetch('/api/editor/context')]);
    if (c.ok) setCharts(await c.json()); else setMsg({ kind: 'error', text: await readError(c) });
    if (t.ok) setTemplates(await t.json());
    if (x.ok) setCtx(await x.json());
    const e = await apiFetch('/api/charts/effective');
    if (e.ok) setInherited((await e.json()).style);
  };
  useEffect(() => { load(); }, []);

  const style = edit?.style || {};
  const set = (path, value) => {
    const keys = path.split('.');
    const next = JSON.parse(JSON.stringify(style));
    let cur = next;
    keys.slice(0, -1).forEach((k) => { cur[k] = cur[k] || {}; cur = cur[k]; });
    if (value === null || value === '') delete cur[keys[keys.length - 1]]; else cur[keys[keys.length - 1]] = value;
    setEdit({ ...edit, style: next });
  };

  const save = async () => {
    const res = await apiFetch('/api/charts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(edit) });
    if (!res.ok) { setMsg({ kind: 'error', text: await readError(res) }); return; }
    setEdit(await res.json());
    setMsg({ kind: 'ok', text: 'Charte enregistrée.' });
    load();
  };

  const uploadLogo = async (file, position) => {
    const form = new FormData();
    form.append('file', file);
    const res = await apiFetch('/api/files/images', { method: 'POST', body: form });
    if (!res.ok) { setMsg({ kind: 'error', text: await readError(res) }); return; }
    const { file_id } = await res.json();
    const logos = (style.logos || []).filter((l) => l.position !== position);
    setEdit({ ...edit, style: { ...style, logos: [...logos, { file_id, position, height_mm: 14 }] } });
  };

  const showEffective = async (projectId) => {
    setPreview({ project_id: projectId, result: null });
    if (!projectId) return;
    const res = await apiFetch(`/api/charts/effective?project_id=${projectId}`);
    if (res.ok) setPreview({ project_id: projectId, result: await res.json() });
  };

  const templateAction = async (t, action) => {
    if (action === 'delete' && !window.confirm(`Supprimer le modèle « ${t.name} » ?`)) return;
    const res = action === 'duplicate'
      ? await apiFetch(`/api/templates/${t.id}/duplicate`, { method: 'POST' })
      : action === 'share'
        ? await apiFetch('/api/templates', { method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...(await (await apiFetch(`/api/templates/${t.id}`)).json()), is_shared: !t.is_shared }) })
        : await apiFetch(`/api/templates/${t.id}`, { method: 'DELETE' });
    if (!res.ok) setMsg({ kind: 'error', text: await readError(res) });
    load();
  };

  const scopeLabel = (c) => (c.scope === 'Association' ? 'Association (par défaut)'
    : c.scope === 'Funder' ? `Bailleur : ${ctx.funders.find((f) => f.id === c.funder_id)?.name || c.funder_id}`
      : `Projet : ${ctx.projects.find((p) => p.id === c.project_id)?.code || c.project_id}`);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><Palette className="w-6 h-6" />Chartes graphiques et modèles</h1>
        <p className="text-sm text-slate-500">La charte de l'association s'applique à tous les documents ; celle d'un bailleur la complète, celle d'un projet complète les deux. Une valeur laissée vide est héritée.</p>
      </div>
      {msg && <div role="status" className={`rounded px-3 py-2 text-sm ${msg.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{msg.text}</div>}

      <div className="grid grid-cols-12 gap-4">
        <section className="col-span-12 lg:col-span-4 bg-white border rounded-xl p-3 space-y-2">
          <div className="flex items-center"><h2 className="font-semibold flex-1">Chartes</h2>
            <button className="text-sm bg-afmi-forest text-white rounded px-2 py-1 flex items-center gap-1" onClick={() => setEdit({ name: 'Nouvelle charte', scope: 'Funder', style: {} })}><Plus size={14} />Charte</button>
          </div>
          {charts.map((c) => (
            <button key={c.id} onClick={() => setEdit(c)} className={`w-full text-start border rounded p-2 ${edit?.id === c.id ? 'border-afmi-forest bg-afmi-lightmint' : ''}`}>
              <div className="font-medium">{c.name}</div><div className="text-xs text-slate-500">{scopeLabel(c)}</div>
            </button>
          ))}
          <div className="border-t pt-2">
            <h3 className="text-sm font-semibold mb-1">Charte effective d'un projet</h3>
            <select aria-label="Projet pour la charte effective" className="border rounded px-2 py-1 text-sm w-full" value={preview.project_id} onChange={(e) => showEffective(e.target.value)}>
              <option value="">Choisir un projet…</option>
              {ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
            </select>
            {preview.result && (
              <div className="text-xs mt-2 space-y-1">
                <div>{preview.result.chain.join(' → ')}</div>
                <div className="flex gap-1">{Object.entries(preview.result.style.colors).map(([k, v]) => <span key={k} title={`${k} ${v}`} className="w-5 h-5 rounded border" style={{ background: v }} />)}</div>
                {preview.result.style.mentions.map((m, i) => <div key={i} className="italic">« {m} »</div>)}
              </div>
            )}
          </div>
        </section>

        <section className="col-span-12 lg:col-span-8 bg-white border rounded-xl p-4">
          {!edit && <p className="text-sm text-slate-500">Choisissez ou créez une charte.</p>}
          {edit && (
            <div className="space-y-3 text-sm">
              <div className="flex flex-wrap gap-3 items-end">
                <label className="flex flex-col text-xs">Nom<input className="border rounded px-2 py-1 text-sm" value={edit.name} onChange={(e) => setEdit({ ...edit, name: e.target.value })} /></label>
                <label className="flex flex-col text-xs">Portée
                  <select className="border rounded px-2 py-1 text-sm" disabled={edit.scope === 'Association' && !!edit.id} value={edit.scope} onChange={(e) => setEdit({ ...edit, scope: e.target.value })}>
                    <option value="Association">Association</option><option value="Funder">Bailleur</option><option value="Project">Projet</option>
                  </select>
                </label>
                {edit.scope === 'Funder' && (
                  <label className="flex flex-col text-xs">Bailleur
                    <select className="border rounded px-2 py-1 text-sm" value={edit.funder_id ?? ''} onChange={(e) => setEdit({ ...edit, funder_id: Number(e.target.value) || null })}>
                      <option value="">—</option>{ctx.funders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                  </label>
                )}
                {edit.scope === 'Project' && (
                  <label className="flex flex-col text-xs">Projet
                    <select className="border rounded px-2 py-1 text-sm" value={edit.project_id ?? ''} onChange={(e) => setEdit({ ...edit, project_id: Number(e.target.value) || null })}>
                      <option value="">—</option>{ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                    </select>
                  </label>
                )}
              </div>

              <fieldset className="border rounded p-2 grid md:grid-cols-2 gap-2"><legend className="text-xs px-1">Couleurs</legend>
                {[['primary', 'Principale (titres)'], ['secondary', 'Secondaire'], ['text', 'Texte']].map(([k, l]) =>
                  <ColorField key={k} label={l} value={style.colors?.[k]} inherited={inherited.colors?.[k]} onChange={(v) => set(`colors.${k}`, v)} />)}
                {[['header_bg', 'Fond des en-têtes de tableau'], ['header_color', 'Texte des en-têtes de tableau'], ['border_color', 'Bordures'], ['stripe', 'Lignes alternées']].map(([k, l]) =>
                  <ColorField key={k} label={l} value={style.table?.[k]} inherited={inherited.table?.[k]} onChange={(v) => set(`table.${k}`, v)} />)}
              </fieldset>

              <fieldset className="border rounded p-2 flex flex-wrap gap-3"><legend className="text-xs px-1">Polices et mise en page</legend>
                <label className="flex flex-col text-xs">Texte<select className="border rounded px-1 py-1" value={style.fonts?.body || ''} onChange={(e) => set('fonts.body', e.target.value)}>{FONTS.map((f) => <option key={f} value={f}>{f || '(héritée)'}</option>)}</select></label>
                <label className="flex flex-col text-xs">Titres<select className="border rounded px-1 py-1" value={style.fonts?.headings || ''} onChange={(e) => set('fonts.headings', e.target.value)}>{FONTS.map((f) => <option key={f} value={f}>{f || '(héritée)'}</option>)}</select></label>
                <label className="flex flex-col text-xs">Taille (pt)<input type="number" className="border rounded px-1 py-1 w-16" value={style.fonts?.size_pt || ''} onChange={(e) => set('fonts.size_pt', e.target.value ? Number(e.target.value) : null)} /></label>
                {['top', 'bottom', 'left', 'right'].map((k) => (
                  <label key={k} className="flex flex-col text-xs">Marge {({ top: 'haute', bottom: 'basse', left: 'gauche', right: 'droite' })[k]} (mm)
                    <input type="number" className="border rounded px-1 py-1 w-16" value={style.margins_mm?.[k] || ''} onChange={(e) => set(`margins_mm.${k}`, e.target.value ? Number(e.target.value) : null)} /></label>
                ))}
                <label className="flex flex-col text-xs">Photos par ligne<select className="border rounded px-1 py-1" value={style.photo_grid?.per_row || ''} onChange={(e) => set('photo_grid.per_row', e.target.value ? Number(e.target.value) : null)}><option value="">(hérité)</option>{[1, 2, 3, 4].map((n) => <option key={n}>{n}</option>)}</select></label>
              </fieldset>

              <fieldset className="border rounded p-2 space-y-2"><legend className="text-xs px-1">Logos</legend>
                <div className="grid md:grid-cols-3 gap-2">
                  {Object.entries(POSITIONS).map(([pos, label]) => {
                    const logo = (style.logos || []).find((l) => l.position === pos);
                    return (
                      <div key={pos} className="border rounded p-2 text-xs space-y-1">
                        <div className="font-medium">{label}</div>
                        {logo ? <img alt={label} className="h-8" src={`/api/files/${logo.file_id}/image`} /> : <div className="text-slate-400">aucun</div>}
                        <label className="inline-flex items-center gap-1 cursor-pointer text-afmi-forest"><Upload size={12} />Choisir
                          <input type="file" accept="image/*" hidden onChange={(e) => e.target.files?.[0] && uploadLogo(e.target.files[0], pos)} /></label>
                        {logo && (
                          <>
                            <label className="flex items-center gap-1">Hauteur (mm)<input type="number" className="border rounded w-12" value={logo.height_mm || 14}
                              onChange={(e) => setEdit({ ...edit, style: { ...style, logos: style.logos.map((l) => (l.position === pos ? { ...l, height_mm: Number(e.target.value) } : l)) } })} /></label>
                            <button className="text-red-600" onClick={() => setEdit({ ...edit, style: { ...style, logos: style.logos.filter((l) => l.position !== pos) } })}>Retirer</button>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              </fieldset>

              <fieldset className="border rounded p-2 grid md:grid-cols-2 gap-2"><legend className="text-xs px-1">En-tête, pied de page et mentions</legend>
                {[['header.text', 'En-tête (toutes les pages)'], ['header.first_page_text', 'En-tête de la première page'], ['header.even_text', 'En-tête des pages paires'], ['footer.text', 'Pied de page']].map(([p, l]) => (
                  <label key={p} className="flex flex-col text-xs">{l}<input className="border rounded px-2 py-1" value={p.split('.').reduce((v, k) => v?.[k], style) || ''} onChange={(e) => set(p, e.target.value)} /></label>
                ))}
                <label className="flex flex-col text-xs md:col-span-2">Mentions obligatoires (une par ligne, cumulées avec les chartes parentes)
                  <textarea className="border rounded px-2 py-1" rows={2} value={(style.mentions || []).join('\n')} onChange={(e) => set('mentions', e.target.value.split('\n').filter((x) => x.trim()))} /></label>
                <p className="text-[11px] text-slate-500 md:col-span-2">Champs utilisables dans les textes : {'{project_name}'}, {'{funder_name}'}, {'{date}'}, {'{association}'}, {'{title}'}.</p>
              </fieldset>

              <div className="flex gap-2">
                <button className="bg-afmi-forest text-white rounded px-3 py-1.5 flex items-center gap-1" onClick={save}><Save size={14} />Enregistrer</button>
                {edit.id && edit.scope !== 'Association' && (
                  <button className="text-red-700 px-3 py-1.5 flex items-center gap-1" onClick={async () => {
                    if (!window.confirm('Supprimer cette charte ?')) return;
                    await apiFetch(`/api/charts/${edit.id}`, { method: 'DELETE' }); setEdit(null); load();
                  }}><Trash2 size={14} />Supprimer</button>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      <section className="bg-white border rounded-xl p-3">
        <h2 className="font-semibold mb-2">Modèles de documents</h2>
        <p className="text-xs text-slate-500 mb-2">Créez un modèle depuis l'éditeur (bouton « Modèle ») ; il sert ensuite de point de départ aux nouveaux documents.</p>
        {templates.length === 0 && <p className="text-sm text-slate-500">Aucun modèle pour l'instant.</p>}
        <table className="w-full text-sm">
          <tbody>
            {templates.map((t) => (
              <tr key={t.id} className="border-t">
                <td className="py-1">{t.name}<div className="text-xs text-slate-500">{t.kind} · {t.created_by}</div></td>
                <td className="text-xs">{t.is_shared ? 'Partagé' : 'Personnel'}</td>
                <td className="text-end space-x-2">
                  <button className="text-xs" onClick={() => templateAction(t, 'share')}>{t.is_shared ? 'Rendre personnel' : 'Partager'}</button>
                  <button className="text-xs inline-flex items-center gap-1" onClick={() => templateAction(t, 'duplicate')}><Copy size={12} />Dupliquer</button>
                  <button className="text-xs text-red-700" onClick={() => templateAction(t, 'delete')}>Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
