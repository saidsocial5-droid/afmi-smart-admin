# AFMI Smart Admin — Officiel

Application unifiée de l'Association Forêt Modèle d'Ifrane (AFMI), issue de la fusion de :

| Module | Origine | Technologie | Fonctions |
|---|---|---|---|
| **Desktop** | `AFMI Gestion projet 2` | WPF .NET 9, EF Core SQLite, QuestPDF | Portefeuille, WBS, EVM, rapports PDF, bailleurs, modèles, agent IA interne, diffusion SMTP |
| **SmartOffice** | `AFMI Smart admin` | Python FastAPI + React (Vite) | Agents IA (rédaction, suivi, finance, communication), OCR financier marocain, radar d'appels à projets RSS, mémoire institutionnelle, exports Word/Excel |

## Architecture

```
AFMI Smart Admin Officiel/
├── AFMI Smart Admin.sln
├── Lancer_AFMI_Smart_Admin.bat     ← lance l'application
├── Desktop/                         ← application WPF (fenêtre principale)
│   ├── Services/SmartOfficeHostService.cs   ← démarre/arrête le backend Python
│   └── Views/SmartOfficeView.xaml            ← affiche l'UI Smart Office (WebView2)
├── Core/                            ← entités, AppDbContext, migrations EF Core, règles financières (net9.0)
├── Core.Tests/                      ← tests xUnit multiplateformes (migrations, finance, audit)
├── Desktop.Tests/                   ← tests xUnit (Windows)
├── SharedTestCases/                 ← vecteurs de test communs .NET / Python
└── SmartOffice/
    ├── backend/                     ← FastAPI (sert aussi frontend/dist)
    ├── frontend/                    ← React ; dist/ = build déjà compilé
    ├── requirements.txt
    └── install_backend.bat
```

L'application WPF est le point d'entrée. Le menu **🌲 Smart Office** démarre le backend sur un port libre de
127.0.0.1, puis affiche son interface dans un WebView2. Le backend est arrêté à la fermeture de l'application.
Journal : `%LocalAppData%\AFMIGestionProjet\smartoffice.log`.

- **Version installée** : backend compilé `SmartOffice\smartoffice-backend\smartoffice-backend.exe` (Python non requis).
- **Développement** : `python -m uvicorn backend.main:app` depuis `SmartOffice/`.

## Installation (utilisateurs)

Exécuter `AFMI_Smart_Admin_Setup_2.0.0.exe` : installation sans droits administrateur, raccourcis menu Démarrer et
bureau, **guide utilisateur** (menu Démarrer). L'installateur embarque Tesseract (français, arabe), la police arabe
Amiri et une **base de démonstration** (bouton « 🎓 Démonstration »).
Prérequis : Windows 10 (1809+) ou 11 x64, Microsoft Edge WebView2 Runtime (présent par défaut sur Windows 11).
Facultatif : LibreOffice, pour les exports PDF/A.

Documentation : [guide utilisateur](docs/v2/GUIDE_UTILISATEUR.md), [architecture](docs/v2/ARCHITECTURE.md),
[analyse](docs/v2/ANALYSE.md), [historique des versions](CHANGELOG.md).

## Construire l'installateur

`build_installer.bat` enchaîne : composants tiers (`installer\prepare_third_party.ps1` : Tesseract et langues fra/ara,
police Amiri, empreintes SHA-256 consignées) → tests .NET → tests Python → build React → backend PyInstaller →
`dotnet publish` autonome → base de démonstration (`SmartOffice/demo/build_demo.py`) → guide HTML → Inno Setup.
Résultat : `build\installer\AFMI_Smart_Admin_Setup_2.0.0.exe`.
Prérequis développeur : .NET 9 SDK, Python 3.11+, Node.js, Inno Setup 6+, accès Internet pour la première préparation
des composants tiers.

## Développement

1. Une seule fois : `SmartOffice\install_backend.bat`.
2. `Lancer_AFMI_Smart_Admin.bat`, ou `dotnet run --project "Desktop\AFMI Smart Admin.csproj"`.

Variables optionnelles : `AFMI_PYTHON` (chemin de python.exe), `AFMI_SMARTOFFICE_DIR` (dossier SmartOffice),
`AFMI_DATA_DIR` (dossier de données du backend), plus `LLM_PROVIDER`, `GEMINI_API_KEY`, `OLLAMA_URL`…

## Commandes

- Build : `dotnet build "AFMI Smart Admin.sln"`
- Tests bureau : `dotnet test "AFMI Smart Admin.sln"` (`dotnet test Core.Tests` fonctionne aussi hors Windows)
- Nouvelle migration : `dotnet ef migrations add <Nom> --project Core -o Data/Migrations`, puis régénérer
  `SmartOffice/tests/fixtures/unified_schema.sql` (voir [docs/v2/ARCHITECTURE.md](docs/v2/ARCHITECTURE.md))
- Tests backend : `python -m pytest SmartOffice\tests`
- Modifier l'UI Smart Office : `cd SmartOffice/frontend && npm install && npm run build` (régénère `dist/`)

## Chaînes d'agents connectés

Menu Smart Office → **Chaînes d'Agents** (`SmartOffice/backend/core/orchestrator.py`, API `/api/workflows`).
Chaque chaîne enchaîne les agents spécialisés, transmet les productions d'une étape à l'autre, injecte des données
vérifiées de la base (portefeuille, trésorerie, contrôles d'audit déterministes) et se termine par une revue qualité.
Chaînes : montage complet d'une proposition, rapport d'avancement bailleur, audit des dépenses, veille & priorisation.
Pour en ajouter une : déclarer un `Workflow` dans `WORKFLOWS` (les tests vérifient l'ordre des dépendances).

## Paie & déclarations (Maroc)

Menu Smart Office → **Paie & Déclarations** (`backend/tools/payroll_ma.py`, API `/api/payroll`).
- Bulletin : salaire de base, heures supplémentaires (taux horaire = base / 191 h), prime d'ancienneté (Code du travail
  art. 350), CNSS (4,48 % plafonné à 6 000 DH), AMO, frais professionnels, IR (CGI art. 73), réduction pour charges
  de famille (art. 74), charges patronales et coût employeur.
- Règles datées dans `backend/config/payroll_rules_ma.json` : **LF2017** (2017–2022), LF2023, LF2025, LF2026. La version
  est choisie selon le mois de paie ; on peut forcer une version dans le simulateur. À faire valider par l'expert-comptable
  à chaque nouvelle loi de finances (ajouter une version, ne jamais modifier une version passée).
- Déclarations : IR mensuel (SIMPL-IR), récapitulatif CNSS (Damancom), état 9421 annuel, avec échéances et contrôles
  (CIN et n° CNSS manquants, bulletins non validés). Exports Excel et bulletins Word.
- **Télédéclaration :** l'application ouvre les portails officiels (tax.gov.ma, damancom.ma) ; le dépôt et la signature
  se font avec le compte de l'employeur. Aucun identifiant n'est stocké.
- **EDI état 9421** (`backend/tools/edi_9421.py`) : XML `<TraitementEtSalaire>` selon le cahier des charges EDI DTS de la
  DGI (v2.0, janvier 2015), compressé en .zip comme l'exige Simpl-IR (Menu → « Envoi de fichiers EDI »).
  - Codes de l'Annexe 2 (refTaux, situation familiale, commune, moyen de paiement) et coordonnées employeur :
    `edi_9421_config.json`, modifiable depuis l'écran. Un code vide **bloque** l'export (aucun code inventé).
  - **Schéma officiel :** déposer le `.xsd` téléchargé sur Simpl-IR dans le dossier `edi_schemas`
    (installé : `%LocalAppData%\AFMI Smart Admin\SmartOffice\edi_schemas\` ; développement : `SmartOffice\backend\data\edi_schemas\`).
    Dès qu'il est présent, chaque fichier est validé contre lui et un fichier non conforme n'est pas exporté.
  - Versements IR (`listVersements`) : à saisir après chaque paiement sur Simpl-IR.
  - Le format e-BDS de Damancom (CNSS) n'est pas généré (spécification non publiée).

Comparaison avec les logiciels du marché et feuille de route : [docs/COMPARAISON_ET_FEUILLE_DE_ROUTE.md](docs/COMPARAISON_ET_FEUILLE_DE_ROUTE.md).

## Données

- Desktop : `%LocalAppData%\AFMIGestionProjet\database.db` (inchangé, partagé avec l'ancienne application).
- SmartOffice installé : `%LocalAppData%\AFMI Smart Admin\SmartOffice\` (base, exports, profil institutionnel).
- SmartOffice en développement : `SmartOffice/backend/data/`.

Depuis la v2 (Lot 1), `database.db` est la **base unique** : son schéma est géré par les migrations EF Core (`Core/`),
sauvegardée automatiquement avant chaque migration (`backups\`), et le backend y accède sans en modifier la structure.
`afmi_smartoffice.db` ne garde que les données techniques du backend (agents, chaînes, paie) ; la reprise de ses projets
et transactions est prévue au Lot 2. Feuille de route v2 : [docs/v2/ANALYSE.md](docs/v2/ANALYSE.md).

## 🔒 Sécurité

Corrigé :
- Upload OCR : nom de fichier réduit au nom de base, extensions limitées à PDF/PNG/JPG/WEBP, suffixe unique.
- Fallback statique : tout chemin sortant de `frontend/dist` est refusé.
- Backend accessible uniquement en local : en-tête `Host` limité à `127.0.0.1`/`localhost` (anti DNS-rebinding),
  `Origin` étrangère refusée (anti-CSRF), CORS limité aux origines locales.
- Clé Gemini transmise en en-tête `x-goog-api-key`, plus jamais dans l'URL.
- Desktop : mot de passe SMTP et clé API cloud protégés par DPAPI (`SecretProtector`). Une base importée depuis un
  autre compte Windows demandera de ressaisir ces secrets.
- Desktop : un envoi SMTP non configuré ou en échec est signalé comme « non envoyé ».

- v2 Lot 1 : faux chiffrement AES (clé en dur) retiré, montants migrés en clair après sauvegarde ; IA externe désactivée
  par défaut et masquage des RIB/ICE/IF/CIN/CNSS/salaires avant envoi ; jeton de session pour l'API locale ;
  clé Gemini chiffrée par DPAPI ; journal d'audit en ajout seul et chaîné ; suppression logique. Détails : `CHANGELOG.md`.

Reste à traiter :
- Chiffrement complet de la base (SQLCipher) : à évaluer (décision D2-b de `docs/v2/ANALYSE.md`).
