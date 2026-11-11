import React, { useEffect, useState } from 'react';
import { NodeViewWrapper } from '@tiptap/react';
import { useDoc } from './context';

/** Titres du document avec numérotation hiérarchique (1, 1.1, 1.1.1). */
export function collectHeadings(doc) {
  const out = [];
  const counters = [0, 0, 0];
  doc.descendants((node) => {
    if (node.type.name === 'heading' && node.attrs.level <= 3 && node.textContent.trim()) {
      const level = node.attrs.level;
      counters[level - 1] += 1;
      for (let i = level; i < 3; i += 1) counters[i] = 0;
      out.push({ level, text: node.textContent, number: counters.slice(0, level).join('.') });
    }
  });
  return out;
}

export default function TocView({ editor }) {
  const { layout } = useDoc();
  const [items, setItems] = useState(() => collectHeadings(editor.state.doc));
  useEffect(() => {
    const update = () => setItems(collectHeadings(editor.state.doc));
    editor.on('update', update);
    return () => editor.off('update', update);
  }, [editor]);
  return (
    <NodeViewWrapper className="toc-block" contentEditable={false}>
      <div className="toc-title">Table des matières</div>
      {items.length === 0 && <div className="toc-empty">Ajoutez des titres (Titre 1, 2, 3) : ils apparaîtront ici.</div>}
      <ol className="toc-list">
        {items.map((h, i) => (
          <li key={i} className={`toc-l${h.level}`}>
            {layout?.heading_numbering ? <span className="toc-num">{h.number}</span> : null}{h.text}
          </li>
        ))}
      </ol>
    </NodeViewWrapper>
  );
}
