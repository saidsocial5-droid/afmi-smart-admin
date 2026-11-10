# AFMI - Documentation Technique et Guide Utilisateur

Ce document sert de guide de référence pour le logiciel de gestion de portefeuille de projets (Windows). Il détaille l'architecture technique, le modèle de données, les algorithmes clés, ainsi qu'un manuel utilisateur complet.

---

## 1. Documentation Technique

### Architecture Générale
L'application est construite sur le framework **.NET 10 WPF** (Windows Presentation Foundation) en suivant le patron de conception **MVVM** (Model-View-ViewModel).

- **Couche de Présentation (Views)** : Fichiers XAML contenant l'interface graphique. Elle s'appuie sur un système de style moderne Windows 11 Fluent (`Themes/ModernStyles.xaml`).
- **Couche de Logique Applicative (ViewModels)** : Gère l'état de l'application et les commandes utilisateur, implémentée via `CommunityToolkit.Mvvm` (source generators).
- **Couche de Données (Models & Data)** : Entités mappées par Entity Framework Core (EF Core) vers une base de données locale **SQLite** (`database.db`), stockée de manière isolée dans le profil utilisateur Windows (`%LocalAppData%\AFMIGestionProjet`).
- **Services (Services)** : Logique métier autonome (Calculs EVM, Génération PDF QuestPDF, Exports CSV).

### Schéma de la Base de Données
Le schéma comprend les tables clés suivantes :
1. **`Projects`** : Détails du projet (Manager, Client, BudgetGlobal, Dates, Statuts, LessonsLearned).
2. **`Tasks`** (WBS) : Modèle arborescent auto-référencé (`ParentTaskId` -> `Id`) pour construire la WBS (Work Breakdown Structure).
3. **`CostEntries`** : Registre comptable contenant les dépenses (estimées et réelles) ventilées par catégorie (Ressources, Matériel, Prestataires, Divers).
4. **`WorkflowSteps`** : Les étapes/jalons du workflow de cycle de vie (PM² ou personnalisé).
5. **`AuditLogs`** : Enregistrement de l'historique d'audit (Changements d'états, créations, modifications de tâches et coûts).
6. **`ReportHistory`** : Versioning et fichiers des rapports générés.
7. **`Templates`** : Modèles sérialisés en JSON pour la création rapide.

### Algorithmes Métier

#### 1. Agrégation WBS (Hiérarchie des Tâches)
Lorsqu'une tâche enfant est modifiée, un algorithme récursif remonte l'arborescence pour recalculer les valeurs du parent :
- **Budget / Coût** : Somme directe des budgets/coûts des tâches enfants.
- **Dates (Début/Fin)** : Min des dates de début enfants, Max des dates de fin enfants.
- **Avancement (%)** : Moyenne pondérée par le budget des enfants :
  $$\text{Avancement Parent} = \frac{\sum (\text{Avancement Enfant}_i \times \text{Budget}_i)}{\sum \text{Budget}_i}$$
  *(Si les budgets sont à zéro, une moyenne arithmétique simple est appliquée).*
- **Statut** : Automatiquement mis à "Terminé" si tous les enfants sont terminés, "Bloqué" si au moins un enfant est bloqué, "À faire" si tous les enfants sont à faire, sinon "En cours".

#### 2. Earned Value Management (EVM)
Les indicateurs de valeur acquise sont calculés en temps réel :
- **BAC (Budget at Completion)** : Budget global alloué.
- **PV (Planned Value)** : Budget prévu à date, interpolé linéairement sur la durée planifiée de chaque tâche :
  $$PV = \text{Budget} \times \frac{\text{Date Réf} - \text{Date Début}}{\text{Date Fin} - \text{Date Début}} \quad (\text{borné entre } 0 \text{ et } \text{Budget})$$
- **EV (Earned Value)** : $\text{Budget} \times (\text{Avancement} / 100)$.
- **AC (Actual Cost)** : Dépense réelle cumulée (somme des coûts réels des tâches).
- **CPI (Cost Performance Index)** : $EV / AC$ (si $AC = 0$, index $= 1.0$).
- **SPI (Schedule Performance Index)** : $EV / PV$ (si $PV = 0$, index $= 1.0$).
- **EAC (Estimate at Completion)** : $BAC / CPI$ (Coût final prévisionnel).
- **ETC (Estimate to Complete)** : $EAC - AC$ (Reste à dépenser).
- **VAC (Variance at Completion)** : $BAC - EAC$ (Écart final estimé).

---

## 2. Guide de l'Utilisateur

### Démarrage Rapide
1. **Lancement** : Exécutez l'application. Au premier démarrage, la base de données SQLite est automatiquement créée et pré-peuplée avec des projets exemples (CRM Corporate et Refonte Site Web) et les modèles de méthodologies (PM², Agile, Waterfall).
2. **Sauvegarde automatique** : À chaque démarrage, l'application effectue une copie de sauvegarde tournante de la base de données SQLite (garde les 5 dernières sauvegardes dans `%LocalAppData%\AFMIGestionProjet\Backups`).

### Utilisation des Modules

#### Tableau de Bord Global
Affiche les indicateurs consolidés (budget total, avancement moyen, nombre de projets actifs).
- **Tâches en retard** : Affiche toutes les tâches des projets dont la date de fin est dépassée et le statut n'est pas "Terminé".
- **Alertes Budget** : Liste les projets dont le CPI est inférieur à $0.95$, signalant un risque financier de dépassement budgétaire.

#### Gestion du Portefeuille
Affiche la grille de tous les projets.
- **Filtres** : Recherchez par mot-clé (nom, manager, client) ou filtrez par statut et niveau de priorité.
- **Création / Édition** : Cliquez sur "+ Nouveau Projet" ou "Éditer" pour ouvrir le formulaire.
- **Comparaison (Benchmarking)** : Cochez les cases en début de ligne pour sélectionner 2 projets ou plus, puis cliquez sur "Comparer Sélection". Un tableau comparatif des indicateurs de performance (Avancement, Budget, CPI, SPI, EAC) s'affiche côte à côte.
- **Export** : Cliquez sur "Exporter CSV" pour générer un fichier de synthèse compatible Excel.

#### Suivi de Projet (Détails)
Double-cliquez ou cliquez sur "Ouvrir" sur un projet pour entrer dans son espace de gestion :
1. **Onglet Synthèse & EVM** : Affiche la synthèse rédigée automatiquement par l'assistant textuel (évaluation des dérives calendaires/financières et conseils d'actions). Affiche également la **Courbe en S** vectorielle (courbes cumulées PV, EV, AC).
2. **Onglet Hiérarchie (WBS)** : Affiche l'arborescence des tâches. Ajoutez des sous-tâches, éditez la progression ou modifiez les budgets. Les modifications se propagent instantanément vers le haut.
3. **Onglet Diagramme de Gantt** : Affiche le planning visuel. Les barres de progression sont dessinées sur un Canvas. Les dépendances sont affichées sous forme de lignes pointillées.
   - *Dépendances* : Renseignez les prédécesseurs d'une tâche sous forme d'identifiants séparés par des virgules (ex: `12`) pour lier les barres de planning.
4. **Onglet Cycle de vie (Workflow)** : Cochez les jalons franchis (Initiation, Planification, Exécution, Clôture). Ajoutez vos propres étapes personnalisées.
5. **Budget & Dépenses** : Saisissez vos factures et dépenses de projet par catégorie pour alimenter le registre de coûts réels.
6. **Rapports (Prévisualisation & Multi-Format)** : Choisissez un type de rapport (Avancement, Financier, Clôture) et cliquez sur **Afficher l'Aperçu** pour charger le texte et les indicateurs réels directement à l'écran. 
   - *Choix du Format* : Sélectionnez le format souhaité (PDF/Word pour l'avancement/clôture, PDF/Excel pour le rapport financier) puis cliquez sur **Exporter le Rapport Final** pour l'enregistrer à l'emplacement choisi.
   - *Historique* : L'onglet *Historique des Éditions* liste tous les rapports précédemment exportés pour les réouvrir en un clic.
7. **Piste d'Audit (Audit Trail)** : Historique chronologique complet de chaque modification apportée aux éléments du projet (avec anciennes et nouvelles valeurs).

### Outils d'Administration et Sécurité (Sidebar)
- **Configuration SMTP** : Configurez le serveur mail et programmez une diffusion de rapport automatique (hebdomadaire ou mensuelle). Au démarrage, l'application vérifie si un rapport est dû, génère le PDF et l'envoie (ou affiche une boîte d'émulation si vous êtes hors-ligne ou si le serveur n'est pas renseigné).
- **Exporter la base** : Crée instantanément une copie de sauvegarde du fichier SQLite `database.db` vers l'emplacement de votre choix.
- **Importer une base** : Permet de charger un fichier de base de données externe. L'application ferme ses connexions actives, effectue une copie de sécurité de la base actuelle (`database_before_import.db`), écrase le fichier SQLite puis recharge l'affichage à chaud.
- **Partage de vues personnalisées** : Sur l'en-tête de la liste des projets, utilisez "Exporter Vue" pour enregistrer l'état de vos filtres de recherche dans un fichier JSON, et "Importer Vue" pour réappliquer les mêmes filtres à la volée.

### Compilation et Packaging (.exe autonome)
Exécutez le script `build_publish.bat` situé à la racine du projet. Il compile et assemble le code sous forme d'un exécutable unique autonome (`publish/AFMI Gestion projet.exe`) optimisé pour Windows 10/11 x64, contenant son propre runtime .NET 10.

