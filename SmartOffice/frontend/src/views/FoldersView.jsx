import React, { useCallback, useEffect, useState } from 'react';
import { FolderTree, Folder, FolderOpen, FolderPlus, FileText, ChevronRight, ChevronDown, Pencil, Trash2 } from 'lucide-react';
import { apiFetch } from '../apiClient';

// Classement des documents (Lot 9) : Année › Projet › Type, dossiers personnalisés, déplacement des documents.
// Chaque document importé est aussi copié dans les dossiers locaux du projet (explorateur Windows).

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

export default function FoldersView() {
  const [tree, setTree] = useState(null);
  const [open, setOpen] = useState({});
  const [sel, setSel] = useState(null);           // { year, project_id, doc_type?, folder_id?, label }
  const [docs, setDocs] = useState([]);
  const [message, setMessage] = useState('');

  const loadTree = useCallback(() => apiFetch('/api/ged/tree').then((r) => r.json()).then((t) => {
    setTree(t);
    if (t.years[0]) setOpen((o) => ({ [t.years[0].year]: true, ...o }));
  }).catch(() => setMessage('Base indisponible.')), []);
  useEffect(() => { loadTree(); }, [loadTree]);

  const loadDocs = useCallback(async (s) => {
    if (!s) return;
    const q = new URLSearchParams();
    if (s.year && !s.folder_id) q.set('year', s.year);
    if (s.project_id) q.set('project_id', s.project_id);
    if (s.doc_type) q.set('doc_type', s.doc_type);
    if (s.folder_id) q.set('folder_id', s.folder_id);
    const r = await apiFetch(`/api/ged/tree/documents?${q}`);
    setDocs(r.ok ? await r.json() : []);
  }, []);
  useEffect(() => { loadDocs(sel); }, [sel, loadDocs]);

  const toggle = (k) => setOpen((o) => ({ ...o, [k]: !o[k] }));
  const newFolder = async (project, year) => {
    const name = window.prompt(`Nouveau dossier dans ${project.code} — ${year} :`);
    if (!name) return;
    const r = await apiFetch('/api/ged/folders', json('POST', { name, project_id: project.id, year: Number(year) || null }));
    setMessage(r.ok ? `Dossier « ${name} » créé.` : (await r.json()).detail);
    loadTree();
  };
  const renameFolder = async (f) => {
    const name = window.prompt('Nouveau nom :', f.name);
    if (!name) return;
    await apiFetch(`/api/ged/folders/${f.id}`, json('PUT', { name }));
    loadTree();
  };
  const deleteFolder = async (f) => {
    if (!window.confirm(`Supprimer le dossier « ${f.name} » ? Ses documents reviennent dans le classement automatique (rien n'est supprimé).`)) return;
    await apiFetch(`/api/ged/folders/${f.id}`, { method: 'DELETE' });
    setSel(null);
    loadTree();
  };
  const move = async (doc, folderId) => {
    const r = await apiFetch(`/api/ged/documents/${doc.id}`, json('PUT', { folder_id: folderId ? Number(folderId) : null }));
    setMessage(r.ok ? 'Document classé.' : (await r.json()).detail);
    loadTree();
    loadDocs(sel);
  };

  if (!tree) return <div className="text-sm text-slate-500">{message || 'Chargement…'}</div>;
  const projectFolders = (pid) => tree.folders.filter((f) => f.project_id === pid);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><FolderTree className="w-6 h-6" />Dossiers & classement</h1>
        <p className="text-sm text-slate-500">Tous les documents, classés automatiquement par année, projet et type, avec vos dossiers personnalisés.
          Chaque document importé est aussi copié dans les dossiers locaux du projet (Année › Trimestre › Comptes rendus, Rapports…), visibles dans l'explorateur Windows.</p>
      </div>
      {message && <div role="status" className="bg-emerald-50 text-emerald-800 rounded px-3 py-2 text-sm">{message}</div>}
      <div className="grid grid-cols-12 gap-4">
        <nav className="col-span-12 md:col-span-4 bg-white border rounded-xl p-3 text-sm max-h-[70vh] overflow-auto" aria-label="Arborescence des documents">
          {tree.years.length === 0 && <p className="text-slate-400">Aucun document.</p>}
          {tree.years.map((y) => (
            <div key={y.year}>
              <button className="flex items-center gap-1 w-full text-start py-1 font-semibold" onClick={() => toggle(y.year)}>
                {open[y.year] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}{y.year} <span className="text-xs text-slate-400">({y.count})</span>
              </button>
              {open[y.year] && y.projects.map((p) => {
                const key = `${y.year}-${p.id}`;
                return (
                  <div key={key} className="ps-4">
                    <div className="flex items-center gap-1">
                      <button className="flex items-center gap-1 flex-1 text-start py-0.5" onClick={() => { toggle(key); setSel({ year: y.year, project_id: p.id, label: `${y.year} › ${p.code}` }); }}>
                        {open[key] ? <FolderOpen className="w-4 h-4 text-amber-600" /> : <Folder className="w-4 h-4 text-amber-600" />}{p.code} <span className="text-xs text-slate-400">({p.count})</span>
                      </button>
                      <button title="Nouveau dossier" aria-label={`Nouveau dossier dans ${p.code}`} onClick={() => newFolder(p, y.year)}><FolderPlus className="w-3.5 h-3.5 text-slate-500" /></button>
                    </div>
                    {open[key] && (
                      <div className="ps-5">
                        {p.types.map((t) => (
                          <button key={t.name} className={`flex items-center gap-1 w-full text-start py-0.5 ${sel?.doc_type === t.name && sel?.project_id === p.id && sel?.year === y.year ? 'text-afmi-forest font-medium' : ''}`}
                            onClick={() => setSel({ year: y.year, project_id: p.id, doc_type: t.name, label: `${y.year} › ${p.code} › ${t.name}` })}>
                            <Folder className="w-3.5 h-3.5 text-slate-400" />{t.name} <span className="text-xs text-slate-400">({t.count})</span>
                          </button>
                        ))}
                        {projectFolders(p.id).filter((f) => !f.year || String(f.year) === y.year).map((f) => (
                          <div key={f.id} className="flex items-center gap-1">
                            <button className="flex items-center gap-1 flex-1 text-start py-0.5 italic" onClick={() => setSel({ folder_id: f.id, project_id: p.id, label: `${p.code} › ${f.name}` })}>
                              <Folder className="w-3.5 h-3.5 text-afmi-forest" />{f.name} <span className="text-xs text-slate-400">({f.count})</span>
                            </button>
                            <button aria-label="Renommer" onClick={() => renameFolder(f)}><Pencil className="w-3 h-3 text-slate-400" /></button>
                            <button aria-label="Supprimer le dossier" onClick={() => deleteFolder(f)}><Trash2 className="w-3 h-3 text-red-600" /></button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </nav>
        <section className="col-span-12 md:col-span-8 bg-white border rounded-xl p-3 text-sm">
          <h2 className="font-semibold mb-2">{sel ? sel.label : 'Choisissez un dossier'}</h2>
          {sel && (
            <table className="w-full text-xs">
              <thead><tr className="text-slate-500"><th className="text-start p-1">Document</th><th className="text-start p-1">Type</th><th className="text-start p-1">Date</th><th className="text-start p-1">Dossier personnalisé</th></tr></thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id} className="border-t">
                    <td className="p-1"><a className="text-afmi-forest underline flex items-center gap-1" href={`/api/ged/documents/${d.id}/file`} target="_blank" rel="noreferrer">
                      <FileText className="w-3.5 h-3.5" />{d.title}</a></td>
                    <td className="p-1">{d.doc_type}</td>
                    <td className="p-1">{d.signature_date || d.uploaded?.slice(0, 10)}</td>
                    <td className="p-1">
                      <select aria-label="Classer dans un dossier" className="border rounded px-1" value={d.folder_id || ''} onChange={(e) => move(d, e.target.value)}>
                        <option value="">Classement automatique</option>
                        {projectFolders(d.project_id).map((f) => <option key={f.id} value={f.id}>{f.name}{f.year ? ` (${f.year})` : ''}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
                {docs.length === 0 && <tr><td className="p-2 text-slate-400" colSpan={4}>Aucun document dans ce dossier.</td></tr>}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
