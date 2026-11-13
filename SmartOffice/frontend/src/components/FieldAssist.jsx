import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Sparkles, Mic, Loader2, Undo2 } from 'lucide-react';
import { apiFetch } from '../apiClient';
import { useLanguage } from '../context/LanguageContext';

// Lot 11 — assistant de rédaction et dictée sur TOUS les champs de saisie de Smart Office, sans modifier chaque écran :
// une petite barre apparaît au-dessus du champ qui a le focus (✨ IA, 🎤 dictée). Un champ peut s'en exclure avec
// l'attribut data-no-assist. L'éditeur de documents (TipTap) a son propre assistant et n'est pas concerné.

const ACTIONS = [
  ['corriger', 'Corriger (orthographe, grammaire)'],
  ['reformuler', 'Reformuler (style institutionnel)'],
  ['enrichir', 'Enrichir / développer'],
  ['generer', 'Générer le contenu du champ'],
  ['resumer', 'Résumer'],
  ['traduire:ar', 'Traduire en arabe'],
  ['traduire:fr', 'Traduire en français'],
  ['traduire:en', 'Traduire en anglais'],
];
const TEXT_TYPES = new Set(['text', 'search', '', 'email', 'url']);

function eligible(el) {
  if (!el || el.closest?.('[data-no-assist]') || el.readOnly || el.disabled) return false;
  if (el.tagName === 'TEXTAREA') return true;
  if (el.tagName !== 'INPUT' || !TEXT_TYPES.has((el.getAttribute('type') || '').toLowerCase())) return false;
  return el.getBoundingClientRect().width >= 140;            // pas sur les petites cases (codes, montants)
}

function labelOf(el) {
  const aria = el.getAttribute('aria-label') || el.getAttribute('placeholder');
  if (aria) return aria;
  if (el.id) {
    const l = document.querySelector(`label[for="${el.id}"]`);
    if (l) return l.textContent.trim();
  }
  const wrap = el.closest('label');
  if (wrap) return wrap.textContent.replace(el.value || '', '').trim().slice(0, 80);
  let prev = el.previousElementSibling;
  while (prev && !prev.textContent.trim()) prev = prev.previousElementSibling;
  return prev ? prev.textContent.trim().slice(0, 80) : 'texte';
}

function setValue(el, value) {
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);   // champs contrôlés par React
  el.dispatchEvent(new Event('input', { bubbles: true }));
}

export default function FieldAssist() {
  const { language } = useLanguage();
  const [field, setField] = useState(null);
  const [rect, setRect] = useState(null);
  const [menu, setMenu] = useState(false);
  const [busy, setBusy] = useState('');
  const [toast, setToast] = useState(null);           // { text, undo?: () => void, error?: bool }
  const recog = useRef(null);
  const hideTimer = useRef(null);

  const place = useCallback((el) => { if (el && document.contains(el)) setRect(el.getBoundingClientRect()); }, []);

  useEffect(() => {
    const onFocus = (e) => {
      if (eligible(e.target)) {
        clearTimeout(hideTimer.current);
        setField(e.target);
        place(e.target);
      }
    };
    const onBlur = () => {
      hideTimer.current = setTimeout(() => { if (!document.activeElement || !eligible(document.activeElement)) { setField(null); setMenu(false); } }, 200);
    };
    const onMove = () => setField((f) => { if (f) place(f); return f; });
    document.addEventListener('focusin', onFocus);
    document.addEventListener('focusout', onBlur);
    window.addEventListener('scroll', onMove, true);
    window.addEventListener('resize', onMove);
    return () => {
      document.removeEventListener('focusin', onFocus);
      document.removeEventListener('focusout', onBlur);
      window.removeEventListener('scroll', onMove, true);
      window.removeEventListener('resize', onMove);
    };
  }, [place]);

  useEffect(() => { if (toast && !toast.sticky) { const t = setTimeout(() => setToast(null), toast.undo ? 9000 : 5000); return () => clearTimeout(t); } }, [toast]);

  const run = async (key) => {
    const el = field;
    if (!el) return;
    setMenu(false);
    const [action, target] = key.split(':');
    const old = el.value;
    const s = el.selectionStart ?? 0;
    const e2 = el.selectionEnd ?? 0;
    const hasSel = e2 > s;
    const text = hasSel ? old.slice(s, e2) : old;
    const context = [document.title, document.querySelector('h1')?.textContent].filter(Boolean).join(' — ');
    setBusy(action);
    try {
      const res = await apiFetch('/api/assist/text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, text, field: labelOf(el), context, target: target || '', language: '' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Erreur ${res.status}`);
      const next = hasSel ? old.slice(0, s) + data.text + old.slice(e2) : (action === 'generer' && old.trim() ? `${old.trim()}\n${data.text}` : data.text);
      setValue(el, next);
      el.focus();
      setToast({ text: `Texte ${action === 'corriger' ? 'corrigé' : 'modifié'} par ${data.engine}.`, undo: () => { setValue(el, old); setToast(null); } });
    } catch (err) {
      setToast({ text: err.message, error: true });
    } finally {
      setBusy('');
    }
  };

  const dictate = () => {
    const el = field;
    if (!el) return;
    el.focus();
    if (window.chrome?.webview) {             // dans l'application de bureau : dictée vocale de Windows (Win + H)
      window.chrome.webview.postMessage(JSON.stringify({ type: 'dictate' }));
      setToast({ text: 'Dictée Windows ouverte : parlez, le texte s\'écrit dans le champ. Recliquez sur le micro de Windows pour arrêter.' });
      return;
    }
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setToast({ text: 'Dictée : sous Windows, appuyez sur la touche Windows + H dans le champ.', error: true });
      return;
    }
    if (recog.current) { recog.current.stop(); return; }
    const r = new SR();
    r.lang = language === 'ar' ? 'ar-MA' : language === 'en' ? 'en-US' : 'fr-FR';
    r.interimResults = false;
    r.continuous = true;
    r.onresult = (ev) => {
      const said = Array.from(ev.results).slice(ev.resultIndex).map((x) => x[0].transcript).join(' ').trim();
      if (!said) return;
      const pos = el.selectionStart ?? el.value.length;
      const before = el.value.slice(0, pos);
      setValue(el, `${before}${before && !/\s$/.test(before) ? ' ' : ''}${said}${el.value.slice(pos)}`);
    };
    r.onend = () => { recog.current = null; setBusy(''); };
    r.onerror = (ev) => setToast({ text: `Dictée interrompue (${ev.error}).`, error: true });
    recog.current = r;
    setBusy('dictate');
    r.start();
    setToast({ text: 'Parlez… recliquez sur le micro pour arrêter.' });
  };

  const keep = (e) => e.preventDefault();          // garder le focus dans le champ
  const top = rect ? Math.max(4, rect.top - 30) : 0;
  const left = rect ? Math.min(window.innerWidth - 90, Math.max(4, rect.right - 84)) : 0;

  return (
    <>
      {field && rect && (
        <div data-no-assist className="fixed z-[60] flex items-center gap-1 bg-white border border-slate-200 shadow rounded-full px-1 py-0.5"
          style={{ top, left }} onMouseDown={keep}>
          <button type="button" title="Assistant IA : corriger, reformuler, enrichir, générer, traduire" aria-label="Assistant IA du champ"
            className="p-1 rounded-full hover:bg-amber-50 text-afmi-gold" onClick={() => setMenu((m) => !m)}>
            {busy && busy !== 'dictate' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          </button>
          <button type="button" title="Dicter au micro" aria-label="Dicter au micro"
            className={`p-1 rounded-full hover:bg-emerald-50 ${busy === 'dictate' ? 'text-red-600 animate-pulse' : 'text-afmi-forest'}`} onClick={dictate}>
            <Mic className="w-4 h-4" />
          </button>
          {menu && (
            <div className="absolute top-7 end-0 w-60 bg-white border rounded-lg shadow-lg py-1 text-sm">
              {ACTIONS.map(([k, l]) => (
                <button key={k} type="button" className="block w-full text-start px-3 py-1.5 hover:bg-slate-50" onClick={() => run(k)}>{l}</button>
              ))}
              <div className="px-3 pt-1 text-[11px] text-slate-400 border-t">S'applique à la sélection, sinon à tout le champ.</div>
            </div>
          )}
        </div>
      )}
      {toast && (
        <div data-no-assist role="status" className={`fixed bottom-4 start-1/2 -translate-x-1/2 z-[70] rounded-lg shadow px-4 py-2 text-sm flex items-center gap-3 ${toast.error ? 'bg-red-700 text-white' : 'bg-slate-800 text-white'}`}>
          <span>{toast.text}</span>
          {toast.undo && <button type="button" className="flex items-center gap-1 underline" onMouseDown={keep} onClick={toast.undo}><Undo2 className="w-3.5 h-3.5" />Annuler</button>}
        </div>
      )}
    </>
  );
}
