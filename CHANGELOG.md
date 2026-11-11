# Journal des modifications

## [2.0.0] — 11/11/2026 — Lot 8 : finalisation, démonstration, installateur

Version 2.0.0 : les huit lots du cahier des charges sont livrés. Documentation :
[guide utilisateur illustré](docs/v2/GUIDE_UTILISATEUR.md), [architecture](docs/v2/ARCHITECTURE.md),
[analyse](docs/v2/ANALYSE.md).

### Décisions prises pour ce lot
- **Démonstration séparée** : la base fictive est livrée avec l'application et s'ouvre dans une seconde fenêtre.
  Elle ne peut jamais remplacer ni modifier la base réelle.
- **Rôles étendus** à la Trésorerie de l'application de bureau.
- **Alertes envoyées automatiquement**, sans répétition : une alerte n'est rappelée qu'au bout de 7 jours.
- **LibreOffice non embarqué** (plus de 300 Mo) : il reste facultatif, pour le PDF/A.

### Ajouté
- **Base de démonstration** : « Association des Cèdres de l'Atlas », entièrement fictive.
  - 3 projets : restauration de la cédraie (Fonds Vert, fictif), gestion de l'eau (Fondation Atlas, en EUR),
    éducation à l'environnement (fonds propres).
  - 3 comptes bancaires (Banque Populaire, Attijariwafa, CIH en euros) et **12 relevés mensuels** PDF, de janvier à
    avril 2026.
  - Conventions et tranches, budgets, taux de change, activités, indicateurs avec mesures par sexe et par âge,
    10 photos légendées, 3 documents dans la GED (convention, rapport narratif, procès-verbal), rapport annuel.
  - Tout est construit **par les traitements réels** : lecture des relevés, imputation, validation, intégration,
    rapprochement, analyse des documents, génération du rapport.
  - Un relevé est laissé « à vérifier » et deux opérations en brouillon, pour montrer les écrans de validation et
    les contrôles.
- **Mode démonstration** (bouton « 🎓 Démonstration ») : fenêtre marquée « DÉMONSTRATION — données fictives »,
  remise à zéro possible, aucun e-mail envoyé.
- **Rôles dans toute l'application de bureau**, y compris les écrans de la 1.3.0 (portefeuille, tâches, bailleurs,
  SMTP). Le contrôle se fait à l'enregistrement en base (`AppDbContext.WritePermission`), mêmes zones que Smart Office :
  - paramètres : administrateur ;
  - trésorerie : administrateur et comptable ;
  - projets : tous sauf lecteur.

  La Trésorerie affiche en plus un bandeau « consultation seule ».
- **Alertes par e-mail** :
  - contenu : échéances de rapports et de conventions, solde négatif ou sous le seuil, éléments non rapprochés,
    échec d'une sauvegarde automatique ;
  - vérification toutes les heures ; un récapitulatif part seulement s'il contient une alerte nouvelle ;
  - aperçu et envoi immédiat dans Paramètres › Notifications ; chaque envoi est journalisé.
- **Tests de bout en bout** :
  - la construction de la démonstration ;
  - les contrôles, exports Word, Excel et ZIP, et la recherche dans la GED sur cette base ;
  - les alertes ;
  - la **performance** : 15 000 opérations sur 5 ans donnent les états du rapport annuel en 0,5 s et le classeur
    Excel en 3,6 s.
- **Guide utilisateur** illustré de 11 captures d'écran prises sur la démonstration. L'installateur le livre en
  HTML, avec un raccourci dans le menu Démarrer.
- **Installateur 2.0.0** :
  - **Tesseract OCR** (français et arabe) embarqué ;
  - **police arabe Amiri** installée (licence libre OFL) ; c'est désormais la police arabe par défaut des rapports ;
  - base de démonstration et guide inclus ;
  - empreintes SHA-256 des composants tiers consignées et vérifiées à chaque construction.

### Corrigé
- **Installation** : le backend compilé n'embarquait pas les fichiers de configuration ajoutés aux Lots 3, 5 et 6
  (gabarits de relevés, présentation des états, cycle de vie), ni les modèles de python-docx. La version installée
  aurait échoué sur les relevés, les rapports et les exports Word. Un test le vérifie désormais.
- **En-tête de Smart Office** : il affichait « Gemini 2.5 Flash » même en mode hors ligne, un nom d'association, une
  version (« v1.0 ») et des montants codés en dur ou tirés de l'ancienne base 1.x. Il affiche maintenant l'état réel de
  l'IA (« IA locale (hors ligne) »), l'association des paramètres, la version 2.0.0, et la trésorerie et les budgets
  de la base unique.
- **Dossier annuel** : le message d'erreur plantait quand un contrôle bloquant empêchait la génération du rapport.
  Le défaut a été trouvé par le test de bout en bout.
- La sauvegarde automatique signale désormais ses échecs (paramètres et alertes) au lieu de les ignorer.
- Tests : 97 xUnit, 164 pytest.

### Points à valider
1. **Première construction de l'installateur sous Windows** :
   - je n'ai pas pu télécharger Tesseract ni la police depuis cet environnement : les adresses officielles sont dans
     `installer/prepare_third_party.ps1` ;
   - à la première construction, contrôlez les empreintes consignées dans `third_party/SHA256SUMS.txt` ;
   - testez ensuite l'installation, la démonstration et les écrans WPF (Trésorerie en consultation seule).
2. **Alertes par e-mail** : renseignez le SMTP et les destinataires (Paramètres › Notifications), puis faites un envoi
   de test.
3. Toujours en attente : vrais relevés anonymisés, modèle de l'expert-comptable (Q3, Q4), formats des bailleurs
   (Q10), réponse à Q13 (identifiants réels dans `ngo_profile.json`, affichés en bas de la barre latérale).

## [2.0.0 — Lot 7 : Exports Word, PDF, Excel et paramètres avancés] — 11/11/2026

### Ajouté — exports
- **Word (.docx)** depuis l'éditeur (menu « Exporter… ») : fidèle à l'éditeur et à la charte.
  - Styles Word natifs : Normal, Titre 1 à 3, Citation, listes. Le volet de navigation de Word fonctionne.
  - **Table des matières** en champ Word : pré-remplie, Word la met à jour à l'ouverture.
  - **Vraies notes de bas de page** Word.
  - En-têtes et pieds de page : première page distincte, pages paires et impaires, logos, mentions obligatoires,
    « Page X / Y ».
  - Tableaux (en-tête répété à chaque page, cellules fusionnées, trames), images, graphiques, galeries photo
    légendées et numérotées.
  - Arabe de droite à gauche.
  - Les blocs de données sont recalculés depuis la base au moment de l'export.
- **PDF** de qualité impression :
  - polices intégrées, signets tirés des titres, métadonnées (titre, auteur, langue) ;
  - imprimé par Microsoft Edge, présent sur tout Windows 10/11 (ou Chrome/Chromium) ;
  - option **PDF/A-2b** (archivage) si LibreOffice est installé.
- **Excel avec de vraies formules** (Rapports annuels → « États financiers ») :
  - une feuille par état : CER, recettes et dépenses, budget par projet et par bailleur, trésorerie, reports,
    comparaison N-1 ;
  - sous-totaux, totaux, écarts, taux et résultats en formules ; une formule n'est écrite que si elle redonne
    exactement le chiffre du rapport ;
  - feuille « Ventilations » (détail des opérations validées) et feuille « Contrôles » qui recalcule les totaux
    par SOMME.SI.ENS (écarts attendus : 0) ;
  - couleurs de la charte, impression paysage, volets figés.
- **Opérations bancaires** (Excel) : une feuille par compte, solde progressif en formule à partir du solde
  d'ouverture.
- **État de rapprochement** d'un relevé (Excel, depuis « Relevés bancaires ») : solde du relevé, opérations absentes,
  lignes non comptabilisées et écart en formules.
- **Dossier annuel complet** (Rapports annuels → ZIP), qui contient :
  - le rapport moral et le rapport financier en Word et en PDF ;
  - les états financiers Excel ;
  - les annexes choisies dans la GED ;
  - un **PDF unique** moral + financier + annexes, avec signets par partie ;
  - la liste des empreintes SHA-256.
- **Nommage configurable** des fichiers, par exemple `AFMI_RapportFinancier_2026_FR.pdf`.
- Chaque export est inscrit au journal d'audit, avec l'empreinte du fichier.

### Ajouté — panneau « Paramètres » (nouveau menu)
- Onze sections. On peut **rechercher** un paramètre, **exporter et importer** les réglages en JSON (sans les clés
  d'API ; un import invalide ne modifie rien), et **restaurer les valeurs par défaut** par paramètre, par section ou
  en totalité. Toute modification est validée par le serveur et tracée dans le journal d'audit.
- **Association** : nom, sigle, adresse, premier mois de l'exercice, devise, langue.
- **Comptabilité** : seuil de justificatif obligatoire, apprentissage des règles de classement.
- **Banques** :
  - **tolérance du rapprochement** (3 jours par défaut), reprise par l'écran Trésorerie et par les relevés ;
  - seuil des frais bancaires inhabituels ;
  - gabarits de relevés (éditeur JSON validé).
- **Exports** : modèles de nom, moteur PDF, moteurs détectés sur le poste.
- **IA** :
  - **fournisseur par tâche** (rédaction, synthèse des rapports, lecture des relevés, questions sur la GED, légendes
    des photos) : Anthropic, OpenAI, Gemini, Mistral, Ollama, serveur compatible OpenAI ou moteur local ;
  - clé chiffrée par DPAPI, modèle, température, limite de jetons ;
  - « **Tester la connexion** », qui liste les modèles disponibles ;
  - **plafond de coût mensuel** et consommation du mois ;
  - mode hors ligne et masquage ;
  - **prompts système modifiables**, avec retour au texte d'origine.
- **Notifications** : messagerie SMTP (mot de passe DPAPI), e-mail de test, alertes à envoyer.
- **Utilisateurs et rôles** : Administrateur, Comptable, Chargé de projet, Lecteur.
- **Sauvegardes** :
  - dossier, fréquence (démarrage, quotidienne, hebdomadaire, manuelle), nombre de sauvegardes conservées ;
  - « Sauvegarder maintenant » ;
  - **restauration** appliquée au prochain démarrage, après une sauvegarde de sécurité.
- **Apparence** : langue de l'interface, taille du texte, couleur principale.
- **Rapports et cycle de vie** : niveau de chaque contrôle des rapports (bloquant, avertissement, ignoré),
  documents attendus par phase.

### Modifié
- Sauvegarde automatique du Desktop : l'ancienne copie du fichier de base ouvert (risque de copie incohérente,
  5 exemplaires) est remplacée par `BackupService` : copie par l'API de sauvegarde SQLite, planification et
  conservation paramétrables.
- Le backend exige désormais la dernière migration (`DocumentManagement`) et l'indique clairement si la base
  n'est pas à jour.
- Le journal d'audit écrit par Python masque les colonnes secrètes (mot de passe SMTP), comme côté .NET.
- Tests : 91 xUnit, 157 pytest. Les formules Excel ont été vérifiées par recalcul ; un PDF, un PDF/A et la
  conversion Word → PDF ont été produits avec un vrai moteur.

### Vérifié dans un navigateur
- Paramètres :
  - recherche « toler » ;
  - enregistrement de la tolérance ;
  - choix d'Ollama pour les questions sur la GED ;
  - test de connexion refusé en mode hors ligne ;
  - ajout d'un utilisateur Comptable ;
  - sauvegarde manuelle ;
  - niveaux des contrôles et documents attendus.
- Exports :
  - Word et PDF depuis l'éditeur ;
  - états financiers Excel et dossier annuel ZIP depuis les rapports annuels.
- Rendu des fichiers Word (FR et AR) et PDF contrôlé page par page.

### Points à valider
1. **Moteur PDF sous Windows** : vérifier qu'Edge imprime correctement sur le poste de l'AFMI. Pour le
   **PDF/A**, installer LibreOffice (gratuit), ou indiquer s'il faut un autre outil (Ghostscript, par exemple).
2. **Notes de bas de page dans le PDF** : avec le moteur navigateur, elles sont regroupées en fin de document. Elles
   sont en bas de page dans Word et dans le PDF produit par LibreOffice.
3. **Rôles** : ils protègent les modules Smart Office. Les écrans de l'application de bureau (Trésorerie…) ne sont
   pas encore restreints. Faut-il le faire au Lot 8 ?
4. **Prix de l'IA** : le plafond de coût n'agit que si vous saisissez les prix par million de jetons de chaque
   fournisseur. Aucun prix n'est préréglé.
5. **Alertes par e-mail** : les préférences sont enregistrées, mais l'envoi automatique des alertes (échéances,
   trésorerie) reste à brancher au Lot 8. Les rapports programmés existants (SMTP) sont inchangés.
6. **Tableaux Excel** : la présentation du CER reste provisoire, en attente du modèle de l'expert-comptable (Q3, Q4).

## [2.0.0 — Lot 6 : GED et cycle de vie des projets] — 11/11/2026

Nouveau menu Smart Office : **Documents & cycle de vie**. La GED reprend la table de documents de l'application de
bureau : il n'y a qu'un seul dossier documentaire par projet, partagé entre les deux interfaces.

### Ajouté
- **Import et analyse** : PDF natif ou scanné (OCR local), Word .docx, Excel, texte, images, à l'unité ou par lot.
  Chaque document est :
  - archivé (empreinte SHA-256 ; un même fichier ne peut pas être importé deux fois dans un projet) ;
  - **classé** par type (convention, avenant, budget, cadre logique, termes de référence, document de projet, étude,
    rapport narratif, financier, final ou d'évaluation, procès-verbal, facture, contrat, liste de présence,
    correspondance), avec une confiance affichée ; un type peu sûr est surligné et le type reste modifiable ;
  - **rattaché à une phase** : identification, formulation, contractualisation, mise en œuvre, suivi, clôture,
    évaluation ;
  - **analysé** : dates (numériques et en toutes lettres), montants et devises, parties (« ci-après dénommé »),
    durée, dates de début, de fin et de signature, langue.
- **Obligations de reporting** déduites des conventions :
  - phrases mentionnant des rapports et des échéances, dates explicites, périodicité (trimestrielle, semestrielle,
    annuelle) avec délai (« dans les 30 jours »), rapport final ;
  - proposées avec la **phrase source**, puis confirmées, saisies ou supprimées par l'utilisateur ;
  - un rapport importé solde la prochaine échéance confirmée du même type, ou l'échéance est soldée explicitement par
    un document choisi.
- **Frise du cycle de vie** : phases atteintes (déduites du statut, des dates et des documents), jalons (saisis),
  rapports dus (remis, à venir, en retard, proposés), tranches de financement, fin de convention, documents, repère
  « aujourd'hui ».
- **Documents attendus par phase** (configurables dans `config/lifecycle_config.json`), avec la liste des documents
  reçus et manquants.
- **Alertes** : rapport en retard, rapport à remettre sous 30 jours, échéances à confirmer, document attendu absent,
  convention ou contrat arrivant à échéance sous 60 jours.
- **Recherche** :
  - plein texte (SQLite FTS5, insensible aux accents, extraits surlignés) ;
  - **sémantique** quand un modèle d'embeddings est disponible : Ollama local (`nomic-embed-text`), ou Gemini si
    l'IA externe est autorisée, avec masquage ;
  - fusion des deux classements.
- **Questions en langage naturel** sur les documents d'un projet. Chaque réponse cite ses sources [n] (document, page,
  extrait). Sans modèle d'IA, la réponse est extractive : les passages pertinents sont cités tels quels.
- **Documents existants** (importés dans l'application de bureau) : bouton « Analyser les documents existants »
  (texte relu, classement, métadonnées, index). La migration reclasse aussi leurs anciennes catégories et phases.
- **Mémoire institutionnelle** : les agents IA reçoivent le résumé des documents de référence (conventions, rapports
  finaux, évaluations).
- **Migration `DocumentManagement`** :
  - colonnes de GED et suppression logique sur `Documents` (une suppression depuis l'application de bureau est
    désormais logique) ;
  - tables `ReportingObligations`, `ProjectMilestones`, `DocumentChunks` et index FTS5 synchronisé par
    déclencheurs ;
  - testée sur une base 1.3.0.
- Tests : 80 xUnit, 120 pytest.

### Vérifié dans un navigateur
- Import de 3 documents :
  - convention PDF → « Convention », 4 échéances proposées (30/07/2026, 30/01/2027, 30/07/2027, rapport final le
    29/08/2027) ;
  - rapport Word → « Rapport narratif » ;
  - procès-verbal **scanné** → « Procès-verbal », grâce à l'OCR.
- Phase atteinte « Suivi », alertes, confirmation d'une échéance, frise.
- Recherche « plantation mars » (trouve le PV scanné) et question citant la convention.

Ces essais ont fait apparaître deux défauts, corrigés : un calcul d'échéance décalé d'un mois, et l'impossibilité de
solder une échéance par un rapport importé avant sa confirmation.

### Points à valider
1. **Documents attendus par phase** : la liste par défaut est une proposition. À ajuster avec vos procédures et les
   exigences de vos bailleurs (`lifecycle_config.json`).
2. **Obligations de reporting** : elles sont déduites par règles des formulations courantes des conventions. Une
   formulation inhabituelle peut échapper à l'analyse ; vérifiez toujours avec la convention (la phrase source est
   affichée).
3. **Recherche sémantique** : elle nécessite Ollama avec `nomic-embed-text` sur le poste (ou l'IA externe autorisée).
   Sinon, seule la recherche plein texte fonctionne.
4. **Ancien format Word (.doc)** : il n'est pas analysé ; convertissez-le en .docx ou en PDF.

## [2.0.0 — Lot 5 : Rapports annuels moral et financier] — 11/11/2026

Nouveaux menus Smart Office : **Rapports annuels** et **Indicateurs & bénéficiaires**. Le rapport est généré à partir de
toutes les données de l'exercice, puis ouvert dans l'éditeur pour relecture et personnalisation.

### Ajouté
- **Assistant de génération** :
  - exercice, périmètre (association entière, programme et ses sous-projets, projet, bailleur), type de rapport
    (complet, moral, financier), langue (français, arabe en RTL, anglais), modèle de mise en page ;
  - synthèse IA en option ;
  - contrôles de cohérence affichés avant la génération.
- **Contrôles de cohérence**, avec un niveau paramétrable par contrôle (`config/financial_report_layout.json`) :
  - **bloquants** par défaut : opérations en brouillon sur l'exercice, virement interne incomplet, taux de change
    manquant ;
  - **avertissements** par défaut : écritures sans catégorie, comptes non rapprochés au 31/12, dépenses de 1 000 MAD
    ou plus sans justificatif, indicateurs sans mesure datée.
- **Rapport moral** :
  - synthèse chiffrée établie à partir des données (toujours traçable) et, en option, synthèse rédigée par l'IA à
    partir des seuls faits, avec la liste des chiffres absents des données ;
  - projets de l'exercice (objectifs, bailleur, statut, période, avancement) ;
  - activités ; indicateurs GAR (niveau, référence, cible, réalisé de l'exercice, taux) ; bénéficiaires par sexe,
    tranche d'âge et zone ; partenaires ; faits marquants ; difficultés (rapports d'activité, leçons apprises) ;
    perspectives ;
  - galeries photos par projet sur la période (consentement obligatoire).
- **Rapport financier** (présentation **provisoire**, en attendant le référentiel de l'expert-comptable) :
  - **compte d'emploi des ressources** paramétrable : sections, catégories, détail des emplois par projet et des
    subventions par bailleur ;
  - recettes et dépenses par nature et par projet, fonctionnement compris ;
  - exécution budgétaire (prévu, réalisé, écart, taux) par projet et par bailleur ;
  - trésorerie au 31/12 par compte (contre-valeur MAD) avec l'état de rapprochement ;
  - **fonds reçus non utilisés et reports** par convention (reçu et utilisé sur l'exercice et en cumul). Leur
    traitement comptable reste à valider ;
  - comparaison avec l'exercice N-1, graphique d'évolution, camemberts des ressources et des emplois ;
  - rappel des contrôles en fin de rapport.
- Les tableaux du rapport sont des **blocs dynamiques** (exercice, périmètre, langue) : ils se recalculent à chaque
  ouverture. Chaque tableau porte un format par colonne, pour un affichage en format français à l'écran comme à
  l'impression.
- **Indicateurs GAR** :
  - niveau (impact, effet, extrant), valeur de référence, mode de cumul (somme ou dernière mesure) ;
  - **mesures datées et désagrégées** (sexe, tranche d'âge, zone, source) ;
  - la valeur courante, affichée dans l'application de bureau, suit les mesures ;
  - migration `ResultsIndicators`.
- **Ventilation multiple** dans la Trésorerie (point 1 du Lot 2) :
  - une opération peut être répartie sur plusieurs projets ou lignes budgétaires ;
  - « Répartir selon les clés » utilise les liaisons du compte (projet unique ou pourcentages) et choisit la ligne de
    la catégorie quand elle est unique ;
  - le reste à ventiler s'affiche pendant la saisie.
- **Reprise des photos des anciens rapports d'activité** (point 6 du Lot 4) : les photos sont reprises avec leur
  légende ; le consentement est à confirmer, et relancer la reprise ne crée pas de doublon.
- **Scénario commun .NET / Python** (`SharedTestCases/annual_scenario.json`) : multi-ventilations avec arrondis,
  devise étrangère, restitution, avoir, virement interne, relevé et rapprochement. Les états Python et
  `FinanceService` / `ReconciliationService` donnent exactement les mêmes totaux.
- Tests : 77 xUnit, 112 pytest.

### Vérifié dans un navigateur
Assistant, contrôles, rapport annuel complet de 6 pages : 13 blocs alimentés, 2 camemberts, compte d'emploi juste
(74 500 − 28 000 = 46 500 MAD). Rapport moral en arabe (RTL) pour un projet. Saisie des indicateurs. Corrigés au
passage : titres en double, légende du graphique N-1, lignes vides de la comparaison, libellé du périmètre non
traduit.

### Points à valider
1. **Référentiel comptable (Q3, Q4)** : le compte d'emploi des ressources et la présentation des états sont
   provisoires. Avec le plan de comptes et le modèle de votre expert-comptable, il suffira de modifier
   `financial_report_layout.json`, sans programmation.
2. **Fonds dédiés** : le tableau « fonds reçus non utilisés » présente le reçu et l'utilisé par convention. La
   comptabilisation en fonds dédiés ou en produits constatés d'avance est à confirmer.
3. **Lignes budgétaires pluriannuelles** (sans exercice) : le réalisé présenté est cumulé depuis le début. Pour un
   budget annuel, rattachez les lignes à l'exercice (exercices au Lot 7, paramètres).
4. **Niveaux des contrôles** : faut-il garder les comptes non rapprochés en avertissement, ou les rendre bloquants
   pour le rapport financier présenté à l'assemblée générale ?
5. **Ventilation multiple (écran WPF)** : compilée et liaisons vérifiées par script, mais pas testée visuellement.
   À essayer sous Windows.

## [2.0.0 — Lot 4 : Éditeur, chartes graphiques, photos] — 11/11/2026

Trois nouveaux menus dans Smart Office : **Éditeur de documents**, **Chartes & modèles**, **Photos des activités**.
Éditeur retenu : **TipTap 2.27.3** (licence MIT, décision D3). Toutes les versions `@tiptap/*` sont figées et
alignées par des `overrides`, pour éviter le mélange de versions qui casse la compilation.

### Ajouté
- **Éditeur de documents** :
  - page A4 avec les marges, les couleurs et les polices de la charte ;
  - styles de titres, polices, tailles, couleur, surlignage, gras, italique, souligné, barré, indice, exposant ;
  - alignements, listes, citations ;
  - tableaux : ajout et suppression de lignes et de colonnes, fusion et scission de cellules, ligne d'en-tête,
    trame des cellules, colonnes redimensionnables ;
  - images, sauts de page, bloc en 2 colonnes, notes de bas de page numérotées ;
  - table des matières automatique, numérotation des titres en option (1, 1.1, 1.1.1) ;
  - champs dynamiques : date, projet, code du projet, bailleur, association, titre ;
  - sens d'écriture par paragraphe : documents arabes (RTL) et mixtes français/arabe ;
  - enregistrement automatique 8 s après la dernière frappe, et Ctrl+S.
- **Blocs dynamiques**, recalculés depuis la base à l'ouverture et sur « Actualiser » :
  - tableau budgétaire (prévu, réalisé, écart, taux, réalisé net des avoirs) ;
  - indicateurs (cible, réalisé, taux) ;
  - activités de la période ;
  - graphique « prévu / réalisé » en SVG, sans bibliothèque ;
  - galerie photos : 1 à 4 par ligne, numérotation « Photo n° X », légende et crédit, sélection automatique,
    photos réordonnables et retirables.
- **Révision** : mode révision (ajouts soulignés en vert, suppressions barrées en rouge, avec auteur et date),
  acceptation ou refus d'une modification ou de toutes. Retirer son propre ajout le supprime vraiment.
- **Commentaires** ancrés sur un passage, avec liste, navigation et résolution. **Versions** enregistrées avec une
  note ; à la restauration, l'état courant est d'abord conservé comme version.
- **Assistant IA dans l'éditeur** : reformuler, résumer, traduire (arabe, français, anglais), rédiger une section à
  partir des données du projet.
  - seuls les faits de la base sont fournis au modèle ;
  - les chiffres du texte absents de ces faits sont signalés ;
  - les règles de confidentialité s'appliquent, et le mode hors ligne est indiqué clairement.
- **Aperçu paginé et impression ou PDF** :
  - pagination A4 ;
  - en-têtes et pieds de page avec logos, première page différente, pages paires et impaires, « Page n / N » ;
  - mentions obligatoires en pied de page, notes en fin de document ;
  - version finale imprimée (suppressions en révision masquées, ajouts intégrés) ;
  - techniquement : règles CSS `@page` et boîtes de marge de Chromium/WebView2.
- **Chartes graphiques** avec héritage **association → fiche du bailleur (couleur, logo, mentions, textes saisis dans
  l'application de bureau) → charte du bailleur → charte du projet** :
  - couleurs, polices, taille, marges, logos sur 7 positions, en-têtes et pieds de page, mentions obligatoires
    (cumulées), style des tableaux, photos par ligne ;
  - la charte effective d'un projet et sa chaîne d'héritage sont affichées.
- **Modèles** : enregistrer un document comme modèle, dupliquer, partager ou rendre personnel, supprimer. Un modèle de
  base « Rapport d'activité » est proposé, avec titres, champs et blocs.
- **Photos** :
  - import par lot, avec date et GPS lus dans l'EXIF ;
  - archivage de l'original (SHA-256) et version allégée (2000 px) pour les documents ;
  - activité liée, légende, crédit, consentement au droit à l'image ;
  - légende proposée par un modèle de vision, à valider, jamais inventée si aucun modèle n'est disponible ;
  - sélection automatique pour un rapport : consentement obligatoire, légendes validées d'abord, jours variés.
- **Migration `EditorChartsAndPhotos`** (6 tables), réversible. Les écritures sont journalisées, et le journal résume
  les contenus longs.
- 7 tests pytest supplémentaires (105 au total).

### Vérifié dans un navigateur (Playwright, Chromium)
Parcours complet sur une association fictive :
- création d'un rapport (5 blocs alimentés, 4 photos), saisie, paragraphe arabe ;
- révision (ajout, suppression, tout accepter), commentaire, tableau, note, version ;
- aperçu paginé converti en PDF de 3 pages : logo du bailleur en en-tête, mention obligatoire en pied de page,
  pas de numéro sur la première page, « Page 2 / 3 » ensuite.

Ces essais ont fait apparaître trois défauts, corrigés : numéro de page sur la première page, taux au format
anglais, table des matières numérotée par erreur.

### Points à valider
1. **Fidélité de l'impression** : la pagination et les en-têtes s'appuient sur Chromium. Le WebView2 de Windows est
   à jour sur Windows 10 et 11 ; un rendu identique sous Word viendra avec l'export .docx (Lot 7).
2. **Notes de bas de page** : elles sont regroupées en fin de document à l'impression, car Chromium ne sait pas les
   placer en bas de chaque page. L'export .docx (Lot 7) les placera en bas de page.
3. **Numéros de page dans la table des matières** : non disponibles à l'impression (limite de Chromium). Ils le seront
   dans l'export .docx, avec le champ TOC de Word.
4. **Révision** : version simplifiée. Le texte tapé, effacé ou collé est suivi ; les changements de mise en forme et
   les fusions de paragraphes ne le sont pas. Il n'y a pas de co-édition simultanée.
5. **Arabe** : les polices Amiri ou Noto Naskh Arabic sont proposées, mais elles doivent être installées sur le poste.
   Leur intégration dans l'installateur est à prévoir au Lot 8.
6. **Anciennes photos des rapports d'activité** (application de bureau) : elles ne sont pas reprises automatiquement
   dans la galerie. Je propose une reprise au Lot 5.

## [2.0.0 — Lot 3 : Lecture intelligente des relevés] — 11/11/2026

Nouveau menu **Smart Office → Relevés bancaires**. La lecture se fait **sur le poste** (OCR Tesseract) ; l'IA n'est
qu'un recours facultatif, soumis aux paramètres de confidentialité du Lot 1.

### Ajouté
- **Import** à l'unité ou par lot : PDF natif, PDF scanné, JPG, PNG, TIFF, CSV, Excel. Les photos de plusieurs pages
  d'un même relevé peuvent être regroupées (« les pages d'un même relevé »).
- **Pipeline** (`SmartOffice/backend/tools/statements/`) :
  1. prétraitement (OpenCV) : redressement par profil de projection, débruitage, contraste local, mise à
     300 dpi ;
  2. OCR Tesseract (français), avec position et confiance de chaque mot. Les PDF natifs sont lus directement, sans
     OCR ;
  3. détection de la banque par gabarits configurables (`config/bank_templates.json` : Banque Populaire,
     Attijariwafa bank, Bank of Africa, CIH, Crédit Agricole du Maroc, Société Générale, générique) ;
  4. extraction structurée :
     - colonnes repérées sur l'en-tête, lignes commençant par une date, libellés sur plusieurs lignes ;
     - montants à milliers séparés recollés, confusions O/0 et l/1 corrigées ;
     - soldes initial et final, période, RIB (clé contrôlée) ;
     - pages multiples, en-tête répété ignoré ;
  5. **seconde lecture** si l'équilibre des soldes échoue. Un montant n'est corrigé que si une seule correction
     rétablit l'équilibre ; il est alors surligné pour vérification ;
  6. **IA en option**, seulement si la lecture OCR ne s'équilibre pas et que l'utilisateur l'a cochée. Le résultat
     n'est retenu que s'il équilibre les soldes.
- **Contrôles bloquants** : solde initial + mouvements = solde final, relevé déjà importé (même fichier, ou même
  période et même solde), continuité avec le relevé précédent. Relevé manquant signalé.
- **Écran de validation** :
  - image du relevé à côté du tableau extrait ;
  - champs à faible confiance surlignés ;
  - un clic sur une ligne la repère sur l'image ;
  - correction des dates, libellés, montants et soldes, ajout ou suppression de lignes ;
  - écart de soldes recalculé en direct. La validation reste impossible tant qu'un écart subsiste.
- **Catégorisation** :
  - règles saisies, règles apprises des corrections de l'utilisateur (la correction d'une catégorie ou d'une
    imputation est mémorisée et reproposée), puis règles de base prudentes (frais bancaires, salaires et CNSS,
    loyer, déplacements, subventions, dons, cotisations, intérêts, prestations) ;
  - projet proposé d'après les liaisons du compte ;
  - ligne budgétaire proposée si elle est unique pour ce projet et cette catégorie.
- **Anomalies** : frais bancaires inhabituels (au-delà de 3 fois la médiane de l'historique, ou de 500 MAD sans
  historique), dépassement d'une ligne budgétaire (en cumul), dépense de 1 000 MAD ou plus sans justificatif, ligne
  en double, champs peu sûrs.
- **Intégration** (après validation explicite) : une opération en **brouillon** par ligne, avec l'imputation
  proposée. Elle est à ventiler et valider dans la Trésorerie, qui applique toutes les règles de `Core/Finance`.
  - une ligne déjà comptabilisée (même montant, à ± 3 jours) n'est pas dupliquée ;
  - relancer l'intégration ne crée aucun doublon.
- **Archivage** : le fichier source est conservé, identifié par son SHA-256 et lié au relevé ; les images des pages
  sont conservées pour la relecture. Toutes les écritures sont journalisées dans `AuditEntries`.
- **Mesure de précision** :
  - générateur déterministe de relevés de test (`SmartOffice/tests/tools/statement_fixtures.py`) : 3 mises en page,
    chacune en PDF natif, en scan (inclinaison ±2°, bruit, flou, JPEG) et en photo difficile (3 à 4,5°,
    150 dpi, éclairage inégal) ;
  - banc de mesure (`tests/tools/statement_accuracy.py`) et dossier `backend/tests/fixtures/releves/` pour les vrais
    relevés, évalués automatiquement dès qu'ils sont déposés.
- 27 tests pytest (98 au total), dont un parcours complet vérifié dans un navigateur (Playwright) : import d'un scan,
  correction, contrôle de l'écart, validation, intégration.

### Résultats mesurés
| Jeu | Lignes correctes | Soldes corrects |
|---|---|---|
| Relevés **synthétiques** (6 PDF natifs, 6 scans, 3 photos difficiles) | **270/270 (100 %)** | 15/15 |
| **Vrais relevés de l'AFMI** | **non mesuré : aucun relevé fourni** | — |

Le critère d'acceptation (≥ 95 % sur `fixtures/releves/`) est automatisé, mais il ne vaut que pour des relevés que
j'ai moi-même générés. Les mises en page réelles des banques marocaines, les tampons, le papier froissé ou les
colonnes alignées différemment ne sont pas encore éprouvés.

### Points à valider
1. **Relevés réels anonymisés** : 2 à 3 par banque utilisée, à déposer dans `SmartOffice/backend/tests/fixtures/releves/`
   avec leur vérité terrain (le format est décrit dans le README du dossier). C'est la seule façon de mesurer
   réellement les 95 %.
2. **Seuils d'anomalies** : frais inhabituels (3 × la médiane, ou 500 MAD) et justificatif attendu dès 1 000 MAD.
   Ils seront paramétrables au Lot 7.
3. **Tesseract dans l'installateur Windows** : à intégrer au Lot 8, avec les langues fra et ara (environ +70 Mo).
   D'ici là, il faut l'installer à part ou renseigner `AFMI_TESSERACT`. Sans lui, seuls les PDF natifs, CSV et Excel
   sont lus.
4. **Arabe** : la reconnaissance est réglée sur le français, la langue des relevés bancaires marocains courants.
   Un relevé entièrement en arabe nécessitera un réglage du gabarit.

## [2.0.0 — Lot 2 : Banque et trésorerie] — 10/11/2026

Nouveau menu **🏦 Trésorerie** dans l'application de bureau. Toutes les règles de calcul sont dans `Core/Finance`
et testées (76 tests .NET) ; l'écran ne fait qu'appeler ces services.

### Décisions prises (points à valider du Lot 1, tranchés par délégation)
| Point | Décision |
|---|---|
| Remboursements et avoirs | Pas de nouvelle nature : une **recette au débit** (restitution à un bailleur) et une **dépense au crédit** (avoir, remboursement fournisseur) sont admises et viennent **en diminution** des recettes ou des dépenses. Case « Contre-passation » dans la saisie. |
| Arrondi des conversions | Conservé : au centime, arrondi commercial (0,5 au-dessus), sur la contre-valeur de chaque opération. |
| Clé RIB | Reste un avertissement tant qu'elle n'est pas confirmée sur de vrais RIB. |
| Natures de dépenses | 9 catégories génériques, modifiables, sans rattachement comptable imposé : personnel, achats, prestations et honoraires, déplacements, loyers, communication, frais bancaires, équipements, autres. |
| Reprise de Smart Office 1.x | Bouton dédié : transactions reprises en **brouillons** sur un compte choisi, projets manquants recréés, aucune duplication en cas de relance. |

### Ajouté
- **Comptes :**
  - création et modification, avec contrôle du RIB ;
  - typologie : fonctionnement, dédié projet, dépôt ;
  - seuil d'alerte « solde bas » ;
  - clôture, refusée si le solde n'est pas nul ;
  - solde du jour et solde consolidé en MAD.
- **Liaisons comptes ↔ projets :**
  - période de validité ;
  - clé de répartition en % ou en montant, refusée au-delà de 100 % et pour un même projet sur une période qui
    chevauche ;
  - proposition automatique du projet à la saisie d'une opération.
- **Opérations :** recette, dépense ou contre-passation, avec imputation (projet ou fonctionnement, ligne budgétaire,
  catégorie). Une opération est soit un brouillon, soit validée, et sa suppression est logique. Une opération
  rapprochée ne peut pas être supprimée.
- **Virements internes :** même devise, ou devises différentes avec le montant reçu. Ils sont exclus des recettes et
  des dépenses.
- **Budget et conventions :**
  - lignes budgétaires par projet ou pour le fonctionnement, avec le réalisé en MAD et le taux d'exécution ;
  - conventions par bailleur (taux contractuel facultatif) et échéanciers de tranches ;
  - rattachement d'une tranche à la recette qui l'encaisse ;
  - saisie des taux de change datés.
- **Rapprochement bancaire :**
  - import d'un relevé CSV de la banque : séparateur et colonnes détectés, formats français et ISO, débit/crédit ou
    montant signé, encodages UTF-8 et Windows-1252 ;
  - contrôles : solde initial + mouvements = solde final, relevé déjà importé, continuité avec le relevé précédent,
    relevé manquant ;
  - rapprochement automatique (même montant, date à ± N jours, libellé approchant). Un cas ambigu n'est **jamais**
    rapproché automatiquement ;
  - rapprochement manuel, et son annulation ;
  - **état de rapprochement** : solde bancaire rectifié, solde comptable, écart inexpliqué. Export PDF et CSV
    (Excel), nom de fichier `AFMI_EtatRapprochement_<compte>_<date>`.
- **Prévision de trésorerie** sur 3, 6 ou 12 mois, mois par mois, en MAD :
  - encaissements : tranches non reçues (une tranche en retard est comptée le premier mois) ;
  - décaissements : reste à consommer des lignes budgétaires, réparti uniformément jusqu'à la fin du projet ou de
    l'exercice ;
  - point bas et hypothèses affichés.
- **Alertes :** solde négatif ou bas, compte projet sans mouvement depuis 90 jours, écart de rapprochement, lignes non
  rapprochées, virement orphelin, tranche en retard, brouillons à valider.
- **Migration `BankingAndReconciliation` :** relevés, lignes, rapprochements, seuil d'alerte et catégories de
  dépenses. Elle est sauvegardée et réversible comme les précédentes.

### Points à valider
1. **Ventilation multiple à l'écran.** Le moteur sait répartir une opération sur plusieurs projets (clés de
   répartition), mais la saisie à l'écran ne propose qu'une imputation par opération. Pour l'instant, il faut
   saisir une opération par projet. Je propose la saisie multi-lignes au Lot 5, avec la répartition des frais de
   fonctionnement.
2. **Hypothèse de prévision :** reste à consommer étalé uniformément jusqu'à la fin du projet. Si vos plans de
   décaissement sont plus précis (par trimestre, par activité), on pourra les saisir plus tard.
3. **Rapprochement un pour un :** une remise de plusieurs chèques en une seule ligne bancaire n'est pas encore gérée.
4. **Paramètres par défaut :** tolérance de date de 3 jours, compte projet « inactif » après 90 jours. Ils seront
   modifiables au Lot 7.
5. **Import CSV :** les soldes initial et final sont à saisir, car les exports bancaires ne les contiennent souvent
   pas. Au Lot 3, ils seront lus sur le relevé PDF ou scanné.
6. **Écran non vérifié visuellement.** Il compile, et toutes ses liaisons de données correspondent à une propriété
   existante (vérifié par un script), mais je ne peux pas lancer WPF dans mon environnement. **Merci de l'essayer
   sous Windows** et de me signaler tout problème d'affichage ou de saisie.

## [2.0.0 — Lot 1 : Fondations] — 10/11/2026

Base de la version 2.0 : socle de données financières, migrations, journal d'audit et sécurité.
Aucun écran financier n'est encore livré (Lot 2). Plan complet : [docs/v2/ANALYSE.md](docs/v2/ANALYSE.md).

### Ajouté
- **Bibliothèque `Core/`** (net9.0, sans WPF) : entités, `AppDbContext`, migrations et règles de calcul,
  testable sur tout système. Projet de tests **`Core.Tests`** (52 tests xUnit).
- **Migrations EF Core** à la place de `EnsureCreated` et des `ALTER TABLE` ignorés en cas d'erreur :
  - `Baseline_1_3_0` : schéma 1.3.0. Une base existante est complétée puis marquée comme déjà à ce niveau ;
  - `LegacyAmountsInClear` puis `DecryptLegacyAmounts` : montants hérités remis en clair (voir *Modifié*) ;
  - `FinanceFoundation` : nouvelles tables financières et journal d'audit.
- **Sauvegarde automatique avant migration** : copie cohérente (API de sauvegarde SQLite) dans
  `%LocalAppData%\AFMIGestionProjet\backups\`, 30 dernières conservées. Un échec de migration arrête
  l'application avec un message, sans travailler sur une base incohérente.
- **Modèle financier** (montants en centimes, jamais en `double`) :
  - comptes bancaires et caisse, avec typologie et statut ;
  - liaisons comptes ↔ projets, avec période et clé de répartition ;
  - opérations et ventilations (projet ou fonctionnement, ligne budgétaire, catégorie) ;
  - catégories et plan de comptes paramétrables ;
  - conventions de financement et tranches ;
  - lignes budgétaires, exercices, taux de change datés ;
  - fichiers archivés (SHA-256), justificatifs, règles de catégorisation, paramètres.
- **Règles financières** (`Core/Finance`) :
  - solde à une date (ouverture + crédits − débits) et solde consolidé en MAD ;
  - virements internes appariés, exclus des recettes et des dépenses ;
  - validation d'une opération : ventilation exacte, ligne budgétaire du bon projet, devise du compte, dates du compte ;
  - conversion de devises au taux daté. Un taux manquant bloque l'opération ; il n'est jamais deviné ;
  - répartition au plus fort reste, sans centime perdu ;
  - contrôle de la clé du RIB marocain.
- **Contraintes en base** : montants positifs, cohérence des virements, unicité RIB / exercice / taux.
- **Journal d'audit** (`AuditEntries`) :
  - toute création, modification ou suppression est tracée (qui, quand, quoi, ancienne et nouvelle valeur),
    dans la même transaction que la donnée ;
  - le journal est en ajout seul, protégé par des déclencheurs SQLite ;
  - chaque entrée est chaînée par une empreinte SHA-256, ce qui rend toute falsification détectable ;
  - les secrets n'y apparaissent jamais.
- **Suppression logique** : projets, dépenses, comptes, opérations, conventions, tranches et lignes budgétaires.
  Supprimer un projet ne supprime plus ses tâches, ses dépenses ni son historique.
- **Paramètres partagés** Desktop/backend (table `AppSettings`, `SettingsService`). Les secrets y sont chiffrés
  par DPAPI.
- **Backend → base unique** (`backend/core/unified_db.py`) : lecture et écriture sans toucher au schéma.
  Chaque écriture est journalisée avec la même chaîne d'empreintes que le Desktop.
- **Confidentialité de l'IA** :
  - l'IA externe est **désactivée par défaut** ;
  - le masquage du RIB, de l'IBAN, de l'ICE, de l'IF, de la CIN, du n° CNSS et des salaires avant envoi est
    **activé par défaut** ;
  - une image scannée n'est jamais envoyée à l'extérieur quand le masquage est actif ;
  - réglage dans Smart Office → Mémoire institutionnelle → paramètres IA.
- **Jeton de session de l'API locale** : généré par le Desktop à chaque démarrage. Les autres programmes du poste ne
  peuvent plus appeler le backend.
- **Clé Gemini conservée chiffrée** (DPAPI) dans la base unique ; elle était perdue à chaque redémarrage.
- **Vecteurs de tests partagés** .NET/Python (`SharedTestCases/` : RIB, empreinte d'audit, répartition) et script
  de schéma pour les tests Python (`SmartOffice/tests/fixtures/unified_schema.sql`, dont l'actualité est vérifiée).
- **Intégration continue** GitHub Actions sous Windows : build, tests .NET et Python, migrations à jour, frontend.

### Modifié
- **Montants hérités en clair.** L'ancien chiffrement AES utilisait une clé écrite dans le code : il ne protégeait
  rien et empêchait tout calcul en base. La migration les déchiffre après sauvegarde, et une valeur illisible
  arrête la migration. Les champs hérités (budgets et coûts de projets) restent en `double` pour ne pas toucher
  aux écrans existants ; les flux réels passent désormais par les opérations, en centimes.
- **Base surchargeable** par la variable `AFMI_DESKTOP_DB`. Les tests Desktop et Python n'utilisent plus jamais la
  base réelle de l'utilisateur, alors qu'auparavant `Desktop.Tests` l'ouvrait.
- **Import d'une base** (menu Desktop) : la base importée est migrée immédiatement. En cas d'échec, l'ancienne base
  est restaurée.
- Le backend reçoit du Desktop le chemin de la base unique et l'utilisateur à inscrire dans le journal d'audit.

### Sécurité
- Corrigé : S1 (clé AES en dur), S2 (RIB, ICE et IF envoyés à Gemini), S3 (API sans authentification),
  S4 (clé Gemini non persistée de façon sûre), S5 (journal d'audit effaçable), S6 (suppressions physiques).
- Reste à traiter :
  - S7 : le RIB et l'ICE de `ngo_profile.json` sont-ils réels ?
  - chiffrement complet de la base (option SQLCipher, décision D2-b).

### Points à valider
1. **Sens des opérations :** une recette est toujours un crédit et une dépense toujours un débit. Comment
   enregistrer un remboursement à un bailleur, ou un avoir fournisseur ? Je propose une nature « Correction »
   au Lot 2.
2. **Arrondi des conversions de devises :** au centime, arrondi commercial (0,5 → au-dessus). Est-ce conforme à la
   pratique de votre comptable et de vos bailleurs ?
3. **Contrôle de la clé RIB :** il est implémenté, mais n'est encore vérifié que sur des vecteurs générés par la
   règle. Pouvez-vous confirmer sur 2 ou 3 RIB réels de l'AFMI ? Tant que ce n'est pas fait, une clé invalide reste
   un avertissement.
4. **Catégories préchargées :** seules les 5 catégories de recettes du cahier des charges (subventions,
   cotisations, dons, prestations, produits financiers) sont créées. Les natures de dépenses et le plan de comptes
   attendent le référentiel de votre expert-comptable (Q3).
5. **IA externe désactivée par défaut :** si vous utilisiez Gemini en 1.3.0, il faut cocher « Autoriser l'IA
   externe » dans les paramètres IA.
6. **Fusion des tables `projects` et `financial_transactions` de Smart Office :** elle est reportée au Lot 2,
   avec choix du compte de rattachement par l'utilisateur. Rattacher automatiquement d'anciennes transactions à
   un compte reviendrait à inventer une affectation.
7. **Mode WAL non activé :** les copies de base du Desktop (export, sauvegarde) copient un seul fichier, ce qui est
   incompatible avec le WAL. Les accès concurrents Desktop/backend s'appuient sur le verrouillage SQLite standard.
