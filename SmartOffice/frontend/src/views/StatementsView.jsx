import React, { useEffect, useMemo, useRef, useState } from 'react';
import { FileUp, CheckCircle2, AlertTriangle, XCircle, Save, ShieldCheck, ArrowRightLeft, Trash2, Plus, Loader2, FileSpreadsheet } from 'lucide-react';
import { apiFetch, apiDownload } from '../apiClient';

// Relevés bancaires (Lot 3) : import, lecture OCR, validation ligne à ligne à côté de l'image, intégration en brouillons.
// Aucune opération n'est créée sans validation explicite ; les brouillons se valident ensuite dans la Trésorerie (bureau).

const LOW = 75;

const fmt = (cents) => (cents === null || cents === undefined || cents === 0)
  ? ''
  : (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const parseAmount = (text) => {
  const t = String(text ?? '').replace(/[\s  ]/g, '').replace(/(MAD|DH)/gi, '');
  if (!t) return 0;
  const lastComma = t.lastIndexOf(','), lastDot = t.lastIndexOf('.');
  let n = t;
  if (lastComma >= 0 && lastDot >= 0) n = lastComma > lastDot ? t.replace(/\./g, '').replace(',', '.') : t.replace(/,/g, '');
  else if (lastComma >= 0) n = t.replace(',', '.');
  const v = Number(n);
  return Number.isFinite(v) ? Math.round(v * 100) : NaN;
};

const readError = async (res) => {
  try { const j = await res.json(); return j.detail || JSON.stringify(j); } catch { return `Erreur ${res.status}`; }
};

function Field({ label, children }) {
  return (
    <label className="flex flex-col text-xs text-slate-500 gap-1">
      <span>{label}</span>
      {children}
    </label>
  );
}

function AmountInput({ value, onChange, low, disabled, ariaLabel }) {
  const [text, setText] = useState(fmt(value));
  useEffect(() => setText(fmt(value)), [value]);
  return (
    <input
      aria-label={ariaLabel}
      disabled={disabled}
      dir="ltr" className={`w-24 text-end rounded border px-2 py-1 text-sm ${low ? 'bg-amber-100 border-amber-400' : 'border-slate-200'} ${Number.isNaN(parseAmount(text)) ? 'border-red-500' : ''}`}
      value={text}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => { const v = parseAmount(text); if (!Number.isNaN(v)) onChange(v); }}
    />
  );
}

export default function StatementsView() {
  const [ctx, setCtx] = useState(null);
  const [statements, setStatements] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [st, setSt] = useState(null);
  const [lines, setLines] = useState([]);
  const [header, setHeader] = useState({});
  const [deleted, setDeleted] = useState([]);
  const [page, setPage] = useState(1);
  const [activeLine, setActiveLine] = useState(null);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState(null);
  const [upload, setUpload] = useState({ account_id: '', mode: 'documents', use_ai: false, files: [] });
  const [uploadResults, setUploadResults] = useState([]);
  const imageBox = useRef(null);

  const loadContext = async () => {
    const res = await apiFetch('/api/statements/context');
    if (!res.ok) { setMessage({ kind: 'error', text: await readError(res) }); return; }
    const data = await res.json();
    setCtx(data);
    setUpload((u) => ({ ...u, account_id: u.account_id || (data.accounts[0]?.id ?? '') }));
  };
  const loadList = async () => {
    const res = await apiFetch('/api/statements');
    if (res.ok) setStatements(await res.json());
  };
  const loadStatement = async (id) => {
    const res = await apiFetch(`/api/statements/${id}`);
    if (!res.ok) { setMessage({ kind: 'error', text: await readError(res) }); return; }
    const data = await res.json();
    setSt(data);
    setLines(data.lines.map((l) => ({ ...l, dirty: false })));
    setHeader({ period_start: data.period_start, period_end: data.period_end, opening: data.opening, closing: data.closing });
    setDeleted([]);
    setPage(1);
    setActiveLine(null);
  };

  useEffect(() => { loadContext(); loadList(); }, []);
  useEffect(() => { if (selectedId) loadStatement(selectedId); }, [selectedId]);

  const editable = st?.status === 'Draft';
  const movement = useMemo(() => lines.reduce((s, l) => s + (l.credit || 0) - (l.debit || 0), 0), [lines]);
  const balanceGap = (header.opening ?? 0) + movement - (header.closing ?? 0);
  const dirty = lines.some((l) => l.dirty) || deleted.length > 0 || (st && (header.opening !== st.opening || header.closing !== st.closing
    || header.period_start !== st.period_start || header.period_end !== st.period_end));

  const updateLine = (idx, patch) => setLines((ls) => ls.map((l, i) => (i === idx ? { ...l, ...patch, dirty: true } : l)));

  const doUpload = async () => {
    if (!upload.account_id || upload.files.length === 0) {
      setMessage({ kind: 'error', text: 'Choisissez le compte et au moins un fichier.' });
      return;
    }
    setBusy('upload'); setMessage(null); setUploadResults([]);
    const form = new FormData();
    form.append('account_id', upload.account_id);
    form.append('mode', upload.mode);
    form.append('use_ai', upload.use_ai ? 'true' : 'false');
    upload.files.forEach((f) => form.append('files', f));
    const res = await apiFetch('/api/statements/upload', { method: 'POST', body: form });
    setBusy('');
    if (!res.ok) { setMessage({ kind: 'error', text: await readError(res) }); return; }
    const data = await res.json();
    setUploadResults(data.results);
    await loadList();
    const first = data.results.find((r) => r.statement_id);
    if (first) setSelectedId(first.statement_id);
  };

  const save = async () => {
    setBusy('save'); setMessage(null);
    const payload = {
      ...header,
      lines: [
        ...lines.filter((l) => l.dirty || !l.id).map((l) => ({
          id: l.id, date: l.date, value_date: l.value_date, label: l.label, reference: l.reference,
          debit: l.debit || 0, credit: l.credit || 0, category_id: l.category_id ?? null,
          project_id: l.project_id ?? null, budget_line_id: l.budget_line_id ?? null,
        })),
        ...deleted.map((id) => ({ id, deleted: true })),
      ],
    };
    const res = await apiFetch(`/api/statements/${st.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    setBusy('');
    if (!res.ok) { setMessage({ kind: 'error', text: await readError(res) }); return false; }
    const data = await res.json();
    setMessage({ kind: 'ok', text: 'Corrections enregistrées.' + (data.learned_rules ? ` ${data.learned_rules} règle(s) de catégorisation apprise(s).` : '') });
    await loadStatement(st.id);
    await loadList();
    return true;
  };

  const action = async (kind) => {
    if (dirty && kind !== 'delete' && !(await save())) return;
    if (kind === 'delete' && !window.confirm('Supprimer ce relevé ? Il reste dans l\'historique (suppression logique).')) return;
    setBusy(kind); setMessage(null);
    const res = await apiFetch(`/api/statements/${st.id}${kind === 'delete' ? '' : '/' + kind}`, { method: kind === 'delete' ? 'DELETE' : 'POST' });
    setBusy('');
    if (!res.ok) { setMessage({ kind: 'error', text: await readError(res) }); return; }
    if (kind === 'delete') { setSelectedId(null); setSt(null); await loadList(); return; }
    if (kind === 'integrate') {
      const r = await res.json();
      setMessage({ kind: 'ok', text: `${r.created} opération(s) créée(s) en brouillon, ${r.skipped_existing} déjà présente(s) dans la comptabilité, ${r.already_integrated} déjà intégrée(s). Ventilez-les et validez-les dans la Trésorerie.` });
    } else {
      setMessage({ kind: 'ok', text: 'Relevé validé : vous pouvez l\'intégrer.' });
    }
    await loadStatement(st.id);
    await loadList();
  };

  const focusLine = (idx) => {
    const l = lines[idx];
    setActiveLine(idx);
    if (l.page !== undefined) setPage(l.page + 1);
    const box = imageBox.current;
    if (box && l.y) setTimeout(() => { box.scrollTop = Math.max(0, l.y * box.scrollHeight - box.clientHeight / 2); }, 50);
  };

  const categoriesFor = (l) => (ctx?.categories || []).filter((c) => c.kind === ((l.credit || 0) > 0 ? 'Income' : 'Expense'));
  const budgetLinesFor = (l) => (ctx?.budget_lines || []).filter((b) => (b.project_id ?? null) === (l.project_id ?? null));
  const low = (l, field) => (l.confidence?.[field] ?? 100) < LOW;
  const active = activeLine !== null ? lines[activeLine] : null;
  const excel = async (url) => {
    try {
      const name = await apiDownload(url);
      setMessage({ kind: 'ok', text: `Fichier exporté : ${name}` });
    } catch (e) {
      setMessage({ kind: 'error', text: `Export impossible : ${e.message}` });
    }
  };

  return (
    <div className="space-y-4" dir="auto">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Relevés bancaires</h1>
        <p className="text-sm text-slate-500">
          Import de relevés PDF, scannés, photographiés ou exportés (CSV, Excel). La lecture est locale (OCR sur le poste).
          Rien n'entre en comptabilité sans votre validation : les lignes validées deviennent des opérations en brouillon.
        </p>
      </div>

      {message && (
        <div role="status" className={`rounded-lg px-4 py-2 text-sm ${message.kind === 'error' ? 'bg-red-50 text-red-800 border border-red-200' : 'bg-emerald-50 text-emerald-800 border border-emerald-200'}`}>
          {message.text}
        </div>
      )}

      {/* Import */}
      <section className="bg-white rounded-xl border border-slate-200 p-4">
        <h2 className="font-semibold text-slate-800 mb-3 flex items-center gap-2"><FileUp className="w-4 h-4" />Importer</h2>
        {ctx && !ctx.ocr_available && (
          <p className="text-xs text-amber-800 bg-amber-50 rounded p-2 mb-3">OCR local indisponible (Tesseract non installé) : seuls les PDF natifs, CSV et Excel peuvent être lus.</p>
        )}
        {ctx && ctx.accounts.length === 0 && (
          <p className="text-xs text-amber-800 bg-amber-50 rounded p-2 mb-3">Aucun compte : créez d'abord vos comptes dans l'application de bureau (menu Trésorerie).</p>
        )}
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Compte">
            <select className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={upload.account_id}
                    onChange={(e) => setUpload({ ...upload, account_id: e.target.value })}>
              {(ctx?.accounts || []).map((a) => <option key={a.id} value={a.id}>{a.title} ({a.currency})</option>)}
            </select>
          </Field>
          <Field label="Les fichiers sont…">
            <select className="border border-slate-200 rounded px-2 py-1.5 text-sm" value={upload.mode}
                    onChange={(e) => setUpload({ ...upload, mode: e.target.value })}>
              <option value="documents">des relevés distincts</option>
              <option value="pages">les pages d'un même relevé</option>
            </select>
          </Field>
          <Field label="Fichiers (PDF, JPG, PNG, TIFF, CSV, XLSX)">
            <input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.bmp,.webp,.csv,.txt,.xlsx,.xlsm" className="text-sm"
                   onChange={(e) => setUpload({ ...upload, files: Array.from(e.target.files || []) })} />
          </Field>
          <label className="flex items-center gap-2 text-xs text-slate-600" title="Selon vos paramètres de confidentialité (IA locale ou externe autorisée)">
            <input type="checkbox" checked={upload.use_ai} onChange={(e) => setUpload({ ...upload, use_ai: e.target.checked })} />
            Essayer l'IA si la lecture ne s'équilibre pas
          </label>
          <button onClick={doUpload} disabled={busy === 'upload'}
                  className="bg-afmi-forest text-white rounded-lg px-4 py-2 text-sm font-semibold flex items-center gap-2 disabled:opacity-60">
            {busy === 'upload' ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileUp className="w-4 h-4" />} Lire les relevés
          </button>
        </div>
        {uploadResults.length > 0 && (
          <ul className="mt-3 text-sm space-y-1">
            {uploadResults.map((r, i) => (
              <li key={i} className={r.error ? 'text-red-700' : 'text-slate-700'}>
                {r.error ? <XCircle className="inline w-4 h-4 me-1" /> : r.balance_ok ? <CheckCircle2 className="inline w-4 h-4 me-1 text-emerald-600" /> : <AlertTriangle className="inline w-4 h-4 me-1 text-amber-600" />}
                <strong>{r.file}</strong> : {r.error || `${r.lines} ligne(s) lue(s) (${r.engine})${r.balance_ok === false ? ' — soldes déséquilibrés, à vérifier' : ''}`}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="space-y-4">
        {/* Liste */}
        <section className="bg-white rounded-xl border border-slate-200 p-3 flex flex-wrap items-center gap-3">
          <h2 className="font-semibold text-slate-800">Relevés importés</h2>
          {statements.length === 0 && <p className="text-sm text-slate-500">Aucun relevé importé.</p>}
          {statements.length > 0 && (
            <select aria-label="Relevé à vérifier" className="border border-slate-200 rounded px-2 py-1.5 text-sm min-w-[28rem]" dir="auto"
                    value={selectedId ?? ''} onChange={(e) => setSelectedId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">— choisir un relevé —</option>
              {statements.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.status === 'Validated' ? '✔' : '•'} {s.account} — {s.period_start} → {s.period_end} — {s.lines} lignes — {s.status === 'Validated' ? 'validé' : 'à vérifier'}
                </option>
              ))}
            </select>
          )}
          <div className="flex flex-wrap gap-2 mt-3 text-sm">
            <button className="bg-slate-100 rounded px-3 py-1.5 flex items-center gap-2" onClick={() => excel('/api/exports/operations')}>
              <FileSpreadsheet className="w-4 h-4" />Opérations bancaires (Excel)
            </button>
            {selectedId && (
              <button className="bg-slate-100 rounded px-3 py-1.5 flex items-center gap-2" onClick={() => excel(`/api/exports/reconciliation/${selectedId}`)}>
                <FileSpreadsheet className="w-4 h-4" />État de rapprochement de ce relevé (Excel)
              </button>
            )}
          </div>
        </section>

        {/* Validation */}
        <section className="bg-white rounded-xl border border-slate-200 p-4" dir="ltr">
          {!st && <p className="text-sm text-slate-500">Sélectionnez un relevé pour le vérifier.</p>}
          {st && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-end gap-3">
                <div className="me-4">
                  <div className="text-lg font-semibold">{st.meta?.bank_name || 'Relevé'} <span className="text-xs font-normal text-slate-500">({st.meta?.engine})</span></div>
                  <div className="text-xs text-slate-500">{st.meta?.original_name}{st.meta?.rib ? ` · RIB lu ${st.meta.rib}` : ''}</div>
                </div>
                <Field label="Du"><input type="date" disabled={!editable} className="border rounded px-2 py-1 text-sm" value={header.period_start || ''} onChange={(e) => setHeader({ ...header, period_start: e.target.value })} /></Field>
                <Field label="Au"><input type="date" disabled={!editable} className="border rounded px-2 py-1 text-sm" value={header.period_end || ''} onChange={(e) => setHeader({ ...header, period_end: e.target.value })} /></Field>
                <Field label="Solde initial"><AmountInput ariaLabel="Solde initial" disabled={!editable} value={header.opening} low={st.meta && st.meta.opening_found === false} onChange={(v) => setHeader({ ...header, opening: v })} /></Field>
                <Field label="Solde final"><AmountInput ariaLabel="Solde final" disabled={!editable} value={header.closing} low={st.meta && st.meta.closing_found === false} onChange={(v) => setHeader({ ...header, closing: v })} /></Field>
                <div className={`text-sm font-semibold px-3 py-1.5 rounded-lg ${balanceGap === 0 ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-800'}`}>
                  {balanceGap === 0 ? '✔ Soldes équilibrés' : `Écart : ${(balanceGap / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}`}
                </div>
              </div>

              {(st.blocking.length > 0 || st.anomalies.length > 0 || (st.meta?.warnings || []).length > 0) && (
                <div className="grid md:grid-cols-2 gap-2 text-xs">
                  {st.blocking.length > 0 && (
                    <ul className="bg-red-50 border border-red-200 rounded p-2 space-y-1 text-red-800">
                      {st.blocking.map((b, i) => <li key={i} dir="auto"><XCircle className="inline w-3 h-3 me-1" />{b.message}</li>)}
                    </ul>
                  )}
                  <ul className="bg-amber-50 border border-amber-200 rounded p-2 space-y-1 text-amber-900">
                    {st.anomalies.map((a, i) => (
                      <li key={i} dir="auto" className={a.line_id ? 'cursor-pointer hover:underline' : ''}
                          onClick={() => { const idx = lines.findIndex((l) => l.id === a.line_id); if (idx >= 0) focusLine(idx); }}>
                        <AlertTriangle className="inline w-3 h-3 me-1" />{a.message}
                      </li>
                    ))}
                    {(st.meta?.warnings || []).map((w, i) => <li key={`w${i}`} dir="auto">ℹ️ {w}</li>)}
                  </ul>
                </div>
              )}

              <div className="grid grid-cols-12 gap-3">
                {/* Image du relevé */}
                <div className="col-span-12 lg:col-span-5">
                  {(st.meta?.pages || 0) > 0 ? (
                    <>
                      <div className="flex items-center gap-2 text-xs mb-1">
                        {Array.from({ length: st.meta.pages }, (_, i) => (
                          <button key={i} onClick={() => setPage(i + 1)} className={`px-2 py-0.5 rounded ${page === i + 1 ? 'bg-slate-800 text-white' : 'bg-slate-100'}`}>Page {i + 1}</button>
                        ))}
                      </div>
                      <div ref={imageBox} className="relative border rounded max-h-[65vh] overflow-y-auto bg-slate-50">
                        <img src={`/api/statements/${st.id}/pages/${page}`} alt={`Page ${page} du relevé`} className="w-full block" />
                        {active && active.page + 1 === page && active.y > 0 && (
                          <div className="absolute left-0 right-0 border-2 border-afmi-forest bg-emerald-300/20 pointer-events-none"
                               style={{ top: `calc(${active.y * 100}% - 12px)`, height: '24px' }} />
                        )}
                      </div>
                    </>
                  ) : <p className="text-xs text-slate-500">Pas d'image (fichier tableur).</p>}
                </div>

                {/* Tableau extrait */}
                <div className="col-span-12 lg:col-span-7 overflow-x-auto max-h-[70vh] overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="sticky top-0 bg-white text-xs text-slate-500">
                      <tr>
                        <th className="text-start p-1">Date</th><th className="text-start p-1">Libellé</th>
                        <th className="text-end p-1">Débit</th><th className="text-end p-1">Crédit</th>
                        <th className="text-start p-1">Catégorie</th><th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {lines.map((l, idx) => (
                        <React.Fragment key={l.id ?? `n${idx}`}>
                        <tr onClick={() => focusLine(idx)}
                            className={`border-t align-top ${activeLine === idx ? 'bg-emerald-50' : ''} ${l.integrated ? 'opacity-60' : ''}`}>
                          <td className="p-1">
                            <input type="date" disabled={!editable} aria-label="Date" value={l.date || ''}
                                   className={`border rounded px-1 py-1 text-xs ${low(l, 'date') ? 'bg-amber-100 border-amber-400' : 'border-slate-200'}`}
                                   onChange={(e) => updateLine(idx, { date: e.target.value })} />
                          </td>
                          <td className="p-1 min-w-[16rem]">
                            <input dir="auto" disabled={!editable} aria-label="Libellé" value={l.label}
                                   className={`w-full border rounded px-2 py-1 text-xs ${low(l, 'label') ? 'bg-amber-100 border-amber-400' : 'border-slate-200'}`}
                                   onChange={(e) => updateLine(idx, { label: e.target.value })} />
                            {l.integrated && <div className="text-[10px] text-emerald-700">intégrée</div>}
                          </td>
                          <td className="p-1 text-end"><AmountInput ariaLabel="Débit" disabled={!editable} value={l.debit} low={low(l, 'debit')} onChange={(v) => updateLine(idx, { debit: v, credit: v > 0 ? 0 : l.credit })} /></td>
                          <td className="p-1 text-end"><AmountInput ariaLabel="Crédit" disabled={!editable} value={l.credit} low={low(l, 'credit')} onChange={(v) => updateLine(idx, { credit: v, debit: v > 0 ? 0 : l.debit })} /></td>
                          <td className="p-1 w-44">
                            <select disabled={!editable} aria-label="Catégorie" className="w-full border border-slate-200 rounded text-xs py-1" value={l.category_id ?? ''}
                                    onChange={(e) => updateLine(idx, { category_id: e.target.value ? Number(e.target.value) : null })}>
                              <option value="">— catégorie —</option>
                              {categoriesFor(l).map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                            </select>
                          </td>
                          <td className="p-1">
                            {editable && (
                              <button title="Supprimer la ligne" aria-label="Supprimer la ligne" className="text-red-600"
                                      onClick={(e) => { e.stopPropagation(); if (l.id) setDeleted((d) => [...d, l.id]); setLines((ls) => ls.filter((_, i) => i !== idx)); }}>
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </tr>
                        {activeLine === idx && (
                          <tr className="bg-emerald-50">
                            <td></td>
                            <td colSpan={5} className="p-1 pb-2">
                              <div className="flex flex-wrap items-center gap-2 text-xs">
                                <span className="text-slate-500">Imputation :</span>
                                <select disabled={!editable} aria-label="Projet" className="border border-slate-200 rounded py-1" value={l.project_id ?? ''}
                                        onChange={(e) => updateLine(idx, { project_id: e.target.value ? Number(e.target.value) : null, budget_line_id: null })}>
                                  <option value="">Fonctionnement général</option>
                                  {(ctx?.projects || []).map((p) => <option key={p.id} value={p.id}>{p.code} — {p.name}</option>)}
                                </select>
                                <select disabled={!editable} aria-label="Ligne budgétaire" className="border border-slate-200 rounded py-1" value={l.budget_line_id ?? ''}
                                        onChange={(e) => updateLine(idx, { budget_line_id: e.target.value ? Number(e.target.value) : null })}>
                                  <option value="">— ligne budgétaire —</option>
                                  {budgetLinesFor(l).map((b) => <option key={b.id} value={b.id}>{b.code} {b.label}</option>)}
                                </select>
                                {l.suggestion_source && <span className="text-slate-400">proposé : {l.suggestion_source}</span>}
                              </div>
                            </td>
                          </tr>
                        )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                  {editable && (
                    <button className="mt-2 text-xs text-afmi-forest flex items-center gap-1"
                            onClick={() => setLines((ls) => [...ls, { id: null, date: header.period_end, label: '', reference: '', debit: 0, credit: 0, confidence: {}, page: 0, y: 0, dirty: true }])}>
                      <Plus className="w-3 h-3" /> Ajouter une ligne oubliée
                    </button>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2 pt-2 border-t">
                {editable && (
                  <>
                    <button onClick={save} disabled={!dirty || !!busy} className="rounded-lg px-4 py-2 text-sm bg-slate-100 flex items-center gap-2 disabled:opacity-50">
                      <Save className="w-4 h-4" /> Enregistrer les corrections
                    </button>
                    <button onClick={() => action('validate')} disabled={!!busy || balanceGap !== 0}
                            title={balanceGap !== 0 ? 'Les soldes doivent être équilibrés' : ''}
                            className="rounded-lg px-4 py-2 text-sm bg-afmi-forest text-white flex items-center gap-2 disabled:opacity-50">
                      <ShieldCheck className="w-4 h-4" /> Valider le relevé
                    </button>
                  </>
                )}
                {st.status === 'Validated' && (
                  <button onClick={() => action('integrate')} disabled={!!busy}
                          className="rounded-lg px-4 py-2 text-sm bg-afmi-forest text-white flex items-center gap-2 disabled:opacity-50">
                    <ArrowRightLeft className="w-4 h-4" /> Intégrer en opérations brouillons
                  </button>
                )}
                <button onClick={() => action('delete')} disabled={!!busy} className="rounded-lg px-4 py-2 text-sm text-red-700 flex items-center gap-2 ms-auto">
                  <Trash2 className="w-4 h-4" /> Supprimer le relevé
                </button>
              </div>
              <p className="text-xs text-slate-500">
                Les champs surlignés en jaune ont été lus avec une confiance faible : comparez-les à l'image (cliquez sur une ligne pour la repérer).
                Une catégorie ou une imputation corrigée est mémorisée et proposée automatiquement la prochaine fois.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
