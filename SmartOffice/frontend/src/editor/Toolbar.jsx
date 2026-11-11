import React, { useRef } from 'react';
import {
  Undo2, Redo2, Bold, Italic, Underline as U, Strikethrough, Subscript as Sub, Superscript as Sup, AlignLeft, AlignCenter,
  AlignRight, AlignJustify, List, ListOrdered, Table2, Image as ImageIcon, SeparatorHorizontal, Columns2, MessageSquarePlus,
  FileText, Highlighter, Pilcrow, Quote,
} from 'lucide-react';
import { apiFetch } from '../apiClient';
import { FIELD_LABELS } from './FieldView';
import { BLOCK_LABELS } from './DynamicBlockView';

const FONTS = ['Calibri', 'Arial', 'Times New Roman', 'Cambria', 'Georgia', 'Verdana', 'Tahoma', 'Noto Naskh Arabic', 'Amiri'];
const SIZES = ['8pt', '9pt', '10pt', '11pt', '12pt', '14pt', '16pt', '18pt', '20pt', '24pt', '28pt', '36pt'];

function Btn({ onClick, active, title, children, disabled }) {
  return (
    <button type="button" title={title} aria-label={title} disabled={disabled}
            onMouseDown={(e) => e.preventDefault()} onClick={onClick}
            className={`tb-btn ${active ? 'is-active' : ''}`}>
      {children}
    </button>
  );
}

const Sep = () => <span className="tb-sep" />;

export default function Toolbar({ editor, onComment, trackChanges, onToggleTrack }) {
  const fileInput = useRef(null);
  if (!editor) return null;
  const c = () => editor.chain().focus();
  const blockType = editor.isActive('heading', { level: 1 }) ? 'h1' : editor.isActive('heading', { level: 2 }) ? 'h2'
    : editor.isActive('heading', { level: 3 }) ? 'h3' : 'p';
  const inTable = editor.isActive('table');

  const insertImage = async (file) => {
    const form = new FormData();
    form.append('file', file);
    const res = await apiFetch('/api/files/images', { method: 'POST', body: form });
    if (res.ok) {
      const { url } = await res.json();
      c().setImage({ src: url, alt: file.name }).run();
    } else {
      window.alert((await res.json()).detail || 'Image refusée.');
    }
  };

  return (
    <div className="editor-toolbar no-print" role="toolbar" aria-label="Mise en forme">
      <Btn title="Annuler" onClick={() => c().undo().run()} disabled={!editor.can().undo()}><Undo2 size={15} /></Btn>
      <Btn title="Rétablir" onClick={() => c().redo().run()} disabled={!editor.can().redo()}><Redo2 size={15} /></Btn>
      <Sep />
      <select aria-label="Style de paragraphe" value={blockType} onChange={(e) => {
        const v = e.target.value;
        if (v === 'p') c().setParagraph().run(); else c().setHeading({ level: Number(v[1]) }).run();
      }}>
        <option value="p">Paragraphe</option><option value="h1">Titre 1</option><option value="h2">Titre 2</option><option value="h3">Titre 3</option>
      </select>
      <select aria-label="Police" value={editor.getAttributes('textStyle').fontFamily || ''} onChange={(e) => (e.target.value ? c().setFontFamily(e.target.value).run() : c().unsetFontFamily().run())}>
        <option value="">Police de la charte</option>
        {FONTS.map((f) => <option key={f} value={f}>{f}</option>)}
      </select>
      <select aria-label="Taille" value={editor.getAttributes('textStyle').fontSize || ''} onChange={(e) => (e.target.value ? c().setFontSize(e.target.value).run() : c().unsetFontSize().run())}>
        <option value="">Taille</option>
        {SIZES.map((s) => <option key={s} value={s}>{s.replace('pt', '')}</option>)}
      </select>
      <Sep />
      <Btn title="Gras" active={editor.isActive('bold')} onClick={() => c().toggleBold().run()}><Bold size={15} /></Btn>
      <Btn title="Italique" active={editor.isActive('italic')} onClick={() => c().toggleItalic().run()}><Italic size={15} /></Btn>
      <Btn title="Souligné" active={editor.isActive('underline')} onClick={() => c().toggleUnderline().run()}><U size={15} /></Btn>
      <Btn title="Barré" active={editor.isActive('strike')} onClick={() => c().toggleStrike().run()}><Strikethrough size={15} /></Btn>
      <Btn title="Indice" active={editor.isActive('subscript')} onClick={() => c().toggleSubscript().run()}><Sub size={15} /></Btn>
      <Btn title="Exposant" active={editor.isActive('superscript')} onClick={() => c().toggleSuperscript().run()}><Sup size={15} /></Btn>
      <label className="tb-color" title="Couleur du texte">A
        <input type="color" aria-label="Couleur du texte" value={editor.getAttributes('textStyle').color || '#1f2937'} onChange={(e) => c().setColor(e.target.value).run()} />
      </label>
      <Btn title="Surligner" active={editor.isActive('highlight')} onClick={() => c().toggleHighlight({ color: '#FEF08A' }).run()}><Highlighter size={15} /></Btn>
      <Sep />
      <Btn title="Aligner à gauche" active={editor.isActive({ textAlign: 'left' })} onClick={() => c().setTextAlign('left').run()}><AlignLeft size={15} /></Btn>
      <Btn title="Centrer" active={editor.isActive({ textAlign: 'center' })} onClick={() => c().setTextAlign('center').run()}><AlignCenter size={15} /></Btn>
      <Btn title="Aligner à droite" active={editor.isActive({ textAlign: 'right' })} onClick={() => c().setTextAlign('right').run()}><AlignRight size={15} /></Btn>
      <Btn title="Justifier" active={editor.isActive({ textAlign: 'justify' })} onClick={() => c().setTextAlign('justify').run()}><AlignJustify size={15} /></Btn>
      <Btn title="Gauche à droite (français)" active={editor.isActive({ dir: 'ltr' })} onClick={() => c().setTextDirection('ltr').run()}>LTR</Btn>
      <Btn title="Droite à gauche (arabe)" active={editor.isActive({ dir: 'rtl' })} onClick={() => c().setTextDirection('rtl').run()}><Pilcrow size={15} /> RTL</Btn>
      <Sep />
      <Btn title="Liste à puces" active={editor.isActive('bulletList')} onClick={() => c().toggleBulletList().run()}><List size={15} /></Btn>
      <Btn title="Liste numérotée" active={editor.isActive('orderedList')} onClick={() => c().toggleOrderedList().run()}><ListOrdered size={15} /></Btn>
      <Btn title="Citation" active={editor.isActive('blockquote')} onClick={() => c().toggleBlockquote().run()}><Quote size={15} /></Btn>
      <Sep />
      <Btn title="Insérer un tableau" onClick={() => c().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}><Table2 size={15} /></Btn>
      {inTable && (
        <span className="tb-group" aria-label="Tableau">
          <Btn title="Ligne au-dessous" onClick={() => c().addRowAfter().run()}>+L</Btn>
          <Btn title="Colonne à droite" onClick={() => c().addColumnAfter().run()}>+C</Btn>
          <Btn title="Supprimer la ligne" onClick={() => c().deleteRow().run()}>−L</Btn>
          <Btn title="Supprimer la colonne" onClick={() => c().deleteColumn().run()}>−C</Btn>
          <Btn title="Fusionner ou scinder les cellules" onClick={() => c().mergeOrSplit().run()}>⊞</Btn>
          <Btn title="Ligne d'en-tête" onClick={() => c().toggleHeaderRow().run()}>En-tête</Btn>
          <label className="tb-color" title="Trame de la cellule">▦
            <input type="color" aria-label="Trame de la cellule" onChange={(e) => c().setCellAttribute('backgroundColor', e.target.value).run()} />
          </label>
          <Btn title="Supprimer le tableau" onClick={() => c().deleteTable().run()}>✕</Btn>
        </span>
      )}
      <Btn title="Insérer une image" onClick={() => fileInput.current?.click()}><ImageIcon size={15} /></Btn>
      <input ref={fileInput} type="file" accept="image/*" hidden onChange={(e) => { if (e.target.files?.[0]) insertImage(e.target.files[0]); e.target.value = ''; }} />
      <Btn title="Saut de page" onClick={() => c().insertPageBreak().run()}><SeparatorHorizontal size={15} /></Btn>
      <Btn title={editor.isActive('columns') ? 'Retirer les colonnes' : 'Deux colonnes'} active={editor.isActive('columns')}
           onClick={() => (editor.isActive('columns') ? c().unwrapColumns().run() : c().wrapInColumns(2).run())}><Columns2 size={15} /></Btn>
      <Btn title="Note de bas de page" onClick={() => { const t = window.prompt('Texte de la note :'); if (t) c().insertFootnote(t).run(); }}>¹</Btn>
      <Btn title="Table des matières" onClick={() => c().insertTableOfContents().run()}><FileText size={15} /></Btn>
      <select aria-label="Insérer un champ" value="" onChange={(e) => { if (e.target.value) c().insertField(e.target.value).run(); }}>
        <option value="">Champ…</option>
        {Object.entries(FIELD_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <select aria-label="Insérer un bloc de données" value="" onChange={(e) => { if (e.target.value) c().insertDynamicBlock({ kind: e.target.value }).run(); }}>
        <option value="">Bloc de données…</option>
        {Object.entries(BLOCK_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
      </select>
      <Sep />
      <Btn title="Commenter la sélection" onClick={onComment}><MessageSquarePlus size={15} /></Btn>
      <Btn title="Mode révision (suivi des modifications)" active={trackChanges} onClick={onToggleTrack}>Révision</Btn>
      {trackChanges !== undefined && (
        <span className="tb-group" aria-label="Modifications suivies">
          <Btn title="Accepter la modification sous le curseur" onClick={() => c().acceptChangeAtSelection().run()}>✓</Btn>
          <Btn title="Refuser la modification sous le curseur" onClick={() => c().rejectChangeAtSelection().run()}>✗</Btn>
          <Btn title="Tout accepter" onClick={() => c().acceptAllChanges().run()}>✓✓</Btn>
          <Btn title="Tout refuser" onClick={() => c().rejectAllChanges().run()}>✗✗</Btn>
        </span>
      )}
    </div>
  );
}
