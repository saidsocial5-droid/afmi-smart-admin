import React, { useEffect, useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';

// Lot 11 — glisser-déposer de documents et de photos sur TOUT écran de Smart Office : les fichiers déposés sont remis au
// champ « Choisir des fichiers » de l'écran (celui de la zone survolée, sinon le seul visible), comme s'ils avaient été
// choisis à la main. Les zones de dépôt qui gèrent déjà le dépôt (import de dossier…) gardent leur comportement.

function visible(input) {
  const box = input.offsetParent ? input : input.closest('label') || input.parentElement;
  return !!box && box.offsetParent !== null && !input.disabled;
}

function accepts(input, file) {
  const acc = (input.getAttribute('accept') || '').toLowerCase().split(',').map((x) => x.trim()).filter(Boolean);
  if (!acc.length) return true;
  const name = file.name.toLowerCase();
  return acc.some((a) => (a.startsWith('.') ? name.endsWith(a) : a.endsWith('/*') ? file.type.startsWith(a.slice(0, -1)) : file.type === a));
}

function pickInput(target) {
  const inputs = Array.from(document.querySelectorAll('input[type=file]')).filter(visible);
  if (!inputs.length) return null;
  let node = target instanceof Element ? target : null;
  while (node && node !== document.body) {                     // champ de la section survolée
    const inside = inputs.find((i) => node.contains(i));
    if (inside) return inside;
    node = node.parentElement;
  }
  return inputs[0];
}

export default function GlobalDrop() {
  const [over, setOver] = useState(false);
  const [toast, setToast] = useState('');
  const depth = useRef(0);

  useEffect(() => {
    const hasFiles = (e) => Array.from(e.dataTransfer?.types || []).includes('Files');
    const enter = (e) => { if (hasFiles(e)) { depth.current += 1; setOver(true); } };
    const leave = (e) => { if (hasFiles(e)) { depth.current = Math.max(0, depth.current - 1); if (!depth.current) setOver(false); } };
    const overFn = (e) => { if (hasFiles(e)) e.preventDefault(); };
    const drop = (e) => {
      depth.current = 0;
      setOver(false);
      if (!hasFiles(e) || e.defaultPrevented) return;             // zone de dépôt propre à l'écran : déjà traité
      e.preventDefault();
      const input = pickInput(e.target);
      if (!input) {
        setToast('Cet écran n\'importe pas de fichier : ouvrez Documents, Relevés bancaires, Photos ou Importer un dossier.');
        return;
      }
      let files = Array.from(e.dataTransfer.files).filter((f) => accepts(input, f));
      if (!files.length) { setToast('Format non accepté par cet écran.'); return; }
      if (!input.multiple) files = files.slice(0, 1);
      const dt = new DataTransfer();
      files.forEach((f) => dt.items.add(f));
      input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      setToast(`${files.length} fichier(s) ajouté(s).`);
    };
    window.addEventListener('dragenter', enter);
    window.addEventListener('dragleave', leave);
    window.addEventListener('dragover', overFn);
    window.addEventListener('drop', drop);
    return () => {
      window.removeEventListener('dragenter', enter);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('dragover', overFn);
      window.removeEventListener('drop', drop);
    };
  }, []);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(''), 5000); return () => clearTimeout(t); } }, [toast]);

  return (
    <>
      {over && (
        <div className="fixed inset-0 z-[80] pointer-events-none bg-afmi-forest/10 border-4 border-dashed border-afmi-forest flex items-center justify-center">
          <div className="bg-white rounded-xl shadow px-6 py-4 flex items-center gap-3 text-afmi-forest font-semibold">
            <UploadCloud className="w-7 h-7" />Déposez les documents ou les photos ici
          </div>
        </div>
      )}
      {toast && <div role="status" className="fixed bottom-16 start-1/2 -translate-x-1/2 z-[70] bg-slate-800 text-white rounded-lg px-4 py-2 text-sm">{toast}</div>}
    </>
  );
}
