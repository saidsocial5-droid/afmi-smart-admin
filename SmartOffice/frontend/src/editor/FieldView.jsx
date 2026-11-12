import React from 'react';
import { NodeViewWrapper } from '@tiptap/react';
import { useDoc } from './context';

export const FIELD_LABELS = {
  date: 'Date du jour', project_name: 'Nom du projet', project_code: 'Code du projet', funder_name: 'Bailleur',
  association: 'Association', title: 'Titre du document', page: 'N° de page', pages: 'Nombre de pages',
};

export default function FieldView({ node }) {
  const { fields } = useDoc();
  const name = node.attrs.name;
  // Les numéros de page n'existent qu'à l'impression (compteurs CSS de l'aperçu paginé).
  const value = name === 'page' || name === 'pages' ? null : fields?.[name];
  return (
    <NodeViewWrapper as="span" className="field-chip" data-field={name} title={FIELD_LABELS[name] || name}>
      {value || `[${FIELD_LABELS[name] || name}]`}
    </NodeViewWrapper>
  );
}
