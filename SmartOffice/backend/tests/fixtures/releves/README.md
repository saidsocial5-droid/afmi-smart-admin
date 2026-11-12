# Relevés bancaires de test

Ce dossier reçoit les **vrais relevés anonymisés** de l'AFMI, qui servent à mesurer la lecture automatique
(critère : au moins 95 % des lignes extraites correctement). Les tests les évaluent dès qu'ils sont présents
(`SmartOffice/tests/test_lot3_statements.py`).

Pour chaque relevé, déposez :

- le ou les fichiers (PDF natif, PDF scanné, photos JPG/PNG page par page) ;
- un fichier `<nom>.truth.json` décrivant ce qu'il faut lire :

```json
{
  "bank": "Banque Populaire",
  "rib": "190...",
  "period_start": "2026-03-01", "period_end": "2026-03-31",
  "opening": 1234567, "closing": 1200000,
  "lines": [
    {"date": "2026-03-04", "label": "FRAIS TENUE DE COMPTE", "debit": 7921, "credit": 0}
  ],
  "files": {"documents": [["releve_mars_p1.jpg", "releve_mars_p2.jpg"], "releve_mars.pdf"]}
}
```

Montants en **centimes**. Dans `documents`, une liste désigne les pages d'un même relevé.

**Anonymisation** : masquez les noms de personnes, les numéros de compte de tiers et les montants de salaires
nominatifs. Les relevés générés automatiquement (`tests/tools/statement_fixtures.py`) ne remplacent pas de vrais
relevés : ils ne prouvent que la cohérence du pipeline.
