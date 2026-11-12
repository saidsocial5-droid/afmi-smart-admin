import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Settings, Search, Download, Upload, RotateCcw, Save, KeyRound, PlugZap, Loader2, ShieldCheck, Users, HardDriveDownload,
  Mail, FileJson, Plus, Trash2, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import { apiFetch, apiDownload } from '../apiClient';
import { useLanguage } from '../context/LanguageContext';

// Panneau de paramètres avancé (Lot 7) : une seule source (registre du backend), validation côté serveur,
// recherche, import/export JSON (sans secrets), retour aux valeurs par défaut.

const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const norm = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
const readError = async (res) => { try { return (await res.json()).detail || `Erreur ${res.status}`; } catch { return `Erreur ${res.status}`; } };
const MONTHS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
const OPTION_LABELS = {
  startup: 'À chaque démarrage', daily: 'Quotidienne', weekly: 'Hebdomadaire', manual: 'Manuelle uniquement',
  auto: 'Automatique', browser: 'Navigateur (Edge / Chromium)', libreoffice: 'LibreOffice', normal: 'Normale', compact: 'Compacte',
  fr: 'Français', ar: 'العربية', en: 'English',
};
const LEVELS = { blocking: 'Bloquant', warning: 'Avertissement', ignore: 'Ignoré' };
const CHECK_LABELS = {
  DRAFT_OPERATIONS: 'Opérations en brouillon', UNPAIRED_TRANSFER: 'Virements internes incomplets', MISSING_RATE: 'Taux de change manquant',
  UNCATEGORIZED: 'Opérations sans catégorie', UNRECONCILED_ACCOUNT: 'Comptes non rapprochés', MISSING_RECEIPT: 'Dépenses sans justificatif',
  INDICATOR_WITHOUT_MEASURE: 'Indicateurs sans mesure',
};

function Badge({ children, tone = 'slate' }) {
  const tones = { slate: 'bg-slate-100 text-slate-600', green: 'bg-emerald-50 text-emerald-700', amber: 'bg-amber-50 text-amber-800' };
  return <span className={`text-[11px] rounded px-1.5 py-0.5 ${tones[tone]}`}>{children}</span>;
}

/** Champ générique selon son type (bool, int, float, string, text, select, color). */
function FieldInput({ field, value, onChange }) {
  const common = 'border border-slate-200 rounded px-2 py-1.5 text-sm w-full';
  const id = `f-${field.key}`;
  if (field.type === 'bool') {
    return <input id={id} type="checkbox" className="w-4 h-4" checked={!!value} onChange={(e) => onChange(e.target.checked)} />;
  }
  if (field.type === 'select') {
    return (
      <select id={id} className={common} value={value ?? ''} onChange={(e) => onChange(typeof field.options[0] === 'number' ? Number(e.target.value) : e.target.value)}>
        {field.options.map((o) => (
          <option key={o} value={o}>{field.key.endsWith('start_month') ? `${o} — ${MONTHS[o - 1]}` : (OPTION_LABELS[o] || o)}</option>
        ))}
      </select>
    );
  }
  if (field.type === 'int' || field.type === 'float') {
    return <input id={id} type="number" className={common} value={value ?? ''} min={field.min} max={field.max} step={field.type === 'int' ? 1 : 'any'}
      onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} />;
  }
  if (field.type === 'text') {
    return <textarea id={id} className={`${common} font-mono text-xs`} rows={field.key.startsWith('ai.prompts') ? 5 : 3} value={value ?? ''} dir="auto"
      onChange={(e) => onChange(e.target.value)} />;
  }
  if (field.type === 'color') {
    return (
      <span className="flex items-center gap-2">
        <input id={id} type="color" value={value || '#1B4332'} onChange={(e) => onChange(e.target.value.toUpperCase())} />
        <code className="text-xs">{value}</code>
      </span>
    );
  }
  return <input id={id} type="text" className={common} value={value ?? ''} dir="auto" onChange={(e) => onChange(e.target.value)} />;
}

function FieldRow({ field, value, dirty, onChange, onReset }) {
  return (
    <div className={`grid md:grid-cols-12 gap-2 py-3 border-b border-slate-100 ${dirty ? 'bg-amber-50/40' : ''}`}>
      <div className="md:col-span-5">
        <label htmlFor={`f-${field.key}`} className="text-sm font-medium text-slate-800">{field.label}</label>
        <div className="flex flex-wrap gap-1 mt-1">
          {field.is_default ? <Badge>par défaut</Badge> : <Badge tone="green">personnalisé</Badge>}
          {field.restart && <Badge tone="amber">au prochain démarrage</Badge>}
          {dirty && <Badge tone="amber">non enregistré</Badge>}
        </div>
        {field.help && <p className="text-xs text-slate-500 mt-1">{field.help}</p>}
      </div>
      <div className="md:col-span-6">{field.type === 'secret' ? null : <FieldInput field={field} value={value} onChange={onChange} />}</div>
      <div className="md:col-span-1 flex md:justify-end items-start">
        {!field.is_default && (
          <button className="text-xs text-slate-500 hover:text-red-700 flex items-center gap-1" title="Restaurer la valeur par défaut" onClick={onReset}>
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}

function SecretRow({ field, onSaved, notify }) {
  const [value, setValue] = useState('');
  const save = async (v) => {
    const res = await apiFetch('/api/settings/secret', json('PUT', { key: field.key, value: v }));
    if (!res.ok) { notify('error', await readError(res)); return; }
    setValue('');
    notify('ok', v ? 'Clé enregistrée (chiffrée par DPAPI).' : 'Clé supprimée.');
    onSaved();
  };
  return (
    <div className="flex flex-wrap items-center gap-2">
      <KeyRound className="w-4 h-4 text-slate-500" />
      <span className="text-sm">{field.label}</span>
      {field.configured ? <Badge tone="green">configurée</Badge> : <Badge>non configurée</Badge>}
      <input type="password" autoComplete="new-password" aria-label={field.label} className="border border-slate-200 rounded px-2 py-1 text-sm flex-1 min-w-[12rem]"
        placeholder={field.configured ? 'Saisir une nouvelle clé pour la remplacer' : 'Coller la clé'} value={value} onChange={(e) => setValue(e.target.value)} />
      <button className="bg-slate-100 rounded px-2 py-1 text-xs disabled:opacity-50" disabled={!value} onClick={() => save(value)}>Enregistrer</button>
      {field.configured && <button className="text-xs text-red-700" onClick={() => save('')}>Supprimer</button>}
    </div>
  );
}

// --- IA ---------------------------------------------------------------------------------------------------------

function AiPanel({ fields, values, setValue, reload, notify }) {
  const [catalog, setCatalog] = useState(null);
  const [models, setModels] = useState({});
  const [testing, setTesting] = useState('');
  useEffect(() => { apiFetch('/api/settings/ai/catalog').then((r) => r.json()).then(setCatalog).catch(() => {}); }, []);
  if (!catalog) return null;
  const byKey = Object.fromEntries(fields.map((f) => [f.key, f]));
  const test = async (provider) => {
    setTesting(provider);
    const res = await apiFetch('/api/settings/ai/test', json('POST', { provider, base_url: values[`ai.providers.${provider}`]?.base_url }));
    const data = await res.json();
    setTesting('');
    notify(data.ok ? 'ok' : 'error', `${catalog.providers[provider].label} : ${data.message || data.detail}`);
    if (data.models?.length) setModels((m) => ({ ...m, [provider]: data.models }));
  };
  const usage = catalog.usage;
  return (
    <div className="space-y-4">
      <div className="text-xs text-slate-600 bg-slate-50 rounded p-2">
        Consommation de {usage.month} : {Object.keys(usage.providers).length === 0 ? 'aucun appel externe.' : Object.entries(usage.providers).map(([p, u]) =>
          `${catalog.providers[p]?.label || p} : ${u.calls} appel(s), ${u.in} + ${u.out} jetons`).join(' · ')}
        {usage.cost > 0 && ` — coût estimé ${usage.cost.toFixed(4)} USD`}{usage.cap > 0 && ` / plafond ${usage.cap} USD`}.
      </div>
      <section>
        <h3 className="font-semibold text-sm mb-2">Fournisseur par tâche</h3>
        <div className="overflow-x-auto">
          <table className="text-sm w-full">
            <thead><tr className="text-xs text-slate-500 text-start"><th className="text-start p-1">Tâche</th><th className="text-start p-1">Fournisseur</th>
              <th className="text-start p-1">Modèle</th><th className="text-start p-1">Température</th><th className="text-start p-1">Jetons max</th></tr></thead>
            <tbody>
              {Object.entries(catalog.tasks).map(([task, meta]) => {
                const key = `ai.tasks.${task}`;
                const v = values[key] || {};
                const set = (patch) => setValue(key, { ...v, ...patch });
                return (
                  <tr key={task} className="border-t border-slate-100">
                    <td className="p-1">{meta.label}{meta.vision && <span className="text-[11px] text-slate-400"> (images)</span>}</td>
                    <td className="p-1">
                      <select aria-label={`Fournisseur — ${meta.label}`} className="border rounded px-1 py-1" value={v.provider || 'auto'} onChange={(e) => set({ provider: e.target.value })}>
                        <option value="auto">Automatique (réglage général)</option>
                        {Object.entries(catalog.providers).map(([p, pm]) => <option key={p} value={p}>{pm.label}</option>)}
                      </select>
                    </td>
                    <td className="p-1">
                      <input aria-label={`Modèle — ${meta.label}`} list={`models-${v.provider}`} className="border rounded px-1 py-1 w-44" placeholder="modèle par défaut du fournisseur"
                        value={v.model || ''} onChange={(e) => set({ model: e.target.value })} />
                    </td>
                    <td className="p-1"><input aria-label={`Température — ${meta.label}`} type="number" step="0.1" min="0" max="2" className="border rounded px-1 py-1 w-20"
                      value={v.temperature ?? ''} onChange={(e) => set({ temperature: e.target.value === '' ? null : Number(e.target.value) })} /></td>
                    <td className="p-1"><input aria-label={`Jetons max — ${meta.label}`} type="number" min="1" className="border rounded px-1 py-1 w-24"
                      value={v.max_tokens ?? ''} onChange={(e) => set({ max_tokens: e.target.value === '' ? null : Number(e.target.value) })} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {Object.entries(models).map(([p, list]) => <datalist key={p} id={`models-${p}`}>{list.map((m) => <option key={m} value={m} />)}</datalist>)}
        <p className="text-xs text-slate-500 mt-1">Un fournisseur en ligne n'est appelé que si le mode hors ligne est désactivé, sous le plafond de coût,
          et jamais avec une image quand le masquage est actif : sinon le moteur local prend le relais.</p>
      </section>
      <section>
        <h3 className="font-semibold text-sm mb-2">Fournisseurs</h3>
        <div className="grid lg:grid-cols-2 gap-3">
          {Object.entries(catalog.providers).filter(([p]) => p !== 'heuristic').map(([p, meta]) => {
            const key = `ai.providers.${p}`;
            const v = values[key] || {};
            const set = (patch) => setValue(key, { ...v, ...patch });
            return (
              <div key={p} className="border border-slate-200 rounded-lg p-3 space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <strong>{meta.label}</strong>
                  {meta.external === true && <Badge tone="amber">en ligne</Badge>}{meta.external === false && <Badge tone="green">local</Badge>}
                  <button className="ms-auto bg-slate-100 rounded px-2 py-1 text-xs flex items-center gap-1" onClick={() => test(p)} disabled={!!testing}>
                    {testing === p ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <PlugZap className="w-3.5 h-3.5" />} Tester la connexion
                  </button>
                </div>
                <label className="block text-xs">Adresse<input className="border rounded px-2 py-1 w-full text-sm" value={v.base_url || ''} onChange={(e) => set({ base_url: e.target.value })} /></label>
                <label className="block text-xs">Modèle par défaut<input list={`models-${p}`} className="border rounded px-2 py-1 w-full text-sm" value={v.model || ''} onChange={(e) => set({ model: e.target.value })} /></label>
                <div className="flex gap-2 text-xs">
                  <label>Prix entrée (USD / M jetons)<input type="number" min="0" step="any" className="border rounded px-2 py-1 w-full" value={v.price_in ?? 0} onChange={(e) => set({ price_in: Number(e.target.value) })} /></label>
                  <label>Prix sortie (USD / M jetons)<input type="number" min="0" step="any" className="border rounded px-2 py-1 w-full" value={v.price_out ?? 0} onChange={(e) => set({ price_out: Number(e.target.value) })} /></label>
                </div>
                {byKey[`ai.keys.${p}`] && <SecretRow field={byKey[`ai.keys.${p}`]} onSaved={reload} notify={notify} />}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

// --- Utilisateurs ---------------------------------------------------------------------------------------------

function UsersPanel({ value, setValue, roles, currentUser }) {
  const users = value || [];
  const update = (i, patch) => setValue(users.map((u, k) => (k === i ? { ...u, ...patch } : u)));
  return (
    <div className="space-y-2 text-sm">
      <p className="text-xs text-slate-500">Compte courant : <strong>{currentUser}</strong>. Liste vide = poste mono-utilisateur (tous les droits).
        Les droits s'appliquent aux modules Smart Office ; les écrans de l'application de bureau (Trésorerie…) ne sont pas encore restreints.</p>
      <table className="w-full">
        <thead><tr className="text-xs text-slate-500"><th className="text-start p-1">Compte Windows</th><th className="text-start p-1">Nom</th><th className="text-start p-1">Rôle</th><th className="p-1">Actif</th><th /></tr></thead>
        <tbody>
          {users.map((u, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="p-1"><input aria-label="Compte Windows" className="border rounded px-2 py-1 w-full" value={u.login} onChange={(e) => update(i, { login: e.target.value })} /></td>
              <td className="p-1"><input aria-label="Nom" className="border rounded px-2 py-1 w-full" value={u.name || ''} onChange={(e) => update(i, { name: e.target.value })} /></td>
              <td className="p-1"><select aria-label="Rôle" className="border rounded px-2 py-1" value={u.role} onChange={(e) => update(i, { role: e.target.value })}>
                {Object.keys(roles).map((r) => <option key={r}>{r}</option>)}</select></td>
              <td className="p-1 text-center"><input type="checkbox" aria-label="Actif" checked={u.active !== false} onChange={(e) => update(i, { active: e.target.checked })} /></td>
              <td className="p-1"><button aria-label="Retirer" className="text-red-700" onClick={() => setValue(users.filter((_, k) => k !== i))}><Trash2 className="w-4 h-4" /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="bg-slate-100 rounded px-2 py-1 text-xs flex items-center gap-1"
        onClick={() => setValue([...users, users.length ? { login: '', name: '', role: 'Lecteur', active: true } : { login: currentUser, name: '', role: 'Administrateur', active: true }])}>
        <Plus className="w-3.5 h-3.5" /> Ajouter un utilisateur</button>
      <ul className="text-xs text-slate-600 list-disc ps-5">{Object.entries(roles).map(([r, d]) => <li key={r}><strong>{r}</strong> : {d}</li>)}</ul>
    </div>
  );
}

// --- Sauvegardes, SMTP, fichiers de configuration ---------------------------------------------------------------

function BackupsPanel({ notify }) {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => apiFetch('/api/settings/backups').then((r) => r.json()).then(setData).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const now = async () => {
    setBusy(true);
    const res = await apiFetch('/api/settings/backups', { method: 'POST' });
    setBusy(false);
    notify(res.ok ? 'ok' : 'error', res.ok ? `Sauvegarde créée : ${(await res.json()).name}` : await readError(res));
    load();
  };
  const restore = async (name) => {
    if (!window.confirm(`Restaurer « ${name} » ?\n\nLa restauration sera appliquée au prochain démarrage de l'application, après une sauvegarde de sécurité de la base actuelle.`)) return;
    const res = await apiFetch('/api/settings/backups/restore', json('POST', { name }));
    notify(res.ok ? 'ok' : 'error', res.ok ? 'Restauration programmée : fermez puis rouvrez l\'application.' : await readError(res));
    load();
  };
  const cancel = async () => { await apiFetch('/api/settings/backups/restore', { method: 'DELETE' }); load(); };
  if (!data) return null;
  return (
    <div className="space-y-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500">Dossier : <code>{data.folder}</code></span>
        <button className="ms-auto bg-afmi-forest text-white rounded px-3 py-1.5 text-xs flex items-center gap-1" onClick={now} disabled={busy}>
          {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <HardDriveDownload className="w-3.5 h-3.5" />} Sauvegarder maintenant</button>
      </div>
      {data.pending && (
        <div className="bg-amber-50 text-amber-900 rounded p-2 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> Restauration de {data.pending.name} programmée au prochain démarrage (demandée par {data.pending.requested_by}).
          <button className="ms-auto underline" onClick={cancel}>Annuler</button>
        </div>
      )}
      <ul className="max-h-56 overflow-auto divide-y divide-slate-100 border rounded">
        {data.items.map((b) => (
          <li key={b.name} className="flex items-center gap-2 px-2 py-1.5 text-xs">
            <span className="font-mono">{b.created_at.replace('T', ' ')}</span><Badge>{b.reason}</Badge>
            <span className="text-slate-400">{(b.size / 1048576).toFixed(1)} Mo</span>
            <button className="ms-auto text-afmi-forest underline" onClick={() => restore(b.name)}>Restaurer…</button>
          </li>
        ))}
        {data.items.length === 0 && <li className="px-2 py-2 text-xs text-slate-400">Aucune sauvegarde dans ce dossier.</li>}
      </ul>
    </div>
  );
}

function SmtpPanel({ notify }) {
  const [form, setForm] = useState(null);
  const [to, setTo] = useState('');
  useEffect(() => { apiFetch('/api/settings/smtp').then((r) => r.json()).then((d) => setForm({ ...d, password: '' })).catch(() => {}); }, []);
  if (!form) return null;
  const save = async () => {
    const res = await apiFetch('/api/settings/smtp', json('PUT', form));
    if (!res.ok) { notify('error', await readError(res)); return; }
    setForm({ ...(await res.json()), password: '' });
    notify('ok', 'Messagerie enregistrée.');
  };
  const test = async () => {
    const res = await apiFetch('/api/settings/smtp/test', json('POST', { to }));
    notify(res.ok ? 'ok' : 'error', res.ok ? `Message de test envoyé à ${(await res.json()).sent_to}.` : await readError(res));
  };
  const input = (k, label, type = 'text') => (
    <label className="text-xs flex flex-col gap-1">{label}
      <input type={type} className="border rounded px-2 py-1 text-sm" value={form[k] ?? ''} autoComplete={type === 'password' ? 'new-password' : undefined}
        placeholder={k === 'password' && form.password_configured ? 'enregistré (laisser vide pour le conserver)' : ''}
        onChange={(e) => setForm({ ...form, [k]: type === 'number' ? Number(e.target.value) : e.target.value })} /></label>
  );
  return (
    <div className="space-y-2">
      <div className="grid md:grid-cols-3 gap-2">
        {input('server', 'Serveur SMTP')}{input('port', 'Port (587 STARTTLS, 465 SSL)', 'number')}{input('username', 'Identifiant')}
        {input('password', 'Mot de passe (chiffré par DPAPI)', 'password')}{input('recipient', 'Destinataire des rapports programmés')}
        <label className="text-xs flex flex-col gap-1">Rapports programmés
          <select className="border rounded px-2 py-1 text-sm" value={form.schedule} onChange={(e) => setForm({ ...form, schedule: e.target.value })}>
            {['Aucun', 'Hebdomadaire', 'Mensuel'].map((s) => <option key={s}>{s}</option>)}</select></label>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <button className="bg-afmi-forest text-white rounded px-3 py-1.5 text-xs" onClick={save}>Enregistrer la messagerie</button>
        <input aria-label="Destinataire du test" className="border rounded px-2 py-1 text-sm" placeholder="destinataire du test" value={to} onChange={(e) => setTo(e.target.value)} />
        <button className="bg-slate-100 rounded px-3 py-1.5 text-xs flex items-center gap-1" onClick={test}><Mail className="w-3.5 h-3.5" /> Envoyer un e-mail de test</button>
      </div>
    </div>
  );
}

function AlertsPanel({ notify }) {
  const [alerts, setAlerts] = useState(null);
  useEffect(() => { apiFetch('/api/settings/notifications/preview').then((r) => r.json()).then((d) => setAlerts(d.alerts || [])).catch(() => setAlerts([])); }, []);
  const send = async () => {
    const res = await apiFetch('/api/settings/notifications/send', { method: 'POST' });
    const d = await res.json();
    notify(res.ok && d.sent ? 'ok' : 'error', res.ok ? (d.sent ? `Récapitulatif envoyé à ${d.recipients.join(', ')}.` : d.reason) : d.detail);
  };
  if (alerts === null) return null;
  return (
    <div className="border border-slate-200 rounded-lg p-3 text-sm space-y-2">
      <div className="flex items-center gap-2"><strong>Alertes en cours ({alerts.length})</strong>
        <button className="ms-auto bg-slate-100 rounded px-3 py-1.5 text-xs flex items-center gap-1" onClick={send}><Mail className="w-3.5 h-3.5" /> Envoyer le récapitulatif maintenant</button></div>
      <ul className="text-xs list-disc ps-5 max-h-40 overflow-auto">{alerts.map((a) => <li key={a.key}><strong>{a.kind}</strong> : {a.message}</li>)}</ul>
      {alerts.length === 0 && <p className="text-xs text-slate-500">Aucune alerte pour les catégories choisies.</p>}
    </div>
  );
}

function ConfigFilePanel({ name, notify, structured }) {
  const [data, setData] = useState(null);
  const [text, setText] = useState('');
  const [content, setContent] = useState(null);
  const load = useCallback(() => apiFetch(`/api/settings/files/${name}`).then((r) => r.json()).then((d) => {
    setData(d); setContent(d.content); setText(JSON.stringify(d.content, null, 2));
  }).catch(() => {}), [name]);
  useEffect(() => { load(); }, [load]);
  if (!data) return null;
  const save = async (value) => {
    let parsed = value;
    if (parsed === undefined) {
      try { parsed = JSON.parse(text); } catch (e) { notify('error', `JSON invalide : ${e.message}`); return; }
    }
    const res = await apiFetch(`/api/settings/files/${name}`, json('PUT', { content: parsed }));
    if (!res.ok) { notify('error', await readError(res)); return; }
    notify('ok', 'Configuration enregistrée (la version précédente est conservée).');
    load();
  };
  const restore = async () => {
    if (!window.confirm('Revenir à la configuration livrée avec l\'application ?')) return;
    await apiFetch(`/api/settings/files/${name}`, { method: 'DELETE' });
    notify('ok', 'Configuration d\'origine restaurée.');
    load();
  };
  return (
    <div className="border border-slate-200 rounded-lg p-3 space-y-2 text-sm">
      <div className="flex items-center gap-2"><FileJson className="w-4 h-4" /><strong>{data.description}</strong>
        {data.customized ? <Badge tone="green">personnalisée</Badge> : <Badge>d'origine</Badge>}
        {data.customized && <button className="ms-auto text-xs text-slate-500 flex items-center gap-1" onClick={restore}><RotateCcw className="w-3.5 h-3.5" /> Restaurer l'origine</button>}
      </div>
      {structured === 'checks' && content && (
        <div className="space-y-1">
          {Object.entries(content.checks || {}).map(([code, level]) => (
            <div key={code} className="flex items-center gap-2">
              <span className="flex-1">{CHECK_LABELS[code] || code}</span>
              <select aria-label={`Niveau — ${CHECK_LABELS[code] || code}`} className="border rounded px-2 py-1" value={level}
                onChange={(e) => setContent({ ...content, checks: { ...content.checks, [code]: e.target.value } })}>
                {Object.entries(LEVELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
            </div>
          ))}
          <button className="bg-afmi-forest text-white rounded px-3 py-1.5 text-xs" onClick={() => save(content)}>Enregistrer les niveaux</button>
        </div>
      )}
      {structured === 'expected' && content && (
        <div className="space-y-2">
          {content.phases.map((phase) => (
            <div key={phase}>
              <div className="font-medium text-xs">{phase}</div>
              <div className="flex flex-wrap gap-x-3 gap-y-1">
                {Object.keys(content.types).map((type) => {
                  const list = content.expected?.[phase] || [];
                  return (
                    <label key={type} className="text-xs flex items-center gap-1">
                      <input type="checkbox" checked={list.includes(type)} onChange={(e) => setContent({ ...content, expected: { ...content.expected,
                        [phase]: e.target.checked ? [...list, type] : list.filter((x) => x !== type) } })} />{type}</label>
                  );
                })}
              </div>
            </div>
          ))}
          <button className="bg-afmi-forest text-white rounded px-3 py-1.5 text-xs" onClick={() => save(content)}>Enregistrer les documents attendus</button>
        </div>
      )}
      <details>
        <summary className="cursor-pointer text-xs text-slate-500">Modifier le fichier JSON (avancé)</summary>
        <textarea aria-label={`JSON ${name}`} className="w-full font-mono text-xs border rounded p-2 mt-2" rows={14} value={text} onChange={(e) => setText(e.target.value)} />
        <button className="bg-slate-100 rounded px-3 py-1.5 text-xs" onClick={() => save(undefined)}>Valider et enregistrer le JSON</button>
      </details>
    </div>
  );
}

function ExportsInfo() {
  const [info, setInfo] = useState(null);
  useEffect(() => { apiFetch('/api/exports/engines').then((r) => r.json()).then(setInfo).catch(() => {}); }, []);
  if (!info) return null;
  return (
    <div className="text-xs text-slate-600 bg-slate-50 rounded p-2 space-y-1">
      <div>Moteurs détectés : navigateur {info.pdf.browser ? '✔' : '✘'} · LibreOffice {info.pdf.libreoffice ? '✔ (PDF/A disponible)' : '✘ (PDF/A indisponible)'}</div>
      <div>Exemples avec les réglages enregistrés : <code>{info.examples.report}</code> · <code>{info.examples.document}</code></div>
    </div>
  );
}

// --- Vue ------------------------------------------------------------------------------------------------------

export default function SettingsView({ onNavigate }) {
  const { setLanguage } = useLanguage();
  const [snap, setSnap] = useState(null);
  const [section, setSection] = useState('association');
  const [query, setQuery] = useState('');
  const [edits, setEdits] = useState({});
  const [me, setMe] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef(null);

  const notify = (kind, text) => setMessage({ kind, text });
  const load = useCallback(async () => {
    const res = await apiFetch('/api/settings/registry');
    if (!res.ok) { notify('error', await readError(res)); return; }
    setSnap(await res.json());
    apiFetch('/api/settings/me').then((r) => r.json()).then(setMe).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const fields = useMemo(() => (snap ? snap.sections.flatMap((s) => s.fields.map((f) => ({ ...f, sectionLabel: s.label }))) : []), [snap]);
  const value = (key) => (key in edits ? edits[key] : fields.find((f) => f.key === key)?.value);
  const setValue = (key, v) => setEdits((e) => ({ ...e, [key]: v }));
  const values = useMemo(() => Object.fromEntries(fields.map((f) => [f.key, key_in(edits, f.key) ? edits[f.key] : f.value])), [fields, edits]);
  const readOnly = me && !me.single_user && me.role !== 'Administrateur';

  const save = async () => {
    if (!Object.keys(edits).length) return;
    setBusy(true);
    const res = await apiFetch('/api/settings/values', json('PUT', { values: edits }));
    setBusy(false);
    if (!res.ok) { notify('error', await readError(res)); return; }
    if ('ui.language' in edits) setLanguage(edits['ui.language']);
    applyAppearance(edits);
    setEdits({});
    notify('ok', 'Paramètres enregistrés.');
    load();
  };
  const reset = async (body, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return;
    const res = await apiFetch('/api/settings/reset', json('POST', body));
    notify(res.ok ? 'ok' : 'error', res.ok ? `${(await res.json()).reset} paramètre(s) remis par défaut.` : await readError(res));
    setEdits({});
    load();
  };
  const importFile = async (file) => {
    let data;
    try { data = JSON.parse(await file.text()); } catch { notify('error', 'Fichier JSON illisible.'); return; }
    const check = await apiFetch('/api/settings/import', json('POST', { data, dry_run: true }));
    if (!check.ok) { notify('error', await readError(check)); return; }
    const c = await check.json();
    if (!window.confirm(`Importer ${c.values} paramètre(s) et ${c.files} fichier(s) de configuration ?${c.secrets_skipped.length ? `\n${c.secrets_skipped.length} clé(s) d'API ignorée(s) : à ressaisir.` : ''}`)) return;
    const res = await apiFetch('/api/settings/import', json('POST', { data }));
    notify(res.ok ? 'ok' : 'error', res.ok ? 'Paramètres importés.' : await readError(res));
    load();
  };

  if (!snap) {
    return <div className="text-sm text-slate-500 flex items-center gap-2">{message ? message.text : <><Loader2 className="w-4 h-4 animate-spin" />Chargement des paramètres…</>}</div>;
  }
  const q = norm(query.trim());
  const visible = q
    ? fields.filter((f) => [f.label, f.help, f.key, f.sectionLabel, f.group].some((x) => norm(x).includes(q)))
    : fields.filter((f) => f.section === section);
  const special = (id) => !q && section === id;
  const generic = visible.filter((f) => f.type !== 'secret' && f.type !== 'users' && !(f.section === 'ia' && /^ai\.(tasks|providers)\./.test(f.key)));
  const secrets = visible.filter((f) => f.type === 'secret' && q);
  const groups = [...new Set(generic.map((f) => (q ? f.sectionLabel : f.group || '')))];
  const dirtyCount = Object.keys(edits).length;

  return (
    <div className="space-y-4" dir="auto">
      <div className="flex flex-wrap items-end gap-3">
        <div className="me-auto">
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2"><Settings className="w-6 h-6" />Paramètres</h1>
          <p className="text-sm text-slate-500">Réglages de l'association, de la comptabilité, des banques, de l'IA, des utilisateurs et des sauvegardes.
            {me && <> Connecté : <strong>{me.user}</strong> ({me.single_user ? 'poste mono-utilisateur' : me.role}).</>}</p>
        </div>
        <button className="bg-slate-100 rounded px-3 py-1.5 text-sm flex items-center gap-1" onClick={() => apiDownload('/api/settings/export').then((n) => notify('ok', `Exporté : ${n} (sans les clés d'API).`)).catch((e) => notify('error', e.message))}>
          <Download className="w-4 h-4" /> Exporter (JSON)</button>
        <button className="bg-slate-100 rounded px-3 py-1.5 text-sm flex items-center gap-1 disabled:opacity-50" disabled={readOnly} onClick={() => fileInput.current?.click()}>
          <Upload className="w-4 h-4" /> Importer</button>
        <input ref={fileInput} type="file" accept="application/json,.json" className="hidden" onChange={(e) => { if (e.target.files[0]) importFile(e.target.files[0]); e.target.value = ''; }} />
        <button className="bg-slate-100 rounded px-3 py-1.5 text-sm flex items-center gap-1 disabled:opacity-50" disabled={readOnly}
          onClick={() => reset({ all: true }, 'Remettre TOUS les paramètres à leur valeur par défaut ?\n(Les clés d\'API, utilisateurs compris, sont supprimées ; un export préalable est conseillé.)')}>
          <RotateCcw className="w-4 h-4" /> Tout restaurer</button>
      </div>

      {readOnly && <div className="bg-amber-50 text-amber-900 rounded px-3 py-2 text-sm flex items-center gap-2"><ShieldCheck className="w-4 h-4" />Consultation seule : seul un administrateur peut modifier les paramètres.</div>}
      {message && (
        <div role="status" className={`rounded px-3 py-2 text-sm flex items-center gap-2 ${message.kind === 'error' ? 'bg-red-50 text-red-800' : 'bg-emerald-50 text-emerald-800'}`}>
          {message.kind === 'error' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}{message.text}
          <button className="ms-auto text-xs underline" onClick={() => setMessage(null)}>fermer</button>
        </div>
      )}

      <div className="grid grid-cols-12 gap-4">
        <nav className="col-span-12 md:col-span-3 space-y-2" aria-label="Sections des paramètres">
          <label className="flex items-center gap-2 border border-slate-200 rounded-lg px-2 py-1.5 bg-white">
            <Search className="w-4 h-4 text-slate-400" />
            <input aria-label="Rechercher un paramètre" className="outline-none text-sm flex-1" placeholder="Rechercher un paramètre…" value={query} onChange={(e) => setQuery(e.target.value)} />
          </label>
          <ul className="bg-white border border-slate-200 rounded-lg divide-y divide-slate-100">
            {snap.sections.map((s) => (
              <li key={s.id}>
                <button className={`w-full text-start px-3 py-2 text-sm ${!q && section === s.id ? 'bg-afmi-forest text-white' : 'hover:bg-slate-50'}`} onClick={() => { setSection(s.id); setQuery(''); }}>
                  <div className="font-medium">{s.label}</div>
                  <div className={`text-[11px] ${!q && section === s.id ? 'text-emerald-100' : 'text-slate-400'}`}>{s.description}</div>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <section className="col-span-12 md:col-span-9 bg-white border border-slate-200 rounded-xl p-4 space-y-4">
          <fieldset disabled={readOnly} className="space-y-4">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-slate-800">{q ? `Résultats pour « ${query} » (${visible.length})` : snap.sections.find((s) => s.id === section)?.label}</h2>
              {!q && <button className="ms-auto text-xs text-slate-500 flex items-center gap-1" onClick={() => reset({ section }, 'Remettre cette section à ses valeurs par défaut ?')}>
                <RotateCcw className="w-3.5 h-3.5" /> Restaurer la section</button>}
            </div>

            {special('utilisateurs') && <UsersPanel value={value('security.users')} setValue={(v) => setValue('security.users', v)} roles={snap.roles} currentUser={snap.current_user} />}
            {special('sauvegardes') && <BackupsPanel notify={notify} />}
            {special('notifications') && <SmtpPanel notify={notify} />}
            {special('notifications') && <AlertsPanel notify={notify} />}
            {special('exports') && <ExportsInfo />}
            {special('chartes') && (
              <p className="text-sm">Les chartes graphiques (couleurs, polices, logos, en-têtes, mentions) et les modèles se gèrent dans
                <button className="text-afmi-forest underline ms-1" onClick={() => onNavigate?.('charts')}>Chartes et modèles</button>.</p>
            )}

            {groups.map((g) => (
              <div key={g || 'main'}>
                {special('ia') && g === 'Prompts système' && <AiPanel fields={visible} values={values} setValue={setValue} reload={load} notify={notify} />}
                {g && <h3 className="font-semibold text-sm text-slate-600 mt-2">{g}</h3>}
                {generic.filter((f) => (q ? f.sectionLabel : f.group || '') === g).map((f) => (
                  <FieldRow key={f.key} field={f} value={value(f.key)} dirty={f.key in edits} onChange={(v) => setValue(f.key, v)}
                    onReset={() => reset({ keys: [f.key] })} />
                ))}
              </div>
            ))}
            {secrets.map((f) => <SecretRow key={f.key} field={f} onSaved={load} notify={notify} />)}

            {special('rapports') && (
              <div className="space-y-3">
                <ConfigFilePanel name="financial_report_layout" notify={notify} structured="checks" />
                <ConfigFilePanel name="lifecycle_config" notify={notify} structured="expected" />
              </div>
            )}
            {special('banques') && <ConfigFilePanel name="bank_templates" notify={notify} />}
          </fieldset>

          {dirtyCount > 0 && (
            <div className="sticky bottom-0 bg-white border-t pt-3 flex items-center gap-2">
              <span className="text-sm text-amber-800">{dirtyCount} modification(s) non enregistrée(s)</span>
              <button className="ms-auto text-sm text-slate-500" onClick={() => setEdits({})}>Annuler</button>
              <button aria-label="Enregistrer les paramètres" className="bg-afmi-forest text-white rounded px-4 py-2 text-sm flex items-center gap-2" onClick={save} disabled={busy}>
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Enregistrer</button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

/** Applique les réglages d'apparence à la page (aussi appelé au démarrage par App.jsx). */
export function applyAppearance(values) {
  if (values['ui.font_scale']) document.documentElement.style.fontSize = `${values['ui.font_scale']}%`;
  const c = values['ui.primary_color'];
  if (c && /^#[0-9a-f]{6}$/i.test(c)) {
    const rgb = [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16)).join(' ');
    document.documentElement.style.setProperty('--afmi-forest-rgb', rgb);
  }
}

function key_in(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj, key);
}
