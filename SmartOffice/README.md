# 🌲 AFMI-SmartOffice (المكتب الذكي للجمعية)
### Multi-Agent AI Platform & Financial OCR Document Parser for Association Forêt Modèle d'Ifrane (AFMI)
*Province d'Ifrane, Azrou, Région Fès-Meknès, Royaume du Maroc*

---

## 📌 Présentation & Objectifs
**AFMI-SmartOffice** est une plateforme applicative hybride (Desktop Electron + Web) conçue pour l'**Association Forêt Modèle d'Ifrane (جمعية الغابة النموذجية إفران)**. Elle combine un noyau multi-agents d'intelligence artificielle, une mémoire institutionnelle partagée et un moteur d'extraction financière par **OCR & Vision Multimodale** pour les relevés bancaires marocains et les factures fournisseurs.

L'architecture est régie par le principe **Ouvert/Fermé (Open-Closed Principle)** : de nouveaux agents, compétences ou outils d'audit peuvent être ajoutés ou configurés dynamiquement depuis l'interface ou par simple ajout de fichier dans `backend/plugins/` sans réécriture du code source.

---

## 🏛️ 1. Identité Institutionnelle & Contexte Territorial
Toutes les interactions IA intègrent automatiquement la mémoire partagée définie dans `backend/config/ngo_profile.json` :
- **Organisation :** Association Forêt Modèle d'Ifrane (AFMI) / جمعية الغابة النموذجية إفران
- **Statut Juridique :** Association à but non lucratif régie par le Dahir n° 1-58-376 du 15 novembre 1958
- **Identifiants Légaux :** ICE `001894235000088` | Identifiant Fiscal `40291845` | RIB `022 330 0001234567890123 45` (Banque Populaire Azrou)
- **Zone Géographique :** Moyen Atlas (Azrou, Ifrane, Timahdite, Ben Smim, Oued Tizguit, Aguelmam Sidi Ali)
- **6 Axes Stratégiques Prioritaires :**
  1. **Axe Forêt :** Conservation de la cédraie (*Cedrus atlantica*), chêne vert, suivi du Macaque de Barbarie.
  2. **Axe Pastoral :** Restauration des parcours et gestion traditionnelle concertée (*système Agdal*).
  3. **Axe Eau :** Monitoring de la qualité des eaux de surface et zones humides Ramsar (Afennourir, Dayats).
  4. **Axe Écotourisme :** Sentiers d'interprétation de la nature, gîtes ruraux et produits du terroir.
  5. **Axe Climat :** Adaptation aux changements climatiques, gestion des SIBE et éducation environnementale.
  6. **Axe Socio-économique :** Autonomisation des femmes et jeunes ruraux (tissage traditionnel en laine de Timahdite).

---

## 🤖 2. Les 4 Agents IA Spécialisés

| Agent | Rôle en Arabe | Rôle en Français | Outils Clés |
| :--- | :--- | :--- | :--- |
| **AgentGrantWriter** | خبير مقترحات التمويل والمشاريع | Expert Montage de Projets & Bailleurs | `generate_logframe`, `export_docx_proposal`, `calculate_forest_carbon_offset` |
| **AgentProjectManager** | مدير المشاريع والمتابعة والتقييم (M&E) | Chef de Projet & Spécialiste M&E | `calculate_project_kpi`, `risk_assessment_matrix`, `calculate_forest_carbon_offset` |
| **AgentFinanceAuditor** | مدقق المالية والوثائق المحاسبية | Auditeur Financier & Expert OCR | `parse_bank_statement_ocr`, `verify_invoice_ice`, `audit_tender_compliance`, `export_excel_ledger` |
| **AgentCommunications** | مسؤول التواصل والإعلام المؤسساتي | Responsable Communication & Médias | `generate_press_release`, `social_media_campaign`, `bilingual_newsletter` |

---

## 🔍 3. Moteur OCR & Analyseur Financier Hybride (`backend/tools/ocr_engine.py`)
Le pipeline d'extraction traite les formats `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp` avec une double approche :
1. **PDFs Numériques :** `pdfplumber` et `PyMuPDF` (`pymupdf`) pour l'extraction vectorielle précise des tableaux de transactions bancaires et libellés.
2. **Documents Scannés & Images :** Multimodal Vision AI (**Google Gemini 2.5 Flash** ou **Ollama Vision `llama3.2-vision` / `llava`**) + moteur heuristique de secours structurant les données en JSON strict.
3. **Reconnaissance Spécifique Marocaine :**
   - **Relevés Bancaires :** Détection automatique de la banque (Banque Populaire, Attijariwafa, BMCE/Bank of Africa, CIH, CAM), extraction du RIB (24 chiffres), débit, crédit, solde et rapprochement.
   - **Factures Fournisseurs :** Contrôle de conformité de l'ICE (15 chiffres), mentions fiscales obligatoires (IF, RC), calcul de TVA (taux standard 20% ou réduits) et cohérence HT / TVA / TTC.

---

## 🧩 4. Architecture d'Extensions & Plugins (`backend/plugins/`)
Le système s'étend dynamiquement sans modifier le code de base :
- **`carbon_calculator_plugin.py` :** Calculateur de séquestration carbone ($tCO_2e$) pour la cédraie du Moyen Atlas selon les tables allométriques de l'INRF et valorisation des crédits carbone.
- **`morocco_procurement_plugin.py` :** Vérificateur de conformité selon le Décret marocain des marchés publics (seuils de bons de commande, attestations fiscales DGI et CNSS pour dépenses > 50 000 DH).

---

## 🎨 5. Interface Utilisateur (React 18 + Vite + Tailwind CSS + Electron)
- **Support RTL Intégral :** Ergonomie fluide en Arabe avec restitution bilingue (Arabe / Français).
- **Palette Institutionnelle Nature :**
  - Vert Forêt Cédraie : `#1B4332`
  - Or Terroir Moyen Atlas : `#D4A373`
  - Blanc Ardoise : `#F8F9FA`
- **Modules de l'Application :**
  - **لوحة القيادة (Dashboard) :** Métriques financières globales, indicateurs d'impact, aperçu des projets et lanceurs rapides.
  - **مساحات الوكلاء (Agents Workspace) :** Chat interactif, suggestions de suivi contextuelles, et export instantané en Word (`.docx`).
  - **مختبر التدقيق و OCR (Financial OCR Lab) :** Glisser-déposer de relevés/factures, grand livre interactif éditable et export Excel (`.xlsx`).
  - **المنح والمشاريع (Grants & Projects) :** Pipeline des opportunités de subvention et fiches projets avec jauges de consommation budgétaire et KPIs.
  - **استوديو الوكلاء (Agent Studio) :** Éditeur de prompts, curseur de température, sélection de modèle et activation d'outils.
  - **الذاكرة والإعدادات (Settings & Memory) :** Gestion de `ngo_profile.json` et test de connectivité en direct avec Gemini et Ollama.

---

## 🚀 6. Guide de Démarrage Rapide

### Option A : Lancement en un clic (Windows)
Double-cliquez sur :
- **`start_desktop.bat`** pour démarrer l'application de bureau Electron.
- **`start_web.bat`** pour démarrer en mode navigateur web (Chrome / Edge / Firefox).

### Option B : Lancement par ligne de commande
```bash
# 1. Lancer le serveur unifié (Backend + Frontend)
python run_app.py

# Pour forcer le mode navigateur web :
python run_app.py --web-only
```

### Option C : Mode Développement Découplé
```bash
# Terminal 1 - Backend FastAPI
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 - Frontend Vite
cd frontend
npm run dev
```

---

## 📁 7. Arborescence du Monorepo
```
AFMI Smart admin/
├── backend/
│   ├── config/
│   │   ├── settings.py            # Configuration et répertoires de runtime
│   │   └── ngo_profile.json       # Mémoire institutionnelle partagée AFMI
│   ├── core/
│   │   ├── database.py            # Schéma SQLite SQLAlchemy et initialisation
│   │   ├── llm_router.py          # Moteur Dual Gemini / Ollama / Heuristique
│   │   ├── base_agent.py          # Classe abstraite BaseAgent extensible
│   │   └── agent_registry.py      # Registre et chargeur dynamique de plugins
│   ├── tools/
│   │   ├── ocr_engine.py          # Moteur OCR Hybride PDF & Vision IA
│   │   └── exporters.py           # Générateurs Word (.docx) et Excel (.xlsx)
│   ├── plugins/
│   │   ├── carbon_calculator_plugin.py
│   │   └── morocco_procurement_plugin.py
│   ├── api/
│   │   ├── routes_agents.py
│   │   ├── routes_ocr.py
│   │   ├── routes_finance.py
│   │   ├── routes_grants.py
│   │   ├── routes_projects.py
│   │   ├── routes_settings.py
│   │   └── routes_plugins.py
│   └── main.py                    # Point d'entrée FastAPI
├── frontend/
│   ├── electron/
│   │   ├── main.cjs               # Script principal Electron Desktop
│   │   └── preload.cjs            # Pont de sécurité IPC
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx         # En-tête institutionnel
│   │   │   └── Sidebar.jsx        # Navigation RTL
│   │   ├── views/
│   │   │   ├── DashboardView.jsx
│   │   │   ├── AgentsWorkspaceView.jsx
│   │   │   ├── OcrFinanceLabView.jsx
│   │   │   ├── GrantsProjectsView.jsx
│   │   │   ├── AgentStudioView.jsx
│   │   │   └── InstitutionalMemoryView.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── dist/                      # Build de production prêt à l'emploi
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── run_app.py                     # Lanceur unifié Python
├── start_desktop.bat              # Script batch Desktop
├── start_web.bat                  # Script batch Web
└── README.md
```

---
*Association Forêt Modèle d'Ifrane (AFMI) — Bureau Central, Azrou, Maroc.*
