import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import TextStyle from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import FontFamily from '@tiptap/extension-font-family';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import Subscript from '@tiptap/extension-subscript';
import Superscript from '@tiptap/extension-superscript';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import { FilePlus2, Save, History, MessageSquare, Sparkles, Printer, LayoutTemplate, Palette, Trash2, BookmarkPlus } from 'lucide-react';
import { apiFetch } from '../apiClient';
import {
  FontSize, TextDirection, ShadedTableCell, ShadedTableHeader, PageBreak, Columns, Footnote, TableOfContents, Field,
  DynamicBlock, Comment, Insertion, Deletion, TrackChanges, markRanges,
} from './extensions';
import Toolbar from './Toolbar';
import { DocContext } from './context';
import { buildPrintHtml, chartCss, deepMerge } from './print';

const readError = async (res) => { try { return (await res.json()).detail || `Erreur ${res.status}`; } catch { return `Erreur ${res.status}`; } };
const json = (body) => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

/** Modèle de base d'un rapport d'activité : titres, champs et blocs de données. */
export function baseReport(title) {
  const h = (level, text) => ({ type: 'heading', attrs: { level }, content: [{ type: 'text', text }] });
  const p = (text) => ({ type: 'paragraph', content: text ? [{ type: 'text', text }] : [] });
  return {
    type: 'doc',
    content: [
      { type: 'heading', attrs: { level: 1 }, content: [{ type: 'text', text: title || 'Rapport d\'activité' }] },
      { type: 'paragraph', content: [{ type: 'text', text: 'Projet : ' }, { type: 'field', attrs: { name: 'project_name' } },
        { type: 'text', text: ' — Bailleur : ' }, { type: 'field', attrs: { name: 'funder_name' } },
        { type: 'text', text: ' — ' }, { type: 'field', attrs: { name: 'date' } }] },
      { type: 'tableOfContents' },
      h(2, 'Résumé'), p('[Synthèse de la période : rédigez-la ou utilisez l\'assistant.]'),
      h(2, 'Activités réalisées'), { type: 'dynamicBlock', attrs: { kind: 'activities' } },
      h(2, 'Indicateurs de résultats'), { type: 'dynamicBlock', attrs: { kind: 'indicators' } },
      h(2, 'Exécution budgétaire'), { type: 'dynamicBlock', attrs: { kind: 'budget' } }, { type: 'dynamicBlock', attrs: { kind: 'chart', chart: 'budget' } },
      h(2, 'Photos des activités'), { type: 'dynamicBlock', attrs: { kind: 'gallery', limit: 4 } },
      h(2, 'Difficultés et perspectives'), p(''),
    ],
  };
}

const LAYOUT_FIELDS = [
  ['margins_mm.top', 'Marge haute (mm)', 'number'], ['margins_mm.bottom', 'Marge basse (mm)', 'number'],
  ['margins_mm.left', 'Marge gauche (mm)', 'number'], ['margins_mm.right', 'Marge droite (mm)', 'number'],
  ['header.text', 'En-tête (toutes les pages) — {project_name}, {funder_name}, {date}…', 'text'],
  ['header.first_page_text', 'En-tête de la première page', 'text'], ['header.even_text', 'En-tête des pages paires', 'text'],
  ['footer.text', 'Pied de page', 'text'], ['footer.page_numbers', 'Numéros de page', 'checkbox'],
  ['footer.first_page_different', 'Première page sans numéro', 'checkbox'], ['footer.odd_even_different', 'Numéros alternés pages paires/impaires', 'checkbox'],
  ['heading_numbering', 'Numéroter les titres (1, 1.1, 1.1.1)', 'checkbox'],
];
const getPath = (o, path) => path.split('.').reduce((v, k) => (v == null ? v : v[k]), o);
const setPath = (o, path, value) => {
  const keys = path.split('.');
  const out = { ...(o || {}) };
  let cur = out;
  keys.slice(0, -1).forEach((k) => { cur[k] = { ...(cur[k] || {}) }; cur = cur[k]; });
  cur[keys[keys.length - 1]] = value;
  return out;
};

export default function DocumentEditor({ initialDocumentId = null }) {
  const [ctx, setCtx] = useState({ projects: [], funders: [], tasks: [], user: '' });
  const [docs, setDocs] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [doc, setDoc] = useState(null);
  const [chart, setChart] = useState({ style: {}, chain: [] });
  const [fields, setFields] = useState({});
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState(null);
  const [panel, setPanel] = useState('layout');
  const [comments, setComments] = useState([]);
  const [versions, setVersions] = useState([]);
  const [track, setTrack] = useState(false);
  const [assistant, setAssistant] = useState({ action: 'reformulate', instruction: '', result: null, busy: false });
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({ title: '', project_id: '', template_id: 'base', language: 'fr' });
  const previewFrame = useRef(null);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Underline, TextStyle, Color, FontFamily, FontSize, TextDirection, Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }), Subscript, Superscript,
      Image.configure({ inline: false }), Placeholder.configure({ placeholder: 'Commencez à écrire…' }),
      Table.configure({ resizable: true }), TableRow, ShadedTableHeader, ShadedTableCell,
      PageBreak, Columns, Footnote, TableOfContents, Field, DynamicBlock, Comment, Insertion, Deletion,
      TrackChanges.configure({ author: 'Utilisateur' }),
    ],
    content: '',
    editable: true,
    onUpdate: () => setDirty(true),
  });

  const loadLists = useCallback(async () => {
    const [d, t, c] = await Promise.all([apiFetch('/api/documents'), apiFetch('/api/templates'), apiFetch('/api/editor/context')]);
    if (d.ok) setDocs(await d.json());
    if (t.ok) setTemplates(await t.json());
    if (c.ok) setCtx(await c.json());
    else setStatus({ kind: 'error', text: await readError(c) });
  }, []);
  useEffect(() => { loadLists(); }, [loadLists]);

  useEffect(() => {
    if (editor && ctx.user) editor.extensionManager.extensions.find((e) => e.name === 'trackChanges').options.author = ctx.user;
  }, [editor, ctx.user]);

  const refreshChartAndFields = useCallback(async (d) => {
    const q = new URLSearchParams();
    if (d.project_id) q.set('project_id', d.project_id);
    if (d.funder_id) q.set('funder_id', d.funder_id);
    const [c, f] = await Promise.all([apiFetch(`/api/charts/effective?${q}`), apiFetch(`/api/editor/fields?${q}`)]);
    if (c.ok) setChart(await c.json());
    if (f.ok) setFields({ ...(await f.json()), title: d.title });
  }, []);

  const openDocument = useCallback(async (id) => {
    const res = await apiFetch(`/api/documents/${id}`);
    if (!res.ok) { setStatus({ kind: 'error', text: await readError(res) }); return; }
    const d = await res.json();
    setDoc(d);
    editor?.commands.setContent(d.content, false);
    setDirty(false);
    setStatus(null);
    await refreshChartAndFields(d);
    const [cm, vs] = await Promise.all([apiFetch(`/api/documents/${id}/comments`), apiFetch(`/api/documents/${id}/versions`)]);
    if (cm.ok) setComments(await cm.json());
    if (vs.ok) setVersions(await vs.json());
  }, [editor, refreshChartAndFields]);

  // Document à ouvrir dès l'arrivée (rapport annuel tout juste généré)
  useEffect(() => { if (initialDocumentId && editor) { openDocument(initialDocumentId); loadLists(); } }, [initialDocumentId, editor]);

  const createDocument = async () => {
    const body = { title: form.title || 'Rapport d\'activité', project_id: form.project_id ? Number(form.project_id) : null, language: form.language };
    if (form.template_id === 'base') body.content = baseReport(body.title);
    else if (form.template_id) body.template_id = Number(form.template_id);
    const project = ctx.projects.find((p) => p.id === body.project_id);
    if (project?.funder_id) body.funder_id = project.funder_id;
    const res = await apiFetch('/api/documents', json(body));
    if (!res.ok) { setStatus({ kind: 'error', text: await readError(res) }); return; }
    const d = await res.json();
    await loadLists();
    await openDocument(d.id);
  };

  const save = useCallback(async (versionNote) => {
    if (!doc || !editor) return;
    const body = { title: doc.title, project_id: doc.project_id, funder_id: doc.funder_id, language: doc.language,
      content: editor.getJSON(), layout: doc.layout };
    if (versionNote !== undefined) body.version_note = versionNote;
    const res = await apiFetch(`/api/documents/${doc.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!res.ok) { setStatus({ kind: 'error', text: await readError(res) }); return; }
    const d = await res.json();
    setDoc((cur) => ({ ...cur, version: d.version, updated_at: d.updated_at }));
    setDirty(false);
    setStatus({ kind: 'ok', text: versionNote !== undefined ? `Version ${d.version} enregistrée.` : 'Document enregistré.' });
    if (versionNote !== undefined) setVersions(await (await apiFetch(`/api/documents/${doc.id}/versions`)).json());
    loadLists();
  }, [doc, editor, loadLists]);

  // Enregistrement automatique 8 s après la dernière modification ; Ctrl+S pour enregistrer tout de suite.
  useEffect(() => {
    if (!dirty || !doc) return undefined;
    const t = setTimeout(() => save(), 8000);
    return () => clearTimeout(t);
  }, [dirty, doc, save]);
  useEffect(() => {
    const onKey = (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); save(); } };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [save]);

  const updateDoc = (patch) => {
    setDoc((d) => {
      const next = { ...d, ...patch };
      if ('project_id' in patch || 'funder_id' in patch) refreshChartAndFields(next);
      return next;
    });
    setDirty(true);
  };

  const addComment = async () => {
    if (!editor || !doc) return;
    const { from, to } = editor.state.selection;
    if (from === to) { setStatus({ kind: 'error', text: 'Sélectionnez le passage à commenter.' }); return; }
    const text = window.prompt('Commentaire :');
    if (!text) return;
    const anchor = Math.random().toString(36).slice(2, 12);
    const quoted = editor.state.doc.textBetween(from, to, ' ').slice(0, 300);
    const res = await apiFetch(`/api/documents/${doc.id}/comments`, json({ text, anchor_id: anchor, quoted }));
    if (!res.ok) { setStatus({ kind: 'error', text: await readError(res) }); return; }
    editor.chain().focus().setMark('comment', { id: anchor }).run();
    setComments(await (await apiFetch(`/api/documents/${doc.id}/comments`)).json());
    setPanel('comments');
    save();
  };

  const goToComment = (anchor) => {
    if (!editor) return;
    let range = null;
    editor.state.doc.descendants((node, pos) => {
      if (range || !node.isText) return;
      if (node.marks.some((m) => m.type.name === 'comment' && m.attrs.id === anchor)) range = { from: pos, to: pos + node.nodeSize };
    });
    if (range) editor.chain().focus().setTextSelection(range).scrollIntoView().run();
  };

  const resolveComment = async (c) => {
    await apiFetch(`/api/documents/${doc.id}/comments/${c.id}/resolve`, json({ resolved: !c.resolved }));
    // Le passage n'est plus surligné une fois le commentaire résolu.
    const { tr } = editor.state;
    editor.state.doc.descendants((node, pos) => {
      const m = node.isText && node.marks.find((mk) => mk.type.name === 'comment' && mk.attrs.id === c.anchor_id);
      if (m) tr.addMark(pos, pos + node.nodeSize, editor.schema.marks.comment.create({ id: c.anchor_id, resolved: !c.resolved }));
    });
    editor.view.dispatch(tr);
    setComments(await (await apiFetch(`/api/documents/${doc.id}/comments`)).json());
  };

  const restore = async (v) => {
    if (!window.confirm(`Restaurer la version ${v.number} ? L'état actuel est conservé comme nouvelle version.`)) return;
    if (dirty) await save();
    const res = await apiFetch(`/api/documents/${doc.id}/versions/${v.id}/restore`, { method: 'POST' });
    if (!res.ok) { setStatus({ kind: 'error', text: await readError(res) }); return; }
    await openDocument(doc.id);
    setStatus({ kind: 'ok', text: `Version ${v.number} restaurée.` });
  };

  const runAssistant = async () => {
    if (!editor) return;
    const { from, to } = editor.state.selection;
    const text = editor.state.doc.textBetween(from, to, '\n');
    setAssistant((a) => ({ ...a, busy: true, result: null }));
    const res = await apiFetch('/api/editor/assistant', json({
      action: assistant.action, text, instruction: assistant.instruction, language: assistant.language || doc?.language || 'fr',
      project_id: doc?.project_id,
    }));
    const data = res.ok ? await res.json() : { error: await readError(res) };
    setAssistant((a) => ({ ...a, busy: false, result: data, range: { from, to } }));
  };

  const insertAssistant = (replace) => {
    const r = assistant.result;
    if (!r?.text) return;
    const paragraphs = r.text.split(/\n{2,}/).map((t) => ({ type: 'paragraph', content: [{ type: 'text', text: t.trim() }] })).filter((p) => p.content[0].text);
    const chain = editor.chain().focus();
    if (replace && assistant.range && assistant.range.from !== assistant.range.to) chain.deleteRange(assistant.range);
    chain.insertContent(paragraphs).run();
  };

  const openPreview = () => {
    if (!editor) return;
    const html = buildPrintHtml({ editorDom: editor.view.dom, title: doc?.title, style: chart.style, layout: doc?.layout,
      fields, language: doc?.language, origin: window.location.origin });
    setPreview(html);
  };

  const saveAsTemplate = async () => {
    const name = window.prompt('Nom du modèle :', doc?.title);
    if (!name) return;
    const res = await apiFetch('/api/templates', json({ name, kind: 'rapport', content: editor.getJSON(), layout: doc.layout, is_shared: true }));
    setStatus(res.ok ? { kind: 'ok', text: `Modèle « ${name} » enregistré.` } : { kind: 'error', text: await readError(res) });
    loadLists();
  };

  const deleteDocument = async () => {
    if (!window.confirm('Supprimer ce document ? Il reste dans l\'historique (suppression logique).')) return;
    await apiFetch(`/api/documents/${doc.id}`, { method: 'DELETE' });
    setDoc(null);
    editor?.commands.clearContent();
    loadLists();
  };

  const effectiveLayout = useMemo(() => deepMerge(chart.style, doc?.layout), [chart.style, doc?.layout]);
  const m = effectiveLayout.margins_mm || {};
  const footnotes = [];
  editor?.state.doc.descendants((n) => { if (n.type.name === 'footnote') footnotes.push(n.attrs.text); });
  const pendingChanges = editor ? markRanges(editor.state.doc, 'insertion').length + markRanges(editor.state.doc, 'deletion').length : 0;
  const ctxValue = useMemo(() => ({ projectId: doc?.project_id, style: chart.style, fields, projects: ctx.projects, tasks: ctx.tasks, layout: effectiveLayout }),
    [doc?.project_id, chart.style, fields, ctx.projects, ctx.tasks, effectiveLayout]);

  return (
    <DocContext.Provider value={ctxValue}>
      <style>{chartCss(chart.style, effectiveLayout)}</style>
      <div className="space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="me-4">
            <h1 className="text-2xl font-bold text-slate-800">Éditeur de documents</h1>
            <p className="text-sm text-slate-500">Rapports et notes aux couleurs de la charte du projet ; blocs de données toujours à jour.</p>
          </div>
          <select aria-label="Ouvrir un document" className="border rounded px-2 py-1.5 text-sm min-w-[18rem]" value={doc?.id ?? ''}
                  onChange={(e) => e.target.value && openDocument(Number(e.target.value))}>
            <option value="">Ouvrir un document…</option>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.title} (v{d.version})</option>)}
          </select>
        </div>

        <section className="bg-white border rounded-xl p-3 flex flex-wrap items-end gap-2 text-sm no-print">
          <FilePlus2 className="w-4 h-4 text-afmi-forest" />
          <input aria-label="Titre du nouveau document" className="border rounded px-2 py-1" placeholder="Titre du nouveau document" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <select aria-label="Projet du nouveau document" className="border rounded px-2 py-1" value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })}>
            <option value="">Sans projet (association)</option>
            {ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
          </select>
          <select aria-label="Modèle" className="border rounded px-2 py-1" value={form.template_id} onChange={(e) => setForm({ ...form, template_id: e.target.value })}>
            <option value="base">Rapport d'activité (modèle de base)</option>
            <option value="">Document vierge</option>
            {templates.map((t) => <option key={t.id} value={t.id}>Modèle : {t.name}</option>)}
          </select>
          <select aria-label="Langue" className="border rounded px-2 py-1" value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
            <option value="fr">Français</option><option value="ar">العربية</option><option value="en">English</option>
          </select>
          <button className="bg-afmi-forest text-white rounded px-3 py-1.5" onClick={createDocument}>Créer</button>
        </section>

        {status && <div role="status" className={`rounded px-3 py-2 text-sm ${status.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>{status.text}</div>}

        {doc && (
          <div className="grid grid-cols-12 gap-3">
            <div className="col-span-12 2xl:col-span-9 space-y-2">
              <div className="flex flex-wrap items-center gap-2 bg-white border rounded-xl p-2 text-sm no-print">
                <input aria-label="Titre du document" className="font-semibold border rounded px-2 py-1 min-w-[16rem]" value={doc.title}
                       onChange={(e) => { updateDoc({ title: e.target.value }); setFields((f) => ({ ...f, title: e.target.value })); }} />
                <select aria-label="Projet du document" className="border rounded px-2 py-1" value={doc.project_id ?? ''}
                        onChange={(e) => {
                          const pid = e.target.value ? Number(e.target.value) : null;
                          updateDoc({ project_id: pid, funder_id: ctx.projects.find((p) => p.id === pid)?.funder_id ?? null });
                        }}>
                  <option value="">Sans projet</option>
                  {ctx.projects.map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                </select>
                <select aria-label="Langue du document" className="border rounded px-2 py-1" value={doc.language} onChange={(e) => updateDoc({ language: e.target.value })}>
                  <option value="fr">Français</option><option value="ar">العربية</option><option value="en">English</option>
                </select>
                <span className="text-xs text-slate-500">{dirty ? 'Modifications non enregistrées…' : `Enregistré · version ${doc.version}`}</span>
                <span className="ms-auto flex gap-1">
                  <button className="tb-text" onClick={() => save()}><Save size={14} /> Enregistrer</button>
                  <button className="tb-text" onClick={() => { const n = window.prompt('Note de version :', 'Relecture'); if (n !== null) save(n); }}><History size={14} /> Version</button>
                  <button className="tb-text" onClick={saveAsTemplate}><BookmarkPlus size={14} /> Modèle</button>
                  <button className="tb-text" onClick={openPreview}><Printer size={14} /> Aperçu paginé</button>
                  <button className="tb-text text-red-700" onClick={deleteDocument}><Trash2 size={14} /></button>
                </span>
              </div>
              <Toolbar editor={editor} onComment={addComment} trackChanges={track}
                       onToggleTrack={() => { editor.commands.setTrackChanges(!track); setTrack(!track); }} />
              {track && <div className="text-xs text-amber-800 bg-amber-50 rounded px-2 py-1 no-print">Mode révision actif : les ajouts sont soulignés en vert, les suppressions barrées en rouge, jusqu'à acceptation ou refus. {pendingChanges} modification(s) en attente.</div>}
              {!track && pendingChanges > 0 && <div className="text-xs text-amber-800 bg-amber-50 rounded px-2 py-1 no-print">{pendingChanges} modification(s) suivie(s) en attente d'acceptation.</div>}
              <div className="doc-canvas">
                <div className="doc-page" dir={doc.language === 'ar' ? 'rtl' : 'ltr'}
                     style={{ padding: `${m.top || 25}mm ${m.right || 20}mm ${m.bottom || 22}mm ${m.left || 20}mm` }}>
                  <div className="doc-header no-print" style={{ marginTop: `-${(m.top || 25) - 6}mm` }}>
                    {(effectiveLayout.logos || []).filter((l) => l.position?.startsWith('header')).map((l, i) => (
                      <img key={i} className={`logo-${l.position}`} style={{ height: `${l.height_mm || 14}mm` }}
                           src={l.funder_logo ? `/api/funders/${l.funder_logo}/logo` : `/api/files/${l.file_id}/image`} alt="Logo" />
                    ))}
                    <span className="doc-header-text">{(effectiveLayout.header?.text || '').replace(/\{(\w+)\}/g, (x, k) => fields[k] ?? x)}</span>
                  </div>
                  <div className="doc-body">
                    <EditorContent editor={editor} />
                    {footnotes.length > 0 && (
                      <section className="footnotes-preview no-print">
                        <div className="text-xs font-semibold text-slate-500">Notes</div>
                        <ol>{footnotes.map((n, i) => <li key={i}>{n}</li>)}</ol>
                      </section>
                    )}
                  </div>
                  <div className="doc-footer no-print">
                    {[effectiveLayout.footer?.text, ...(chart.style.mentions || [])].filter(Boolean).join(' — ')}
                    {effectiveLayout.footer?.page_numbers !== false && <span className="ms-auto">Page n / N</span>}
                  </div>
                </div>
              </div>
            </div>

            <aside className="col-span-12 2xl:col-span-3 bg-white border rounded-xl p-3 text-sm space-y-3 self-start no-print">
              <div className="flex flex-wrap gap-1">
                {[['layout', 'Mise en page', LayoutTemplate], ['chart', 'Charte', Palette], ['comments', `Commentaires (${comments.filter((c) => !c.resolved).length})`, MessageSquare],
                  ['versions', 'Versions', History], ['assistant', 'Assistant IA', Sparkles]].map(([id, label, Icon]) => (
                  <button key={id} onClick={() => setPanel(id)} className={`px-2 py-1 rounded flex items-center gap-1 ${panel === id ? 'bg-afmi-forest text-white' : 'bg-slate-100'}`}>
                    <Icon size={13} />{label}
                  </button>
                ))}
              </div>

              {panel === 'layout' && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-500">Valeurs propres à ce document ; vide = valeur de la charte ({effectiveLayout.margins_mm?.top} mm en haut…).</p>
                  {LAYOUT_FIELDS.map(([path, label, type]) => (
                    <label key={path} className={`flex ${type === 'checkbox' ? 'flex-row items-center gap-2' : 'flex-col gap-1'} text-xs`}>
                      {type === 'checkbox' ? (
                        <input type="checkbox" checked={!!getPath(effectiveLayout, path)} onChange={(e) => updateDoc({ layout: setPath(doc.layout, path, e.target.checked) })} />
                      ) : null}
                      <span>{label}</span>
                      {type !== 'checkbox' && (
                        <input type={type} className="border rounded px-2 py-1" placeholder={String(getPath(chart.style, path) ?? '')}
                               value={getPath(doc.layout, path) ?? ''}
                               onChange={(e) => updateDoc({ layout: setPath(doc.layout, path, type === 'number' ? (e.target.value ? Number(e.target.value) : null) : e.target.value) })} />
                      )}
                    </label>
                  ))}
                </div>
              )}

              {panel === 'chart' && (
                <div className="space-y-2 text-xs">
                  <div>Charte appliquée : <strong>{chart.chain.join(' → ')}</strong></div>
                  <div className="flex gap-2">{Object.entries(chart.style.colors || {}).map(([k, v]) => <span key={k} title={k} className="w-6 h-6 rounded border" style={{ background: v }} />)}</div>
                  <div>Police : {chart.style.fonts?.body} {chart.style.fonts?.size_pt} pt · Photos par ligne : {chart.style.photo_grid?.per_row}</div>
                  {(chart.style.mentions || []).map((mn, i) => <div key={i} className="italic">« {mn} »</div>)}
                  <p className="text-slate-500">Les chartes se modifient dans « Chartes et modèles ». Elles s'appliquent selon le projet et le bailleur du document.</p>
                </div>
              )}

              {panel === 'comments' && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-500">Sélectionnez un passage puis cliquez sur l'icône « commentaire » de la barre d'outils.</p>
                  {comments.length === 0 && <p className="text-xs">Aucun commentaire.</p>}
                  {comments.map((c) => (
                    <div key={c.id} className={`border rounded p-2 ${c.resolved ? 'opacity-50' : ''}`}>
                      <button className="text-start w-full" onClick={() => goToComment(c.anchor_id)}>
                        <div className="text-xs text-slate-500">{c.author} · {String(c.created_at).slice(0, 16)}</div>
                        {c.quoted && <div className="text-xs italic text-slate-500">« {c.quoted} »</div>}
                        <div>{c.text}</div>
                      </button>
                      <button className="text-xs text-afmi-forest mt-1" onClick={() => resolveComment(c)}>{c.resolved ? 'Rouvrir' : 'Résoudre'}</button>
                    </div>
                  ))}
                </div>
              )}

              {panel === 'versions' && (
                <div className="space-y-2">
                  {versions.length === 0 && <p className="text-xs">Aucune version enregistrée (bouton « Version »).</p>}
                  {versions.map((v) => (
                    <div key={v.id} className="flex items-center gap-2 border rounded p-2">
                      <div className="flex-1"><div className="font-semibold">Version {v.number}</div><div className="text-xs text-slate-500">{v.note} · {v.created_by} · {String(v.created_at).slice(0, 16)}</div></div>
                      <button className="text-xs text-afmi-forest" onClick={() => restore(v)}>Restaurer</button>
                    </div>
                  ))}
                </div>
              )}

              {panel === 'assistant' && (
                <div className="space-y-2">
                  <select aria-label="Action de l'assistant" className="border rounded px-2 py-1 w-full" value={assistant.action} onChange={(e) => setAssistant({ ...assistant, action: e.target.value })}>
                    <option value="reformulate">Reformuler la sélection</option>
                    <option value="summarize">Résumer la sélection</option>
                    <option value="translate">Traduire la sélection</option>
                    <option value="complete">Rédiger une section à partir des données du projet</option>
                  </select>
                  {assistant.action === 'translate' && (
                    <select aria-label="Langue cible" className="border rounded px-2 py-1 w-full" value={assistant.language || 'ar'} onChange={(e) => setAssistant({ ...assistant, language: e.target.value })}>
                      <option value="ar">vers l'arabe</option><option value="fr">vers le français</option><option value="en">vers l'anglais</option>
                    </select>
                  )}
                  {assistant.action === 'complete' && (
                    <input className="border rounded px-2 py-1 w-full" placeholder="Section : ex. Résultats du trimestre" value={assistant.instruction} onChange={(e) => setAssistant({ ...assistant, instruction: e.target.value })} />
                  )}
                  <button className="bg-afmi-forest text-white rounded px-3 py-1.5 w-full" disabled={assistant.busy} onClick={runAssistant}>{assistant.busy ? 'Rédaction…' : 'Lancer'}</button>
                  {assistant.result?.error && <p className="text-xs text-red-700">{assistant.result.error}</p>}
                  {assistant.result?.offline && <p className="text-xs text-amber-800">Aucun modèle d'IA disponible (IA externe désactivée et Ollama absent) : le texte ci-dessous est un modèle générique, à réécrire.</p>}
                  {assistant.result?.text && (
                    <>
                      <div className="border rounded p-2 text-xs whitespace-pre-wrap max-h-60 overflow-y-auto" dir="auto">{assistant.result.text}</div>
                      {assistant.result.unverified_numbers?.length > 0 && (
                        <p className="text-xs text-red-700">Chiffres absents des données du projet, à vérifier : {assistant.result.unverified_numbers.join(', ')}</p>
                      )}
                      <div className="flex gap-2">
                        <button className="text-xs bg-slate-100 rounded px-2 py-1" onClick={() => insertAssistant(false)}>Insérer</button>
                        <button className="text-xs bg-slate-100 rounded px-2 py-1" onClick={() => insertAssistant(true)}>Remplacer la sélection</button>
                      </div>
                      <p className="text-[11px] text-slate-500">Moteur : {assistant.result.engine}. Relisez toujours le texte proposé.</p>
                    </>
                  )}
                </div>
              )}
            </aside>
          </div>
        )}
      </div>

      {preview && (
        <div className="fixed inset-0 bg-black/50 z-50 flex flex-col p-4 no-print" role="dialog" aria-label="Aperçu paginé">
          <div className="bg-white rounded-t-lg p-2 flex items-center gap-2 text-sm">
            <strong>Aperçu</strong>
            <span className="text-xs text-slate-500">La pagination, les en-têtes, pieds de page et numéros apparaissent à l'impression (« Enregistrer en PDF » pour un fichier).</span>
            <button className="ms-auto bg-afmi-forest text-white rounded px-3 py-1" onClick={() => previewFrame.current?.contentWindow?.print()}>Imprimer / PDF</button>
            <button className="bg-slate-100 rounded px-3 py-1" onClick={() => setPreview(null)}>Fermer</button>
          </div>
          <iframe ref={previewFrame} title="Aperçu du document" className="flex-1 bg-slate-200 rounded-b-lg" srcDoc={preview} />
        </div>
      )}
    </DocContext.Provider>
  );
}
