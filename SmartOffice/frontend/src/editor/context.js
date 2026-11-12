import { createContext, useContext } from 'react';

// Contexte du document en cours : projet par défaut, charte effective, valeurs des champs, listes de choix.
export const DocContext = createContext({ projectId: null, style: {}, fields: {}, projects: [], tasks: [], layout: {} });
export const useDoc = () => useContext(DocContext);

export const fmtMad = (cents) => (cents === null || cents === undefined)
  ? '—'
  : (cents / 100).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
