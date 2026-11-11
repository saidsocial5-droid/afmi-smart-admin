# Point de reprise — v2

*Dernière session : 11/11/2026. Branche : `claude/v2-analyse`.*

## Où en est le projet

| Lot | Statut |
|---|---|
| Analyse (`ANALYSE.md`) | Validée |
| Lot 1 — Fondations (base unique, migrations, audit, sécurité) | Livré (`eddba95`) |
| Lot 2 — Banque et trésorerie (écran Trésorerie, rapprochement, prévisions) | Livré (`fa047db`) |
| Lot 3 — Relevés scannés (OCR, validation, catégorisation, anomalies) | Livré (voir CHANGELOG) |
| Lot 4 — Éditeur, chartes, galerie photos | Livré (voir CHANGELOG) |
| Lot 5 — Rapports annuels moral et financier | **Prochaine étape** |
| Lots 6 à 8 | À faire (voir `ANALYSE.md` § 7) |

Tests au dernier commit : 76 xUnit (`Core.Tests`) et 105 pytest (1 sauté : vrais relevés absents), tous verts.

## En attente de l'AFMI

1. **Relevés réels anonymisés** : 2 à 3 par banque utilisée, en PDF natif et en scan ou photo. Indispensables pour
   le Lot 3 et le critère des 95 %. À déposer dans `SmartOffice/backend/tests/fixtures/releves/`.
2. **Test de l'écran Trésorerie sous Windows.** Il n'a pas encore été vérifié visuellement (voir le CHANGELOG du
   Lot 2, point 6).
3. **Référentiel de l'expert-comptable** : plan de comptes, modèle de compte d'emploi des ressources, traitement des
   fonds dédiés (questions Q3 et Q4).
4. **Formats exigés par les bailleurs prioritaires (Q10)**, et réponse à Q13 : le RIB et l'ICE de `ngo_profile.json`
   sont-ils réels ?
5. **Confirmation de la clé RIB** sur 2 ou 3 vrais RIB de l'AFMI.

## Pour reprendre (session cloud)

```bash
git fetch origin claude/v2-analyse && git checkout claude/v2-analyse
```

```bash
apt-get install -y dotnet-sdk-10.0
```

```bash
dotnet tool install --global dotnet-ef --version 9.0.8
```

```bash
DOTNET_ROLL_FORWARD=Major dotnet test Core.Tests
```

```bash
apt-get install -y tesseract-ocr tesseract-ocr-fra tesseract-ocr-ara
```

```bash
cd SmartOffice && pip install -r requirements.txt pytest && python -m pytest tests
```

- Frontend : `cd SmartOffice/frontend && npm ci && npm run build`. Les paquets `@tiptap/*` sont figés et alignés par
  `overrides` dans `package.json` : les mettre à jour tous ensemble.
- Le Desktop compile hors Windows avec `-p:EnableWindowsTargeting=true` ; ses tests ne tournent que sous Windows.
- Après toute migration, régénérer `SmartOffice/tests/fixtures/unified_schema.sql` (voir `ARCHITECTURE.md` § 2.1).
