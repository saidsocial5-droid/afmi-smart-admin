// Extensions TipTap propres à AFMI Smart Admin (Lot 4).
import { Extension, Mark, Node, mergeAttributes } from '@tiptap/core';
import { Plugin, PluginKey, TextSelection } from '@tiptap/pm/state';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import { ReactNodeViewRenderer } from '@tiptap/react';
import DynamicBlockView from './DynamicBlockView';
import TocView from './TocView';
import FieldView from './FieldView';

// Taille de police (attribut de textStyle)
export const FontSize = Extension.create({
  name: 'fontSize',
  addGlobalAttributes() {
    return [{
      types: ['textStyle'],
      attributes: {
        fontSize: {
          default: null,
          parseHTML: (el) => el.style.fontSize || null,
          renderHTML: (a) => (a.fontSize ? { style: `font-size: ${a.fontSize}` } : {}),
        },
      },
    }];
  },
  addCommands() {
    return {
      setFontSize: (size) => ({ chain }) => chain().setMark('textStyle', { fontSize: size }).run(),
      unsetFontSize: () => ({ chain }) => chain().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run(),
    };
  },
});

// Sens d'écriture par paragraphe (arabe RTL, documents mixtes français/arabe)
export const TextDirection = Extension.create({
  name: 'textDirection',
  addGlobalAttributes() {
    return [{
      types: ['paragraph', 'heading', 'listItem', 'tableCell', 'tableHeader'],
      attributes: {
        dir: {
          default: null,
          parseHTML: (el) => el.getAttribute('dir'),
          renderHTML: (a) => (a.dir ? { dir: a.dir } : {}),
        },
      },
    }];
  },
  addCommands() {
    return {
      setTextDirection: (dir) => ({ commands }) =>
        ['paragraph', 'heading'].map((t) => commands.updateAttributes(t, { dir })).some(Boolean),
    };
  },
});

// Trame (couleur de fond) des cellules de tableau
const cellBackground = {
  backgroundColor: {
    default: null,
    parseHTML: (el) => el.style.backgroundColor || null,
    renderHTML: (a) => (a.backgroundColor ? { style: `background-color: ${a.backgroundColor}` } : {}),
  },
};
export const ShadedTableCell = TableCell.extend({ addAttributes() { return { ...this.parent?.(), ...cellBackground }; } });
export const ShadedTableHeader = TableHeader.extend({ addAttributes() { return { ...this.parent?.(), ...cellBackground }; } });

// Saut de page
export const PageBreak = Node.create({
  name: 'pageBreak',
  group: 'block',
  atom: true,
  parseHTML() { return [{ tag: 'div[data-page-break]' }]; },
  renderHTML() { return ['div', { 'data-page-break': 'true', class: 'page-break' }]; },
  addCommands() {
    return { insertPageBreak: () => ({ commands }) => commands.insertContent({ type: this.name }) };
  },
});

// Bloc en colonnes (2 ou 3)
export const Columns = Node.create({
  name: 'columns',
  group: 'block',
  content: 'block+',
  defining: true,
  addAttributes() { return { count: { default: 2, parseHTML: (el) => Number(el.getAttribute('data-columns')) || 2 } }; },
  parseHTML() { return [{ tag: 'div[data-columns]' }]; },
  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes({ 'data-columns': HTMLAttributes.count, class: `columns columns-${HTMLAttributes.count}` }), 0];
  },
  addCommands() {
    return {
      wrapInColumns: (count = 2) => ({ commands }) => commands.wrapIn(this.name, { count }),
      unwrapColumns: () => ({ commands }) => commands.lift(this.name),
    };
  },
});

// Note de bas de page (texte stocké dans l'attribut ; numérotée automatiquement)
export const Footnote = Node.create({
  name: 'footnote',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() { return { text: { default: '' } }; },
  parseHTML() { return [{ tag: 'sup[data-footnote]', getAttrs: (el) => ({ text: el.getAttribute('data-footnote') }) }]; },
  renderHTML({ HTMLAttributes }) {
    return ['sup', { 'data-footnote': HTMLAttributes.text, class: 'footnote-ref', title: HTMLAttributes.text }];
  },
  addCommands() {
    return { insertFootnote: (text) => ({ commands }) => commands.insertContent({ type: this.name, attrs: { text } }) };
  },
});

// Table des matières automatique (calculée à partir des titres)
export const TableOfContents = Node.create({
  name: 'tableOfContents',
  group: 'block',
  atom: true,
  parseHTML() { return [{ tag: 'div[data-toc]' }]; },
  renderHTML() { return ['div', { 'data-toc': 'true', class: 'toc' }]; },
  addNodeView() { return ReactNodeViewRenderer(TocView); },
  addCommands() { return { insertTableOfContents: () => ({ commands }) => commands.insertContent({ type: this.name }) }; },
});

// Champ dynamique : date, projet, bailleur, association, numéro de page…
export const Field = Node.create({
  name: 'field',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() { return { name: { default: 'date' } }; },
  parseHTML() { return [{ tag: 'span[data-field]', getAttrs: (el) => ({ name: el.getAttribute('data-field') }) }]; },
  renderHTML({ HTMLAttributes }) { return ['span', { 'data-field': HTMLAttributes.name, class: 'field' }]; },
  addNodeView() { return ReactNodeViewRenderer(FieldView); },
  addCommands() { return { insertField: (name) => ({ commands }) => commands.insertContent({ type: this.name, attrs: { name } }) }; },
});

// Bloc dynamique alimenté par les données : budget, indicateurs, activités, graphique, galerie photos
export const DynamicBlock = Node.create({
  name: 'dynamicBlock',
  group: 'block',
  atom: true,
  draggable: true,
  addAttributes() {
    return {
      kind: { default: 'budget' },
      projectId: { default: null },
      dateFrom: { default: null },
      dateTo: { default: null },
      chart: { default: 'budget' },
      perRow: { default: null },
      photoIds: { default: null },
      limit: { default: 6 },
      title: { default: '' },
      // Blocs des rapports annuels : tableau, exercice, périmètre, langue
      table: { default: null },
      year: { default: null },
      scopeType: { default: 'association' },
      scopeId: { default: null },
      lang: { default: 'fr' },
    };
  },
  parseHTML() {
    return [{ tag: 'div[data-dynamic-block]', getAttrs: (el) => JSON.parse(el.getAttribute('data-dynamic-block') || '{}') }];
  },
  renderHTML({ node }) { return ['div', { 'data-dynamic-block': JSON.stringify(node.attrs), class: 'dynamic-block' }]; },
  addNodeView() { return ReactNodeViewRenderer(DynamicBlockView); },
  addCommands() {
    return { insertDynamicBlock: (attrs) => ({ commands }) => commands.insertContent({ type: this.name, attrs }) };
  },
});

// Commentaire ancré sur un passage
export const Comment = Mark.create({
  name: 'comment',
  inclusive: false,
  excludes: '',
  addAttributes() { return { id: { default: null }, resolved: { default: false } }; },
  parseHTML() { return [{ tag: 'span[data-comment]', getAttrs: (el) => ({ id: el.getAttribute('data-comment') }) }]; },
  renderHTML({ HTMLAttributes }) {
    return ['span', { 'data-comment': HTMLAttributes.id, class: HTMLAttributes.resolved ? 'comment resolved' : 'comment' }, 0];
  },
});

// --- Suivi des modifications (mode révision) ---------------------------------------------------------------

const changeAttrs = () => ({ author: { default: '' }, date: { default: '' } });

export const Insertion = Mark.create({
  name: 'insertion',
  inclusive: true,
  excludes: 'deletion',
  addAttributes: changeAttrs,
  parseHTML() { return [{ tag: 'ins' }]; },
  renderHTML({ HTMLAttributes }) {
    return ['ins', { class: 'tc-ins', title: `Ajout — ${HTMLAttributes.author} ${HTMLAttributes.date}` }, 0];
  },
});

export const Deletion = Mark.create({
  name: 'deletion',
  inclusive: false,
  excludes: 'insertion',
  addAttributes: changeAttrs,
  parseHTML() { return [{ tag: 'del' }]; },
  renderHTML({ HTMLAttributes }) {
    return ['del', { class: 'tc-del', title: `Suppression — ${HTMLAttributes.author} ${HTMLAttributes.date}` }, 0];
  },
});

const trackKey = new PluginKey('trackChanges');

/** Plages (from, to) portant une marque donnée, de la fin vers le début. */
function markRanges(doc, markName, from = 0, to = doc.content.size) {
  const ranges = [];
  doc.nodesBetween(from, to, (node, pos) => {
    if (node.isText && node.marks.some((m) => m.type.name === markName)) {
      const start = Math.max(pos, from), end = Math.min(pos + node.nodeSize, to);
      const last = ranges[ranges.length - 1];
      if (last && last[1] === start) last[1] = end; else ranges.push([start, end]);
    }
  });
  return ranges.reverse();
}

function rangeHasOnly(state, from, to, markName) {
  let only = true;
  state.doc.nodesBetween(from, to, (node) => {
    if (node.isText && !node.marks.some((m) => m.type.name === markName)) only = false;
  });
  return only;
}

export const TrackChanges = Extension.create({
  name: 'trackChanges',
  addOptions() { return { author: 'Utilisateur' }; },
  addStorage() { return { enabled: false }; },
  addCommands() {
    const ext = this;
    const apply = (accept, from, to) => ({ tr, state, dispatch }) => {
      const a = from ?? 0, b = to ?? state.doc.content.size;
      const keep = accept ? 'insertion' : 'deletion';
      const drop = accept ? 'deletion' : 'insertion';
      for (const [f, t] of markRanges(state.doc, drop, a, b)) tr.delete(f, t);
      const map = tr.mapping;
      for (const [f, t] of markRanges(state.doc, keep, a, b)) tr.removeMark(map.map(f), map.map(t), state.schema.marks[keep]);
      if (dispatch) dispatch(tr);
      return true;
    };
    return {
      setTrackChanges: (enabled) => () => { ext.storage.enabled = enabled; return true; },
      acceptAllChanges: () => apply(true),
      rejectAllChanges: () => apply(false),
      acceptChangeAtSelection: () => (props) => {
        const { from, to } = props.state.selection;
        return apply(true, Math.max(0, from - 1), Math.min(props.state.doc.content.size, to + 1))(props);
      },
      rejectChangeAtSelection: () => (props) => {
        const { from, to } = props.state.selection;
        return apply(false, Math.max(0, from - 1), Math.min(props.state.doc.content.size, to + 1))(props);
      },
    };
  },
  addProseMirrorPlugins() {
    const ext = this;
    const stamp = () => ({ author: ext.options.author, date: new Date().toLocaleString('fr-FR') });
    const markDeleted = (view, from, to) => {
      const { state } = view;
      let tr = state.tr;
      if (rangeHasOnly(state, from, to, 'insertion')) {
        tr = tr.delete(from, to);                       // retirer son propre ajout : vraie suppression
      } else {
        for (const [f, t] of markRanges(state.doc, 'insertion', from, to)) tr.delete(f, t);
        const end = tr.mapping.map(to);
        tr.addMark(tr.mapping.map(from), end, state.schema.marks.deletion.create(stamp()));
      }
      return tr;
    };
    return [new Plugin({
      key: trackKey,
      props: {
        handleTextInput(view, from, to, text) {
          if (!ext.storage.enabled) return false;
          const { state } = view;
          let tr = from < to ? markDeleted(view, from, to) : state.tr;
          const at = tr.mapping.map(to);
          const marks = (state.storedMarks || state.doc.resolve(from).marks()).filter((m) => m.type.name !== 'deletion');
          tr = tr.insert(at, state.schema.text(text, [...marks, state.schema.marks.insertion.create(stamp())]));
          tr.setSelection(TextSelection.create(tr.doc, at + text.length));
          view.dispatch(tr);
          return true;
        },
        handleKeyDown(view, event) {
          if (!ext.storage.enabled || (event.key !== 'Backspace' && event.key !== 'Delete')) return false;
          const { state } = view;
          const { from, to, empty, $from } = state.selection;
          if (!empty) {
            const tr = markDeleted(view, from, to);
            tr.setSelection(TextSelection.create(tr.doc, tr.mapping.map(event.key === 'Backspace' ? from : to)));
            view.dispatch(tr);
            return true;
          }
          const back = event.key === 'Backspace';
          if ((back && $from.parentOffset === 0) || (!back && $from.parentOffset === $from.parent.content.size)) return false;
          const a = back ? from - 1 : from, b = back ? from : from + 1;
          const tr = markDeleted(view, a, b);
          tr.setSelection(TextSelection.create(tr.doc, back ? tr.mapping.map(a) : tr.mapping.map(b)));
          view.dispatch(tr);
          return true;
        },
        handlePaste(view, event, slice) {
          if (!ext.storage.enabled) return false;
          const text = slice.content.textBetween(0, slice.content.size, '\n');
          if (!text) return false;
          const { state } = view;
          const { from, to } = state.selection;
          let tr = from < to ? markDeleted(view, from, to) : state.tr;
          const at = tr.mapping.map(to);
          tr = tr.insert(at, state.schema.text(text, [state.schema.marks.insertion.create(stamp())]));
          view.dispatch(tr);
          return true;
        },
      },
    })];
  },
});

export { markRanges };
